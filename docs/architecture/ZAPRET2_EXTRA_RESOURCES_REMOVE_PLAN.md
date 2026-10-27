# Remove Additional Resources — approved staged implementation plan

**Project:** os-zapret2-restyle
**Owner approval:** 24 October 2026; **superseding binding decision:** 26 October 2026
**Status:** APPROVED REVISED PLAN. Historical Stage 1 and v0.5.9_2–_22 no-exec/FreeBSD Jail experimental work is superseded for Remove by the owner's 26 October decision. Stage 1 exact Git HEAD inventory remains usable; abandoned Jail staging/proof is removed from active source/CI, with historical evidence retained in Git. **Current task:** `_44` PUBLISHED TESTING (NOT OWNER-INSTALLED), corrective Stage 6 API denial contract after `_43` owner test; [publication record](../verification/evidence/testing-publications/v0.5.9_44.md). Project/Voice/FreeBSD15 CI PASS; owner-installed negative API retest pending. **The approved native GUI-path prechecks remain mandatory for future Stage 7 GUI execution; the read-only GUI remains gated until separately accepted.** Three invalid POSTs were blocked without mutations but surfaced HTTP 500 ([evidence](../verification/evidence/2026-10-27-v0.5.9_43-owner-negative-api-r2.md)). Replace this with bounded JSON `rejected`/`unavailable` for prelaunch failures, not new exception semantics. Keep native FD9, operation correlation, configd and GUI gating unchanged. `_43` remains installed; positive Remove owner acceptance PENDING. R4 native quarantine/common Apply/forward-recovery and `_42` owner/IPFW health already passed on OPNsense. Stage 7 confirmed GUI and Stage 8 cache/Job/repeat Install remain gated. Startup/health, not DPI reachability or live voice media, defines acceptance. Normal existing full package/GUI verification and owner-installed acceptance remain separate.

**Stage 6 owner positive inventory milestone (installed `_43`) PASS:** 19 Lua + 54 BIN installed via ordinary GUI, `ready` with no busy worker, current 73-file plan and native running/unchanged Config ([owner evidence](../verification/evidence/2026-10-27-v0.5.9_43-owner-resources-installed-r1.md)). Negative-only API checks and positive production Remove owner acceptance are separate pending gates; do not infer them from successful Install.

**Normative requirements:** [revised Remove specification](ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md).
**Existing reuse:** [Additional Resources implementation plan](ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md), native Apply/Voice, installed transaction and rollback.
**Explicitly deferred:** Exclude Domains/hostlist-exclude behavior remains untouched; future ipset-exclude GUI is a separate task. No testing package or release is authorized by this change.

**Binding 26 October Config decision:** Native Strategies and Voice edits use `SharedConfigCommit::persist()` → OPNsense `serializeToConfig(false, true)` / `Config::save()` only for genuinely changed fields; Remove has zero changed Config fields and must never save again. Reuse the existing native candidate preparation, full saved Config snapshot checks, shared Apply journal and native runtime/IPFW rollback. For an interrupted Remove `config-saved`, prove old owner and original unchanged snapshot across both existing journals and verify the actual runtime/IPFW before returning to that owner; normal `shared_apply_recover_saved_service` is **not** a generic old-owner rollback. Keep ambiguous cases blocked, and keep the GUI read-only until installed acceptance. This binding is implemented for the internal `_34` Remove-only source candidate; installed-appliance acceptance and API/GUI Remove remain open. See [decision](../DECISIONS.md).

## Stage 1 — Read-only upstream-only removal planner

Extend extra_resources_reconcile.py / extra_resources_preflight.py and reuse inventory-cache inputs. Under the relevant existing locks, attest current Git HEAD, tracked upstream Lua/BIN bytes, the exact installed file set and all non-upstream removal candidates. Reject symlinks, modified upstream files, unsafe dirs or inconsistent metadata. Produce a structured, digest-bound dry-run with filenames, counts and base configuration/inventory witnesses.

**Gate:** Correct plan in real-Git fixture; **no** service/file/Config/IPFW mutation; changing upstream revisions changes the plan without a code edit.

## Stage 2 — Existing Strategies GUI-path prechecks

