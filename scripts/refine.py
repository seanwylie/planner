#!/usr/bin/env python3
"""
Planner refine: init workspace, run refinement loop.
Usage:
  refine.py init {idea} [--refresh-input]
  refine.py run {idea} [--run-id ID] [--max-rounds N] [--cursor-only] [--openai-only] [--manual-cursor]
  refine.py run {idea} --resume --run-id {run_id} [--force]
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load .env if OPENAI_API_KEY not set (project root, then ~/.env)
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

# Project root: parent of planner/
PLANNER_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PLANNER_ROOT.parent


def _bones_exists(project_root: Path | None = None) -> bool:
    """True if an optional bones directory is present. Never required."""
    from planner.scripts.lib.bones import bones_available

    return bones_available(PLANNER_ROOT)


def _planner_path(*parts: str) -> Path:
    return PLANNER_ROOT.joinpath(*parts)


def _workspace_path(idea: str, *parts: str) -> Path:
    return _planner_path("workspaces", idea, *parts)


def _run_path(idea: str, run_id: str, *parts: str) -> Path:
    return _workspace_path(idea, "runs", run_id, *parts)


def sha256_content(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8", errors="replace")
    return hashlib.sha256(content).hexdigest()


def short_hash(content: str | bytes, length: int = 6) -> str:
    return sha256_content(content)[:length]


def init_cmd(args: argparse.Namespace) -> int:
    """Init workspace and snapshot idea."""
    idea = args.idea
    idea_file = _planner_path("ideas", f"{idea}.md")
    if not idea_file.exists():
        print(f"Error: idea file not found: {idea_file}", file=sys.stderr)
        return 1
    workspace = _workspace_path(idea)
    input_dir = workspace / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    idea_snapshot = input_dir / "idea.md"
    content = idea_file.read_text(encoding="utf-8", errors="replace")
    idea_snapshot.write_text(content, encoding="utf-8")
    print(f"Initialized workspace: {workspace}")
    print(f"Snapshotted idea to {idea_snapshot}")
    return 0


def preflight(args: argparse.Namespace) -> tuple[bool, str]:
    """Run preflight checks. Return (ok, error_msg)."""
    templates = _planner_path("templates")
    if not templates.exists():
        return False, f"Templates not found: {templates}"
    for name in (
        "idea.template.md",
        "plan.template.md",
        "spec.template.md",
        "refinement.schema.json",
    ):
        if not (templates / name).exists():
            return False, f"Missing template: {templates / name}"
    if not args.cursor_only and not args.manual_cursor:
        try:
            from planner.scripts.lib.cursor_runner import (
                find_agent,
                smoke_test_plan_mode,
            )

            found, err = find_agent()
            if not found:
                if args.no_manual_fallback:
                    return False, f"Cursor CLI not available: {err}"
                print(
                    f"Warning: Cursor CLI not available ({err}), switching to --manual-cursor",
                    file=sys.stderr,
                )
                args.manual_cursor = True
            else:
                extra = _agent_extra_args(args)
                ok, err = smoke_test_plan_mode(extra_args=extra if extra else None)
                if not ok and args.no_manual_fallback:
                    return False, f"Plan mode smoke test failed: {err}"
                if not ok:
                    print(
                        f"Warning: Plan mode smoke test failed ({err}), switching to --manual-cursor",
                        file=sys.stderr,
                    )
                    args.manual_cursor = True
        except ImportError as e:
            return False, f"Import error: {e}"
    if not args.cursor_only and not args.manual_cursor:
        if not os.environ.get("OPENAI_API_KEY"):
            return False, "OPENAI_API_KEY not set (use --cursor-only to skip OpenAI)"
    idea_file = _planner_path("ideas", f"{args.idea}.md")
    if not idea_file.exists():
        return False, f"Idea file not found: {idea_file}"
    return True, ""


def make_run_id(config: dict) -> str:
    """Generate run_id: YYYY-MM-DDTHH-mm-ssZ__bundle-{v}__cfg-{hash}"""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    try:
        from planner.config import PROMPT_BUNDLE_VERSION

        bundle = PROMPT_BUNDLE_VERSION
    except ImportError:
        bundle = "v2.1.0"
    cfg_str = json.dumps(config, sort_keys=True)
    cfg_hash = short_hash(cfg_str)
    return f"{ts}__bundle-{bundle}__cfg-{cfg_hash}"


def compute_gates(review: dict, config: dict) -> tuple[bool, dict]:
    """Compute gates from review + config. Return (passed, gates_dict)."""
    score = review.get("overall_score", 0)
    must_fix = review.get("must_fix") or []
    should_fix = review.get("should_fix") or []
    questions = review.get("questions") or []
    sr = review.get("spec_readiness") or {}
    min_score = config.get("min_score", 5)
    req_zero_must = config.get("require_zero_must_fix", True)
    req_zero_q = config.get("require_zero_questions", True)
    req_zero_high_risk = config.get("require_zero_high_risk_should_fix", True)
    min_backend = config.get("min_readiness_backend", 90)
    min_frontend = config.get("min_readiness_frontend", 90)
    min_infra = config.get("min_readiness_infra", 75)
    min_tests = config.get("min_readiness_tests", 90)
    min_docs = config.get("min_readiness_docs", 90)
    high_risk_should = [
        i for i in should_fix if (i.get("risk_level") or "").lower() == "high"
    ]
    score_ok = score >= min_score
    must_ok = not req_zero_must or len(must_fix) == 0
    questions_ok = not req_zero_q or len(questions) == 0
    high_risk_ok = not req_zero_high_risk or len(high_risk_should) == 0
    backend_ok = sr.get("backend", 0) >= min_backend
    frontend_ok = sr.get("frontend", 0) >= min_frontend
    infra_ok = sr.get("infra", 0) >= min_infra
    tests_ok = sr.get("tests", 0) >= min_tests
    docs_ok = sr.get("docs", 0) >= min_docs
    passed = (
        score_ok
        and must_ok
        and questions_ok
        and high_risk_ok
        and backend_ok
        and frontend_ok
        and infra_ok
        and tests_ok
        and docs_ok
    )
    gates = {
        "score": score,
        "must_fix_count": len(must_fix),
        "high_risk_should_fix_count": len(high_risk_should),
        "questions_count": len(questions),
        "readiness": sr,
        "passed": passed,
        "criteria": {
            "score": {"ok": score_ok, "actual": score, "min": min_score},
            "must_fix": {"ok": must_ok, "count": len(must_fix)},
            "questions": {"ok": questions_ok, "count": len(questions)},
            "high_risk_should_fix": {
                "ok": high_risk_ok,
                "count": len(high_risk_should),
            },
            "backend": {
                "ok": backend_ok,
                "actual": sr.get("backend", 0),
                "min": min_backend,
            },
            "frontend": {
                "ok": frontend_ok,
                "actual": sr.get("frontend", 0),
                "min": min_frontend,
            },
            "infra": {"ok": infra_ok, "actual": sr.get("infra", 0), "min": min_infra},
            "tests": {"ok": tests_ok, "actual": sr.get("tests", 0), "min": min_tests},
            "docs": {"ok": docs_ok, "actual": sr.get("docs", 0), "min": min_docs},
        },
    }
    return passed, gates


def print_gates_summary(passed: bool, gates: dict, round_n: int | None = None) -> None:
    """Print detailed gates breakdown."""
    c = gates.get("criteria") or {}
    lines = []
    if round_n is not None:
        lines.append(
            f"=== Gates {'PASSED' if passed else 'FAILED'} at round {round_n} ==="
        )
    else:
        lines.append(f"=== Gates {'PASSED' if passed else 'FAILED'} ===")
    lines.append("")
    for name, info in c.items():
        if not isinstance(info, dict):
            continue
        ok = info.get("ok", False)
        sym = "✓" if ok else "✗"
        if "actual" in info and "min" in info:
            lines.append(
                f"  {sym} {name}: {info['actual']} >= {info['min']} (required)"
            )
        elif "count" in info:
            lines.append(f"  {sym} {name}: {info['count']} items (must be 0)")
        else:
            lines.append(f"  {sym} {name}: {'met' if ok else 'not met'}")
    lines.append("")
    lines.append(f"  Overall score: {gates.get('score', 'N/A')}")
    lines.append(
        f"  Readiness: backend={gates.get('readiness', {}).get('backend', 'N/A')}, frontend={gates.get('readiness', {}).get('frontend', 'N/A')}, infra={gates.get('readiness', {}).get('infra', 'N/A')}, tests={gates.get('readiness', {}).get('tests', 'N/A')}, docs={gates.get('readiness', {}).get('docs', 'N/A')}"
    )
    print("\n".join(lines))


def generate_patch(
    review: dict,
    plan_content: str,
    spec_content: str,
    checklist_content: str,
    config: dict,
    n: int,
) -> str:
    """Pure function: generate patch markdown from review + inputs."""
    lines = [
        f"# Patch v{n} → v{n+1}",
        "",
        "## Apply Order",
        "1. Must-fix (apply in order)",
        "2. Checklist gaps (add missing items)",
        "3. Should-fix (apply in order)",
        "",
        "## Must-Fix",
        "",
        "| ID | Area | Change | Acceptance | Risk | References |",
        "|----|------|--------|------------|------|------------|",
    ]
    for item in review.get("must_fix") or []:
        refs = ",".join((item.get("references") or [])[:2])
        lines.append(
            f"| {item.get('id', '')} | {item.get('area', '')} | {item.get('concrete_change', '')[:80]} | "
            f"{item.get('acceptance_criteria', '')[:60]} | {item.get('risk_level', '')} | {refs} |"
        )
    lines.extend(["", "## Checklist Gaps", ""])
    for m in review.get("missing_checklist_items") or []:
        lines.append(f"- {m}")
    lines.extend(
        [
            "",
            "## Should-Fix",
            "",
            "| ID | Area | Change | Acceptance | Risk | References |",
            "|----|------|--------|------------|------|------------|",
        ]
    )
    for item in review.get("should_fix") or []:
        refs = ",".join((item.get("references") or [])[:2])
        lines.append(
            f"| {item.get('id', '')} | {item.get('area', '')} | {item.get('concrete_change', '')[:80]} | "
            f"{item.get('acceptance_criteria', '')[:60]} | {item.get('risk_level', '')} | {refs} |"
        )
    lines.extend(
        [
            "",
            "## Do Not Change",
            "",
            "- Preserve decisions that were correct and should not churn.",
            "",
        ]
    )
    c = config
    lines.extend(
        [
            "## Acceptance Gates",
            f"- overall_score >= {c.get('min_score', 4)}",
            "- must_fix_count == 0",
            "- questions_count == 0",
            f"- spec_readiness.backend >= {c.get('min_readiness_backend', 80)}",
            f"- spec_readiness.frontend >= {c.get('min_readiness_frontend', 80)}",
            f"- spec_readiness.tests >= {c.get('min_readiness_tests', 80)}",
            f"- spec_readiness.docs >= {c.get('min_readiness_docs', 80)}",
        ]
    )
    return "\n".join(lines)


def merge_plan_refinements(
    refinements_per_model: list[tuple[str, list]],
) -> str:
    """Merge refinements from multiple models into one patch markdown. Dedupe by (category, location)."""
    seen: set[tuple[str, str]] = set()
    by_priority: dict[str, list[dict]] = {"must": [], "should": [], "consider": []}
    for _model, refs in refinements_per_model:
        for r in refs:
            if not isinstance(r, dict):
                continue
            cat = (r.get("category") or "").strip().lower()
            loc = (r.get("location") or "").strip()[:80]
            key = (cat, loc)
            if key in seen:
                continue
            seen.add(key)
            p = (r.get("priority") or "consider").strip().lower()
            if p not in by_priority:
                p = "consider"
            by_priority[p].append(r)
    lines = [
        "# Plan patch (merged from consensus reviews)",
        "",
        "## Apply order: must → should → consider",
        "",
    ]
    for priority in ("must", "should", "consider"):
        items = by_priority.get(priority, [])
        if not items:
            continue
        lines.append(f"## {priority.capitalize()}")
        lines.append("")
        for r in items:
            loc = r.get("location", "")
            issue = (r.get("issue") or "")[:200]
            suggestion = (r.get("suggestion") or "")[:200]
            lines.append(f"- **{loc}**: {issue}")
            lines.append(f"  Suggestion: {suggestion}")
            if r.get("technical_suggestion"):
                lines.append(
                    f"  Technical: {(r.get('technical_suggestion') or '')[:150]}"
                )
            lines.append("")
        lines.append("")
    return "\n".join(lines)


def merge_spec_reviews(reviews: list[dict]) -> dict:
    """Merge multiple spec reviews: union must_fix (dedupe by id), union questions, min readiness."""
    must_fix_seen: set[str] = set()
    must_fix_merged: list[dict] = []
    for rev in reviews:
        for item in rev.get("must_fix") or []:
            id_ = (item.get("id") or "").strip()
            if not id_:
                id_ = (item.get("concrete_change") or "")[:60]
            if id_ and id_ not in must_fix_seen:
                must_fix_seen.add(id_)
                must_fix_merged.append(dict(item))
    should_fix_seen: set[str] = set()
    should_fix_merged: list[dict] = []
    for rev in reviews:
        for item in rev.get("should_fix") or []:
            id_ = (item.get("id") or (item.get("concrete_change") or "")[:60]).strip()
            if id_ and id_ not in should_fix_seen:
                should_fix_seen.add(id_)
                should_fix_merged.append(dict(item))
    questions_merged: list[str] = []
    q_seen: set[str] = set()
    for rev in reviews:
        for q in rev.get("questions") or []:
            qs = (q.strip() if isinstance(q, str) else str(q))[:200]
            if qs and qs not in q_seen:
                q_seen.add(qs)
                questions_merged.append(qs)
    sr = {}
    for k in ("backend", "frontend", "infra", "tests", "docs"):
        vals = [
            rev.get("spec_readiness", {}).get(k)
            for rev in reviews
            if isinstance(rev.get("spec_readiness"), dict)
        ]
        vals = [v for v in vals if isinstance(v, (int, float))]
        sr[k] = min(vals) if vals else 0
    missing = []
    for rev in reviews:
        for m in rev.get("missing_checklist_items") or []:
            if m and m not in missing:
                missing.append(m)
    score_vals = [
        rev.get("overall_score")
        for rev in reviews
        if rev.get("overall_score") is not None
    ]
    overall_score = min(score_vals) if score_vals else 1
    return {
        "overall_score": overall_score,
        "agreed": False,
        "must_fix": must_fix_merged,
        "should_fix": should_fix_merged,
        "questions": questions_merged,
        "missing_checklist_items": missing,
        "spec_readiness": sr,
    }


def run_cmd(args: argparse.Namespace) -> int:
    """Run refinement loop."""
    ok, err = preflight(args)
    if not ok:
        print(f"Preflight failed: {err}", file=sys.stderr)
        return 1
    idea = args.idea
    try:
        from planner.config import DEFAULTS

        config = dict(DEFAULTS)
    except ImportError:
        config = {
            "min_score": 5,
            "max_rounds": 8,
            "min_rounds": 6,
            "require_zero_must_fix": True,
            "require_zero_questions": True,
            "require_zero_high_risk_should_fix": True,
            "min_readiness_backend": 90,
            "min_readiness_frontend": 90,
            "min_readiness_infra": 75,
            "min_readiness_tests": 90,
            "min_readiness_docs": 90,
        }
    config["max_rounds"] = args.max_rounds or config.get("max_rounds", 8)
    config["min_rounds"] = config.get("min_rounds", 6)
    consensus_mode = getattr(args, "consensus", False)
    if consensus_mode:
        try:
            from planner.config import (
                CONSENSUS_MIN_MODELS,
                CONSENSUS_MODELS,
                PLAN_CATEGORIES,
                PLAN_SCORE_THRESHOLD,
            )

            config["consensus_models"] = (
                [m.strip() for m in (args.models or "").split(",") if m.strip()]
                if getattr(args, "models", None)
                else list(CONSENSUS_MODELS)
            )
            if not config["consensus_models"]:
                config["consensus_models"] = list(CONSENSUS_MODELS)
            config["plan_score_threshold"] = PLAN_SCORE_THRESHOLD
            config["plan_categories"] = list(PLAN_CATEGORIES)
            config["consensus_min_models"] = CONSENSUS_MIN_MODELS
        except ImportError:
            config["consensus_models"] = ["gpt-4o", "anthropic.claude-3-5-sonnet-v2:0"]
            config["plan_score_threshold"] = 95
            config["plan_categories"] = [
                "clarity",
                "completeness",
                "executability",
                "ordering",
                "risk",
                "consistency",
                "testing",
                "docs",
            ]
            config["consensus_min_models"] = 2
    run_id = args.run_id or make_run_id(config)
    run_dir = _run_path(idea, run_id)
    if args.resume:
        if not run_dir.exists():
            print(f"Run not found: {run_dir}", file=sys.stderr)
            return 1
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
        snapshots = run_dir / "snapshots"
        snapshots.mkdir(exist_ok=True)
        idea_src = _planner_path("ideas", f"{idea}.md")
        idea_content = idea_src.read_text(encoding="utf-8", errors="replace")
        (snapshots / "idea.md").write_text(idea_content, encoding="utf-8")
        for name in ("CHECKLIST.md",):
            src = _planner_path(name)
            if src.exists():
                (snapshots / name).write_text(
                    src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
                )
        (snapshots / "effective_config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        (run_dir / "plans").mkdir(exist_ok=True)
        (run_dir / "specs").mkdir(exist_ok=True)
        (run_dir / "reviews").mkdir(exist_ok=True)
        (run_dir / "patches").mkdir(exist_ok=True)
        (run_dir / "rounds").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        if consensus_mode:
            (run_dir / "plan_reviews").mkdir(exist_ok=True)
            (run_dir / "spec_reviews").mkdir(exist_ok=True)
    _workspace_path(idea, "state.json").write_text(
        json.dumps({"latest_run_id": run_id}), encoding="utf-8"
    )
    has_bones = _bones_exists(PROJECT_ROOT)
    if not has_bones:
        print(
            "Warning: bones submodule not found. Everything is better with bones (architectural guidance). Continuing without bones.",
            file=sys.stderr,
        )
    if args.cursor_only:
        _run_cursor_only(idea, run_id, run_dir, config, args, bones_available=has_bones)
        return 0
    if args.openai_only:
        _run_openai_only(idea, run_id, run_dir, config, args)
        return 0
    if args.manual_cursor:
        _run_manual_cursor(
            idea, run_id, run_dir, config, args, bones_available=has_bones
        )
        return 0
    if consensus_mode:
        _run_consensus_loop(
            idea, run_id, run_dir, config, args, bones_available=has_bones
        )
        return 0
    _run_full_loop(idea, run_id, run_dir, config, args, bones_available=has_bones)
    return 0


def _agent_extra_args(args: argparse.Namespace) -> list[str]:
    """Build agent CLI extra flags from refine/execute args."""
    out = []
    if getattr(args, "trust", False):
        out.append("--trust")
    if getattr(args, "yolo", False):
        out.append("--yolo")
    if getattr(args, "agent_force", False):
        out.append("-f")
    return out


def _run_cursor_only(
    idea: str,
    run_id: str,
    run_dir: Path,
    config: dict,
    args: argparse.Namespace,
    *,
    bones_available: bool = True,
) -> None:
    """Produce plan/spec only, no OpenAI."""
    from planner.scripts.lib.cursor_runner import run_plan_mode
    from planner.scripts.lib.prompts import cursor_plan_prompt, cursor_spec_prompt

    snapshots = run_dir / "snapshots"
    idea_content = (snapshots / "idea.md").read_text(encoding="utf-8", errors="replace")
    plan_tpl = (_planner_path("templates", "plan.template.md")).read_text(
        encoding="utf-8", errors="replace"
    )
    spec_tpl = (_planner_path("templates", "spec.template.md")).read_text(
        encoding="utf-8", errors="replace"
    )
    import re

    headings = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", plan_tpl)
    plan_headings = (
        headings.group(1).strip()
        if headings
        else "Existing Alignment, Summary, Architecture, Files"
    )
    checklist = (
        (snapshots / "CHECKLIST.md").read_text(encoding="utf-8", errors="replace")
        if (snapshots / "CHECKLIST.md").exists()
        else ""
    )
    prompt = cursor_plan_prompt(
        idea_content, checklist[:2000], plan_headings, bones_available=bones_available
    )
    extra = _agent_extra_args(args)
    code, stdout, stderr = run_plan_mode(
        prompt,
        log_path=run_dir / "logs" / "cursor_plan_v1.log",
        extra_args=extra if extra else None,
    )
    plan_content = stdout.strip() if code == 0 else ""
    if plan_content:
        (run_dir / "plans" / "plan_v1.md").write_text(plan_content, encoding="utf-8")
        spec_headings = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", spec_tpl)
        spec_headings_str = spec_headings.group(1).strip() if spec_headings else ""
        spec_prompt = cursor_spec_prompt(
            plan_content, spec_headings_str, bones_available=bones_available
        )
        code2, stdout2, _ = run_plan_mode(
            spec_prompt,
            log_path=run_dir / "logs" / "cursor_spec_v1.log",
            extra_args=extra if extra else None,
        )
        if code2 == 0 and stdout2.strip():
            (run_dir / "specs" / "spec_v1.md").write_text(
                stdout2.strip(), encoding="utf-8"
            )
            (run_dir / "specs" / "final_spec.md").write_text(
                stdout2.strip(), encoding="utf-8"
            )
    meta = {
        "run_id": run_id,
        "stop_reason": "cursor_only",
        "effective_config": config,
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    manifest = {
        "run_id": run_id,
        "final_round": 1,
        "stop_reason": "cursor_only",
        "artifacts": [],
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("Done (cursor_only). Plan/spec written.")


def _run_openai_only(
    idea: str, run_id: str, run_dir: Path, config: dict, args: argparse.Namespace
) -> None:
    """Review existing plan/spec, produce review + patch."""
    plans = run_dir / "plans"
    specs = run_dir / "specs"
    if not plans.exists() or not specs.exists():
        print("Error: plans/ and specs/ required for --openai-only", file=sys.stderr)
        return
    latest = 1
    plan_file = plans / f"plan_v{latest}.md"
    spec_file = specs / f"spec_v{latest}.md"
    if not plan_file.exists() or not spec_file.exists():
        print(
            f"Error: plan_v{latest}.md and spec_v{latest}.md required", file=sys.stderr
        )
        return
    plan_content = plan_file.read_text(encoding="utf-8", errors="replace")
    spec_content = spec_file.read_text(encoding="utf-8", errors="replace")
    checklist = ""
    for name in ("CHECKLIST.md",):
        p = run_dir / "snapshots" / name
        if p.exists():
            checklist += p.read_text(encoding="utf-8", errors="replace") + "\n"
    from planner.scripts.lib.openai_refiner import call_openai
    from planner.scripts.lib.prompts import openai_review_prompt

    schema_inst = "See refinement.schema.json: overall_score, agreed, must_fix, should_fix, questions, missing_checklist_items, spec_readiness"
    prompt = openai_review_prompt(plan_content, spec_content, checklist, schema_inst)
    review, err = call_openai(prompt)
    if err:
        print(f"OpenAI error: {err}", file=sys.stderr)
        return
    (run_dir / "reviews" / f"review_v{latest}.json").write_text(
        json.dumps(review, indent=2), encoding="utf-8"
    )
    from planner.scripts.lib.render import render_review_md

    (run_dir / "reviews" / f"review_v{latest}.md").write_text(
        render_review_md(review), encoding="utf-8"
    )
    patch = generate_patch(
        review, plan_content, spec_content, checklist, config, latest
    )
    (run_dir / "patches" / f"patch_v{latest}_to_v{latest+1}.md").write_text(
        patch, encoding="utf-8"
    )
    passed, gates = compute_gates(review, config)
    print_gates_summary(passed, gates)


def _run_manual_cursor(
    idea: str,
    run_id: str,
    run_dir: Path,
    config: dict,
    args: argparse.Namespace,
    *,
    bones_available: bool = True,
) -> None:
    """Print prompts, instruct user to drop files."""
    from planner.scripts.lib.prompts import cursor_plan_prompt

    snapshots = run_dir / "snapshots"
    idea_content = (snapshots / "idea.md").read_text(encoding="utf-8", errors="replace")
    plan_tpl = (_planner_path("templates", "plan.template.md")).read_text(
        encoding="utf-8", errors="replace"
    )
    import re

    headings = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", plan_tpl)
    plan_headings = headings.group(1).strip() if headings else ""
    checklist = (
        (snapshots / "CHECKLIST.md").read_text(encoding="utf-8", errors="replace")
        if (snapshots / "CHECKLIST.md").exists()
        else ""
    )
    prompt = cursor_plan_prompt(
        idea_content, checklist[:2000], plan_headings, bones_available=bones_available
    )
    print("=== CURSOR PLAN PROMPT (paste into Cursor) ===\n")
    print(prompt)
    print("\n=== Save output to:", run_dir / "plans" / "plan_v1.md", "===")
    print("Then run again with --openai-only to review.")


def _run_consensus_loop(
    idea: str,
    run_id: str,
    run_dir: Path,
    config: dict,
    args: argparse.Namespace,
    *,
    bones_available: bool = True,
) -> None:
    """Consensus mode: plan phase (each model must pass plan) then spec phase (each model must pass gates)."""
    import re

    from planner.config import SIZE_CAP_FAIL_PLAN_SPEC
    from planner.scripts.lib.cursor_runner import run_plan_mode
    from planner.scripts.lib.openai_refiner import call_openai
    from planner.scripts.lib.plan_review import call_openai_plan_review
    from planner.scripts.lib.prompts import (
        cursor_plan_prompt,
        cursor_revise_plan_prompt,
        cursor_spec_prompt,
        openai_review_prompt,
    )

    extra = _agent_extra_args(args)
    max_rounds = config.get("max_rounds", 8)
    models = config.get(
        "consensus_models", ["gpt-4o", "anthropic.claude-3-5-sonnet-v2:0"]
    )
    plan_threshold = config.get("plan_score_threshold", 95)
    plan_categories = tuple(
        config.get(
            "plan_categories",
            [
                "clarity",
                "completeness",
                "executability",
                "ordering",
                "risk",
                "consistency",
                "testing",
                "docs",
            ],
        )
    )
    snapshots = run_dir / "snapshots"
    idea_content = (snapshots / "idea.md").read_text(encoding="utf-8", errors="replace")
    plan_tpl = (_planner_path("templates", "plan.template.md")).read_text(
        encoding="utf-8", errors="replace"
    )
    spec_tpl = (_planner_path("templates", "spec.template.md")).read_text(
        encoding="utf-8", errors="replace"
    )
    plan_headings = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", plan_tpl)
    plan_headings_str = plan_headings.group(1).strip() if plan_headings else ""
    spec_headings = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", spec_tpl)
    spec_headings_str = spec_headings.group(1).strip() if spec_headings else ""
    checklist_content = ""
    for name in ("CHECKLIST.md",):
        p = snapshots / name
        if p.exists():
            checklist_content += p.read_text(encoding="utf-8", errors="replace") + "\n"
    (run_dir / "plan_reviews").mkdir(exist_ok=True)
    (run_dir / "spec_reviews").mkdir(exist_ok=True)

    # ----- Plan phase -----
    locked_plan_content = ""
    for plan_round in range(1, max_rounds + 1):
        print(f"\n--- Plan phase round {plan_round}/{max_rounds} ---\n")
        plan_path = run_dir / "plans" / f"plan_v{plan_round}.md"
        if args.resume and plan_path.exists() and not args.force:
            plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
            print(f"  [Resume] Loaded plan from {plan_path}")
        else:
            print(f"  [Cursor] Requesting plan (round {plan_round})...")
            prompt = cursor_plan_prompt(
                idea_content,
                checklist_content[:2000],
                plan_headings_str,
                bones_available=bones_available,
            )
            code, stdout, _ = run_plan_mode(
                prompt,
                log_path=run_dir / "logs" / f"cursor_plan_v{plan_round}.log",
                extra_args=extra if extra else None,
            )
            plan_content = stdout.strip() if code == 0 else ""
            if not plan_content:
                print(
                    f"  Cursor plan failed (round {plan_round})",
                    file=sys.stderr,  # noqa: E225
                )
                return
            if len(plan_content.encode("utf-8")) > SIZE_CAP_FAIL_PLAN_SPEC:
                print(
                    f"  Plan exceeds size cap ({SIZE_CAP_FAIL_PLAN_SPEC})",
                    file=sys.stderr,  # noqa: E225
                )
                return
            plan_path.write_text(plan_content, encoding="utf-8")
        all_passed = True
        refinements_per_model = []
        for model_id in models:
            safe_id = model_id.replace(".", "-")
            review_path = (
                run_dir / "plan_reviews" / f"round_{plan_round}_{safe_id}.json"
            )
            print(f"  [OpenAI] Plan review ({model_id})...")
            scores, refs, err = call_openai_plan_review(
                plan_content, model_id, active_categories=plan_categories
            )
            if err:
                print(f"  Model {model_id} failed: {err}", file=sys.stderr)
                all_passed = False
                continue
            payload = {"scores": scores, "refinements": refs}
            review_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            if any(scores.get(c, 0) < plan_threshold for c in plan_categories):
                all_passed = False
                refinements_per_model.append((model_id, refs))
        if all_passed:
            locked_plan_content = plan_content
            print("  Plan consensus passed.")
            break
        if plan_round < max_rounds and refinements_per_model:
            patch = merge_plan_refinements(refinements_per_model)
            (
                run_dir
                / "patches"
                / f"plan_patch_v{plan_round}_to_v{plan_round + 1}.md"
            ).write_text(patch, encoding="utf-8")
            print(
                f"  [Cursor] Revising plan (round {plan_round} -> {plan_round + 1})..."
            )
            revise_prompt = cursor_revise_plan_prompt(
                plan_content, patch, bones_available=bones_available
            )
            code, stdout, _ = run_plan_mode(
                revise_prompt,
                log_path=run_dir / "logs" / f"cursor_plan_v{plan_round + 1}.log",
                extra_args=extra if extra else None,
            )
            idea_content = (
                stdout.strip() if code == 0 and stdout.strip() else plan_content
            )
    if not locked_plan_content:
        print("  Plan consensus not reached after max_rounds.", file=sys.stderr)
        (run_dir / "logs").mkdir(exist_ok=True)
        final_scores_path = run_dir / "logs" / "consensus_final_scores.json"
        final_scores_path.write_text(
            json.dumps(
                {"plan_round": plan_round, "message": "plan consensus not reached"},
                indent=2,
            ),
            encoding="utf-8",
        )
        return
    current_plan = locked_plan_content

    # ----- Spec phase -----
    meta_rounds = []
    for spec_round in range(1, max_rounds + 1):
        print(f"\n--- Spec phase round {spec_round}/{max_rounds} ---\n")
        spec_path = run_dir / "specs" / f"spec_v{spec_round}.md"
        if args.resume and spec_path.exists() and not args.force:
            spec_content = spec_path.read_text(encoding="utf-8", errors="replace")
            print(f"  [Resume] Loaded spec from {spec_path}")
        else:
            print(f"  [Cursor] Requesting spec (round {spec_round})...")
            spec_prompt = cursor_spec_prompt(
                current_plan, spec_headings_str, bones_available=bones_available
            )
            code, stdout, _ = run_plan_mode(
                spec_prompt,
                log_path=run_dir / "logs" / f"cursor_spec_v{spec_round}.log",
                extra_args=extra if extra else None,
            )
            spec_content = stdout.strip() if code == 0 and stdout.strip() else ""
            if not spec_content:
                print(
                    f"  Cursor spec failed (round {spec_round})",
                    file=sys.stderr,  # noqa: E225
                )
                return
            spec_path.write_text(spec_content, encoding="utf-8")
        schema_inst = "Return JSON with overall_score, agreed, must_fix, should_fix, questions, missing_checklist_items, spec_readiness (backend, frontend, infra, tests, docs)."
        reviews = []
        all_gates_passed = True
        for model_id in models:
            safe_id = model_id.replace(".", "-")
            review_path = (
                run_dir / "spec_reviews" / f"round_{spec_round}_{safe_id}.json"
            )
            print(f"  [OpenAI] Spec review ({model_id})...")
            review, err = call_openai(
                openai_review_prompt(
                    current_plan, spec_content, checklist_content, schema_inst
                ),
                model=model_id,
            )
            if err:
                print(f"  Model {model_id} failed: {err}", file=sys.stderr)
                all_gates_passed = False
                continue
            reviews.append(review)
            review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
            passed, gates = compute_gates(review, config)
            if not passed:
                all_gates_passed = False
            meta_rounds.append({"round": spec_round, "model": model_id, "gates": gates})
        if all_gates_passed and len(reviews) == len(models):
            (run_dir / "specs" / "final_spec.md").write_text(
                spec_content, encoding="utf-8"
            )
            meta = {
                "run_id": run_id,
                "consensus": True,
                "plan_rounds": plan_round,
                "spec_rounds": spec_round,
                "final_stop_reason": "passed_gates",
                "effective_config": config,
            }
            (run_dir / "meta.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8"
            )
            (run_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "final_round": spec_round,
                        "stop_reason": "passed_gates",
                        "artifacts": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("  Spec consensus passed. Wrote final_spec.md")
            return
        if spec_round < max_rounds and reviews:
            merged = merge_spec_reviews(reviews)
            patch = generate_patch(
                merged,
                current_plan,
                spec_content,
                checklist_content,
                config,
                spec_round,
            )
            (
                run_dir / "patches" / f"patch_v{spec_round}_to_v{spec_round + 1}.md"
            ).write_text(patch, encoding="utf-8")
            print("  [Cursor] Revising plan for next spec round...")
            revise_prompt = cursor_revise_plan_prompt(
                current_plan, patch, bones_available=bones_available
            )
            code, stdout, _ = run_plan_mode(
                revise_prompt,
                log_path=run_dir
                / "logs"
                / f"cursor_plan_spec_rev_{spec_round + 1}.log",
                extra_args=extra if extra else None,
            )
            current_plan = (
                stdout.strip() if code == 0 and stdout.strip() else current_plan
            )
    (run_dir / "specs" / "final_spec.md").write_text(spec_content, encoding="utf-8")
    (run_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "consensus": True,
                "final_stop_reason": "max_rounds",
                "effective_config": config,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "final_round": max_rounds,
                "stop_reason": "max_rounds",
                "artifacts": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("  Consensus max_rounds reached. Wrote final_spec.md with known gaps.")


def _run_full_loop(
    idea: str,
    run_id: str,
    run_dir: Path,
    config: dict,
    args: argparse.Namespace,
    *,
    bones_available: bool = True,
) -> None:
    """Full refinement loop: Cursor -> OpenAI -> patch -> Cursor until gates pass or max rounds."""
    import re

    from planner.scripts.lib.cursor_runner import run_plan_mode
    from planner.scripts.lib.openai_refiner import call_openai
    from planner.scripts.lib.prompts import (
        cursor_plan_prompt,
        cursor_revise_plan_prompt,
        cursor_spec_prompt,
        openai_review_prompt,
    )
    from planner.scripts.lib.render import render_review_md

    extra = _agent_extra_args(args)
    max_rounds = config.get("max_rounds", 8)
    min_rounds = config.get("min_rounds", 6)
    snapshots = run_dir / "snapshots"
    idea_content = (snapshots / "idea.md").read_text(encoding="utf-8", errors="replace")
    plan_tpl = (_planner_path("templates", "plan.template.md")).read_text(
        encoding="utf-8", errors="replace"
    )
    spec_tpl = (_planner_path("templates", "spec.template.md")).read_text(
        encoding="utf-8", errors="replace"
    )
    plan_headings = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", plan_tpl)
    plan_headings_str = plan_headings.group(1).strip() if plan_headings else ""
    spec_headings = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", spec_tpl)
    spec_headings_str = spec_headings.group(1).strip() if spec_headings else ""
    checklist_content = ""
    for name in ("CHECKLIST.md",):
        p = snapshots / name
        if p.exists():
            checklist_content += p.read_text(encoding="utf-8", errors="replace") + "\n"
    meta_rounds = []
    plan_content = ""
    spec_content = ""
    print(
        f"\nStarting refinement loop (max_rounds={max_rounds}, min_rounds={min_rounds})\n"
    )
    for round_n in range(1, max_rounds + 1):
        print(f"\n--- Round {round_n}/{max_rounds} ---\n")
        plan_path = run_dir / "plans" / f"plan_v{round_n}.md"
        spec_path = run_dir / "specs" / f"spec_v{round_n}.md"
        if args.resume and plan_path.exists() and not args.force:
            print(f"  [Resume] Loading plan/spec from disk (round {round_n})")
            plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
            spec_content = (
                spec_path.read_text(encoding="utf-8", errors="replace")
                if spec_path.exists()
                else ""
            )
        else:
            print(f"  [Cursor] Requesting plan (round {round_n})...")
            prompt = cursor_plan_prompt(
                idea_content,
                checklist_content[:2000],
                plan_headings_str,
                bones_available=bones_available,
            )
            code, stdout, stderr = run_plan_mode(
                prompt,
                log_path=run_dir / "logs" / f"cursor_plan_v{round_n}.log",
                extra_args=extra if extra else None,
            )
            plan_content = stdout.strip() if code == 0 else ""
            if not plan_content:
                print(
                    f"Cursor plan failed (round {round_n})",
                    file=sys.stderr,  # noqa: E225
                )
                return
            plan_path.write_text(plan_content, encoding="utf-8")
            print(f"  [Cursor] Requesting spec (round {round_n})...")
            spec_prompt = cursor_spec_prompt(
                plan_content, spec_headings_str, bones_available=bones_available
            )
            code2, stdout2, _ = run_plan_mode(
                spec_prompt,
                log_path=run_dir / "logs" / f"cursor_spec_v{round_n}.log",
                extra_args=extra if extra else None,
            )
            spec_content = stdout2.strip() if code2 == 0 and stdout2.strip() else ""
            if spec_content:
                spec_path.write_text(spec_content, encoding="utf-8")
        print(f"  [OpenAI] Requesting review (round {round_n})...")
        schema_inst = "Return JSON with overall_score, agreed, must_fix, should_fix, questions, missing_checklist_items, spec_readiness (backend, frontend, infra, tests, docs)."
        review, err = call_openai(
            openai_review_prompt(
                plan_content, spec_content, checklist_content, schema_inst
            )
        )
        if err:
            print(f"OpenAI error (round {round_n}): {err}", file=sys.stderr)
            return
        (run_dir / "reviews" / f"review_v{round_n}.json").write_text(
            json.dumps(review, indent=2), encoding="utf-8"
        )
        (run_dir / "reviews" / f"review_v{round_n}.md").write_text(
            render_review_md(review), encoding="utf-8"
        )
        passed, gates = compute_gates(review, config)
        meta_rounds.append(
            {
                "round": round_n,
                "gates": gates,
                "stop_reason": "passed_gates" if passed else None,
            }
        )
        print_gates_summary(passed, gates, round_n)
        if passed and round_n >= min_rounds:
            (run_dir / "specs" / "final_spec.md").write_text(
                spec_content, encoding="utf-8"
            )
            meta = {
                "run_id": run_id,
                "rounds": meta_rounds,
                "final_stop_reason": "passed_gates",
                "effective_config": config,
            }
            (run_dir / "meta.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8"
            )
            manifest = {
                "run_id": run_id,
                "final_round": round_n,
                "stop_reason": "passed_gates",
                "artifacts": [],
            }
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
            return
        if passed and round_n < min_rounds:
            print(
                f"  Gates passed but round {round_n} < min_rounds ({min_rounds}). Continuing refinement.",
                file=sys.stderr,
            )
        if round_n < max_rounds:
            patch = generate_patch(
                review, plan_content, spec_content, checklist_content, config, round_n
            )
            (run_dir / "patches" / f"patch_v{round_n}_to_v{round_n+1}.md").write_text(
                patch, encoding="utf-8"
            )
            print(
                f"  [Cursor] Requesting revised plan (round {round_n} → {round_n + 1})..."
            )
            revise_prompt = cursor_revise_plan_prompt(
                plan_content, patch, bones_available=bones_available
            )
            code3, stdout3, _ = run_plan_mode(
                revise_prompt,
                log_path=run_dir / "logs" / f"cursor_plan_v{round_n+1}.log",
                extra_args=extra if extra else None,
            )
            idea_content = (
                stdout3.strip() if code3 == 0 and stdout3.strip() else plan_content
            )
    (run_dir / "specs" / "final_spec.md").write_text(spec_content, encoding="utf-8")
    meta = {
        "run_id": run_id,
        "rounds": meta_rounds,
        "final_stop_reason": "max_rounds",
        "effective_config": config,
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    manifest = {
        "run_id": run_id,
        "final_round": max_rounds,
        "stop_reason": "max_rounds",
        "artifacts": [],
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Max rounds ({max_rounds}) reached. Final spec written with Known Gaps.")


def main() -> int:
    parser = argparse.ArgumentParser(prog="refine")
    sub = parser.add_subparsers(dest="cmd", required=True)
    init_p = sub.add_parser("init", help="Init workspace + snapshot idea")
    init_p.add_argument("idea", help="Idea slug")
    init_p.add_argument(
        "--refresh-input", action="store_true", help="Force refresh idea snapshot"
    )
    init_p.set_defaults(func=init_cmd)
    run_p = sub.add_parser("run", help="Run refinement loop")
    run_p.add_argument("idea", help="Idea slug")
    run_p.add_argument("--run-id", help="Use specific run_id")
    run_p.add_argument("--max-rounds", type=int, default=8)
    run_p.add_argument("--cursor-only", action="store_true")
    run_p.add_argument("--openai-only", action="store_true")
    run_p.add_argument("--manual-cursor", action="store_true")
    run_p.add_argument("--resume", action="store_true")
    run_p.add_argument("--force", action="store_true")
    run_p.add_argument(
        "--no-manual-fallback",
        action="store_true",
        help="Do not auto-switch to manual on CLI failure",
    )
    run_p.add_argument(
        "--trust",
        action="store_true",
        help="Pass --trust to agent (trust workspace without prompting)",
    )
    run_p.add_argument(
        "--yolo", action="store_true", help="Pass --yolo to agent (alias for --force)"
    )
    run_p.add_argument(
        "--agent-force",
        dest="agent_force",
        action="store_true",
        help="Pass -f to agent (force allow commands)",
    )
    run_p.add_argument(
        "--consensus",
        action="store_true",
        help="Multi-model consensus: each model must pass plan then spec",
    )
    run_p.add_argument(
        "--models",
        type=str,
        default=None,
        metavar="MODELS",
        help="Comma-separated model ids for consensus (default: from config)",
    )
    run_p.set_defaults(func=run_cmd)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
