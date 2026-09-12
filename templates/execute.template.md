# Execution Invariants

<!--
TEMPLATE_VERSION: v2.1.0
-->

## Invariants

- Do not change files outside the spec's scope unless necessary; if necessary, explain why.
- Do not introduce new dependencies without explicitly calling it out and justifying it.
- Do not invent file paths; if unsure, add a `VERIFY:` TODO with a grep target.
- Run tests relevant to the changes; add tests if coverage is missing.
- Update documentation if the spec declares docs impact.

## Phase Discipline

Work in phases:

1. Backend + shared code
2. Frontend
3. Infra/CDK
4. Tests
5. Docs

After each phase:

- Summarize what changed (files and key behaviors).
- List what remains.
- Call out any risk or uncertainty.
