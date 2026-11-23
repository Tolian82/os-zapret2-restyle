# TZ6v5 S04 — independent component inventory: formal native GO

**Accepted 23 November 2026.** Physically qualified production source `v0.6.5_153`, accepted [PR #1266](https://github.com/Tolian82/os-zapret2-restyle/pull/1266), merged source `main 6a71e10edb5b59d727e4d1320895923662064297`. Exact tested source head `7f4c6a4f1abca6993deb3f3f6f88e892bfa361d7`. This formal document is a **documentation-only** candidate `v0.6.5_154`, not an additional physical build or owner-device release.

## Actual physical qualifying matrix

The [two native OPNsense 26.7 FreeBSD 15 guest jobs #45215394069](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45215394069) both **SUCCESS**, using the original official-Mk package builder and real hook installation, native G03 selected upstream `v1.0.7`, actual Common release and authenticated HTTPS Strategies Apply. They exercise real installed reader except the genuine no-plugin case, where the **identical checked-out source** must run because there is no installed CLI. After installation, byte identity between source and installed reader is asserted.

| Actual native physical state | Component facts | Classification | No-write |
| --- | --- | --- | --- |
| No plugin, engine, saved Zapret subtree or manifest | plugin=absent, engine=absent, config=absent, manifest=missing, runtime=STOPPED | `PLUGIN_NOT_INSTALLED` | PASS |
| Real plugin installed; upstream engine still absent | plugin=installed, engine=absent, config=initialized, manifest=missing, runtime=STOPPED | `ENGINE_NOT_INSTALLED` | PASS |
| Real G03 engine installed; Zapret subtree absent (native Config fixture) | plugin=installed, engine=valid, config=absent, manifest=missing, runtime=STOPPED | `CONFIG_UNINITIALIZED` | PASS |
| Original Common owner genuinely RUNNING, editable native Config toggle corrupted | plugin=installed, engine=valid, config=invalid, manifest=valid, runtime=RUNNING | `CONFIG_INVALID` | PASS |
| Original Common owner RUNNING plus an actual unrelated nonblocking IPFW `19098` rule | plugin=installed, engine=valid, config=invalid, manifest=valid, runtime=FOREIGN_OR_UNVERIFIED | `FOREIGN_OWNER` | PASS |

One additional **healthy RUNNING** original owner control yielded `RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION` with five valid/initialized facts and no-write PASS.

Each observation compares **before and after** Config XML content/hash/inode/mtime/mode, executable, original pkgdb, shared operation journal/seal, active release/epoch tree, relevant PID files, process census, native IPFW rules/tables and module state. Output is enum-only, `authorization=NONE`, `physical_transition_allowed=false`, `original_fd9_attestation_required=true`. Fixture mutations occur only *before* each observation, only in independent disposable VMs. No foreign-resource cleanup/Stop is attempted in the contaminated hot guest; it is discarded.

## The RED defects actually reproduced and corrected

1. The original root `pkg info -e` updated the **mtime of existing SQLite pkgdb `-shm`**, although its contents stayed identical. Both cold and hot physical no-write probes refused. The final S04 adapter invokes the **same installed stock pkg binary** with `nobody` UID/GID, no supplementary groups; failures report `unknown` without escalation. No new SQLite database, watcher, pkghook or second state authority.
2. The original adapter assumed `/conf/config.xml` was UID0-owned and falsely returned `invalid`. The canonical OPNsense `AppConfig.globals.owner` is `wwwonly:wheel`; resolve `wwwonly` through native passwd, preserve strict regular-file/permissions/inode/bounded-read/race checks. Unknown OS identity remains `unknown`. Future pfSense is a **different platform adapter**, not a hardcoded OPNsense policy in the neutral model.
3. Prevent Python bytecode-cache side effects with `sys.dont_write_bytecode=True` **before** importing the neutral classifier and existing runtime attesters. The physical before/after file-tree checks qualify this.

## All acceptance gates

- [S04 native cold/hot #45215394069](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45215394069): **SUCCESS/SUCCESS** at exact head `7f4c6a4f`.
- [Central CI #45215393926](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45215393926): **SUCCESS**, including user path contracts, full Project, Voice, and official source-only native OPNsense package build.
- [Stage 1 #45215394446](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45215394446): **SUCCESS**.
- [Published predecessor _107 schema2→native schema3 regression #45215394374](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45215394374): **SUCCESS**.
- [PR title policy #45215393964](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45215393964): **SUCCESS**.
- [PR #1266](https://github.com/Tolian82/os-zapret2-restyle/pull/1266) **MERGED**. No `_153.pkg` or `_154.pkg` published or installed on operator's device.

**Formal S04 GO is for non-authoritative component observation only**: no Start, Stop, force, reload, repair, compilation, configd save, or second owner. `engine=valid` currently means bounded native FreeBSD/amd64 ELF structure, **not** independently attested upstream source provenance or working traffic/packet passing. The existing original sealed owner/epoch/IPFW observer is reused, but the neutral classification itself is never a terminal authorization receipt.

**Next ordered milestone:** S05 unified read-only `status --json`, keep old plain `status` compatible, truthful original owner/epoch/IPFW census and a safe bounded diagnostic envelope; no state mutation. S05 **not implemented by S04**, and S06–S20 remain pending. Continue tracking original Lab/Auto/UI lifecycle failures in open issues #1223/#1224/#1225. S03 RED GO remains historical and unaffected.
