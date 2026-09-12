"""
Prompt bundle for Cursor plan/spec and OpenAI review.
PROMPT_BUNDLE_VERSION from planner.config.
"""

# Reviewer context is the host repository, not a specific product.
HOST_PRODUCT_SUMMARY = """
You are reviewing a plan and spec for the repository the operator pointed Planner at.
Align with that repo's existing docs, code, tests, and conventions. Do not invent a
product, stack, or file layout that is not in the idea or the repo.
"""

# Allow running from project root (PYTHONPATH=.)
try:
    from planner.config import PROMPT_BUNDLE_VERSION
except ImportError:
    PROMPT_BUNDLE_VERSION = "v2.1.0"


def cursor_plan_prompt(
    idea_content: str,
    checklist_keys: str,
    plan_template_headings: str,
    bones_available: bool = True,
) -> str:
    """Prompt for Cursor plan mode. Includes discovery-first instruction."""
    bones_bullet = (
        "- **bones/** directory (optional architectural notes; present in this workspace)\n"
        if bones_available
        else ""
    )
    return f"""You are planning an implementation for the host repository. Follow these steps strictly.

**Product context:** Use the idea below and the repo in front of you. Align with existing docs and code. Do not assume a product, stack, or path that is not there.

**Rigor standard:** The plan and spec will be reviewed to implementation-ready, safety-critical standards (e.g. space-flight software): no hand-waving, no TBDs, no vague sections. Include explicit error handling, edge cases, and traceability to the idea. If a section cannot be made concrete yet, say so and state what is needed to resolve it.

## Step 1: Discovery (REQUIRED — do this first)
Scour the repo for pre-existing docs and code that align with this idea. Search:
- README, docs/, architecture notes, ADRs
{bones_bullet}- Shared libraries, similar handlers, existing tests
- Feature flags, analytics, or inventory files if the host uses them

List what you found and how the plan will leverage it. Do NOT reinvent the wheel.

## Step 2: Draft the plan
Using the idea below, produce a full implementation plan.

**Required headings (include all):**
{plan_template_headings}

**Checklist areas to address:**
{checklist_keys}

**Evidence rules:**
- Cite existing file paths you expect to touch
- If unsure whether a module exists, say "VERIFY: grep ..." with a grep target
- Do not invent file paths

## Idea

{idea_content}

Output the plan as markdown with all required headings. Start with "Existing Alignment" section.
"""  # noqa: E231,E221,E222,E702


def cursor_spec_prompt(
    plan_content: str,
    spec_template_headings: str,
    bones_available: bool = True,
) -> str:
    """Prompt for Cursor to produce spec from plan. Use bones for architectural guidance when available."""
    bones_guidance = (
        " Align with the optional **bones/** directory for architectural guidance where it exists."
        if bones_available
        else ""
    )
    return f"""Produce an implementation spec from this plan. Follow the spec template.

**Rigor standard:** The spec will be reviewed to implementation-ready, safety-critical standards. Every section must be concrete enough to implement without guessing: explicit APIs, error paths, edge cases, and acceptance criteria. No TBDs or hand-waving; if something is out of scope, say so explicitly.{bones_guidance}

**CRITICAL:** Output the COMPLETE spec as your response. Do NOT write to files. Do NOT output a summary, changelog, or "what changed" — the entire spec MUST appear in your response. Your stdout is captured; we need the full spec text.

**Required headings:**
{spec_template_headings}

**Plan:**

{plan_content}

Output the complete spec as markdown with all required headings. Include all section content, not a summary.
"""  # noqa: E231,E221,E222,E702


