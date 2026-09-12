# Planner Checklist — Generic Engineering

<!--
CHECKLIST_VERSION: v2.1.0
ID_PREFIX: GEN
-->

Stable IDs for generic engineering concerns. Use in plans/specs; OpenAI references these in `missing_checklist_items`. Loader validates IDs against this list.

## Generic IDs

| ID     | Item                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------- |
| GEN-0  | Existing Alignment: scoured repo for pre-existing docs/code; plan lists what to leverage vs. build from scratch |
| GEN-1  | New events defined, call sites listed, no PII in payloads                                                       |
| GEN-2  | Feature flags: new flag rollout plan, fail-closed, env-gated                                                    |
| GEN-3  | CDK / Infra: stack impact, 500-resource limit, env config                                                       |
| GEN-4  | Unit and integration tests specified, paths listed                                                              |
| GEN-5  | Docs impact declared; target path if Update/New; index update if New                                            |
| GEN-6  | Security & privacy: no PII in logs/analytics, secrets handling                                                  |
| GEN-7  | APIs: endpoints, request/response shapes, authz, error handling                                                 |
| GEN-8  | Data: schema changes, migrations, caching, retention                                                            |
| GEN-9  | Rollout: backward compatibility, monitoring, rollback strategy                                                  |
| GEN-10 | File changes: explicit paths, change summaries, invariants                                                      |
