#!/usr/bin/env python3
"""
Planner execute: run Cursor agent with final spec.
Usage:
  execute.py {idea} [--run-id ID] [--single-pass] [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

PLANNER_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PLANNER_ROOT.parent


def _bones_exists() -> bool:
    """True if an optional bones directory is present. Never required."""
    from planner.scripts.lib.bones import bones_available

    return bones_available(PLANNER_ROOT)


def _planner_path(*parts: str) -> Path:
    return PLANNER_ROOT.joinpath(*parts)


def _workspace_path(idea: str, *parts: str) -> Path:
    return _planner_path("workspaces", idea, *parts)


def main() -> int:
    parser = argparse.ArgumentParser(prog="execute")
    parser.add_argument("idea", help="Idea slug")
    parser.add_argument("--run-id", help="Use specific run (default: latest)")
    parser.add_argument(
        "--single-pass", action="store_true", help="One Cursor run instead of phases"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print prompt only, do not invoke Cursor"
    )
    parser.add_argument("--trust", action="store_true", help="Pass --trust to agent")
    parser.add_argument("--yolo", action="store_true", help="Pass --yolo to agent")
    parser.add_argument(
        "--agent-force",
        dest="agent_force",
        action="store_true",
        help="Pass -f to agent",
    )
    args = parser.parse_args()
    idea = args.idea
    workspace = _workspace_path(idea)
    state_file = workspace / "state.json"
    if not state_file.exists() and not args.run_id:
        print(f"Error: no run found. Run 'refine run {idea}' first.", file=sys.stderr)
        return 1
    run_id = args.run_id
    if not run_id and state_file.exists():
        run_id = json.loads(state_file.read_text(encoding="utf-8")).get("latest_run_id")
    if not run_id:
        print("Error: no run_id", file=sys.stderr)
        return 1
    run_dir = _workspace_path(idea, "runs", run_id)
    final_spec = run_dir / "specs" / "final_spec.md"
    if not final_spec.exists():
        print(f"Error: final_spec.md not found at {final_spec}", file=sys.stderr)
        return 1
    spec_content = final_spec.read_text(encoding="utf-8", errors="replace")
    execute_tpl = _planner_path("templates", "execute.template.md")
    execute_invariants = (
        execute_tpl.read_text(encoding="utf-8", errors="replace")
        if execute_tpl.exists()
        else ""
    )
    phases = [
        "Backend + shared code",
        "Frontend",
        "Infra/CDK",
        "Tests",
        "Docs",
    ]
    prompt = f"""Implement the following spec. Work in phases: {', '.join(phases)}.
After each phase, summarize what changed and what remains.
Do not invent file paths. If unsure, add a VERIFY: TODO with grep target.

{execute_invariants}

## Spec

{spec_content}

Execute the spec. Work through each section in order."""
    if args.dry_run:
        print("=== EXECUTE PROMPT (dry-run) ===\n")
        print(prompt)
        return 0
    extra = []
    if args.trust:
        extra.append("--trust")
    if args.yolo:
        extra.append("--yolo")
    if getattr(args, "agent_force", False):
        extra.append("-f")
    try:
        from planner.scripts.lib.cursor_runner import run_plan_mode
        from planner.scripts.lib.prompts import execute_fix_pass_prompt

        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        code, stdout, stderr = run_plan_mode(
            prompt,
            log_path=run_dir / "logs" / "execute.log",
            extra_args=extra if extra else None,
        )
        print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        bones_available = _bones_exists()
        try:
            from planner.config import EXECUTE_FIX_PASSES
        except ImportError:
            EXECUTE_FIX_PASSES = 3
        for fix_pass in range(1, EXECUTE_FIX_PASSES + 1):
            print(
                f"\n=== Fix-up pass {fix_pass}/{EXECUTE_FIX_PASSES} (scan and apply fixes) ===\n",
                file=sys.stderr,
            )
            fix_prompt = execute_fix_pass_prompt(
                fix_pass, bones_available=bones_available
            )
            code_f, stdout_f, stderr_f = run_plan_mode(
                fix_prompt,
                log_path=run_dir / "logs" / f"execute_fix_pass_{fix_pass}.log",
                extra_args=extra if extra else None,
            )
            print(stdout_f)
            if stderr_f:
                print(stderr_f, file=sys.stderr)
            if code_f != 0:
                code = code_f
        print("\n=== Review gates ===")
        print("- Verify changes match spec scope")
        print("- Run tests")
        print("- Update docs if declared")
        return 0 if code == 0 else 1
    except ImportError as e:
        print(f"Import error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
