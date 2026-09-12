"""
Planner gates config. Effective config is snapshotted into runs/{run_id}/snapshots/effective_config.json.
Replay uses that file, not this module.
"""

PROMPT_BUNDLE_VERSION = "v2.1.0"

DEFAULTS = {
    "min_score": 5,
    "max_rounds": 8,
    "min_rounds": 6,  # Require at least this many rounds before accepting a pass
    "require_zero_must_fix": True,
    "require_zero_questions": True,
    "require_zero_high_risk_should_fix": True,
    "min_readiness_backend": 90,
    "min_readiness_frontend": 90,
    "min_readiness_infra": 75,
    "min_readiness_tests": 90,
    "min_readiness_docs": 90,
}

# Consensus mode: multi-model plan/spec review (OpenAI + Bedrock; no mini)
CONSENSUS_MODELS = ["gpt-4o", "anthropic.claude-3-5-sonnet-v2:0"]
PLAN_SCORE_THRESHOLD = 95
PLAN_CATEGORIES = (
    "clarity",
    "completeness",
    "executability",
    "ordering",
    "risk",
    "consistency",
    "testing",
    "docs",
)
CONSENSUS_MIN_MODELS = (
    2  # Require at least this many models to pass (skip one if unavailable)
)

# Artifact size caps (bytes)
SIZE_CAP_WARN_PLAN_SPEC = 50 * 1024  # 50KB
SIZE_CAP_FAIL_PLAN_SPEC = 200 * 1024  # 200KB
SIZE_CAP_FAIL_REVIEW_JSON = 200 * 1024  # 200KB
LOG_TRUNCATE_BYTES = 100 * 1024  # 100KB per log file

# Execute: number of post-implementation fix-up passes ("scan what you did, apply fixes")
EXECUTE_FIX_PASSES = 3
