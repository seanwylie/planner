"""
Atomic writes, redaction, and size caps enforcement.
"""
import hashlib
import re
from pathlib import Path

# Redaction patterns
MASK_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{10,}"), "sk-***REDACTED***"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA***REDACTED***"),
    (
        re.compile(
            r"-----BEGIN .* PRIVATE KEY-----[^\n]*-----END .* PRIVATE KEY-----",
            re.DOTALL,
        ),
        "***PRIVATE_KEY_REDACTED***",
    ),
]


def redact(text: str) -> str:
    """Apply redaction patterns. Never log env vars — caller must not pass them."""
    if not text or not isinstance(text, str):
        return text
    out = text
    for pattern, replacement in MASK_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def truncate_for_log(text: str, max_bytes: int = 100 * 1024) -> str:
    """Truncate long text for log storage."""
    if not text:
        return text
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n...[truncated]"


def sha256_content(content: str | bytes) -> str:
    """Compute SHA256 hex digest of content."""
    if isinstance(content, str):
        content = content.encode("utf-8", errors="replace")
    return hashlib.sha256(content).hexdigest()


def short_hash(content: str | bytes, length: int = 6) -> str:
    """Short hash for run_id config component."""
    return sha256_content(content)[:length]


def atomic_write(
    path: Path | str,
    content: str,
    redact_content: bool = False,
    check_size: bool = True,
) -> None:
    """
    Write content atomically (write to temp, rename).
    If redact_content, apply redaction before writing.
    If check_size, enforce size caps and warn/fail per config.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if redact_content:
        content = redact(content)
    raw = content.encode("utf-8", errors="replace")
    size = len(raw)
    # Size caps: plan/spec warn 50KB, fail 200KB; review json fail 200KB
    try:
        from planner.config import SIZE_CAP_FAIL_PLAN_SPEC, SIZE_CAP_WARN_PLAN_SPEC
    except ImportError:
        SIZE_CAP_WARN_PLAN_SPEC = 50 * 1024
        SIZE_CAP_FAIL_PLAN_SPEC = 200 * 1024
    if check_size:
        if size > SIZE_CAP_FAIL_PLAN_SPEC:
            raise ValueError(
                f"Artifact too large: {path} ({size} bytes > {SIZE_CAP_FAIL_PLAN_SPEC})"
            )
        if size > SIZE_CAP_WARN_PLAN_SPEC:
            import sys

            print(f"Warning: large artifact {path} ({size} bytes)", file=sys.stderr)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(raw)
    tmp.rename(path)


def read_safe(path: Path | str) -> str:
    """Read file or return empty string if missing."""
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")
