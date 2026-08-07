# 2026-08-07 — Strategy Lab third-audit corrective plan

## Objective

Convert the third Strategy Lab source audit into an executable serial corrective plan before any further owner-assisted OPNsense validation.

## Baseline

- `main`: `b5b98679838c1a73c074fc132d675440d9294123`;
- `VERSION=0.3.3`;
- `PLUGIN_REVISION=6`;
- `_6` source/CI corrections passed their historical gates;
- `_6` was not published and was not owner-tested on OPNsense.

## Decision recorded

Seven findings are opened as `SL3-001` through `SL3-007` in `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

The approved sequence is:

1. documentation and corrective plan;
2. ordinary stale recovery and timeout chain;
3. circular stale recovery lifecycle ownership;
4. remove load-order overrides and obsolete hooks;
5. serialize worker state transitions;
6. complete RU/EN progress localization;
7. integrated third-audit regression gate;
8. source/CI closure and live-test handoff.

## Verification boundary

Patch 1 changes documentation only and does not change `VERSION` or `PLUGIN_REVISION`.

The `_6` live scenario-1 retest is no longer the next action. The live matrix remains paused until Patch 8 designates a later FreeBSD 15 amd64 candidate after all corrective source and CI work passes.

## Next action

Patch 2 — ordinary stale-worker semantic recovery and the synchronous timeout envelope.
