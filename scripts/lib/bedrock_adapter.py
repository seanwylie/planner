"""
AWS Bedrock adapter for planner consensus.

Invokes Bedrock Converse API for plan/spec review when model_id is a Bedrock
model (e.g. anthropic.claude-3-5-sonnet-v2:0). Uses default AWS credentials
(env, profile, or instance role). No API key; requires bedrock:InvokeModel.
"""
from __future__ import annotations


def is_bedrock_model(model_id: str) -> bool:
    """True if model_id is a Bedrock model (e.g. anthropic.claude-..., amazon.nova-...)."""
    if not model_id or not isinstance(model_id, str):
        return False
    s = model_id.strip()
    return (
        s.startswith("anthropic.") or s.startswith("amazon.") or s.startswith("meta.")
    )


def invoke_converse(
    model_id: str,
    system: str,
    user_content: str,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> tuple[str | None, str | None]:
    """
    Call Bedrock Converse API. Returns (response_text, error_msg).
    On success: (response_text, None). On failure: (None, error_msg).
    """
    try:
        import boto3
    except ImportError:
        return None, "boto3 not installed"

    try:
        client = boto3.client("bedrock-runtime")
        response = client.converse(
            modelId=model_id.strip(),
            messages=[{"role": "user", "content": [{"text": user_content}]}],
            system=[{"text": system}],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        )
    except Exception as e:
        return None, str(e)

    out = response.get("output") or {}
    msg = out.get("message") or {}
    content = msg.get("content") or []
    parts = []
    for block in content:
        if isinstance(block, dict) and "text" in block:
            parts.append(block["text"])
    text = "\n".join(parts).strip()
    if not text:
        return None, "Empty response from Bedrock"
    return text, None
