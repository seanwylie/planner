# Spec: {{IDEA_TITLE}}

<!--
TEMPLATE_VERSION: v2.1.0
REQUIRED_HEADINGS: Overview, Existing Alignment, Architecture, Scope, File Changes, Backend, Frontend, Infra, Feature Flags, Analytics, Security & Privacy, Tests, Docs, Implementation Steps, Acceptance Criteria, Known Gaps
-->

## Overview

- **Status:** Ready | Draft (Gaps Remaining)
- **Spec Version:** v{{SPEC_VERSION}}
- **Run ID:** {{RUN_ID}}
- **Owner:** {{OWNER}}
- **Last Updated:** {{DATE}}

## Existing Alignment

- Pre-existing docs and code to leverage (from discovery).
- Systems/modules to extend; what is built from scratch.

## Architecture

- High-level overview
- Optional diagram (ASCII/mermaid)
- Key decisions and invariants

## Scope

### In Scope

- ...

### Out of Scope

- ...

## File Changes

> Provide file-by-file change list with short summaries.

- `path/to/file`
  - What changes
  - Notes

## Backend

- APIs/endpoints
- Data model changes
- Background jobs / Lambdas
- Error handling + retries
- Caching + invalidation
- VERIFY items (grep targets) if uncertain

## Frontend

- Screens/components
- Navigation impacts
- State management changes
- Loading/empty/error states
- Accessibility considerations (if relevant)

## Infra

- CDK stacks impacted
- New resources
- Limits considerations (e.g., 500-resource)
- Env config / AppConfig changes
- Monitoring/alarms/logging adjustments

## Feature Flags

- Flags to add/use
- Default values
- Fail-closed rules
- Rollout steps

## Analytics

- Events to add/change
- Payload fields (no PII)
- Call sites

## Security & Privacy

- Confirm no PII in analytics/logs
- AuthZ requirements
- Secrets handling
- Data access boundaries

## Tests

- Unit tests
- Integration tests
- Manual verification checklist

## Docs

- **Docs Impact:** None | Update Existing | New System
- **Docs Target:** path to the host doc to add or update (required if not None)
- **Systems Index Update:** true|false
- Steps:
  - If **New System**: create the target doc and update any host inventory
  - If **Update Existing**: update the target doc and inventory if needed

## Implementation Steps

1. Backend changes
2. Frontend changes
3. Infra changes
4. Tests
5. Docs

## Acceptance Criteria

- [ ] Functional requirements satisfied
- [ ] No PII in analytics/logs
- [ ] Feature flags fail closed and are env-gated
- [ ] Tests added and passing
- [ ] Docs updated as declared

## Known Gaps

- List remaining must_fix items / unanswered questions if Status is Draft (Gaps Remaining)
