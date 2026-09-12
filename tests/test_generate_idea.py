"""Tests for generate_idea.py CLI — slug validation, overwrite guard, empty description."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PLANNER_ROOT = Path(__file__).resolve().parent.parent
GENERATE_SCRIPT = PLANNER_ROOT / "scripts" / "generate_idea.py"


class TestGenerateIdeaSlugValidation:
    """Test that generate_idea.py rejects invalid slugs before doing any work."""

    @pytest.mark.parametrize(
        "slug",
        ["../etc", "My-Idea", "my idea", "foo/bar", "my_idea", "trailing-"],
    )
    def test_invalid_slug_rejected(self, slug: str) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(GENERATE_SCRIPT),
                "--slug",
                slug,
                "--description",
                "test",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
        )
        assert result.returncode == 1
        assert "Error" in result.stderr or "Invalid slug" in result.stderr

    def test_valid_slug_accepted(self) -> None:
        """Valid slug passes validation (will fail at Cursor step, which is fine for this test)."""
        result = subprocess.run(
            [
                sys.executable,
                str(GENERATE_SCRIPT),
                "--slug",
                "test-valid",
                "--description",
                "test",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
        )
        # May fail because Cursor CLI not available, but should not fail on slug validation
        if result.returncode != 0:
            assert "Invalid slug" not in result.stderr


class TestGenerateIdeaEmptyDescription:
    def test_empty_description_rejected(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(GENERATE_SCRIPT),
                "--slug",
                "test",
                "--description",
                "   ",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
        )
        assert result.returncode == 1
        assert "non-empty" in result.stderr


class TestGenerateIdeaOverwriteGuard:
    @pytest.mark.skip(reason="PLANNER_ROOT patches do not apply to the subprocess under test")
    def test_overwrite_guard(self, tmp_path: Path) -> None:
        """If idea file exists and --overwrite is not passed, exit 1."""
        # Create a fake idea file
        ideas_dir = tmp_path / "ideas"
        ideas_dir.mkdir()
        (ideas_dir / "existing.md").write_text("# Existing")

        with patch("planner.scripts.generate_idea.PLANNER_ROOT", tmp_path):
            with patch(
                "planner.scripts.generate_idea.IDEA_TEMPLATE_PATH",
                tmp_path / "templates" / "idea.template.md",
            ):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(GENERATE_SCRIPT),
                        "--slug",
                        "existing",
                        "--description",
                        "test",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={"PYTHONPATH": str(PLANNER_ROOT.parent), "PATH": ""},
                )
                assert result.returncode == 1
                assert "already exists" in result.stderr
