"""Tests for planner prompt functions (idea_generation_prompt, idea_edit_prompt)."""
from planner.scripts.lib.prompts import idea_edit_prompt, idea_generation_prompt


class TestIdeaGenerationPrompt:
    def test_includes_description(self) -> None:
        prompt = idea_generation_prompt("Build a cool feature", "## Template\n...")
        assert "Build a cool feature" in prompt

    def test_includes_template(self) -> None:
        prompt = idea_generation_prompt("desc", "## Problem\n## Goals\n")
        assert "## Problem" in prompt
        assert "## Goals" in prompt

    def test_returns_string(self) -> None:
        result = idea_generation_prompt("desc", "template")
        assert isinstance(result, str)
        assert len(result) > 0


class TestIdeaEditPrompt:
    def test_includes_current_content(self) -> None:
        prompt = idea_edit_prompt("# My Idea\n## Problem\nSomething", "Add more goals")
        assert "# My Idea" in prompt

    def test_includes_instructions(self) -> None:
        prompt = idea_edit_prompt("content", "Add a non-goals section")
        assert "Add a non-goals section" in prompt

    def test_returns_string(self) -> None:
        result = idea_edit_prompt("content", "instructions")
        assert isinstance(result, str)
        assert len(result) > 0
