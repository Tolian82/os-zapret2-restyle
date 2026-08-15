# Strategy Lab explicit QUIC control contract

**Status:** CURRENT SPECIALIST ARCHITECTURE
**Updated:** 2026-08-15
**Introduced by source candidate:** `v0.4.1_14`

## Authority

This document records the owner-approved current QUIC execution contract for Strategy Lab.

Where older Strategy Lab documentation says that QUIC candidate execution is enabled, disabled, or skipped according to Stage-30 QUIC capability detection, that language is **superseded**. Historical `_13` evidence may still describe capability gating because that was the behavior of the package that produced the evidence; it is not the `_14` product contract.

## Product behavior

Diagnostics / Strategy Lab Extended mode contains:

- `Generic UDP (optional)`;
- directly below it, `Enable QUIC` with a checkbox.

The checkbox behavior is:

- default: **unchecked**;
- unchecked: QUIC candidate testing is disabled;
- checked: QUIC candidate testing is enabled;
- the state is persisted in OPNsense configuration;
- a page reload reads the persisted state rather than resetting it;
- an active job is not changed retroactively when the saved preference changes.

The UI may hide this control outside Extended mode because Stage 80 itself is an Extended-mode stage.

## Sole execution gate

The saved **Enable QUIC** choice is the sole product decision that determines whether Stage 80 runs QUIC candidate tests.

The Stage-30 IPv4 UDP/443 QUIC control probe may continue to run and record diagnostic evidence such as `quic_ipv4=available` or `quic_ipv4=closed`, but that evidence:

- does not enable QUIC candidate testing;
- does not disable QUIC candidate testing;
- does not produce a capability-based QUIC skip;
- does not override the owner-selected checkbox state.

This distinction is intentional. A provider blocking ordinary QUIC is exactly a case where Strategy Lab must be able to test Zapret2 QUIC bypass candidates.

## Per-job immutability

At job start the validated checkbox value is copied into job-local state.

Therefore:

- the running job uses the value selected at its start boundary;
- changing the persistent checkbox later affects future jobs only;
- Stage 80 does not reread mutable global configuration to change an in-flight job.

## Stage-80 behavior

### Enable QUIC OFF

Stage 80 produces a QUIC result equivalent to:

```json
{
  "enabled": false,
  "status": "skipped",
  "reason": "disabled",
  "tested": [],
  "working": null
}
```

No QUIC candidate is launched.

### Enable QUIC ON

Stage 80 executes the QUIC candidate catalog even when Stage 30 recorded the control path as blocked.

A valid terminal QUIC result is:

- `working` when a candidate passes the required endpoint checks; or
- `not_found` after the enabled QUIC search completes without a working candidate.

An enabled run must not become `skipped` merely because the Stage-30 control probe was closed.

## Network precheck presentation

Stage 30 continues to report what it measured. When QUIC/IPv4 is closed, the message may say that the control probe is blocked. It must not say that QUIC tests have been excluded because that decision belongs only to Enable QUIC.

IPv6 capability gating remains separate and is not changed by this contract.

## Persistence/API boundary

The persistent field is part of the Zapret model under the Strategy Lab configuration namespace, Boolean, default `0`.

The Diagnostics page reads and writes it through a model-backed API. Saving this preference does not apply/restart the normal Zapret2 service; it controls future Strategy Lab jobs only.

The normal Strategy Lab start API receives the resolved `0|1` value and the launcher persists it inside the new job before asynchronous execution begins.

## Verification

Repository tests must prove at least:

1. model default OFF;
2. GUI checkbox exists directly in the Extended input block and uses persistent API state;
3. start API validates and forwards only `0|1`;
4. job-local value is persisted;
5. Stage 80 skips only because the value is disabled;
6. with value enabled, a mocked `quic_ipv4=closed` control result still executes QUIC candidates;
7. both shell/reference and Python production QUIC paths no longer contain capability-based execution gating.

Owner-live `_14` acceptance must prove:

- default/persistence behavior through the actual GUI;
- OFF → `disabled` skip;
- ON while the owner’s ISP still blocks ordinary QUIC → actual QUIC candidates are attempted (`tested > 0`) and the result is truthful `working` or `not_found`.
