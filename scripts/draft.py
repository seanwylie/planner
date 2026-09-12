#!/usr/bin/env python3
"""
Planner draft: turn a paragraph into a full idea doc with qualitative review.
Flow: Cursor (expand using template) → GPT (qualitative review, strict JSON) → Cursor (apply updates) or write alternative.

Output:
  - Pass: planner/ideas/{slug}.md
  - Fail: planner/ideas/{slug}.bad.md (alternative idea, marked for review)

Usage:
  draft.py {slug} -p "one paragraph describing the idea" [--overwrite] [--trust] [--yolo] [--agent-force]
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Load .env if OPENAI_API_KEY not set
if not os.environ.get("OPENAI_API_KEY"):
    try:
        from dotenv import load_dotenv

        project_env = Path(__file__).resolve().parent.parent.parent / ".env"
        if project_env.exists():
            load_dotenv(project_env)
        if not os.environ.get("OPENAI_API_KEY"):
            home_env = Path.home() / ".env"
            if home_env.exists():
                load_dotenv(home_env)
    except ImportError:
        pass

PLANNER_ROOT = Path(__file__).resolve().parent.parent
IDEA_TEMPLATE_PATH = PLANNER_ROOT / "templates" / "idea.template.md"
IDEA_REVIEW_SCHEMA_PATH = PLANNER_ROOT / "templates" / "idea_review.schema.json"


def load_template() -> str:
    """Load idea template content."""
    if not IDEA_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Idea template not found: {IDEA_TEMPLATE_PATH}")
    return IDEA_TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")


def load_review_schema() -> dict:
    """Load idea review JSON schema."""
    if not IDEA_REVIEW_SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {IDEA_REVIEW_SCHEMA_PATH}")
    with open(IDEA_REVIEW_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def cursor_expand(
    paragraph: str, template_content: str, extra_args: list[str] | None
) -> str:
    """Run Cursor to expand paragraph into full idea doc using template. Returns draft markdown."""
    prompt = f"""You are expanding a rough idea into a full idea document.

**Template to follow (sections and structure):**
```
{template_content}
```

**Rough idea (one paragraph):**
{paragraph}

**Instructions:** Produce a complete idea document in markdown that follows the template structure above. Use the exact section headings from the template. Fill each section with content that reflects the rough idea. Output only the markdown document — no preamble, no explanation."""  # noqa: E221,E231,E222,E702
    from planner.scripts.lib.cursor_runner import run_plan_mode

    code, stdout, stderr = run_plan_mode(
        prompt,
        extra_args=extra_args if extra_args else None,
    )
    if code != 0 or not stdout.strip():
        raise RuntimeError(
            f"Cursor expand failed (exit {code}): {stderr[:500] or 'no output'}"
        )
    return stdout.strip()


def gpt_review(draft_markdown: str) -> dict:
    """
    Call OpenAI for qualitative idea review. Returns dict with pass, feedback, suggested_updates, alternative_idea.
    Validates against idea_review.schema.json; alternative_idea required when pass is false.
    """
    import jsonschema
    from openai import OpenAI

    schema = load_review_schema()
    schema_str = json.dumps(schema, indent=2)

    user_prompt = f"""You are evaluating an **idea document** for a product feature. Your job is **qualitative**: is this a good idea, is it well-scoped, are goals and non-goals clear, are constraints realistic? Do **not** evaluate implementation details, code, or technical feasibility in depth — only the idea itself.

**Idea document to evaluate:**
```
{draft_markdown[:12000]}
```

**You MUST respond with ONLY a single JSON object. No other text, no markdown, no code fence, no preamble. The response will be parsed as JSON directly.**

Schema (you must include every required key; no extra keys):
{schema_str}

**Required keys:** pass (boolean), feedback (string), suggested_updates (string), alternative_idea (string).
**Optional key:** fail_reason (string, use when pass is false).

**Rules:**
- pass: true = idea is sound; false = needs significant revision (then you MUST set alternative_idea to the full revised markdown).
- feedback: qualitative evaluation only (2-4 short paragraphs). No implementation details.
- suggested_updates: bullet points or short instructions for the editor.
- alternative_idea: when pass is false, full revised idea document in markdown; when pass is true, use "".

**Example shape (your output must follow this exactly):**
{{"pass": true, "feedback": "...", "suggested_updates": "- Fix X\\n- Clarify Y", "alternative_idea": ""}}
or when failing:
{{"pass": false, "feedback": "...", "suggested_updates": "...", "fail_reason": "Scope too broad.", "alternative_idea": "# Title\\n\\n## Goals\\n..."}}