def cursor_revise_plan_prompt(
    plan_content: str, patch_content: str, bones_available: bool = True
) -> str:
    """Prompt for Cursor to revise plan using feedback; reason against project rules, docs, and optionally bones."""
    reason_sources = (
        "Reason against the project's .cursor rules (MDC), documentation (docs/), the optional **bones/** directory if present, and existing patterns."
        if bones_available
        else "Reason against the project's .cursor rules (MDC), documentation (docs/), and existing patterns."
    )
    prefer_line = (
        "If feedback contradicts project rules, docs, or bones notes, prefer the project's rules, docs, and bones."
        if bones_available
        else "If feedback contradicts project rules or docs, prefer the project's rules and docs."
    )
    return f"""Revise the plan below using the feedback patch. Do NOT accept suggestions verbatim.

**Critical:** {reason_sources} Only apply a suggestion if it aligns with project conventions and you judge it to be a genuinely good idea; otherwise skip it or adapt it. {prefer_line}

**Current plan:**

{plan_content}

**Patch to apply:**

{patch_content}

Output the complete revised plan as markdown. Preserve all required headings. Apply feedback selectively based on your reasoning.
"""  # noqa: E231,E221,E222,E702


def idea_generation_prompt(description: str, template_content: str) -> str:
    """Prompt for Cursor to expand a short description into a full idea file using the template."""
    return f"""You are expanding a rough idea into a full idea document.

**Template to follow (sections and structure):**
```
{template_content}
```

**Rough idea (one paragraph):**
{description}

**Instructions:** Produce a complete idea document in markdown that follows the template structure above. Use the exact section headings from the template. Fill each section with content that reflects the rough idea. Output only the markdown document — no preamble, no explanation."""  # noqa: E231,E221,E222,E702


def idea_edit_prompt(current_content: str, instructions: str) -> str:
    """Prompt for Cursor to apply vague modification instructions to an existing idea file."""
    return f"""You are applying reviewer/author modifications to an existing idea document.

**Current idea document:**
```
{current_content[:14000]}
```

**Modification instructions:**
{instructions}

**Instructions:** Produce the complete revised idea document in markdown. Apply the requested modifications while keeping the same section structure. Output only the markdown — no preamble, no explanation."""  # noqa: E231,E221,E222,E702


def openai_review_prompt(
    plan_content: str,
    spec_content: str,
    checklist_content: str,
    schema_instruction: str,
) -> str:
    """Prompt for OpenAI review. Output must be valid JSON matching the schema."""
    return f"""You are an expert reviewer of implementation plans for the host repository.

**Product context:**
{HOST_PRODUCT_SUMMARY.strip()}

**Review standard:** Hold the plan and spec to implementation-ready standards: no ambiguity, explicit error handling and edge cases, clear acceptance criteria, traceability to the idea and checklist. Be strict: when in doubt, prefer must_fix over should_fix; only give spec_readiness 90+ when the spec is genuinely implementation-ready for that area with no gaps or TBDs. Flag any vague sections, missing error paths, or hand-waving as must_fix or questions. Review the plan and spec below.

**Output format:** JSON only. No markdown, no prose. Valid JSON matching this schema:
{schema_instruction}

**Plan:**
{plan_content[:15000]}

**Spec:**
{spec_content[:15000]}

**Checklist (reference for missing_checklist_items and validation):**
{checklist_content[:5000]}

**Quality requirements:**
- overall_score: integer 1–5 only (1=reject, 5=pass; NOT a percentage; NOT 0–100). Reserve 5 for specs that are truly implementation-ready with no obvious gaps.
- must_fix items MUST have concrete_change (>=20 chars) and acceptance_criteria (>=15 chars)
- category and risk_level required for each issue
- spec_readiness: realistic 0–100 scores per area (backend, frontend, infra, tests, docs). Only 90+ when the spec is complete and unambiguous for that area.
- missing_checklist_items: use exact IDs from checklist (e.g. GEN-0)
- Do not output empty/low-signal review (all lists empty + all readiness 0 or 100). Surface real issues.

Return only the JSON object. No other text.
"""  # noqa: E231,E221,E222,E702


def execute_fix_pass_prompt(pass_number: int, bones_available: bool = True) -> str:
    """Prompt for a post-execute fix-up pass: scan changes and apply fixes. Use bones if available."""
    bones_instruction = (
        " Use the optional **bones/** directory as architectural guidance when it is present."
        if bones_available
        else ""
    )
    return f"""Scan the changes you just made (and the current state of the repo for this feature). Identify any issues: alignment with .cursor rules (MDC) and docs, consistency, obvious bugs or gaps.{bones_instruction}

Apply fixes you can identify. Be concise. Only change what needs fixing. This is fix-up pass {pass_number}."""
