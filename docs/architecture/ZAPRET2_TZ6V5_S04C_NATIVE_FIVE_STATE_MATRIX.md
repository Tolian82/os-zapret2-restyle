# TZ6v5 S04c — actual five-state OPNsense inventory and no-write gate

**Date:** 23 November 2026. Base merged main `v0.6.5_152 8edaf7a3`. Candidate source-only `v0.6.5_153`. No operator testing package and no actions on the owner's OPNsense.

## Physical cases, not mock facts

Native CI runs two **independent disposable OPNsense 26.7 FreeBSD 15** guests using the original official-Mk build, real package/hooks, and real original G03 upstream `v1.0.7` setup:

- **Cold guest:** true fresh state with no plugin, engine, Zapret Config subtree or journal; real installed plugin without upstream engine; real engine with deliberately absent saved Zapret Config subtree.
- **Hot guest:** actual original authenticated HTTPS Strategies Apply and Common runtime, including sealed manifest, original process and IPFW attestation; then running with deliberately invalid saved editable Config; then a real extra foreign IPFW `19098 count ... out via lo0` rule while original Common owner is still running.

One healthy RUNNING control precedes hot fault fixtures. Every fixture mutation is explicitly isolated to the disposable VM **before** measuring; native saved-Config fixtures use only OPNsense Config singleton/lock/save. The test-owned foreign IPFW rule is nonblocking and restricted to a disposable loopback. Never use these fixtures on owner hardware or treat them as a second production Config writer. No arbitrary Stop/cleanup while foreign resources are present; the whole disposable VM is destroyed.

The first no-plugin observation runs the **exact checked-out source adapter**, because no installed CLI exists; after real pkg installation, source and installed adapter bytes must match. All other states invoke the **actual installed** `backend/component_inventory_opnsense.py`, never mocks; compares `/conf/config.xml` bytes/inode/mtime, installed engine, pkgdb tree, original Apply journal/seal/active release tree, relevant PID files, native process census, IPFW rules/tables/module statuses **before and after**. Output contains only neutral enums, no args, PID, secrets or raw addresses. Any changed bytes, created files, unexpected result, unavailable original attestation or foreign-owner misclassification is RED.

The canonical OPNsense saved XML owner is not root: official `AppConfig.globals.owner = wwwonly:wheel` ([platform source](https://github.com/opnsense/core/blob/master/src/opnsense/mvc/app/config/config.php)). The adapter resolves the native `wwwonly` UID using system passwd and otherwise returns `unknown`; file type, mode, inode, size and race guards remain. A strict UID0 policy falsely classified a genuinely valid Config as invalid in the first S04c native guest.

The stock `pkg info -e` subprocess now drops to the fixed system `nobody` user/group without supplementary privileges, so the reader cannot mutate root-owned pkgdb SQLite shared-memory or journals even when the vendor `pkg` implementation uses internal writable DB mappings. A failure to read now yields `unknown`, not a root retry. **Only exact native evidence can qualify this least-privilege choice.**

The adapter must set `sys.dont_write_bytecode = True` **before** importing the pure model or original Common inspectors, preventing new `__pycache__` under the installed plugin tree. No original FD9 acquisition, second process-matcher, independent status authority, active generation write or `status --json`.

## Exact gate

Both native cold and hot jobs and original central source/native CI must PASS at the exact PR head. Until then this is a **candidate, not S04 GO**; issue #1225 stays OPEN, S05 and unified lifecycle remain blocked. No public `.pkg` release.
