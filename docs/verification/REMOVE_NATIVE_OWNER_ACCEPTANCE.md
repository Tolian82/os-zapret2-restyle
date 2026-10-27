# Remove Additional Resources — owner-installed native acceptance

**Owner acceptance status:** Stage 6 `_44` native Remove API PASS; Stage 7–8 `_46` GUI/Help/Job/Install R6–R9 PASS. **Installed `_47` R10 read-only owner baseline PASS** ([evidence](evidence/2026-10-27-v0.5.9_47-owner-installed-read-only-r10.md)): package version seen in `pkg info`, 19 Lua/54 BIN extras and plan 73, cached installed 25 Lua/100 BIN, service RUNNING, sealed native owner plus runtime/Config/managed IPFW fingerprints and saved Config SHA all unchanged against `_46` R8. No post-upgrade new Install/Remove or on-device injected failed-cache-refresh evidence; visual `_47` Full Help/F5 and extended Stage 11 acceptance pending. Testing `_47` publication remains immutable ([asset](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.9_47/os-zapret2-restyle-0.5.9_47.pkg)); no stable release.

**Stage 7 owner-installed testing:** [`v0.5.9_46` package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.9_46/os-zapret2-restyle-0.5.9_46.pkg), exact tag/source `c95aa771538cb98c45eada23dfe96bb522f7bfe3`, SHA-256 `f3bb49aebecb8c46fdb5d2ea1c8382bea309c75f885ca47c5750bfec17824976`. Owner actually performed GUI Install→Remove and independent healthy postchecks ([R6](evidence/2026-10-27-v0.5.9_46-owner-gui-remove-r6.md)). Historical `_45` double-spinner was corrected in `_46` with executable GUI regression.
**Historical GUI bug:** on `_45` both spinners animated during Remove ([R5](evidence/2026-10-27-v0.5.9_45-gui-remove-spinners-r5.md)). On `_46`, the owner confirmed Remove wheel movement during a real new GUI cycle with sound native postchecks ([R6](evidence/2026-10-27-v0.5.9_46-owner-gui-remove-r6.md)); an independent image proving Install-wheel inactivity was not supplied.


**Owner browser-control observation (version not restated):** RU/EN, Advanced, Help and F5 **OWNER-REPORTED PASS** on 27 October 2026 ([scope-limited owner report](evidence/2026-10-27-owner-gui-controls-ru-en-advanced-help-f5.md)). This does **not** prove installed `_45`, a destructive Remove click, cache correctness, or any native transaction. Stage 7 `_45` full GUI acceptance remains pending.

### Stage 7 owner-installed core GUI path — PASS; extended negative scenarios are a separate checklist

For any *additional* destructive GUI test, use confirmed installed `_46`, fresh plan, local console, snapshot, saved Config and `audit-native` witnesses, and absence of pending transaction/quarantine. The ordinary GUI Install→Remove was **already performed** on `_46` ([R6](evidence/2026-10-27-v0.5.9_46-owner-gui-remove-r6.md)); no unnecessary repetition of this destructive acceptance is requested.

Check Advanced OFF (button hidden immediately) and ON (button shown under Install with same dimensions); Help ON/OFF independent; repeat in RU and EN and after F5. With current upstream-only `total=0`, click Remove and confirm truthful no-op with zero mutations and no service restart (read-only follow-up checks required). Then independently Install the verified 19 Lua + 54 BIN catalog, attest fresh plan counts/hash, return to Remove modal: cancel, wrong typed phrase and stale plan must never delete. With fresh owner authorization and snapshot, enter exact `REMOVE 73`, observe one API dispatch and matching operation ID through bounded polling, then verify terminal `not_installed`/0/0, `plan total=0`, native running sealed owner, unchanged saved Config and expected IPFW behavior, no transaction/quarantine/manifest, correct Full Help/cache update. Exercise F5 while a live operation is observed if practical without introducing a new mutation. Lost-acknowledgement and restoration cases stay review-only unless separate fault injection is approved.

**Stage 8 core acceptance:** R7 `installed=false`, current upstream-only cache+Help prompt+new Job and preserved historical inventory identities ([R7](evidence/2026-10-27-v0.5.9_46-stage8-inventories-r7.md)); R8 repeat Install 19/54, healthy service/Config and refreshed 25/100 origin-aware cache ([R8](evidence/2026-10-27-v0.5.9_46-stage8-repeat-install-r8.md)); R9 restored two columns and upstream-green/extra-blue names visually confirmed by owner ([R9](evidence/2026-10-27-v0.5.9_46-stage8-restored-full-help-r9.md)). **All required Stage 8 owner-visible happy-path behavior PASS**. Stage 9 reviews negative/rollback/test boundaries; owner Stage 11 final release acceptance remains separately gated.