Use the **same original persisted-Config common GUI Apply compiler and validators**, specifically `shared_apply_prepare_service()` → `orchestrator_build_release(..., shared-candidate)`, with the existing parser/profile/target/exclude/BLOB/generator path unchanged. Dynamic hostlist placeholders, YouTube Domains, Telegram IPs, User Domains and all future fields remain owned by the NORMAL generator; the Remove route neither enumerates nor duplicates their handling. Existing upstream-only view and Stage 1 inventory can reject obvious missing required resources before Stop; they cannot substitute for live startup. No new Lua/Jail runtime proof. No modification to Exclude Domains, current hostlist-exclude generation, or future ipset-exclude.

## Stage 3 — Existing Voice GUI-path checks

Reuse the current native Voice validators, candidate/draft preview and **the very same shared common GUI Apply candidate/actuator path**, not a new parser. Check five saved services as the GUI does: active Voice enters normal runtime; meaningful OFF saved drafts pass through their existing GUI candidate/preview path, without persistently enabling them. Incomplete OFF drafts keep native GUI semantics. No voice-call/connectivity proof is required.

## Stage 4 — Real native combined startup trial (no Jail)

After owner confirms planned removal and service interruption, under **existing** setup.lock → original FD9, use exact Git HEAD inventory and durable rollback state; normal Stop, temporary quarantine of attested non-upstream Lua/BIN, then build a FRESH full combined release from persisted Config via the existing `shared_apply_prepare_service` / `orchestrator_build_release(..., shared-candidate)` and activate with the same common GUI Apply mechanisms. **Do not substitute ordinary legacy start or existing common boot of a cached release**, which may omit native Voice or skip recompilation after quarantine. Existing process replacement/Started/IPFW/Voice ownership evidence is the success criterion. If compilation or start fails, restore all original files/service under the current transaction. No network bypass test or real Voice call, no independent runtime simulator.

## Source boundary v0.5.9_37 — durable native success before inode deletion, guarded console acceptance

A real saved-Config common Apply may succeed and then the process can die while deleting original quarantine inodes. The former cleanup occurred BEFORE a durable terminal phase and could not roll back missing inode metadata/ACLs after interruption. The source now records a `committing` journal in the SAME existing resource transaction with the verified NEW committed common owner BEFORE any irreversible resource or installed-manifest unlink. Under original setup.lock→FD9, forward recovery verifies unchanged Git HEAD standard Lua/BIN, the surviving original quarantine inodes and manifest evidence, and uses only the original committed common Apply boot/attestation of that exact new owner. It then finishes cleanup and atomically retires the one resource journal. Any mismatch retains evidence as `RESTORE_FAILED`, never claiming old-owner rollback after deletion. Existing `restarting` and earlier phases still require the exact original-inode/owner restoration.

An explicit **root-console-only** acceptance launcher accepts the existing digest-bound plan witness for a real native Remove success, a forced failure after actual Stop/quarantine, and an interrupted quarantine followed by a separate guarded recovery. No public configd/GUI operation is enabled; the service keeps its original common compiler, inode transaction, FD9, saved Config and IPFW ownership. Installed OPNsense acceptance (Config hash/owner/PID/IPFW/inode comparisons) is governed by [the operator protocol](../verification/REMOVE_NATIVE_OWNER_ACCEPTANCE.md). Source CI/package qualification is not appliance evidence; testing package publication and stable release remain separate owner-controlled gates.

## Source boundary v0.5.9_36 — guarded PREPARED cancellation without mutation

A crashed Remove operation may leave a durable `prepared` resource journal before `stopping`. This phase cannot be treated as successful recovery merely because no Stop was issued. Under the same setup.lock → FD9, existing native lifecycle/owner attestation confirms the original service remains **Started**, original common Apply owner identity is unchanged, original Lua/BIN inode and SHA-256 witnesses are intact, backup bytes match, installed metadata is unchanged and no quarantine exists. Only then can the existing resource journal be discarded as `RESTORED` without Stop, Start or Config writes. A foreign/stopped owner, altered resource, changed metadata, unsafe path or unknown state returns `RESTORE_FAILED` and retains the journal. Offline tests are not installed power-cut proof and no GUI/API Remove or package publication is authorized.

## Source boundary v0.5.9_35 — exact original inode/metadata rollback

