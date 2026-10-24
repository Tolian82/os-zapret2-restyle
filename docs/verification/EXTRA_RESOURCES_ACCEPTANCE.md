# Additional Resources — acceptance board M0–M7

**Status:** owner-approved delivery scope, 24 October 2026. **No installed-candidate PASS is inferred from source CI.** This file is the sole live acceptance scoreboard. Normative scope: [requirements](../architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md); milestone meanings and gates: [implementation plan](../architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md).

## Current baseline

- Source: `VERSION=0.5.7`, `PLUGIN_REVISION=46`, introducing commit [065280e](https://github.com/Tolian82/os-zapret2-restyle/commit/065280eef9a03d540c220820380e7103993a07eb).
- Source verification: [Project/Voice/FreeBSD15 PR CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40070741846); [main post-merge integrity PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40071292437).
- Last installed package observed by owner: **[v0.5.7_46 testing release](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.7_46)**. The owner verified `pkg info -x` and native Started with exit code zero.
- Owner-live manual extras installation on `_46`: **first successful operation PASS**, terminal ID `f6320ff10da6465192c35ac11a34ba80`, `ready / INSTALLED`, Lua 19, BIN 54, removed 10, restarted true. [Evidence](evidence/2026-10-24-v0.5.7_46-extra-resources-owner-live.md). Repeat install/independent census and dynamic extra-candidate execution remain **NOT RUN**.
- Independent hypervisor console: **confirmed available** by owner.
- Explicit clean reinstall of an incomplete/corrupted plugin: **NOT RUN / not yet implemented if required by test**.
- Testing-package release for `_46`: **PUBLISHED and verified** — [direct package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.7_46/os-zapret2-restyle-0.5.7_46.pkg), SHA-256 `62217e64e2fe84aff74d7ae0ebcc3f7d667ccb02c2805fd1e08f31feede0e97f`, [publication evidence](evidence/testing-publications/v0.5.7_46.md). Publisher workflow overall failed **only** during automatic PR creation (GitHub Actions permissions); the bounded publication record is merged via connector PR. Stable `v0.5.8`: **NOT AUTHORIZED / NOT PUBLISHED**.

## Milestone scoreboard

| ID | Required deliverable / gate | Status | Evidence / blocking detail |
|---|---|---|---|
| M0 | Approved requirements, governing rules and finite acceptance checklist merged to main, docs CI and post-merge integrity pass | PASS | [Requirements PR #548](https://github.com/Tolian82/os-zapret2-restyle/pull/548), [EOF correction PR #549](https://github.com/Tolian82/os-zapret2-restyle/pull/549), [main integrity #40082179231](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40082179231) |
| M1 | One persistent immutable `v0.5.7_N` testing package, verified source/tag/assets/hash and FreeBSD15 qualification | PASS | [Published `v0.5.7_46`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.7_46), [verification/evidence](evidence/testing-publications/v0.5.7_46.md); publisher PR-permission error repaired by this publication-record PR |
| M2 | Read-only appliance baseline, backup/snapshot and console recovery | IN PROGRESS | [Owner appliance baseline](evidence/2026-10-24-v0.5.7_46-extra-resources-owner-live.md): installed version, native service, upstream Git and firewall inspected; hypervisor console confirmed; VM snapshot unconfirmed |
| M3 | Owner-live manual exact-set extras installation, restart and GUI; ordinary update preserves plugin settings | IN PROGRESS | [First owner-live action PASS](evidence/2026-10-24-v0.5.7_46-extra-resources-owner-live.md): 19 Lua / 54 BIN / removed 10 / restarted true, no repeat or independent digest evidence yet |
| M4 | Owner-live native execution for one reviewed extra BIN and one reviewed Lua; dynamic new Jobs and correct bounded cleanup | NOT RUN | Offline graph tests cannot prove installed execution |
| M5 | Failure matrix, upstream change and explicit clean reinstall after corrupted plugin; unrelated OPNsense state preserved | NOT RUN | Native package hooks currently fail closed on incomplete owner; repair must be demonstrated |
| M6 | Cold restart IPFW/ipdivert, Voice, GUI, saved settings and no lingering firewall/PID/lock residues | NOT RUN | Previous _30 boot acceptance pending |
| M7 | Mandatory rows PASS, concise final report, separately approved `v0.5.8` exact package and OPNsense Web repo delivery | NOT RUN | Stable publication is a separate owner-controlled operation |

## Mandatory proof matrix

| Test | Gate | Expected observable result | Status |
|---|---|---|---|
| GitHub package identity and checksum | M1 | Uploaded persistent `.pkg` matches tested immutable commit and FreeBSD15 build | PASS |
| Source and runtime snapshots, hypervisor access | M2 | Known restore entry point and no destructive diagnostic | IN PROGRESS |
| Orphan/colliding untracked Lua/BIN | M3 | Backed up, then replaced/removed to exact desired inventory; no ad hoc filename exceptions | IN PROGRESS |
| Upstream/catalog identical and different-name collisions | M3/M5 | Identical content single upstream owner; divergent bytes safely block | NOT RUN |
| Saved strategy references changed/deleted resource | M3 | No silent semantic break or config rewrite | NOT RUN |
| First GUI resource installation after historical conflict | M3 | Terminal INSTALLED, exact resource-set verification and attested new native process identity | PASS |
| Idempotent repeat click | M3 | Same bytes, real new native Stop/Start, verified health | NOT RUN |
| Started vs Stopped and concurrent action | M3 | Only Started authorized; proper busy/status handling | NOT RUN |
| RU/EN, F5, two Apply buttons | M3 | User GUI function and layout preserved | NOT RUN |
| Extra BIN and reviewed Lua | M4 | New bounded native candidates execute with correct dependencies | NOT RUN |
| Add/remove compatible descriptors without code change | M4 | New Jobs follow inventory; saved Job unchanged | NOT RUN |
| Network/hash/payload and native Stop/Start failures | M5 | No false success, safe rollback or explicit RESTORE_FAILED | NOT RUN |
| Upstream switch with extras and collisions | M5 | Valid switch succeeds with preserved extras; invalid target refused before unsafe writes | NOT RUN |
| Explicit clean repair of damaged plugin | M5 | Fresh usable plugin; plugin-owned settings may reset; unrelated OPNsense state remains safe | NOT RUN |
| Boot/IPFW/Voice and common lifecycle | M6 | Safe postboot service and no new common owner/rule regressions | NOT RUN |
| Final installed package and stable Web delivery | M7 | Release `v0.5.8` exact bytes after separate approval and corresponding final test | NOT RUN |

## Execution rules

A test becomes **PASS** only with a recorded exact candidate, environment, executed procedure, observed result and evidence source. Allowed states: **NOT RUN**, **IN PROGRESS**, **PASS**, **FAIL**, **BLOCKED**. A blocking FAIL requires the smallest reproducible scoped repair, a new test candidate when packaged source changes, and re-execution of impacted tests. Do not silently waive a mandatory row or spin out speculative hardening. Move to the next milestone when the gate is satisfied; propose useful new work with evidence, but acquire owner approval before enlarging the mandatory scope.

**Single next action:** finish M3 owner-live read-only installed-resource digest/inventory and independent service status, then repeat the resource-install button with a new operation ID and genuine service restart. Confirm the M2 VM snapshot separately; do not infer full M3 PASS from a single successful transaction. Dynamic Stage-60 and all later gates remain untested; stable `v0.5.8` requires separate authorization.