**Stage 6 API contract closure:** The `_43` HTTP 500 invalid-credential defect was corrected in `_44` and the owner observed three HTTP 200 `rejected/started=false` responses ([R3](evidence/2026-10-27-v0.5.9_44-owner-negative-api-r3.md)). Separately the owner authorized and ran a real positive `_44` POST: unique operation receipt `removing` → `not_installed`, 19+54 extras removed, full independent post-checks on service, audit-native, Git HEAD, Config and cleanup ([R4 positive](evidence/2026-10-27-v0.5.9_44-owner-positive-api-r4.md)). GUI invocation and repeated Install not implied.

**Stage 6 `_43` owner positive precondition PASS:** 19 additional Lua, 54 BIN, fresh native Remove `total=73`, inventory SHA-256 `8c34e548ceeac34d5f6665e87cdeafe0384fc1ddbde63a85816b726086791dcc`, running service, unchanged saved Config and no transaction/quarantine ([evidence](evidence/2026-10-27-v0.5.9_43-owner-resources-installed-r1.md)). This is a **precondition only**, not a tested production API Remove. GUI `ready=false` remains mandatory.

**Latest published owner-installed R4 testing candidate:** [v0.5.9_41](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.9_41), exact source `379139552eb47c0faa77db0496a0c66f9970cb28`, SHA-256 `4ed5fc24a43fffc73a2d6b6e09aa900e8f44441cdecc57f9966d7ae7ecee0a0b`, FreeBSD15 amd64 ([publication record](evidence/testing-publications/v0.5.9_41.md)). **Previous owner-installed (R4 FD9 gate BROKEN):** [v0.5.9_40](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.9_40), FreeBSD 15 amd64, exact source/tag `a3b6a140a5ebe253f67958f4cc6abbd1747acb94`, package SHA-256 `19b34ba683752def52a0ee49484dd24901c80b98d745f9dc7eafccfaea82c8aa` ([publication record](evidence/testing-publications/v0.5.9_40.md)). Not a stable release; `_40` owner-installed read-only baseline PASS; R4 not run.

**New owner-installed native audit package (LIVE AUDIT PASS):** [v0.5.9_42](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.9_42), source/tag `6d79349ead6fca0a563e7854f17fc663b25ad4aa`, [FreeBSD15 package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.9_42/os-zapret2-restyle-0.5.9_42.pkg), SHA-256 `77528cbad26c0c50ff974463cc33541dbff39aee30f0b01e2c21b161f30b8dda` ([publication record](evidence/testing-publications/v0.5.9_42.md)). The standalone root-console `audit-native` attestation is designed to reuse original setup.lock → FD9 and sealed native owner / managed IPFW health. **Owner's live `_42` audit PASS**: sealed `strategies` common owner, RUNNING child/supervisor and managed IPFW fingerprint, unchanged Config and 0/0 extra resources. [Redacted owner evidence](evidence/2026-10-27-v0.5.9_42-owner-native-audit.md). Historical pre-R4 owner/IPFW snapshot equality was not recorded. No GUI Remove permission or stable release.
**Evidence state:** R0/R1/R2 owner-live PASS on `_37`. On installed `_38`, the owner confirmed RU/EN/F5 GUI and R3 native `REMOVED` for 19 Lua + 54 BIN, subsequent zero-extra plan, running service, absent transaction/quarantine. A matching pre-R3 Config SHA-256 and full internal owner/IPFW witnesses were not supplied in this interaction; do not upgrade this to complete all-checks PASS. On installed `_40`, read-only owner baseline PASS: 0 extra Lua/BIN in status, cache and plan, engine running, no transaction/quarantine, 28G available; [R0 evidence](evidence/2026-10-27-v0.5.9_40-owner-installed-r0.md). R4 **attempted on `_40` but refused BEFORE transaction/Stop**: `EXTRA_RESOURCES_FAILED: original lifecycle FD9 is not inherited`. The native service top-level `case` did not send this newly added command through original lifecycle FD9, and its shared-owner preflight also omitted the route. Owner-reported Python journal read did not complete and was interrupted. Owner's subsequent **read-only post-error check PASS**: native `zapret is running`, `phase=failed`, `detail=original lifecycle FD9 is not inherited`, `lua=19`, `bin=54`, `installed=1`, `busy=0`, journal directory absent, quarantine absent. No post-error Config SHA-256 or full IPFW owner witness supplied. [Incident](evidence/2026-10-27-v0.5.9_40-r4-fd9-refusal.md). Do NOT retry on `_40` or manually clean journal; first perform read-only console checks. `_41` is owner-installed; the corrected FD9 dispatch reached durable `committing` and the R4 injected one-inode interruption. Owner observed `mode=remove`, `phase=committing`, `new_native_owner` and `recover-test` printed `REMOVED` ([R4 evidence](evidence/2026-10-27-v0.5.9_41-owner-r4-interruption-forward-recovery.md)). **R4 fault/forward-recovery milestones and owner-console post-recovery service/Config/0-extra/cleanup PASS; independent **current** new owner and managed IPFW health **confirmed on installed `_42`** ([evidence](evidence/2026-10-27-v0.5.9_42-owner-native-audit.md)); historical pre-R4 owner/IPFW comparison not captured. GUI Remove authority still gated pending separate Stages 6–8 acceptance.**
**Authority:** [approved Remove spec](../architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) and [plan](../architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md).

