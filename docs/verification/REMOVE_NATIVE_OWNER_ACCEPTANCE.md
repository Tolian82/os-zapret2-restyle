# Remove Additional Resources — owner-installed native acceptance

**Latest published R4-fix testing candidate (NOT owner-installed):** [v0.5.9_41](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.9_41), exact source `379139552eb47c0faa77db0496a0c66f9970cb28`, SHA-256 `4ed5fc24a43fffc73a2d6b6e09aa900e8f44441cdecc57f9966d7ae7ecee0a0b`, FreeBSD15 amd64 ([publication record](evidence/testing-publications/v0.5.9_41.md)). **Previous owner-installed (R4 FD9 gate BROKEN):** [v0.5.9_40](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.9_40), FreeBSD 15 amd64, exact source/tag `a3b6a140a5ebe253f67958f4cc6abbd1747acb94`, package SHA-256 `19b34ba683752def52a0ee49484dd24901c80b98d745f9dc7eafccfaea82c8aa` ([publication record](evidence/testing-publications/v0.5.9_40.md)). Not a stable release; `_40` owner-installed read-only baseline PASS; R4 not run.
**Evidence state:** R0/R1/R2 owner-live PASS on `_37`. On installed `_38`, the owner confirmed RU/EN/F5 GUI and R3 native `REMOVED` for 19 Lua + 54 BIN, subsequent zero-extra plan, running service, absent transaction/quarantine. A matching pre-R3 Config SHA-256 and full internal owner/IPFW witnesses were not supplied in this interaction; do not upgrade this to complete all-checks PASS. On installed `_40`, read-only owner baseline PASS: 0 extra Lua/BIN in status, cache and plan, engine running, no transaction/quarantine, 28G available; [R0 evidence](evidence/2026-10-27-v0.5.9_40-owner-installed-r0.md). R4 **attempted on `_40` but refused BEFORE transaction/Stop**: `EXTRA_RESOURCES_FAILED: original lifecycle FD9 is not inherited`. The native service top-level `case` did not send this newly added command through original lifecycle FD9, and its shared-owner preflight also omitted the route. Owner-reported Python journal read did not complete and was interrupted. Owner's subsequent **read-only post-error check PASS**: native `zapret is running`, `phase=failed`, `detail=original lifecycle FD9 is not inherited`, `lua=19`, `bin=54`, `installed=1`, `busy=0`, journal directory absent, quarantine absent. No post-error Config SHA-256 or full IPFW owner witness supplied. [Incident](evidence/2026-10-27-v0.5.9_40-r4-fd9-refusal.md). Do NOT retry on `_40` or manually clean journal; first perform read-only console checks. `_41` is now published for testing (not installed) with both missing FD9 case labels fixed and a passing dedicated regression test. No claim of R4 acceptance.
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

## 5. Evidence board and stop rules

| Case | Expected result | Source/CI | Installed result |
| --- | --- | --- | --- |
| R0 read-only plan and owner health | Trusted started original owner, exact HEAD plan; no pending journal | Source routes | **OWNER-LIVE PASS** on `_37` (observed baseline; no separately printed internal owner ID), [evidence](evidence/2026-10-26-v0.5.9_37-remove-r0-r1-owner-live.md) |
| R1 forced after-quarantine failure | Old inodes/Config/IPFW/process owner restored | Offline regression | **OWNER-LIVE PASS** on `_37`: forced rollback, same inode/metadata/hash/Config/IPFW, service running, journal absent; [evidence](evidence/2026-10-26-v0.5.9_37-remove-r0-r1-owner-live.md) |
| R2 pre-commit interruption + separate recovery | Original old common owner restored; journal cleared | Offline regression | **OWNER-LIVE PASS** `_37`: interrupt 130, `remove/restarting`, `RESTORED`/0, six comparisons 0, Started, 73 extras intact, journal cleared; [evidence](evidence/2026-10-26-v0.5.9_37-remove-r2-owner-live.md) |
| R3 native fresh common Apply success | New owner verified, only HEAD Lua/BIN, Config unchanged | Offline regression | **OWNER-LIVE operation PASS on `_38`**: receipt `REMOVED` (19 Lua, 54 BIN, restart true), `plan total=0`, service running, no pending journal/quarantine. Config after SHA captured, matching before SHA and full native owner/IPFW proof **not provided**, so complete acceptance pending |
| `_40` read-only status/cache check | Counters reflect current upstream-only cache; no hanging journal | Source tests PASS | **OWNER-LIVE PASS**: [R0 evidence](evidence/2026-10-27-v0.5.9_40-owner-installed-r0.md) |
| R4 post-commit partial deletion + cold completion | Resume forward, never falsely rollback lost inodes | Offline regression; `_41` top-level FD9 repair proposed | **BLOCKED** on `_40` by missing original FD9 dispatch, before transaction; [incident](evidence/2026-10-27-v0.5.9_40-r4-fd9-refusal.md); post-error read-only state confirmed safe |
| GUI Advanced/RU/EN/Full Help and new Job | Remain gated pending real owner acceptance | GUI contract tested | **Owner RU/EN/F5 PASS** on `_38`; read-only Remove plan modal shows Close only as designed. Full post-Remove Help/New Job acceptance NOT RUN; destructive Remove GUI intentionally gated |

Record the exact **installed package**, upstream HEAD, plan witness, before/after Config digests, attested common-owner ID, process/IPFW snapshots, transaction phases, console command exit status and observed result for each test. Redact private details before any GitHub record. A test is PASS only after the owner's actual appliance observations, not after CI. **Do not enable the public Remove GUI/configd until installed verification and the owner's explicit acceptance.**
