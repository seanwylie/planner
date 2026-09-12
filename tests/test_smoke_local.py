"""No Cursor, no OpenAI, no AWS, no bones."""

from __future__ import annotations

from pathlib import Path

from planner.scripts.lib.prompts import (
    HOST_PRODUCT_SUMMARY,
    cursor_plan_prompt,
    openai_review_prompt,
)
from planner.scripts.lib.validation import validate_slug

ROOT = Path(__file__).resolve().parent.parent


def test_example_idea_ships() -> None:
    idea = ROOT / "ideas" / "example-health-check.md"
    assert idea.is_file()
    text = idea.read_text()
    assert "fictional" in text.lower()
    assert "InnerCompass" not in text


def test_workspaces_are_not_part_of_the_tool_tree() -> None:
    tracked_hint = (ROOT / ".gitignore").read_text()
    assert "workspaces/" in tracked_hint


def test_prompts_are_host_generic() -> None:
    assert "InnerCompass" not in HOST_PRODUCT_SUMMARY
    plan = cursor_plan_prompt("idea", "GEN-0", "## Existing Alignment", bones_available=False)
    assert "InnerCompass" not in plan
    assert "bones/" not in plan
    assert "mobile-expo" not in plan
    assert "docs/Activities" not in plan
    review = openai_review_prompt("p", "s", "GEN-0", "{}")
    assert "InnerCompass" not in review


def test_prompts_mention_bones_only_when_present() -> None:
    with_bones = cursor_plan_prompt("idea", "GEN-0", "## Existing Alignment", bones_available=True)
    assert "bones/" in with_bones


def test_this_repo_does_not_vendor_or_gitlink_bones() -> None:
    gitignore = (ROOT / ".gitignore").read_text()
    assert "bones/" in gitignore
    assert not (ROOT / ".gitmodules").exists()
    assert not (ROOT / "bones" / "README.md").is_file()


def test_example_slug_is_valid() -> None:
    assert validate_slug("example-health-check") == "example-health-check"