The original resource transaction now includes an `original_inodes` witness for each non-upstream Lua/BIN file in its same durable Remove journal: device/inode identity, ownership, mode, size, modification time and flags. Stop is preceded by re-attestation of those inodes; the quarantine move requires exactly those original inodes. If a saved-config native Apply trial fails or an interrupted Remove is recovered, the transaction first checks the complete resource backup and existing quarantine contents, then uses `os.replace` to return the **same original inode** instead of writing its bytes into a fresh `0644` file. This retains inode-backed ACLs, flags, uid/gid and file timestamps. Recovery is idempotent for files already returned to their original paths. A missing/multiply-linked/foreign inode, even if it contains the same SHA-256 bytes, rejects restoration and preserves the journal/backups as `RESTORE_FAILED` rather than claiming full metadata restoration. No alternate resource registry, Config writer, process manager, or shared Apply recovery route is added.

Test cases model failed fresh activation, abrupt interruption and hostile same-byte substitution. CI and owner-installed native acceptance are separate and still required; GUI/API remains read-only, package and stable release unapproved.

## Source boundary v0.5.9_34 — unchanged Config-saved native cold rollback

Only for a live pending Remove resource transaction in `restarting`, and only when the original shared Apply journal contains exact saved-unchanged Strategies candidate, native FD9 recovery may enter the previously unqualified `config-saved` state. It verifies full native saved Config, the pinned predecessor, both sealed release trees, the old or exact new active tree, and no running engine/supervisor or foreign IPFW. The existing `shared_apply_recover_activated_cold_service` alone restores old release, staged managed IPFW and retirement; a dedicated `finish-remove-saved` finishes the **same** shared Apply journal as `restored` after the original resource-journal identity and seals are re-attested. A generic `record restored` after `config-saved` remains illegal, and ordinary `shared_apply_recover_saved_service` still commits its new owner, not an old Remove owner. No Config write, no extra journal/engine/Strategy/Voice/XML parser, no changed HOSTLIST exclusion behavior. Tests run in CI; actual installed appliance cold crash/rollback and user-confirmed GUI/API Remove remain unavailable pending acceptance.

## Source boundary v0.5.9_33 — cold installed ACTIVATING/ACTIVATED and truthful restored receipt

The resource Remove recovery still accepts only the original single `restarting` resource journal with exact prior committed common owner, unchanged full saved Config digest, and sealed old/new common bundles. It now distinguishes the strictly attested OLD active tree from a fully sealed NEW active tree before recovery. At `activating` with OLD installed it delegates to original pristine recovery; when NEW is installed, or at `activated`, it delegates exclusively to the existing `shared_apply_recover_activated_cold_service` for original common IPFW staged table rollback, empty engine/supervisor inventory, atomic runtime restore and durable terminalization. No duplicate state machine, Config writer, process ownership or IPFW parser. The final receipt is the REAL `shared_apply_inspect_service` terminal `committed OLD_ID OLD_PAGE` (the same old native boot owner), fixing a false `RESTORE_FAILED` from previous wrapper code. Unsealed/newly running/parked/partial or foreign states still refuse and keep the existing journals. `config-saved` remains unqualified and GUI Remove remains read-only pending installed-appliance testing.

## Source boundary v0.5.9_32 — pristine ACTIVATING cold recovery

A power interruption in a saved unchanged native trial's common Apply `activating` phase can be recovered only when the existing resource journal still pins the original committed owner and original saved Config, the old sealed release still occupies the active path, and native process/IPFW ownership is empty. The original `shared_apply_recover_activating_pristine_service` additionally verifies and removes only an exact new staging tree and refuses parked/backup/drift. No cloned runtime logic, Config writer or second journal. Other interrupted phases remain fail-closed; user-facing GUI Remove stays read-only.

## Source boundary v0.5.9_31 — first cold power-cut recovery for pre-mutation PREPARED

A crash after the saved GUI common candidate is journaled as `prepared` but before native Apply activation must not route to generic Stop while the shared owner is nonterminal. Under existing setup.lock→FD9, the native Remove recovery checks the same durable resource journal's `restarting` phase and pinned previous owner against the common PREPARED record (unchanged page, base, candidate and fields), verifies both sealed candidate/old release and saved Config digest, **exact old stopped active tree**, empty engine/supervisor census and managed IPFW, then uses the ORIGINAL `shared_apply_recover_prepared_service`. The resource transaction only skips redundant Stop after this exact attestation and restores original bytes/metadata and old native common service. All foreign/partial phases, drift and unverifiable states keep recovery evidence. Fast read-only shell/body+real-Git journal tests precede expensive CI. GUI/configd Remove still disabled; no owner-live claim.

