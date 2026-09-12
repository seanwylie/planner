"""Slug validation for planner idea names. Single source of truth for the canonical regex."""
from __future__ import annotations

import re

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_SLUG_LENGTH = 64


def validate_slug(slug: str) -> str:
    """
    Validate and return a cleaned slug.

    Strips whitespace, checks regex (lowercase alphanumeric + hyphens, no leading/trailing/
    consecutive hyphens, no special chars), and enforces max length.

    Raises ValueError with a descriptive message on failure.
    Returns the validated slug on success.
    """
    slug = slug.strip()
    if not slug:
        raise ValueError("Slug must not be empty")
    if len(slug) > MAX_SLUG_LENGTH:
        raise ValueError(
            f"Slug too long ({len(slug)} chars, max {MAX_SLUG_LENGTH}): {slug[:20]}..."
        )
    if not SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug: {slug!r}. "
            "Slugs must contain only lowercase letters, digits, and single hyphens "
            "(no leading/trailing hyphens, no consecutive hyphens, no special characters)."
        )
    return slug
