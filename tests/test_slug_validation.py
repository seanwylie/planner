"""Tests for planner.scripts.lib.validation — slug validation."""
import pytest

from planner.scripts.lib.validation import MAX_SLUG_LENGTH, SLUG_RE, validate_slug


class TestSlugRegex:
    """Test SLUG_RE directly."""

    @pytest.mark.parametrize(
        "slug",
        [
            "my-idea",
            "a",
            "abc123",
            "ops-dashboard-planner-tab",
            "x",
            "123",
            "a-b-c",
            "feature1",
        ],
    )
    def test_valid_slugs(self, slug: str) -> None:
        assert SLUG_RE.match(slug), f"{slug!r} should match"

    @pytest.mark.parametrize(
        "slug",
        [
            "My-Idea",
            "ABC",
            "camelCase",
        ],
    )
    def test_invalid_slug_uppercase(self, slug: str) -> None:
        assert not SLUG_RE.match(slug), f"{slug!r} should not match (uppercase)"

    @pytest.mark.parametrize(
        "slug",
        [
            "my_idea",
            "foo_bar_baz",
        ],
    )
    def test_invalid_slug_underscores(self, slug: str) -> None:
        assert not SLUG_RE.match(slug), f"{slug!r} should not match (underscores)"

    @pytest.mark.parametrize(
        "slug",
        [
            "my idea",
            " leading",
            "trailing ",
        ],
    )
    def test_invalid_slug_spaces(self, slug: str) -> None:
        assert not SLUG_RE.match(slug), f"{slug!r} should not match (spaces)"

    @pytest.mark.parametrize(
        "slug",
        [
            "../etc",
            "foo/bar",
            "..",
            "./foo",
        ],
    )
    def test_invalid_slug_path_traversal(self, slug: str) -> None:
        assert not SLUG_RE.match(slug), f"{slug!r} should not match (path traversal)"

    @pytest.mark.parametrize(
        "slug",
        [
            "my@idea",
            "my.idea",
            "my!idea",
            "my#idea",
        ],
    )
    def test_invalid_slug_special_chars(self, slug: str) -> None:
        assert not SLUG_RE.match(slug), f"{slug!r} should not match (special chars)"

    @pytest.mark.parametrize(
        "slug",
        [
            "-leading",
            "trailing-",
            "-both-",
        ],
    )
    def test_invalid_slug_leading_trailing_hyphen(self, slug: str) -> None:
        assert not SLUG_RE.match(
            slug
        ), f"{slug!r} should not match (leading/trailing hyphen)"

    @pytest.mark.parametrize(
        "slug",
        [
            "my--idea",
            "a---b",
        ],
    )
    def test_invalid_slug_consecutive_hyphens(self, slug: str) -> None:
        assert not SLUG_RE.match(
            slug
        ), f"{slug!r} should not match (consecutive hyphens)"


class TestValidateSlug:
    """Test validate_slug() function."""

    def test_valid_slug_returned(self) -> None:
        assert validate_slug("my-idea") == "my-idea"

    def test_valid_slug_stripped(self) -> None:
        assert validate_slug("  my-idea  ") == "my-idea"

    def test_valid_single_char(self) -> None:
        assert validate_slug("x") == "x"

    def test_valid_numeric_only(self) -> None:
        assert validate_slug("123") == "123"

    def test_valid_max_length(self) -> None:
        slug = "a" * MAX_SLUG_LENGTH
        assert validate_slug(slug) == slug

    def test_invalid_empty(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            validate_slug("")

    def test_invalid_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            validate_slug("   ")

    def test_invalid_too_long(self) -> None:
        slug = "a" * (MAX_SLUG_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            validate_slug(slug)

    def test_invalid_uppercase(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("My-Idea")

    def test_invalid_path_traversal(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("../etc")

    def test_invalid_slash(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("foo/bar")

    def test_invalid_consecutive_hyphens(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("my--idea")

    def test_invalid_leading_hyphen(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("-leading")

    def test_invalid_trailing_hyphen(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("trailing-")

    def test_invalid_underscore(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("my_idea")

    def test_invalid_special_chars(self) -> None:
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("my@idea")