## Source boundary v0.5.9_30 — actual saved common native trial, no user mutation entry yet

The original `NativeLifecycle.start_trial_native_common_apply()` now calls a root-only inherited-FD9 Remove trial actor under the existing setup.lock and original resource transaction (must be phase `restarting` with a pinned predecessor and physically quarantined extras). This actor calls the existing saved unchanged `SharedApplyRequest::prepare()` / `shared_apply_prepare_service()` common Strategies+Voice compiler **AFTER quarantine**, then the same shared Apply operation phases, `apply_runtime_activate/attest/commit`, saved Config readback with zero fields and identical complete baseline/candidate digests, sealed bundle, live process and scoped IPFW. It never calls Config save/legacy Start or adds another journal. Proven precommit failures restore the original stopped release and terminal common predecessor before resource bytes are restored; uncertain/crash states retain evidence and refuse. Ordinary Start/Restart cannot race an unfinished resource transaction. Fast tests run source body under isolated native shell mocks and the original real-Git resource transaction before long CI. GUI remains read-only; full crash-recovery and installed OPNsense acceptance are explicit remaining gates.

## Source boundary v0.5.9_29 — exact original common owner native restoration route

The existing root FD9 native service and shared Apply runtime now offer an executable **restore-previous** callback invoked only after the exact Lua/BIN bytes are restored by the existing resource journal. It validates the same resource journal's pinned old owner against the single native Apply journal, previously sealed release and persisted unchanged Config. If still old, native common boot restores it; if a valid unchanged-Config trial has already committed, the same apply_runtime actuator switches back to the old sealed runtime and managed IPFW, then the one common Apply journal is atomically reverted to `restored` carrying its original predecessor. The native lifecycle guard treats a trusted restored common predecessor as native rather than falling into the legacy path. Unknown partial/mixed runtime or saved Config rejects. No second Config writer, engine, IPFW owner or ledger. The native trial starter is STILL absent; GUI Remove remains read-only until cross-journal crash-safe final activation.

## Source boundary v0.5.9_28 — bind the real saved previous common owner (source-only)

The native internal Remove pre-stop observation reads the original terminal shared Apply journal and attests its ID/page/candidate digest against the saved native Config, sealed old release, exact installed runtime bytes, process census, managed IPFW and ready status, all under the existing setup.lock → inherited FD9. That witness is rechecked before Stop and written inside the already-durable resource journal; subsequent rollback receives exactly that value. Missing/legacy, changed or malformed owners reject before Stop, rather than using an arbitrary cached Start. Runtime trial activation and rollback remain unwired in production. No destructive GUI route is enabled.

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

**v0.5.9_43 published testing implementation (Project/Voice/FreeBSD15 PASS; NOT YET owner-tested):** `ServiceController::resourcesRemoveAction` requires authenticated POST, Started/busy/recovery preflight, a current read-only Git HEAD/Config/inode `inventory_sha256` and explicit text `REMOVE <positive current total>`. A separate random operation ID binds the asynchronous receipt to status. `extra_resources_remove` is the only configd mutation route (ID + 64hex witness + server literal confirmation). The original launcher rejects missing/invalid fields and a second busy operation, executes under nonqueueing setup.lock → original FD9, and reuses the existing fault-free `remove_with_native_trial` path. It recomputes the signed-by-content plan and seals old/new native owners under lock; stale / altered saved Config or files stop before mutation. `recover-test` fault injection remains root-console-only; no duplicate runtime, Config save, IPFW implementation, or GUI Remove click. `ready=false` in the existing GUI plan response is intentional until Stage 7.

**Pending gates:** run affected local quick tests, full Project/Voice/FreeBSD15 CI, package owner installation and auth/status safety testing, followed by GUI integration under Stage 7. A missing AJAX acknowledgement is `uncertain`, not a false terminal success or permission to blind-retry.



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
