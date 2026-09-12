# Patch v{{N}} → v{{N_PLUS_1}}

<!--
TEMPLATE_VERSION: v2.1.0
REQUIRED_HEADINGS: Apply Order, Must-Fix, Checklist Gaps, Should-Fix, Do Not Change, Acceptance Gates
-->

## Apply Order

1. Must-fix (apply in order)
2. Checklist gaps (add missing items)
3. Should-fix (apply in order)

## Must-Fix

| ID  | Area | Change | Acceptance | Risk | References |
| --- | ---- | ------ | ---------- | ---- | ---------- |
|     |      |        |            |      |            |

## Checklist Gaps

- CHECKLIST_KEY.1: ...
- FLAGS.2: ...

## Should-Fix

| ID  | Area | Change | Acceptance | Risk | References |
| --- | ---- | ------ | ---------- | ---- | ---------- |
|     |      |        |            |      |            |

## Do Not Change

- Preserve decisions that were correct and should not churn.

## Acceptance Gates

- overall_score >= {{MIN_SCORE}}
- must_fix_count == 0
- questions_count == 0
- spec_readiness.backend >= {{MIN_BACKEND}}
- spec_readiness.frontend >= {{MIN_FRONTEND}}
- spec_readiness.tests >= {{MIN_TESTS}}
- spec_readiness.docs >= {{MIN_DOCS}}
