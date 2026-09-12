#!/usr/bin/env python3
"""
Planner replay: re-evaluate gates, rebuild patch, re-render from stored artifacts.
Proves determinism.
Usage:
  replay.py {idea} {run_id}
"""
import argparse
import json
import sys
from pathlib import Path

PLANNER_ROOT = Path(__file__).resolve().parent.parent


def _run_path(idea: str, run_id: str, *parts: str) -> Path:
    return PLANNER_ROOT / "workspaces" / idea / "runs" / run_id / Path(*parts)


def main() -> int:
    parser = argparse.ArgumentParser(prog="replay")
    parser.add_argument("idea", help="Idea slug")
    parser.add_argument("run_id", help="Run ID to replay")
    args = parser.parse_args()
    run_dir = _run_path(args.idea, args.run_id)
    if not run_dir.exists():
        print(f"Error: run not found: {run_dir}", file=sys.stderr)
        return 1
    config_path = run_dir / "snapshots" / "effective_config.json"
    if not config_path.exists():
        print("Error: effective_config.json not found", file=sys.stderr)
        return 1
    config = json.loads(config_path.read_text(encoding="utf-8"))
    from planner.scripts.lib.render import render_review_md

    n = 1
    while True:
        review_path = run_dir / "reviews" / f"review_v{n}.json"
        if not review_path.exists():
            break
        review = json.loads(review_path.read_text(encoding="utf-8"))
        passed, gates = _compute_gates(review, config)
        print(
            f"Round {n}: score={gates['score']}, must_fix={gates['must_fix_count']}, passed={passed}"
        )
        md = render_review_md(review)
        (run_dir / "reviews" / f"review_v{n}.md").write_text(md, encoding="utf-8")
        print(f"  Re-rendered review_v{n}.md")
        plan_next = run_dir / "plans" / f"plan_v{n+1}.md"
        if (run_dir / "plans" / f"plan_v{n}.md").exists() and plan_next.exists():
            from planner.scripts import refine as refine_mod

            plan = (run_dir / "plans" / f"plan_v{n}.md").read_text(encoding="utf-8")
            spec_path = run_dir / "specs" / f"spec_v{n}.md"
            spec = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
            checklist = ""
            for name in ("CHECKLIST.md",):
                p = run_dir / "snapshots" / name
                if p.exists():
                    checklist += p.read_text(encoding="utf-8") + "\n"
            patch = refine_mod.generate_patch(review, plan, spec, checklist, config, n)
            (run_dir / "patches" / f"patch_v{n}_to_v{n+1}.md").write_text(
                patch, encoding="utf-8"
            )
            print(f"  Rebuilt patch_v{n}_to_v{n+1}.md")
        n += 1
    print("Replay complete.")
    return 0


def _compute_gates(review: dict, config: dict) -> tuple[bool, dict]:
    score = review.get("overall_score", 0)
    must_fix = review.get("must_fix") or []
    should_fix = review.get("should_fix") or []
    questions = review.get("questions") or []
    sr = review.get("spec_readiness") or {}
    min_score = config.get("min_score", 5)
    req_zero_must = config.get("require_zero_must_fix", True)
    req_zero_q = config.get("require_zero_questions", True)
    req_zero_high_risk = config.get("require_zero_high_risk_should_fix", True)
    high_risk_should = [
        i for i in should_fix if (i.get("risk_level") or "").lower() == "high"
    ]
    passed = (
        score >= min_score
        and (not req_zero_must or len(must_fix) == 0)
        and (not req_zero_q or len(questions) == 0)
        and (not req_zero_high_risk or len(high_risk_should) == 0)
        and sr.get("backend", 0) >= config.get("min_readiness_backend", 90)
        and sr.get("frontend", 0) >= config.get("min_readiness_frontend", 90)
        and sr.get("infra", 0) >= config.get("min_readiness_infra", 75)
        and sr.get("tests", 0) >= config.get("min_readiness_tests", 90)
        and sr.get("docs", 0) >= config.get("min_readiness_docs", 90)
    )
    gates = {
        "score": score,
        "must_fix_count": len(must_fix),
        "high_risk_should_fix_count": len(high_risk_should),
        "questions_count": len(questions),
        "readiness": sr,
        "passed": passed,
    }
    return passed, gates
