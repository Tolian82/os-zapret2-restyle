# Strategy Lab explicit QUIC control contract

**Status:** CURRENT SPECIALIST ARCHITECTURE

## Authority

This document records the owner-approved current QUIC execution and presentation contract for Strategy Lab.

Where older Strategy Lab documentation says that QUIC candidate execution is enabled, disabled, or skipped according to Stage-30 QUIC capability detection, that language is **superseded**. Historical `_13` evidence may still describe capability gating because that was the behavior of the package that produced the evidence; it is not the current product contract.

## Product behavior

Diagnostics / Strategy Lab Extended mode contains `Enable QUIC` directly below `Generic UDP (optional)`.

The checkbox behavior is:

- default: **unchecked**;
- unchecked: QUIC candidate testing is disabled;
- checked: QUIC candidate testing is enabled;
- state persists in OPNsense configuration and survives page reload;
- the resolved value is copied into immutable job-local state at launch;
- changing the saved preference later affects future jobs only.

The UI may hide this control outside Extended mode because Stage 80 itself is an Extended-mode stage.

## Explicit execution preference and job eligibility

The saved **Enable QUIC** checkbox is the sole product decision that determines whether Stage 80 runs QUIC candidate tests when the stage is reached and endpoint/time prerequisites are satisfied. It does not override `TARGET_ACCESSIBLE`, cancellation, finite deadlines, or the requirement for Host/SNI on a bare IPv4 target. A successful direct HTTPS baseline terminates the job before Stage 80 even when Enable QUIC is ON.

The current [browser reachability contract](STRATEGY_LAB_BROWSER_HTTP.md) preserves this early exit and accepts a proven target TLS handshake, target QUIC handshake, or genuine target HTTP response independently. A measured HTTP/3 GET is not mandatory after a valid QUIC handshake. Older OpenSSL-only/four-candidate evidence keeps its original attribution; current candidates use the qualified private-client path.

Stage-30 QUIC control evidence (`quic_ipv4=available|closed`):

- does not enable candidate testing;
- does not disable candidate testing;
- does not produce a capability-based skip;
- does not override the owner-selected checkbox state.

This distinction is intentional. A provider blocking ordinary QUIC is exactly a case where Strategy Lab must be able to test Zapret2 QUIC bypass candidates.

## Stage-80 execution behavior

### Enable QUIC OFF

Structured evidence is equivalent to:

```json
{
  "enabled": false,
  "status": "skipped",
  "reason": "disabled",
  "tested": [],
  "working": null
}
```

No QUIC candidate is launched. Ordinary UI text translates this state naturally rather than printing `skipped/disabled` as raw enums.

### Enable QUIC ON

If the job reaches Stage 80 and target identity/budget permit execution, Stage 80 executes the QUIC candidate catalog even when Stage 30 recorded the control path as blocked.

Stage-4 source catalog `v0.5.6_14` (original four IDs and order unchanged):

1. `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`;
2. `quic-fake-5`, `quic-fake-10`, `quic-fake-20`;
3. `quic-ipfrag-32`, `quic-ipfrag-64`;
4. `quic-fake-ipfrag-8`, `quic-fake-ipfrag-16`, `quic-fake-ipfrag-32`, `quic-fake-ipfrag-64`.

The existing `fake_default_quic` builtin is used, not an invented external BLOB. Python production checks canonical `CandidateSpec`/external resource compatibility and admits 3/3 attempts only inside the existing Stage-80 and overall deadlines while reserving follow-up/replay/Stage-90 work. `tested` includes only attempted variants; `incompatible` and `deferred` are separate, with `incomplete_budget` distinct from exhaustive `not_found`. The legacy shell reference runner reads the same catalog but is not the Python production owner.

