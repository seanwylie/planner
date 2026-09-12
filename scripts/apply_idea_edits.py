#!/usr/bin/env python3
"""
Apply vague modification instructions to an existing idea file via Cursor CLI.

Usage:
  apply_idea_edits.py --idea {slug} --instructions "what to change" [--dry-run] [--trust] [--yolo] [--agent-force]
"""
import argparse
import sys
from pathlib import Path

PLANNER_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apply_idea_edits",
        description="Apply vague modification instructions to an existing idea file via Cursor CLI.",
    )
    parser.add_argument(
        "--idea", required=True, help="Idea slug (reads/writes planner/ideas/<slug>.md)"
    )
    parser.add_argument(
        "--instructions", required=True, help="Modification instructions (free text)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print prompt only, do not write"
    )
    parser.add_argument("--trust", action="store_true", help="Pass --trust to Cursor")
    parser.add_argument("--yolo", action="store_true", help="Pass --yolo to Cursor")
    parser.add_argument(
        "--agent-force",
        dest="agent_force",
        action="store_true",
        help="Pass -f to Cursor",
    )
    args = parser.parse_args()

    # Validate slug
    from planner.scripts.lib.validation import validate_slug

    try:
        slug = validate_slug(args.idea)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    instructions = args.instructions.strip()
    if not instructions:
        print("Error: --instructions must be non-empty", file=sys.stderr)
        return 1

    idea_path = PLANNER_ROOT / "ideas" / f"{slug}.md"
    if not idea_path.exists():
        print(f"Error: idea file not found: {idea_path}", file=sys.stderr)
        return 1

    current_content = idea_path.read_text(encoding="utf-8", errors="replace")

    # Build prompt
    from planner.scripts.lib.prompts import idea_edit_prompt

    prompt = idea_edit_prompt(current_content, instructions)

    if args.dry_run:
        print("=== EDIT PROMPT (dry-run) ===\n")
        print(prompt)
        return 0

    extra_args: list[str] = []
    if args.trust:
        extra_args.append("--trust")
    if args.yolo:
        extra_args.append("--yolo")
    if args.agent_force:
        extra_args.append("-f")

    try:
        from planner.scripts.lib.cursor_runner import run_plan_mode

        print(f"Applying edits to idea: {slug}")
        code, stdout, stderr = run_plan_mode(
            prompt,
            extra_args=extra_args if extra_args else None,
        )
        if code != 0 or not stdout.strip():
            print(
                f"Error: Cursor failed (exit {code}): {stderr[:500] or 'no output'}",
                file=sys.stderr,
            )
            return 1

        idea_path.write_text(stdout.strip(), encoding="utf-8")
        print(f"Updated: {idea_path}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
