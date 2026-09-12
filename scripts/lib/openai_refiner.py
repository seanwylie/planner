"""
OpenAI refiner: call API, validate against refinement schema, quality gate.
"""
import json
from pathlib import Path

import jsonschema

# Schema path relative to planner root
SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "templates"
    / "refinement.schema.json"
)


def load_schema() -> dict:
    """Load refinement schema."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _sanitize_issue_items(items: list[dict], prefix: str) -> list[dict]:
    """Fill missing required fields so items pass schema validation."""
    valid_risk = {"low", "medium", "high"}
    valid_category = {
        "correctness",
        "security",
        "performance",
        "cost",
        "ux",
        "maintainability",
        "testing",
        "docs",
        "rollout",
    }
    out = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        cc = (item.get("concrete_change") or "").strip()
        ac = (item.get("acceptance_criteria") or "").strip()
        if len(cc) < 10 or len(ac) < 5:
            continue
        fixed = dict(item)
        if not fixed.get("id") or not isinstance(fixed["id"], str):
            fixed["id"] = f"{prefix}-{i + 1}"
        if not fixed.get("area") or not isinstance(fixed["area"], str):
            fixed["area"] = "implementation"
        if not fixed.get("issue") or not isinstance(fixed["issue"], str):
            fixed["issue"] = (cc[:80] + "..") if len(cc) > 80 else cc
        if fixed.get("risk_level") not in valid_risk:
            fixed["risk_level"] = "medium"
        if fixed.get("category") not in valid_category:
            fixed["category"] = "maintainability"
        out.append(fixed)
    return out


def validate_review(review: dict) -> tuple[bool, str | None]:
    """Validate review against schema. Return (valid, error_msg)."""
    schema = load_schema()
    try:
        jsonschema.validate(instance=review, schema=schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)


def quality_gate(review: dict) -> tuple[bool, str | None]:
    """
    Reject schema-valid but low-signal reviews.
    Return (passed, error_msg).
    """
    score = review.get("overall_score")
    must_fix = review.get("must_fix") or []
    should_fix = review.get("should_fix") or []
    questions = review.get("questions") or []
    missing = review.get("missing_checklist_items") or []
    sr = review.get("spec_readiness") or {}
    vals = [sr.get(k) for k in ("backend", "frontend", "infra", "tests", "docs")]
    all_zero = all(v == 0 for v in vals if v is not None) and len(vals) == 5
    all_hundred = all(v == 100 for v in vals if v is not None) and len(vals) == 5
    all_empty = (
        len(must_fix) == 0
        and len(should_fix) == 0
        and len(questions) == 0
        and len(missing) == 0
    )

    if score is not None and all_empty and all_zero:
        return (
            False,
            "Low-signal: score present but all lists empty and readiness all 0",
        )
    if score is not None and all_empty and all_hundred and (score or 0) < 4:
        return (
            False,
            "Low-signal: score < 4 but all lists empty and readiness all 100 (likely cop-out)",
        )

    for item in must_fix:
        cc = (item.get("concrete_change") or "").strip()
        ac = (item.get("acceptance_criteria") or "").strip()
        if len(cc) < 20:
            return (
                False,
                f"must_fix item {item.get('id', '?')} has concrete_change < 20 chars",
            )
        if len(ac) < 15:
            return (
                False,
                f"must_fix item {item.get('id', '?')} has acceptance_criteria < 15 chars",
            )

    return True, None


def _parse_and_validate_review(text: str) -> tuple[dict | None, str | None]:
    """Parse JSON, normalize score/agreed, sanitize items, validate schema, quality gate. Return (review, error)."""
    try:
        review = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"
    score = review.get("overall_score")
    if isinstance(score, (int, float)) and score > 5 and score <= 100:
        review["overall_score"] = max(1, min(5, round(score * 5 / 100)))
    if not isinstance(review.get("agreed"), bool):
        review["agreed"] = bool(review.get("agreed"))
    review["must_fix"] = _sanitize_issue_items(review.get("must_fix") or [], "must")
    review["should_fix"] = _sanitize_issue_items(
        review.get("should_fix") or [], "should"
    )
    valid, err = validate_review(review)
    if not valid:
        return None, f"Schema validation failed: {err}"
    passed, qerr = quality_gate(review)
    if not passed:
        return None, f"Quality gate failed: {qerr}"
    return review, None


def call_openai(
    prompt: str,
    model: str = "gpt-4o-mini",
    schema_path: Path | None = None,
) -> tuple[dict | None, str | None]:
    """
    Call OpenAI or Bedrock; parse JSON, validate. Return (review_dict, error_msg).
    If model is a Bedrock id (e.g. anthropic.claude-3-5-sonnet-v2:0), uses AWS Bedrock Converse.
    """
    try:
        from planner.scripts.lib.bedrock_adapter import (
            invoke_converse,
            is_bedrock_model,
        )
    except ImportError:

        def is_bedrock_model(m):  # type: ignore[assignment]
            return False

    if is_bedrock_model(model):
        system = "Output valid JSON only. Follow the requested schema exactly."
        text, err = invoke_converse(model, system, prompt)
        if err:
            return None, err
        return _parse_and_validate_review(text)

    try:
        from openai import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        if not text:
            return None, "Empty response from OpenAI"
        return _parse_and_validate_review(text)
    except ImportError:
        return None, "openai package not installed"
    except Exception as e:
        return None, str(e)