Return only the raw JSON object, nothing else."""  # noqa: E221,E231,E222,E702

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_prompt}],
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("Empty response from OpenAI")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from OpenAI: {e}") from e

    jsonschema.validate(instance=data, schema=schema)

    if not data.get("pass") and not (data.get("alternative_idea") or "").strip():
        raise RuntimeError(
            "OpenAI returned pass=false but alternative_idea is missing or empty"
        )

    return data


def cursor_apply_updates(
    draft_markdown: str, suggested_updates: str, extra_args: list[str] | None
) -> str:
    """Run Cursor to apply suggested_updates to draft. Returns final markdown."""
    prompt = f"""You are applying reviewer suggestions to an idea document.

**Current idea document:**
```
{draft_markdown[:14000]}
```

**Reviewer suggested updates (apply these):**
{suggested_updates}

**Instructions:** Produce the complete revised idea document in markdown. Apply the suggested updates; keep the same section structure. Output only the markdown — no preamble."""  # noqa: E221,E231,E222,E702
    from planner.scripts.lib.cursor_runner import run_plan_mode

    code, stdout, stderr = run_plan_mode(
        prompt,
        extra_args=extra_args if extra_args else None,
    )
    if code != 0 or not stdout.strip():
        raise RuntimeError(
            f"Cursor apply failed (exit {code}): {stderr[:500] or 'no output'}"
        )
    return stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="draft",
        description="Expand a paragraph into a full idea doc; GPT qualitative review; write to planner/ideas.",
    )
    parser.add_argument(
        "slug", help="Idea slug (filename will be planner/ideas/<slug>.md)"
    )
    parser.add_argument(
        "-p",
        "--paragraph",
        required=True,
        help="Rough idea as one paragraph (required for dashboard)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing planner/ideas/<slug>.md",
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

    slug = args.slug.strip()
    paragraph = args.paragraph.strip()
    if not paragraph:
        print(
            "Error: -p/--paragraph is required and must be non-empty", file=sys.stderr
        )
        return 1

    out_path = PLANNER_ROOT / "ideas" / f"{slug}.md"
    extra_args = []
    if args.trust:
        extra_args.append("--trust")
    if args.yolo:
        extra_args.append("--yolo")
    if args.agent_force:
        extra_args.append("-f")

    try:
        template_content = load_template()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    verbose = True  # Detailed output when run by hand

    try:
        if verbose:
            print("Step 1: Expanding paragraph into full idea (Cursor)...")
        draft = cursor_expand(
            paragraph, template_content, extra_args if extra_args else None
        )
        if verbose:
            print(f"  → Draft length: {len(draft)} chars")

        if verbose:
            print("Step 2: Qualitative review (GPT)...")
        review = gpt_review(draft)
        passed = review.get("pass", False)
        feedback = review.get("feedback", "")
        suggested_updates = review.get("suggested_updates", "")
        alternative_idea = (review.get("alternative_idea") or "").strip()
        fail_reason = review.get("fail_reason", "")

        if verbose:
            print(f"  → Pass: {passed}")
            if feedback:
                print(
                    f"  → Feedback: {feedback[:300]}{'...' if len(feedback) > 300 else ''}"
                )
            if not passed and fail_reason:
                print(f"  → Fail reason: {fail_reason}")

        if passed:
            if out_path.exists() and not args.overwrite:
                print(
                    f"Error: {out_path} already exists. Use --overwrite to replace.",
                    file=sys.stderr,
                )
                return 1
            if verbose:
                print("Step 3: Applying suggested updates (Cursor)...")
            final = cursor_apply_updates(
                draft, suggested_updates, extra_args if extra_args else None
            )
            write_path = out_path  # {slug}.md
        else:
            if verbose:
                print("Step 3: Writing alternative idea (marked for review)...")
            final = alternative_idea
            if not final:
                print(
                    "Error: pass=false but alternative_idea empty after schema validation",
                    file=sys.stderr,
                )
                return 1
            write_path = (
                PLANNER_ROOT / "ideas" / f"{slug}.bad.md"
            )  # failed → {slug}.bad.md

        write_path.parent.mkdir(parents=True, exist_ok=True)
        write_path.write_text(final, encoding="utf-8", errors="replace")
        if verbose:
            print(f"  → Wrote: {write_path}")

        if not passed:
            print(
                "\n*** FAIL — Idea marked for review. File written; review feedback above. ***",
                file=sys.stderr,
            )
            return 1
        if verbose:
            print("\nDone. Idea passed qualitative review and was written.")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
