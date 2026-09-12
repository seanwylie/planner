"""
Cursor CLI wrapper. Runs agent --mode=plan with prompts.
Tool contract: detect agent, run --help, smoke test; auto-fallback to manual if fails.
"""
import shutil
import subprocess
from pathlib import Path

AGENT_CMD = "agent"

# Planner is quality-scoped, not time-scoped. Use a generous default so Cursor can finish.
PLAN_MODE_TIMEOUT = 7200  # 2 hours


def find_agent() -> tuple[bool, str | None]:
    """Check if agent is on PATH and runnable. Return (found, version_or_error)."""
    path = shutil.which(AGENT_CMD)
    if not path:
        return False, f"{AGENT_CMD} not found on PATH"
    try:
        result = subprocess.run(
            [AGENT_CMD, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False, f"{AGENT_CMD} --help returned {result.returncode}"
        return True, None
    except subprocess.TimeoutExpired:
        return False, f"{AGENT_CMD} --help timed out"
    except Exception as e:
        return False, str(e)


def smoke_test_plan_mode(extra_args: list[str] | None = None) -> tuple[bool, str]:
    """Run 1-line plan-mode smoke prompt. Return (success, error_msg)."""
    cmd = [AGENT_CMD, "-p", "Output exactly: OK", "--mode=plan"]
    if extra_args:
        cmd = cmd[:1] + extra_args + cmd[1:]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd(),
        )
        if result.returncode != 0:
            return (
                False,
                f"plan-mode smoke test returned {result.returncode}: {result.stderr[:500]}",
            )
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "plan-mode smoke test timed out"
    except Exception as e:
        return False, str(e)


def run_plan_mode(
    prompt: str,
    log_path: Path | None = None,
    timeout: int | None = None,
    extra_args: list[str] | None = None,
) -> tuple[int, str, str]:
    """
    Run agent --mode=plan -p "<prompt>". Return (exit_code, stdout, stderr).
    If log_path, write stdout+stderr (redacted) to log.
    timeout: seconds (default PLAN_MODE_TIMEOUT; planner is quality-scoped).
    extra_args: additional agent flags (e.g. ["--trust", "--yolo", "-f"]).
    """
    effective_timeout = timeout if timeout is not None else PLAN_MODE_TIMEOUT
    cmd = [AGENT_CMD, "--mode=plan", "-p", prompt]
    if extra_args:
        cmd = cmd[:1] + extra_args + cmd[1:]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            cwd=Path.cwd(),
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if log_path:
            from planner.scripts.lib.io import redact, truncate_for_log

            log_path.parent.mkdir(parents=True, exist_ok=True)
            content = f"STDOUT:\n{truncate_for_log(redact(stdout))}\n\nSTDERR:\n{truncate_for_log(redact(stderr))}"  # noqa: E231
            log_path.write_text(content, encoding="utf-8", errors="replace")
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        err = f"agent timed out after {effective_timeout}s"
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(f"ERROR: {err}", encoding="utf-8")
        return -1, "", err
    except Exception as e:
        err = str(e)
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(f"ERROR: {err}", encoding="utf-8")
        return -1, "", err
