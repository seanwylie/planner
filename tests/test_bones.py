"""Optional bones discovery."""

from __future__ import annotations

from pathlib import Path

from planner.scripts.lib.bones import bones_available, find_bones_root


def test_missing_bones_is_ok(tmp_path: Path) -> None:
    planner = tmp_path / "planner"
    planner.mkdir()
    assert find_bones_root(planner) is None
    assert bones_available(planner) is False


def test_bones_inside_planner(tmp_path: Path) -> None:
    planner = tmp_path / "planner"
    (planner / "bones").mkdir(parents=True)
    (planner / "bones" / "README.md").write_text("notes")
    assert find_bones_root(planner) == planner / "bones"
    assert bones_available(planner) is True


def test_bones_as_host_sibling(tmp_path: Path) -> None:
    host = tmp_path / "host"
    planner = host / "planner"
    bones = host / "bones"
    planner.mkdir(parents=True)
    bones.mkdir()
    (bones / "README.md").write_text("notes")
    assert find_bones_root(planner) == bones
