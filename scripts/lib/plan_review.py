"""
Plan-only OpenAI review for consensus mode.

Calls OpenAI to score a plan 0-100 per category (same rubric as
scripts/operations/refine-plan.py) and return refinements. Used by
planner consensus loop for plan-phase review.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Rubric and categories aligned with refine-plan.py
PLAN_SCORE_CATEGORIES = (
    "clarity",
    "completeness",
    "executability",
    "ordering",
    "risk",
    "consistency",
    "testing",
    "docs",
)
VALID_PRIORITIES = frozenset({"must", "should", "consider"})

SCORING_RUBRIC = """
Scoring (0-100, integer). Higher = better. Score strictly; reserve 95+ for plans that truly meet the bar.

- clarity: 100 = unambiguous, anyone can follow; 0 = vague or contradictory. Deduct for missing definitions, unclear scope, jargon without explanation.
- completeness: 100 = nothing missing for execution (steps, edge cases, rollback); 0 = major gaps. Deduct for TBDs, missing error paths, or hand-waving.
- executability: 100 = an executor can do it as-written (paths, commands, acceptance criteria); 0 = not actionable. Deduct for missing details, unclear ownership, or unverifiable steps.
- ordering: 100 = dependencies and sequence are correct and explicit; 0 = wrong or undefined order. Deduct for missing prerequisites, circular deps, or unclear phase order.
- risk: 100 = risks identified and mitigated or accepted explicitly; 0 = unaddressed or hidden risk. Higher score = lower residual risk / better risk handling. Deduct for unmentioned failure modes, no rollback, or optimistic assumptions.
- consistency: 100 = aligns with repo patterns, naming, and existing systems; 0 = contradicts or ignores them. Deduct for reinventing patterns, wrong layering, or inconsistent style.
- testing: 100 = test strategy and acceptance criteria are clear and sufficient; 0 = untestable or no test plan. Deduct for missing test cases, no verification steps, or untestable success criteria.
- docs: 100 = docs/updates are specified and sufficient for handoff; 0 = no doc plan or unclear. Deduct for missing runbooks, no README updates, or undocumented decisions.
"""


def _load_env() -> None:
    if os.environ.get("OPENAI_API_KEY"):
        return
    try:
        from dotenv import load_dotenv

        # Project root: planner/scripts/lib -> project root
        root = Path(__file__).resolve().parent.parent.parent.parent
        if (root / ".env").exists():
            load_dotenv(root / ".env")
        if not os.environ.get("OPENAI_API_KEY") and (Path.home() / ".env").exists():
            load_dotenv(Path.home() / ".env")
    except ImportError:
        pass


def validate_plan_review_response(data: dict) -> str | None:
    """None if valid, else error message."""
    if not isinstance(data, dict):
        return "Response is not a JSON object"
    scores = data.get("scores")
    if not isinstance(scores, dict):
        return "scores must be an object with category keys and 0-100 values"
    for cat in PLAN_SCORE_CATEGORIES:
        if cat not in scores:
            return f"scores missing category: {cat}"
        v = scores[cat]
        if not isinstance(v, (int, float)) or v < 0 or v > 100:
            return f"scores[{cat}] must be a number 0-100"
    refs = data.get("refinements")
    if not isinstance(refs, list):
        return "refinements must be a list"
    required = {"category", "location", "issue", "suggestion", "priority"}
    valid_cats = set(PLAN_SCORE_CATEGORIES)
    for i, item in enumerate(refs):
        if not isinstance(item, dict):
            return f"refinements[{i}] is not an object"
        missing = required - set(item.keys())
        if missing:
            return f"refinements[{i}] missing: {missing}"
        cat = (item.get("category") or "").strip().lower()
        if cat not in valid_cats:
            return f"refinements[{i}] category must be one of: {sorted(valid_cats)}"
        p = (item.get("priority") or "").strip().lower()
        if p not in VALID_PRIORITIES:
            return f"refinements[{i}] priority must be must|should|consider"
    return None


def _parse_plan_review_response(
    text: str, cats: tuple[str, ...]
) -> tuple[dict | None, list | None, str | None]:
    """Parse JSON from response text and normalize scores/refinements. Returns (scores, refinements, error)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, None, f"Invalid JSON: {e}"
    err = validate_plan_review_response(data)
    if err:
        return None, None, err
    scores_raw = data.get("scores") or {}
    refinements = data.get("refinements") or []

    def _norm(v: object) -> int:
        if isinstance(v, int) and 0 <= v <= 100:
            return v
        if isinstance(v, (float, str)):
            try:
                n = int(float(v))
                return max(0, min(100, n))
            except (ValueError, TypeError):
                pass
        return 0

    scores = {k: _norm(v) for k, v in scores_raw.items() if k in PLAN_SCORE_CATEGORIES}
    for c in cats:
        if c not in scores:
            scores[c] = 0
    return scores, refinements, None


def call_openai_plan_review(
    plan_content: str,
    model: str,
    active_categories: tuple[str, ...] | None = None,
) -> tuple[dict | None, list | None, str | None]:
    """
    Call OpenAI or Bedrock to review a plan. Same rubric as refine-plan.py.
    If model is a Bedrock id (e.g. anthropic.claude-3-5-sonnet-v2:0), uses AWS Bedrock.

    Returns:
        (scores_dict, refinements_list, error_msg).
        On success: (scores_dict, refinements_list, None). scores_dict has 0-100 per category.
        On failure: (None, None, error_msg).
    """
    cats = active_categories if active_categories is not None else PLAN_SCORE_CATEGORIES
    cats_list = ", ".join(cats)

    system = (
        "You are a senior staff engineer reviewing an implementation plan. "
        "Output valid JSON only. Give detailed, substantive suggestions—not brief one-liners. "
        "Apply the scoring rubric strictly: 95+ only when the plan truly meets that category's bar."
    )
    user = (
        "Score this plan 0-100 for each of these categories (integer only): "
        + cats_list
        + ".\n"
        + SCORING_RUBRIC
        + "\n"
        "Return refinements: array of objects. Each object must have: category (one of "
        + cats_list
        + "), location (section/heading), issue (1-2 sentences), suggestion (short summary), priority (must | should | consider). "
        "Also include detailed suggestions—each 2-4 sentences—for:\n"
        "- technical_suggestion: implementation details, APIs, patterns, code-level changes\n"
        "- product_suggestion: UX, scope, acceptance criteria, user-facing impact\n"
        "- architectural_suggestion: structure, boundaries, integration points, dependencies\n\n"
        "Be substantive. Avoid one-line suggestions.\n\n"
        "Return a single JSON object with: scores (object with each category key and 0-100 value), "
        "refinements (array of objects with category, location, issue, suggestion, priority, technical_suggestion, product_suggestion, architectural_suggestion), "
        "optional summary (string).\n\n"
        "Plan:\n---\n" + plan_content + "\n---"
    )

    from planner.scripts.lib.bedrock_adapter import invoke_converse, is_bedrock_model

    if is_bedrock_model(model):
        text, err = invoke_converse(model, system, user)
        if err:
            return None, None, err
        return _parse_plan_review_response(text, cats)
    # OpenAI
    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        return None, None, "OPENAI_API_KEY not set"
    try:
        from openai import OpenAI
    except ImportError:
        return None, None, "openai package not installed"
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content
    if not text:
        return None, None, "Empty response from OpenAI"
    return _parse_plan_review_response(text, cats)
