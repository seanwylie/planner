#!/usr/bin/env python3
"""
Generate a full idea file from a short description via Cursor CLI.
Simpler than draft.py (no GPT qualitative review) — intended for quick dashboard-driven idea creation.

Usage:
  generate_idea.py --slug {slug} --description "short description" [--overwrite] [--trust] [--yolo] [--agent-force]
"""
import argparse
import sys
from pathlib import Path

PLANNER_ROOT = Path(__file__).resolve().parent.parent
IDEA_TEMPLATE_PATH = PLANNER_ROOT / "templates" / "idea.template.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="generate_idea",
        description="Generate a full idea file from a short description via Cursor CLI.",
    )
    parser.add_argument(
        "--slug", required=True, help="Idea slug (filename: planner/ideas/<slug>.md)"
    )
    parser.add_argument(
        "--description", required=True, help="Short description of the idea"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing idea file"
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
        slug = validate_slug(args.slug)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    description = args.description.strip()
    if not description:
        print("Error: --description must be non-empty", file=sys.stderr)
        return 1

    # Truncate very long descriptions
    if len(description) > 2000:
        description = description[:2000]
        print("Warning: description truncated to 2000 chars", file=sys.stderr)

    out_path = PLANNER_ROOT / "ideas" / f"{slug}.md"
    if out_path.exists() and not args.overwrite:
        print(
            f"Error: {out_path} already exists. Use --overwrite to replace.",
            file=sys.stderr,
        )
        return 1

    # Load template
    if not IDEA_TEMPLATE_PATH.exists():
        print(f"Error: idea template not found: {IDEA_TEMPLATE_PATH}", file=sys.stderr)
        return 1
    template_content = IDEA_TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")

    # Build prompt and run Cursor
    from planner.scripts.lib.prompts import idea_generation_prompt

    prompt = idea_generation_prompt(description, template_content)

    extra_args: list[str] = []
    if args.trust:
        extra_args.append("--trust")
    if args.yolo:
        extra_args.append("--yolo")
    if args.agent_force:
        extra_args.append("-f")

    try:
        from planner.scripts.lib.cursor_runner import run_plan_mode

        print(f"Generating idea for slug: {slug}")
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

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(stdout.strip(), encoding="utf-8")
        print(f"Wrote: {out_path}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
