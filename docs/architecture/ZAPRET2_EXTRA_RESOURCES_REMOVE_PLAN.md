# Remove Additional Resources — approved staged implementation plan

**Project:** os-zapret2-restyle
**Owner approval:** 24 October 2026; **superseding binding decision:** 26 October 2026
**Status:** APPROVED REVISED PLAN. Historical Stage 1 and v0.5.9_2–_22 no-exec/FreeBSD Jail experimental work is superseded for Remove by the owner's 26 October decision. Stage 1 exact Git HEAD inventory remains usable; abandoned Jail staging/proof is removed from active source/CI, with historical evidence retained in Git. **Current task:** real native GUI-path prechecks and original FD9 Stop → temporary extra-resource quarantine → original combined Strategies/Voice Apply/Start → success or exact original-state rollback. Startup/health, not DPI reachability or live voice media, defines acceptance. Normal existing full package/GUI verification and owner-installed acceptance remain separate.

**Normative requirements:** [revised Remove specification](ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md).
**Existing reuse:** [Additional Resources implementation plan](ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md), native Apply/Voice, installed transaction and rollback.
**Explicitly deferred:** Exclude Domains/hostlist-exclude behavior remains untouched; future ipset-exclude GUI is a separate task. No testing package or release is authorized by this change.

## Stage 1 — Read-only upstream-only removal planner

Extend extra_resources_reconcile.py / extra_resources_preflight.py and reuse inventory-cache inputs. Under the relevant existing locks, attest current Git HEAD, tracked upstream Lua/BIN bytes, the exact installed file set and all non-upstream removal candidates. Reject symlinks, modified upstream files, unsafe dirs or inconsistent metadata. Produce a structured, digest-bound dry-run with filenames, counts and base configuration/inventory witnesses.

**Gate:** Correct plan in real-Git fixture; **no** service/file/Config/IPFW mutation; changing upstream revisions changes the plan without a code edit.

## Stage 2 — Existing Strategies GUI-path prechecks

Use the **same original persisted-Config common GUI Apply compiler and validators**, specifically `shared_apply_prepare_service()` → `orchestrator_build_release(..., shared-candidate)`, with the existing parser/profile/target/exclude/BLOB/generator path unchanged. Dynamic hostlist placeholders, YouTube Domains, Telegram IPs, User Domains and all future fields remain owned by the NORMAL generator; the Remove route neither enumerates nor duplicates their handling. Existing upstream-only view and Stage 1 inventory can reject obvious missing required resources before Stop; they cannot substitute for live startup. No new Lua/Jail runtime proof. No modification to Exclude Domains, current hostlist-exclude generation, or future ipset-exclude.

## Stage 3 — Existing Voice GUI-path checks

Reuse the current native Voice validators, candidate/draft preview and **the very same shared common GUI Apply candidate/actuator path**, not a new parser. Check five saved services as the GUI does: active Voice enters normal runtime; meaningful OFF saved drafts pass through their existing GUI candidate/preview path, without persistently enabling them. Incomplete OFF drafts keep native GUI semantics. No voice-call/connectivity proof is required.

## Stage 4 — Real native combined startup trial (no Jail)

After owner confirms planned removal and service interruption, under **existing** setup.lock → original FD9, use exact Git HEAD inventory and durable rollback state; normal Stop, temporary quarantine of attested non-upstream Lua/BIN, then build a FRESH full combined release from persisted Config via the existing `shared_apply_prepare_service` / `orchestrator_build_release(..., shared-candidate)` and activate with the same common GUI Apply mechanisms. **Do not substitute ordinary legacy start or existing common boot of a cached release**, which may omit native Voice or skip recompilation after quarantine. Existing process replacement/Started/IPFW/Voice ownership evidence is the success criterion. If compilation or start fails, restore all original files/service under the current transaction. No network bypass test or real Voice call, no independent runtime simulator.

## Source boundary v0.5.9_27 — mandatory original-owner rollback callback (source-only)

The internal Remove transaction now demands both the real native common Apply trial starter and a **distinct previous-owner rollback callback** before the first Stop. For Remove recovery, it calls `restore_previous_native_common_apply()` after restoring original resource bytes and metadata instead of generic `start()`, which could boot the new release after a partially committed trial. If missing, recovery retains evidence and refuses before Stop; the no-extras case remains a no-op. Production deliberately implements neither callback yet. Next: bind a durable prior native owner witness and implement original common activation/rollback under FD9, without a second journal or Config save. This does not authorize GUI deletion.

