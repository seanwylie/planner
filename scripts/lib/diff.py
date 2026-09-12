"""
Plan diff utility. Compute what changed between plans.
"""
import difflib
from pathlib import Path


def diff_plans(plan_a: str, plan_b: str) -> str:
    """Return unified diff of two plan strings."""
    lines_a = plan_a.splitlines(keepends=True)
    lines_b = plan_b.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(lines_a, lines_b, fromfile="plan_a", tofile="plan_b")
    )


def diff_files(path_a: Path | str, path_b: Path | str) -> str:
    """Return unified diff of two files."""
    path_a = Path(path_a)
    path_b = Path(path_b)
    if not path_a.exists():
        return f"--- {path_a} (missing)\n"
    if not path_b.exists():
        return f"+++ {path_b} (missing)\n"
    return diff_plans(
        path_a.read_text(encoding="utf-8", errors="replace"),
        path_b.read_text(encoding="utf-8", errors="replace"),
    )
