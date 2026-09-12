"""Optional bones discovery. Never required. Never a private gitlink."""

from __future__ import annotations

from pathlib import Path


def find_bones_root(planner_root: Path) -> Path | None:
    """Return a bones tree if the operator attached one.

    Checked in order:

    1. ``<planner>/bones/README.md`` — cloned or copied next to this tool
    2. ``<planner>/../bones/README.md`` — host project (the original layout)

    Missing is normal. Prompts then omit bones guidance.
    """
    for candidate in (planner_root / "bones", planner_root.parent / "bones"):
        if (candidate / "README.md").is_file():
            return candidate
    return None


def bones_available(planner_root: Path) -> bool:
    return find_bones_root(planner_root) is not None
