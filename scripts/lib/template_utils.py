"""Parse REQUIRED_HEADINGS and REQUIRED_SECTIONS from templates."""
import re


def parse_required_headings(content: str) -> list[str]:
    """Extract REQUIRED_HEADINGS: X, Y, Z from template content."""
    m = re.search(r"REQUIRED_HEADINGS:\s*([^\n]+)", content)
    if not m:
        return []
    raw = m.group(1).strip()
    return [h.strip() for h in raw.split(",") if h.strip()]


def parse_required_sections(content: str) -> list[str]:
    """Extract REQUIRED_SECTIONS: X, Y, Z from template content."""
    m = re.search(r"REQUIRED_SECTIONS:\s*([^\n]+)", content)
    if not m:
        return []
    raw = m.group(1).strip()
    return [s.strip() for s in raw.split(",") if s.strip()]


def validate_headings(md_content: str, required: list[str]) -> list[str]:
    """Check markdown for required ## headings. Return list of missing."""
    present = set()
    for line in md_content.splitlines():
        line = line.strip()
        if line.startswith("## "):
            present.add(line[3:].strip())
    missing = []
    for h in required:
        if h not in present:
            missing.append(h)
    return missing