## Source boundary v0.5.9_26 — native saved Config candidate compiler is integrated

The original PHP shared Apply gained `saved-unchanged`, producing a freshly locked **unchanged** full Config candidate via the current `SettingsApply::prepareStrategies` with zero changed fields. The exact original `SharedApplyRequest::materialize` creates its sealed-work identity, and internal `extra-resources-native-build-saved` under original FD9 and setup.lock calls the exact `shared_apply_prepare_service` (including the real full GUI target/Voice/BLOB/strategy generator), bundle verifier and native preflight. This is a **non-activating** existing-code adapter only. The operator GUI remains read-only `ready=false` until the same normal runtime activation/recovery is safely connected. This step has source and CI evidence only, not installed-device acceptance.

## Source boundary v0.5.9_25 — read-only GUI/command wiring
The native Advanced-only bilingual Remove button now requests exactly the current installed Git HEAD plan through existing setup.lock → original FD9 → `make_remove_plan`; the configd/PHP response is bounded, attested and **non-authorizing (`ready=false`)**. Click displays current Lua/BIN counts and unavailable-to-execute warning, not a destructive confirmation. The new CLI and API are read-only, do not alter Status, service, Config or IPFW. Next: reuse original saved-Config normal combined GUI Apply inside the already-existing `_24` transaction before enabling Remove.

## Source boundary v0.5.9_24 — internal native trial transaction, not yet wired

`extra_resources_transaction.remove_with_native_trial()` adds Git HEAD/Config witness binding, exact extra Lua/BIN snapshot and existing journal, Stop, atomic hidden quarantine inside the original runtime filesystem, before/after exact upstream-only inventory checks, an explicit `start_trial_native_common_apply()` contract, and existing recovery on failure or interrupted start. A **missing callback rejects before Stop**; the current native installed lifecycle has no such callback. Source-only mock tests are NOT equivalent to real GUI Apply. Next: expose original `shared_apply_prepare_service()` / `orchestrator_build_release(..., shared-candidate)` + activation on original saved Config under inherited FD9 without Config save; never introduce list/placeholder/Voice field duplication. Transaction does not become a GUI action or authorize deletion until this real native wiring and all gates are complete.

## Stage 5 — Finalize or restore through existing resource transaction

Reuse existing `extra_resources_transaction.py`, `extra_resources_operation.py`, native lifecycle and durable journal. **Only after real normal start succeeds** finalize removal, remove quarantine, retire extras-installed metadata and update cache. Failure restores byte-identical extra files and prior healthy service; otherwise report `RESTORE_FAILED` with retained journal. No-op never restarts. Retain Install exact-set logic unchanged. Do not implement a second rollback service, new Jail, or independent interpreter.

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

Expand **existing** native-resource transaction, ordinary GUI Strategies/Voice validation, shared Apply and post-start health, cache, locking and graph tests. Include tamper/unsafe files, orphan cleanup, invalid Lua/BIN, meaningful/partial OFF drafts under existing GUI policy, saved Config drift, actual trial startup success/failure, rollback, interrupted restart, no-op and repeat Install. Validate documentation links/governance and FreeBSD 15 package wiring when source changes.

**Gate:** All applicable tests PASS on the exact source candidate. A skipped/unrun check is labelled SKIPPED/UNVERIFIED.

## Stage 10 — Testing package (separate execution authorization)

After source implementation and CI qualification, publish an immutable FreeBSD 15 testing package only under the project's normal owner-authorized delivery procedure. Check candidate identity, commit/tag/package SHA-256 and manifest. This plan approval **does not itself authorize creating or publishing a package now**.

**Gate:** Persistently retrievable and independently verified exact testing package; not a stable release.

## Stage 11 — Owner appliance acceptance

On OPNsense verify exact before/after Git HEAD file sets and SHA inventory, prechecks as in saved Strategies and Voice GUI (including meaningful OFF draft preview), normal Stop→quarantine→same Apply/Start and existing Started/IPFW/Voice ownership verification; intentional failing strategy produces original-file/service restoration with a warning. Verify cache/Help not_installed, new-Job inventory and repeat Install. Record actual observed evidence separately from source tests. Destructive fault injection is not required live without additional safety authorization.

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