This is a bounded **root-console** test of the original saved Strategies+Voice common Apply with the actual OPNsense service, Git HEAD Lua/BIN, IPFW and process ownership. The production GUI Remove stays `ready=false`; no `configd` Remove action is created. The internal acceptance launcher takes an exact digest-bound plan witness. Its action is **destructive after explicit execution** and briefly interrupts the only Zapret2 engine.

## 0. Required safety gate — read-only

Use a local/hypervisor OPNsense root console, not an SSH connection which depends on Zapret2 or the WAN. Plan a maintenance window, ensure the complete system/OPNsense Config backup and a working console/rescue path, and verify sufficient disk space for transaction backups. Do not stop/kill IPFW, remove transaction directories, or modify saved Config during a pending transaction. **Do not perform destructive trials on an unverified or older installed package.** R0-R2 historical evidence was collected on `_37`; owner-live R3 was performed on `_38`; the R4 command introduced below requires an exact owner-installed `_40` or later verified candidate. Source CI/build alone does not authorize any destructive trial.

On the OPNsense root console (`csh` compatible):

```sh
pkg info -x os-zapret2-restyle
git -C /usr/local/etc/zapret2 describe --tags --exact-match HEAD
/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh status
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh plan
sha256 /conf/config.xml
df -h /var/db/zapret2-restyle /usr/local/etc/zapret2
ls -ld /var/db/zapret2-restyle/extra-resources/transaction /usr/local/etc/zapret2/.extra-resources-remove-quarantine
```

The final `ls` MUST report the two paths absent. If either exists, **STOP**: the proper owner recovery and evidence inspection must precede any new Remove. Do not remove the directories manually. `plan` reports `ready:false` intentionally: it is a read-only checksum-bound source of the witness, **not** an authorized GUI action. Record counts and `inventory_sha256` from its JSON. Do not submit private Config contents, raw engine arguments, full IPFW rules or host lists to a public PR.

## 1. Before/after evidence

