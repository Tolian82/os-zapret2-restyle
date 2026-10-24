# Remove Additional Resources — approved staged implementation plan

**Project:** os-zapret2-restyle
**Owner approval:** 24 October 2026
**Status:** APPROVED PLAN; Stage 1 qualified on GitHub source/FreeBSD15 CI and merged ([PR #577](https://github.com/Tolian82/os-zapret2-restyle/pull/577)); Stage 2 `v0.5.9_2` upstream-only temporary view/native Blob resolver qualified (PR #578); `v0.5.9_3` adds full common native Strategies pipeline fixture. Full saved Strategies compatibility gate and Stages 3–13 not completed.
**Normative requirements:** [Remove Additional Resources specification](ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md).
**Existing architecture:** [Additional Resources implementation plan](ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md) and [GUI/install contract](ZAPRET2_EXTRA_RESOURCES_GUI.md).

This scope is **separate from the already accepted M0–M7/H1 campaign and the owner-authorized v0.5.8 release**. Documentation approval alone must not alter the existing package identity, publish a testing package or issue a stable release. Implement in bounded increments, preserve exact-head branch/PR/CI policy and verify installed behavior separately.

## Stage 1 — Read-only upstream-only removal planner

Extend extra_resources_reconcile.py / extra_resources_preflight.py and reuse inventory-cache inputs. Under the relevant existing locks, attest current Git HEAD, tracked upstream Lua/BIN bytes, the exact installed file set and all non-upstream removal candidates. Reject symlinks, modified upstream files, unsafe dirs or inconsistent metadata. Produce a structured, digest-bound dry-run with filenames, counts and base configuration/inventory witnesses.

**Gate:** Correct plan in real-Git fixture; **no** service/file/Config/IPFW mutation; changing upstream revisions changes the plan without a code edit.

## Stage 2 — Saved ordinary Strategies preflight

Reuse backend/parser.sh, backend/profile_pipeline.sh, backend/blobs.sh, backend/orchestrator.sh and common Apply's inert candidate build. Introduce a narrowly scoped upstream-only resource view. Validate saved Traffic Strategy (all --new profiles), Extra Arguments, file and function declarations, Lua initialization, exports and transitive dependencies against the **future** inventory. No raw-XML substring search as the decisive compatibility proof.

**Gate:** Extra BIN/Lua dependencies are rejected before mutation; fully upstream-only Strategies produce a verified inert candidate; unknown is not PASS.

## Stage 3 — Saved native Voice preflight

Reuse VoiceCandidateValidator.php, voice_profile_compiler.py, voice_native_lifecycle_router.py, voice_native_draft_preview_route.py and common Voice+Strategies compilation. Inspect all five services and both active profiles and meaningful disabled saved drafts. Detect removed dependencies in OFF drafts without incorrectly demanding valid ON profiles from intentionally partial drafts. Preserve native Config and FD9 ownership.

**Gate:** Referenced extra Lua/BIN blocks removal for active Voice and disabled saved drafts; compatible Voice stays valid; no new Voice subsystem or service mutation.

## Stage 4 — Unified prospective compatibility gate

Merge Strategies and Voice results under one native preflight with a protected Config generation and exact upstream/resource SHA witness. Validate combined runtime/argv using isolated upstream-only files. Return compatible / incompatible / unknown, bounded failure details and the exact removal-plan binding. On any uncertain result, reject safely. Check the binding again under the native transaction lock.

**Gate:** No Stop, deletions or metadata mutation before verified compatible result, owner confirmation and unchanged Config/resource generation; clear RU/EN error for incompatible strategies.

## Stage 5 — Transactional removal and verified rollback

Extend extra_resources_transaction.py and extra_resources_operation.py with an explicit remove mode and a **zero-extra desired set**, while leaving Install exact-set semantics intact. Reuse durable full-byte snapshots, journal, rollback, setup.lock→original FD9, native Stop/Start, service/new-PID and IPFW health evidence. Verify byte-for-byte original upstream HEAD after removal; retain a complete attested old resource inventory. Do not manufacture installed.json after remove.

**Gate:** Native success produces exactly upstream Lua/BIN with healthy Started owner. Failure restores old files/metadata and service, or explicitly reports RESTORE_FAILED with retained evidence. No-op does not restart.

## Stage 6 — Configd, service controller and API

Wire remove through extra_resources_launcher.sh, zapret_service.sh, actions_zapret.conf and ServiceController.php. Enforce authenticated POST, Started precondition, mutually exclusive operation locking, server-side preflight, confirmation token/generation binding, correlated operation ID and truthful asynchronous status. Reject nested locks and concurrent release/Apply/Voice/Lab/install operations.

**Gate:** Every backend entry follows the same authoritative lifecycle; direct API invocation cannot bypass validation; request timeout/uncertain completion cannot trigger blind retries.

## Stage 7 — GUI and translation

Update general.volt: place same-sized Remove Additional Resources button **directly under** Install, with text-info-blue text and bilingual labels. Show it only when the native show_advanced_frm_GeneralSettings is ON; Help is independent. Implement removal-plan confirmation, specific incompatible-strategy warning, spinner/status/failure localization, F5 recovery and native disable/enable behavior.

**Gate:** RU/EN, Advanced ON/OFF, Help ON/OFF and F5 combinations accepted without layout regressions; no ghost success for unfinished operations.

## Stage 8 — State, Full Help cache and Strategy Lab

On success, set a terminal removed/not_installed status, retire active extra-install manifest, refresh/invalidate atomic cache, and show the existing **install prompt** rather than resource lists. New Job uses the actual upstream-only inventory and dynamic candidate graph; completed Jobs remain unchanged. Repeat Install can restore the verified extra catalog.

**Gate:** Disk, status, cached GUI, ResourceInventory and subsequent Job agree; no on-demand Git scan from Full Help.

## Stage 9 — Source and fault-path regression tests

Expand native-resource transaction, preflight, Voice/Strategies, GUI, cache, service-locking and dynamic-graph tests. Include upstream tamper, manual/orphan removal, broken BIN/Lua reference, indirect Lua function dependency, incomplete OFF drafts, Config drift, crash/rollback, interrupted restart, no-op and repeat Install. Validate documentation links/governance and FreeBSD 15 package wiring when source changes.

**Gate:** All applicable tests PASS on the exact source candidate. A skipped/unrun check is labelled SKIPPED/UNVERIFIED.

## Stage 10 — Testing package (separate execution authorization)

After source implementation and CI qualification, publish an immutable FreeBSD 15 testing package only under the project's normal owner-authorized delivery procedure. Check candidate identity, commit/tag/package SHA-256 and manifest. This plan approval **does not itself authorize creating or publishing a package now**.

**Gate:** Persistently retrievable and independently verified exact testing package; not a stable release.

## Stage 11 — Owner appliance acceptance

On OPNsense verify before/after exact paths and SHA inventory, native started process/health, safe block on incompatible saved Strategies and Voice (including saved OFF drafts), zero mutation on rejection, successful removal, cache/Help not_installed state, Strategy Lab fresh Job and repeat Install. Record actual observed evidence separately from source tests. Destructive fault injection is not required live without additional safety authorization.

**Gate:** Owner expressly confirms the completed installed behavior. Any future stable release remains a distinct decision.

## Stage 12 — README.md audit and user-facing update (penultimate, before release)

After the owner appliance acceptance and **immediately before any future stable release that includes removal**, edit the repository-root README.md, retaining the section names:

1. In **“Useful runtime paths”**, explicitly add `/usr/local/etc/zapret2/lua/` (Lua) and `/usr/local/etc/zapret2/files/fake/` (BIN), noting that the installed upstream files and optional additional files share these directories.
2. In **“Additional Resources — installed Lua/BIN help”**, rewrite the introduction to explain that os-zapret2-restyle offers **optional installation and use of an expanded, integrity-verified Lua/BIN pack** from [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources). Preserve the description of manual installation, native restart and the cache-backed help list, and accurately mention the new removal action only when its implementation and owner acceptance are verified.
3. Qualify "verified" precisely: catalog integrity/provenance/integration are verified, **not** universal DPI-bypass success, feature interoperability or Voice-call success. Check user-facing English, exact path spelling and repository links.

**Gate:** README review, documentation integrity/link tests and feature truthfulness PASS on the release candidate. This is the **penultimate stage** immediately before Stage 13. Do not apply this new gate retroactively to the separately approved v0.5.8 release.

## Stage 13 — Separately authorized stable release (final)

Only after completion of implementation, testing package qualification, owner OPNsense acceptance **and** Stage 12 README review, request/observe the **separate, explicit owner instruction** authorizing a full release for this feature. Use the existing full GitHub Release + FreeBSD15 Pages/pkg process and its immutable version/package/SHA256 gates. This plan amendment is **not** that release authorization.

**Gate:** The exact release tag/asset/checksum/package repository is verified separately. No release work starts solely because the staged plan was approved.

## Implementation boundaries

- Preserve working native Apply, Voice, IPFW, Strategy Lab, upstream switch, existing resource install and all saved configuration without changing their semantics.
- Never substitute raw filename substring detection for compilation against an upstream-only view.
- Do not silently retain unknown manually installed Lua/BIN: final owner decision requires removing **all non-upstream** direct resources after safe snapshot and compatibility preflight.
- Do not advertise network/DPI/Voice-call success on the strength of a dry-run compilation.
- Do not reopen owner-closed M0–M7/H1 or the separately cancelled clean-plugin repair campaign.
- Separate approved documentation from source implementation, CI, installed owner acceptance, testing publication and stable release.
