# TZ6v5 S04a — pure neutral component classification (read-only model)

**Date:** 23 November 2026. First S04 increment after accepted [S03 original RED baseline](ZAPRET2_TZ6V5_S03_RED_BASELINE_GO.md). Merged starting source `main v0.6.5_150 b4e94219`; source candidate `v0.6.5_151`. No published `os-zapret2-restyle-0.6.5_151.pkg`, no operator OPNsense or pfSense actions.

## What this first increment really implements

`backend/component_inventory.py::classify` is a **pure, neutral, typed classifier** with five independent input axes: plugin `installed/absent/unknown`, engine `valid/absent/invalid/unknown`, Config `initialized/absent/invalid/unknown`, manifest `valid/missing/stale/invalid/unknown`, and runtime `RUNNING/STOPPED/INCOMPLETE/FOREIGN_OR_UNVERIFIED/UNKNOWN`.

The component values are **external evidence claims** supplied by a future platform adapter; this module does not read disk, query pkg or Config, inspect PID/epoch, acquire original FD9, run CLI, install anything, write XML, alter IPFW or signal processes. It is deliberately independent of OPNsense, to preserve a future pfSense adapter boundary. A supplied `RUNNING` value **does not prove** exact owner/epoch/PID: output is a classification, never a terminal service status receipt.

Output schema1 contains enum-only `components`, bounded `classification`, `authorization=NONE`, `physical_transition_allowed=false` and `original_fd9_attestation_required=true`. No code path can authorize a Start, Stop, force, automatic repair, reconfigure or manifest promotion. Invalid/missing/extra/wrong-type facts throw bounded `ComponentModelError`, without echoing raw user data.

## S04 required 5-case matrix (source-level GREEN only)

| Facts scenario | Expected neutral classification |
| --- | --- |
| Nothing installed, no Config/runtime/manifest | `PLUGIN_NOT_INSTALLED` |
| Plugin present, no upstream engine | `ENGINE_NOT_INSTALLED` |
| Engine present, Config absent | `CONFIG_UNINITIALIZED` |
| RUNNING claimed with damaged editable Config | `CONFIG_INVALID`, **never Stop or repair without original owner** |
| Foreign/unverified runtime | `FOREIGN_OWNER`, **never destructive intervention** |

Additional type/readiness tests cover invalid/stale/missing manifest, malformed fact enums, all enum combinations (none may grant physical authority), deterministic detached reports and a source-level IO/spawn tripwire. Tests execute in the central CI using the actual newly shipped pure Python module, not a mock implementation. **These are source tests, not qualified native installed OPNsense evidence.**

## S04 complete GO remains pending

**S04a != full S04 GO.** Next under S04: implement narrowly scoped *actual* platform read-only probes for plugin/engine/Config/active manifest/runtime using existing source attesters and sealed original owner. No second PID matcher, second FD9/Config writer, boot action or arbitrary file path from users. Native OPNsense should verify true component snapshots in the five conditions, unchanged byte-level Config, process/foreign IPFW and no new files; do not treat `status --json` as implemented here (it belongs to S05). Missing/invalid Config/manifest cannot authorize a new Start; an existing protected owner may be stopped only by the **original** FD9 lifecycle and its own evidence.

**Until actual probe/native evidence:** S04 NO-GO, S05 not entered, unified lifecycle product NO-GO, #1223/#1224/#1225 OPEN. No package for owner hardware. Central source CI pending.
