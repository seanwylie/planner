# Example: health-check endpoint

<!--
TEMPLATE_VERSION: v2.1.0
REQUIRED_SECTIONS: Problem, Goals, Non-Goals, Constraints, Assumptions, Current State, Existing Alignment, Proposed Approach, Acceptance Criteria, Open Questions
-->

## Problem

Operators cannot tell whether the process is up without reading logs. A fictional
sample service needs a cheap liveness signal.

## Goals

- [ ] Add `GET /health` that returns `{"status": "ok"}` with HTTP 200
- [ ] Cover the handler with one unit test
- [ ] Document the route in the service README

## Non-Goals

- [ ] Authentication
- [ ] Dependency checks (database, cache)
- [ ] Metrics or dashboards

## Constraints

- No new infrastructure
- No secrets in the response
- Keep the change inside the sample service tree

## Assumptions

- The host repo already has an HTTP app and a test runner

## Current State

This is a fictional example idea. It is not tied to a live product.

## Existing Alignment

Reuse the host app's existing router and test layout. Do not invent a second
framework.

## Proposed Approach

One handler, one test, one README sentence. Stop there.

## Acceptance Criteria

- [ ] `GET /health` returns 200 and `{"status": "ok"}`
- [ ] The unit test fails if the route is missing
- [ ] No new dependencies

## Open Questions

- None. If the host repo has no HTTP app, this idea is the wrong example.