**Direct QUIC confirmation is scoped to QUIC/UDP443:** when pinned QUIC-only verification succeeds before catalog search, store `quic.status=direct_accessible` and skip QUIC bypass candidates, but do **not** terminate the overall Extended job as `TARGET_ACCESSIBLE` if the Stage-40 HTTPS/TCP direct baseline failed. Finish the optional UDP branch and run Stage 85 exact finalist replay for TLS candidates found at Stages 60/70. This transport-specific rule corrects an owner-observed `v0.5.6_14` defect in [published testing `v0.5.6_15`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_15); the owner-supplied `_15` [Extended `x.com` GUI result](../verification/evidence/2026-10-22-v0.5.6_15-owner-xcom-extended-stage4-pass.md) reports PASS for Stage85 continuity and restoration summary. This does not prove a working QUIC bypass. Report that direct QUIC reachability does not prove direct TCP/HTTPS availability.

The production runner appends every executed candidate result to `tested`. It may return early when a working candidate is found; otherwise it reaches `not_found` only after the enabled catalog search completes.

Structured terminal state remains:

- `working` when a candidate passes required endpoint checks;
- `not_found` after the enabled search completes without a winner.

An enabled run must never become `skipped` merely because the Stage-30 control probe was closed.

## Required owner-visible execution evidence

A user-facing `QUIC=not_found` string alone is not sufficient proof that candidate execution occurred.

From `_15`, ordinary Stage-80 presentation is generated from the actual structured `tested` array and includes:

- number of attempted QUIC candidates;
- attempted candidate IDs;
- working candidate ID when one exists; or
- a localized statement that no working strategy was found.

Therefore owner-live acceptance can prove `tested > 0` directly from normal output without unpacking telemetry. Raw/advanced output still retains the complete machine result.

## Stage-30 presentation

Stage 30 presents two independent facts:

1. what the control probe measured;
2. whether QUIC strategy search is selected for this job.

Required Russian semantics:

- `QUIC открыт`;
- `QUIC закрыт`;
- `подбор QUIC-стратегий включён` or `подбор QUIC-стратегий отключён`.

Required English semantics:

- `QUIC is open`;
- `QUIC is blocked`;
- `QUIC strategy search is enabled` or `QUIC strategy search is disabled`.

In Standard mode, presentation states that QUIC strategy search belongs to Extended mode rather than implying the measured network state made the decision.

The old Russian `_14` wording `QUIC/IPv4 закрыт по контрольной проверке` remains only as historical live evidence.

## Help localization

The English meaning:

`When enabled, QUIC candidates are tested even when the control probe reports QUIC as blocked.`

has deterministic English and Russian presentation bound to the selected OPNsense UI language. It does not rely on an absent gettext entry to become Russian.

Current Russian meaning:

`Если включено, QUIC-стратегии проверяются даже когда контрольная проверка показывает, что QUIC заблокирован.`

Equivalent minor wording adjustments are allowed as long as the execution contract is unchanged.

## Machine state vs normal UI

Structured/raw evidence may use stable machine enums including `working`, `not_found`, `skipped`, and `disabled`.

Normal Stage-80 UI does not expose those raw enums as the primary explanation. It renders human-readable RU/EN text plus attempt count/IDs.

## Verification

Repository tests prove at least:

1. model default OFF and persistent checkbox behavior;
2. start API validates/forwards only `0|1` and launcher persists immutable per-job intent;
3. Enable QUIC OFF suppresses the catalog; direct baseline success and missing required Host/SNI retain their separate early-exit/eligibility behavior;
4. with Enable QUIC ON, mocked `quic_ipv4=closed` still executes candidates;
5. shell/reference and Python production paths contain no capability-based execution gate;
6. Stage-30 RU/EN separates measured QUIC state from search enabled/disabled state;
7. Stage-80 RU/EN exposes real tested count/IDs and winner/no-winner meaning;
8. normal presentation does not leak raw `not_found/skipped/disabled` fragments;
9. Enable QUIC help exists in deterministic RU/EN presentation.

Automated `_15` source acceptance and persistent testing-package publication are complete. Machine publication evidence is in [`../verification/evidence/testing-publications/v0.4.1_15.md`](../verification/evidence/testing-publications/v0.4.1_15.md).

## Source history

The [full original page](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_QUIC_CONTROL.md) preserves earlier source versions, investigation notes and acceptance claims at their actual dates. [PROJECT_STATE](../PROJECT_STATE.md) owns current evidence; this page owns its bounded technical contract.
