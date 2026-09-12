"""
Extract valid IDs from CHECKLIST.md.
Validate missing_checklist_items against valid IDs.
Optional autocorrect for trivial cases (whitespace).
"""
import re
from pathlib import Path

# Match table rows: | id | or | GEN-0 | or | ic-analytics-1 |
ID_PATTERN = re.compile(r"^\|\s*([A-Za-z0-9-]+)\s*\|")


def extract_ids_from_md(content: str) -> set[str]:
    """Extract checklist IDs from markdown table rows."""
    ids = set()
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip().strip("`") for p in line.split("|") if p.strip()]
        if len(parts) < 2:
            continue
        cand = parts[0]
        if cand == "ID":
            continue
        if re.match(r"^[A-Za-z0-9-]+$", cand):
            ids.add(cand)
    return ids


def load_valid_ids(planner_root: Path | str) -> set[str]:
    """Load all valid IDs from CHECKLIST.md."""
    root = Path(planner_root)
    ids = set()
    path = root / "CHECKLIST.md"
    if path.exists():
        ids.update(extract_ids_from_md(path.read_text(encoding="utf-8", errors="replace")))
    for i in range(11):
        ids.add(f"GEN-{i}")
    return ids


def autocorrect_id(id_val: str) -> str:
    """Trivial autocorrect: strip whitespace, normalize."""
    return id_val.strip()


def validate_missing_checklist_items(
    items: list[str],
    valid_ids: set[str],
    autocorrect: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Validate missing_checklist_items. Return (valid_items, invalid_items).
    If autocorrect, try trivial fixes before rejecting.
    """
    valid = []
    invalid = []
    for item in items:
        fixed = autocorrect_id(item) if autocorrect else item
        if fixed in valid_ids:
            valid.append(fixed)
        else:
            invalid.append(item)
    return valid, invalid
