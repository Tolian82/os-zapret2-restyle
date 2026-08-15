# Strategy Lab explicit QUIC control contract

**Status:** CURRENT SPECIALIST ARCHITECTURE
**Updated:** 2026-08-15
**Execution gate introduced by:** `v0.4.1_14`
**Owner-visible observability/localization implemented by source candidate:** `v0.4.1_15`

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

## Sole execution gate

The saved **Enable QUIC** choice is the sole product decision that determines whether Stage 80 runs QUIC candidate tests.

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

Stage 80 executes the QUIC candidate catalog even when Stage 30 recorded the control path as blocked.

Current catalog:

1. `quic-fake-1`;
2. `quic-fake-2`;
3. `quic-ipfrag-8`;
4. `quic-ipfrag-16`.

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

Repository tests must prove at least:

1. model default OFF and persistent checkbox behavior;
2. start API validates/forwards only `0|1` and launcher persists immutable per-job intent;
3. Stage 80 skips only because Enable QUIC is disabled;
4. with Enable QUIC ON, mocked `quic_ipv4=closed` still executes candidates;
5. shell/reference and Python production paths contain no capability-based execution gate;
6. Stage-30 RU/EN separates measured QUIC state from search enabled/disabled state;
7. Stage-80 RU/EN exposes real tested count/IDs and winner/no-winner meaning;
8. normal presentation does not leak raw `not_found/skipped/disabled` fragments;
9. Enable QUIC help exists in deterministic RU/EN presentation.

## Owner-live `_15` acceptance

After `_15` is persistently published:

- Enable QUIC ON while ordinary QUIC remains blocked must show `QUIC закрыт`/equivalent plus **search enabled**, not skipped;
- Stage 80 must show `tested > 0` and attempted candidate IDs;
- Enable QUIC OFF must show natural disabled wording;
- RU and EN help/Stage-30/Stage-80 presentation must follow selected UI language;
- normal restoration/resource-cleanup requirements remain unchanged.
