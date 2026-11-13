# Strategy Lab — removed surfaces and single ownership

**Status:** CURRENT INVARIANTS. The old shell corrective campaign is complete; its detailed module/function inventory and tests are retained in the [full historical page](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md).

## Current ownership

The packaged asynchronous job has one [Python owner](STRATEGY_LAB_PYTHON_MIGRATION.md), not a parallel shell stage machine selected by load order. Model C is the normal Stage-60 runtime. Native shell adapters retain their actual platform/system boundaries; old shell module names in historical campaigns are not evidence of a second automated owner.

## Circular state and immutable parent

Validated circular sessions keep their own `state.json` and `stop.request` below `circular/sessions/<session-id>/`. Active/latest pointers select a session; they do not duplicate session state or mutate the completed parent job. Former global `circular/state.json` / `circular/stop` aliases are not restored. [Circular isolation](STRATEGY_LAB_CIRCULAR_ISOLATION.md) and [ownership](STRATEGY_LAB_CIRCULAR_OWNERSHIP.md) own the details.

## No competing policy owners

Do not reintroduce removed synchronous blockcheck, implicit source-order dispatch, duplicated state writers, shortlist builders or circular-eligibility policy. Use the actual current Python/result/native-adapter entrypoints and current focused checks. Historical namespace tests remain evidence for the module graph they exercised, not proof that the old shell automated worker is current.
