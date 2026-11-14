# #1052 P2k8e — original Config-held synchronous Model to durable transaction

**Historical/supersession status (source `v0.6.5_46`):** The original native PHP `Config::lock`/Model/FD inheritance survives unchanged and is the active v2 Model owner; the former one-intent Python adapter was retired in `_46`. No alternative adapter or second Config writer exists. This is historical `_35` source evidence. The replacement contract is [P2k8p](P2K8P_ORIGINAL_CONFIG_HELD_V2.md).


**Source candidate:** `v0.6.5_35`, 14 November 2026. **Source-only integration; not an enabled worker, production FD9 run or installed-appliance acceptance.**

## Concrete user path

A correctly sealed YouTube/User **automatic** row is eligible to move into `auto-domains.txt` only after an authenticated unknown-source discovery and current P1 excludes. P2k8d already performs the complete P2k2b physical relocation/atomic multi-target CAS/checkpoint, but its `snapshot()` was an injected tuple without an original Config lock. A stale manual `!example.com` could otherwise be overwritten by background policy timing.

The existing `src/opnsense/scripts/OPNsense/Zapret/auto_detect_config_snapshot.php` now offers `AutoDetectConfigSnapshot::withLockedOriginalModel(config, modelFactory, operation)`. It uses the **same original** `OPNsense\Core\Config::lock()` and fresh registered `OPNsense\Zapret\Zapret::getNodes()` shape already used by the read-only P2k8a adapter, extracts only manual `youtube`/`user` and global `exclude` values, and invokes one **synchronous** operation without releasing that Config lock between policy and destination completion. A fresh native Model digest is checked on return, and the only accepted completed receipt is `destination-and-cursor-committed` with `ack_authorized=false`. Every exit and exception calls original `Config::unlock()`; the callback receives no Config object or ability to save through the adapter.

`backend/auto_detect_verified_owned_commit.py::commit_with_locked_original_model()` accepts exactly the two original manual HOSTLIST fields and global exclusion, requires the original P2a queue to be held by its caller, obtains the current editable shared Auto Hostlist and protected automatic known-list contents **under the existing P2k4/P2k5 destination flock**, and delegates to the existing P2k8d→P2k3/P1→P2k2b transaction. No separate config.xml parser, new policy, journal, Config writer or second list lock is introduced. The strict unknown-observer source contract and private-only removal still apply. This path never returns authorization to delete pending.

## Evidence and remaining bound

Existing focused `scripts/test-auto-detect-config-snapshot.php` covers a synchronous checkpoint callback **while the original test Config is held**, payload-only original Model fields, exception release, rejection of an ACK-capable checkpoint and changed Model digest. Existing `scripts/test-auto-detect-verified-commit.py` covers the real physical-file P2k8d/P2k2b operation starting from only those Model values and current final/owned physical files; it retains the real P2a/PSL policy with injected native owner/FD test fixtures. Both run in existing fast affected CI; source syntax and exact PR/main checks are recorded separately. These source tests do not establish a running native observer.

**Not authorized:** the original queue → PHP Config → Python destination multi-process lifecycle is **not wired to an installed action**. A generic PHP operation callback is not native owner proof, and its contract alone cannot prove that other code did not invoke `Config::save()` (which releases OPNsense's own Config flock) while a child ran. The actual original Config lock owner must remain demonstrably alive across the synchronous child, after the queue owner is established, before native writes can be authorized. No FD9 generation, fresh known-list attribution, old FD/ACK, cron/configd worker, GUI, runtime, IPFW/Voice/WAN/Lab or testing-package publication is added. `commit_authorized=false`; public CLI is still read-only.

[Owner specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k8d physical relocation](P2K8D_DURABLE_OWNED_RELOCATION.md) · [P2k8a Config model](P2K8A_CONFIG_READONLY_SNAPSHOT.md).
