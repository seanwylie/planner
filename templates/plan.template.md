# Implementation Plan: {{IDEA_TITLE}}

<!--
TEMPLATE_VERSION: v2.1.0
REQUIRED_HEADINGS: Existing Alignment, Summary, Architecture, Files, APIs, Data, Feature Flags, Analytics, Security & Privacy, Rollout, Tests, Docs, Risks, Open Questions, Ordered Steps
-->

## Existing Alignment

**Before drafting, scour the repo.** List pre-existing docs and code that align with this idea. Do not reinvent the wheel — leverage and extend.

- **Docs:** README, `docs/`, architecture notes, ADRs — which apply?
- **Code:** Shared libraries, similar handlers, existing tests, patterns to follow
- **Systems:** Feature flags, analytics, inventories, layout — what to reuse if present?
- **Gaps:** What does not exist and must be built from scratch?

## Summary

1–2 paragraphs describing what will be built and why.

## Architecture

- Components involved
- Major flows (optional bullet diagram)
- Dependencies and boundaries
- VERIFY items (if any) with grep targets

## Files

List file-level changes. Prefer explicit paths.

- `path/to/file.ext`
  - Change summary
  - Notes / invariants

## APIs

If applicable:

- Endpoints to add/change
- Request/response shapes
- Authz rules
- Error handling

## Data

If applicable:

- DynamoDB tables/items/keys changes
- Migrations/backfills
- Caching implications
- Data retention

## Feature Flags

- New flags? (IDs/names)
- Fail-closed behavior
- Env-gating policy
- Rollout plan (dev → staging → prod)

## Analytics

- New events? (IDs + payload fields)
- Call sites
- No PII confirmation

## Security & Privacy

- Threat considerations
- PII/PHI: confirm none is logged/sent
- Secrets handling
- Least privilege

## Rollout

- Steps to ship safely
- Backward compatibility
- Monitoring expectations
- Rollback strategy

## Tests

- Unit tests (paths)
- Integration tests (paths)
- Edge cases
- Regression areas

## Docs

- Docs Impact: None | Update Existing | New System
- Docs Target: path to the host doc to add or update (if not None)
- Systems Index Update: true|false (if the host keeps an inventory)
- Any other docs updates (runbooks, inventory, etc.)

## Risks

- Risk list with mitigations

## Open Questions

- Questions that block implementation or require clarification

## Ordered Steps

1. Step 1
2. Step 2
3. Step 3
