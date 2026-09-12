"""
Render review JSON to human-friendly Markdown.
"""
from typing import Any


def render_review_md(review: dict[str, Any]) -> str:
    """Convert review JSON to markdown for review_vN.md."""
    lines = [
        "# Review",
        "",
        f"**Overall score:** {review.get('overall_score', 'N/A')}",
        f"**Agreed:** {review.get('agreed', 'N/A')}",  # noqa: E231
        "",
        "## Spec Readiness",
        "",
    ]
    sr = review.get("spec_readiness") or {}
    for k in ("backend", "frontend", "infra", "tests", "docs"):
        lines.append(f"- {k}: {sr.get(k, 'N/A')}")  # noqa: E231
    lines.extend(["", "## Must Fix", ""])
    for item in review.get("must_fix") or []:
        lines.append(
            f"- **{item.get('id', '?')}** ({item.get('area', '')}): {item.get('issue', '')}"  # noqa: E221,E231
        )
        lines.append(
            f"  - Change: {item.get('concrete_change', '')}"  # noqa: E221,E231
        )
        lines.append(
            f"  - Acceptance: {item.get('acceptance_criteria', '')}"  # noqa: E221,E231
        )
    lines.extend(["", "## Should Fix", ""])
    for item in review.get("should_fix") or []:
        lines.append(
            f"- **{item.get('id', '?')}** ({item.get('area', '')}): {item.get('issue', '')}"  # noqa: E221,E231
        )
    lines.extend(["", "## Questions", ""])
    for q in review.get("questions") or []:
        lines.append(f"- {q}")
    lines.extend(["", "## Missing Checklist Items", ""])
    for m in review.get("missing_checklist_items") or []:
        lines.append(f"- {m}")
    return "\n".join(lines)
