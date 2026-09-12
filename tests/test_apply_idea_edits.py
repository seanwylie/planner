"""Tests for apply_idea_edits.py CLI — slug validation, missing file, empty instructions."""
import subprocess
import sys
from pathlib import Path

import pytest

PLANNER_ROOT = Path(__file__).resolve().parent.parent
APPLY_SCRIPT = PLANNER_ROOT / "scripts" / "apply_idea_edits.py"


class TestApplyEditsSlugValidation:
    @pytest.mark.parametrize(
        "slug",
        ["../etc", "My-Idea", "foo/bar", "my_idea", "trailing-"],
    )
    def test_invalid_slug_rejected(self, slug: str) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(APPLY_SCRIPT),
                "--idea",
                slug,
                "--instructions",
                "test",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
        )
        assert result.returncode == 1
        assert "Error" in result.stderr or "Invalid slug" in result.stderr


class TestApplyEditsMissingFile:
    def test_missing_idea_file(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(APPLY_SCRIPT),
                "--idea",
                "nonexistent-slug",
                "--instructions",
                "test",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
        )
        assert result.returncode == 1
        assert "not found" in result.stderr


class TestApplyEditsEmptyInstructions:
    def test_empty_instructions_rejected(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(APPLY_SCRIPT),
                "--idea",
                "test",
                "--instructions",
                "   ",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
        )
        assert result.returncode == 1
        assert "non-empty" in result.stderr


class TestApplyEditsDryRun:
    def test_dry_run_prints_prompt(self, tmp_path: Path) -> None:
        """With --dry-run, prompt is printed but file is not modified."""
        # Create a fake idea file to read
        ideas_dir = PLANNER_ROOT / "ideas"
        # Use an existing idea if available; otherwise skip
        existing = list(ideas_dir.glob("*.md")) if ideas_dir.is_dir() else []
        if not existing:
            pytest.skip("No idea files available for dry-run test")
        slug = existing[0].stem
        original = existing[0].read_text(encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(APPLY_SCRIPT),
                "--idea",
                slug,
                "--instructions",
                "Add more goals",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
        )
        assert result.returncode == 0
        assert "EDIT PROMPT" in result.stdout
        # File unchanged
        assert existing[0].read_text(encoding="utf-8") == original