For each trial, capture (in the owner's private notes) the Config SHA-256, native status and PID identities, the same `plan` output, and a normalized comparison of managed IPFW rules/tables via the existing original common Apply health evidence. The owner may optionally save read-only `ipfw list` and `ipfw table all list` locally; avoid publishing IP addresses and rules. Compare the same snapshots before and after a rollback, not counters from `ipfw -a list`. The local Git HEAD must be unchanged. SHA-256 equality of `/conf/config.xml` before/after is mandatory. Lua/BIN original inode, uid/gid, mode and mtime must survive negative tests; a same-hash replacement inode is **not** a successful rollback.

Fetch the **current** fresh witness from the exact `plan` output before each test. The instructions below intentionally use a literal placeholder; do not paste it until replaced with the 64-character lowercase `inventory_sha256`. An old witness must refuse before Stop.

## 2. Test R1 — native Stop/quarantine/forced rollback (mutating)

Only with the authorized testing package actually installed, exact source candidate and a confirmed maintenance window:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh remove-test-fail <64-hex-inventory_sha256>
```

The command is **expected to exit nonzero** with `REMOVE_FAILED_RESTORED`: the injected error happens **after actual Stop and physical inode quarantine** but before the new common Apply trial. Prove the old native owner is Started, same Config digest, exact original Lua/BIN set/inodes, restored old IPFW and no pending transaction/quarantine. If any check is unproven or the receipt says `RESTORE_FAILED`, stop further testing, retain evidence and use guarded recovery, not manual file deletion.

## 3. Test R2 — controlled interruption and separate cold recovery (mutating)

After R1 passes and the full fresh witness is reconfirmed:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh remove-test-interrupt <64-hex-inventory_sha256>
```

This raises an intentional hard interruption after actual quarantine, leaving the old engine stopped and a durable resource journal in `restarting`. **Expected: nonzero exit and stopped native engine.** Do not run ordinary Start/Restart. From the local console, run:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh recover-test
```

Expected: exact original owner boot and receipt `RESTORED`, original Lua/BIN inode/metadata, saved Config digest, IPFW and process checks; no pending transaction. This tests an interrupted transaction and separate guarded recovery on installed OPNsense, **not** a physical power-cut. A genuine power-cut remains a distinct explicitly recorded test, not inferred from this injected interruption.

## 4. Test R3 — actual fresh saved-Config common Apply success (mutating and irreversible)

Only after R1 and R2 pass, with a fresh digest-bound plan and with the user accepting that all non-upstream Lua/BIN will be **permanently removed** on success:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh remove-test <64-hex-inventory_sha256>
```

Expected: the real native GUI common Apply compiler runs **after quarantine** with the unchanged full saved Strategies+Voice Config. Its original runtime actuator starts a NEW verified process/common owner; only then the resource journal durably enters `committing`, the optional extra Lua/BIN files are deleted and the transaction is atomically retired. Exit receipt `REMOVED`; exact local HEAD Lua/BIN remain; managed extra `installed.json` is absent; Config SHA-256 unchanged; native health/IPFW passes. A later read-only plan returns zero extra files and a second Remove is a true no-op. The optional installation action must remain separately usable.

If interrupted after `committing`, the only safe action is **guarded forward completion**, not an attempt to restore deleted original inodes:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh recover-test
```

Expected forward receipt is `REMOVED` **only after** existing shared Apply attests the pinned NEW owner and the exact upstream-only files, possibly via its normal guarded cold boot. A foreign or unprovable new owner must produce `RESTORE_FAILED` with retained journal; it is NOT an old-owner rollback.


## 4a. Test R4 — interrupt AFTER durable new-owner commit (irreversible)

This route does NOT exist in installed _38. Run only with a separately
built/published/installed _40-or-later testing package, explicit owner approval,
complete system backup, independent native maintenance console, freshly reinstalled
positive extra-file set, verified Started native service, Config digest and fresh
64-hex Remove-plan witness. Never reuse the earlier R3 witness.

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh remove-test-commit-interrupt <fresh-64-hex-inventory_sha256>
```

Expected: same saved Strategies+Voice native Apply, attested NEW common owner,
durable `committing` journal, physical unlink of one checked quarantine inode
and fsync, followed by deliberate `KeyboardInterrupt` (nonzero). Original inode
is irreversibly gone. Do NOT restart, roll back or clean up anything manually.
From the independent root console use ONLY the native forward-recovery route:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh recover-test
```

Expected: `REMOVED`/exit 0, only exact upstream Lua/BIN, unchanged Config SHA-256,
the exact NEW attested common Apply owner, Started process/IPFW health,
absent managed manifest/transaction/quarantine. Foreign or unverifiable owners
must return `RESTORE_FAILED` with retained evidence. This is a controlled
process interruption, NOT proof of actual hardware power-cut recovery.

## 4b. Independent native owner/IPFW audit after R4 (read-only, source candidate _42)

This is a non-destructive final owner witness, **not** a reason to repeat R4. The `audit-native` command was subsequently installed in `_42` and passed on OPNsense ([redacted live console evidence](evidence/2026-10-27-v0.5.9_42-owner-native-audit.md)); it was not part of `_41`.

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh audit-native
```

Under the ORIGINAL setup.lock → FD9 this read-only root-only command invokes existing `extra_resources_native_previous_owner_service` (sealed shared Apply owner, unchanged saved Config, full active release tree, running engine/IPFW probe) and existing `strategy_lab_semantic_evidence` (live engine/supervisor, active args and Config digests, scoped managed IPFW and five Voice-table fingerprint). No Stop/Start, Config save, resource mutation or kernel IPFW change. A temporary scratch file used by the existing semantic IPFW hasher is cleaned up.

Success outputs exactly a `native-owner=<owner-id>:<page>:<candidate-sha256>` line and a `native-health={...}` JSON line, where native health must report RUNNING, child and supervisor true, and 64-hex args/Config/firewall hashes. These are output shapes, NOT yet observed owner values. Pending resource transaction/quarantine, absent FD9, foreign/invalid owner, failed active tree or IPFW probe, nonrunning child/monitor, or missing IPFW fingerprint all fail closed. No new owner database or raw rules, addresses, hostlists or engine args are exposed.

Record the actual owner ID and digest privately or in a redacted verification report. The old owner ID cannot be reconstructed from an already-retired transaction journal; do not invent that comparison. Source-level tests do not prove on-device owner/IPFW acceptance. Public GUI Remove remains disabled until live evidence and owner acceptance.

## 5. Evidence board and stop rules

| Case | Expected result | Source/CI | Installed result |
| --- | --- | --- | --- |
| R0 read-only plan and owner health | Trusted started original owner, exact HEAD plan; no pending journal | Source routes | **OWNER-LIVE PASS** on `_37` (observed baseline; no separately printed internal owner ID), [evidence](evidence/2026-10-26-v0.5.9_37-remove-r0-r1-owner-live.md) |
| R1 forced after-quarantine failure | Old inodes/Config/IPFW/process owner restored | Offline regression | **OWNER-LIVE PASS** on `_37`: forced rollback, same inode/metadata/hash/Config/IPFW, service running, journal absent; [evidence](evidence/2026-10-26-v0.5.9_37-remove-r0-r1-owner-live.md) |
| R2 pre-commit interruption + separate recovery | Original old common owner restored; journal cleared | Offline regression | **OWNER-LIVE PASS** `_37`: interrupt 130, `remove/restarting`, `RESTORED`/0, six comparisons 0, Started, 73 extras intact, journal cleared; [evidence](evidence/2026-10-26-v0.5.9_37-remove-r2-owner-live.md) |
| R3 native fresh common Apply success | New owner verified, only HEAD Lua/BIN, Config unchanged | Offline regression | **OWNER-LIVE operation PASS on `_38`**: receipt `REMOVED` (19 Lua, 54 BIN, restart true), `plan total=0`, service running, no pending journal/quarantine. Config after SHA captured, matching before SHA and full native owner/IPFW proof **not provided**, so complete acceptance pending |
| `_40` read-only status/cache check | Counters reflect current upstream-only cache; no hanging journal | Source tests PASS | **OWNER-LIVE PASS**: [R0 evidence](evidence/2026-10-27-v0.5.9_40-owner-installed-r0.md) |
| R4 post-commit partial deletion + cold completion | Resume forward after one committed inode is physically unlinked, never falsely roll back | Offline regression + `_41` FD9 wiring/FreeBSD15 PASS | **OWNER-LIVE injection PASS / forward recovery receipt PASS on `_41`**: `KeyboardInterrupt` after first committed inode; journal `committing` with `new_native_owner`; `recover-test` → `REMOVED`. **Post-state (service, 0/0, Config, journal/quarantine/manifest) PASS; sealed current owner and managed IPFW health PASS on installed `_42` ([audit evidence](evidence/2026-10-27-v0.5.9_42-owner-native-audit.md)); historical IPFW baseline not recorded.** [evidence](evidence/2026-10-27-v0.5.9_41-owner-r4-interruption-forward-recovery.md). Earlier `_40` was BLOCKED before transaction ([incident](evidence/2026-10-27-v0.5.9_40-r4-fd9-refusal.md)) |
| `_44` real production API Remove | Confirmed worker removes exact extras and leaves healthy new sealed owner and unchanged Config/IPFW | Project/Voice/FreeBSD15 source CI PASS on `_44` | **OWNER-LIVE PASS:** browser single authenticated remove; matching worker `removing`→`not_installed`, after-plan `total=0`, runtime running with new sealed owner, unchanged Config and scoped IPFW digests, no quarantine/journal/manifest ([R4](evidence/2026-10-27-v0.5.9_44-owner-positive-api-r4.md)) |
| GUI Advanced/RU/EN/Full Help and new Job | Remain gated pending real owner acceptance | GUI contract tested | **Owner RU/EN/F5 PASS** on `_38`; read-only Remove plan modal shows Close only as designed. Full post-Remove Help/New Job acceptance NOT RUN; destructive Remove GUI intentionally gated |

Record the exact **installed package**, upstream HEAD, plan witness, before/after Config digests, attested common-owner ID, process/IPFW snapshots, transaction phases, console command exit status and observed result for each test. Redact private details before any GitHub record. A test is PASS only after the owner's actual appliance observations, not after CI. **Do not enable the public Remove GUI/configd until installed verification and the owner's explicit acceptance.**
