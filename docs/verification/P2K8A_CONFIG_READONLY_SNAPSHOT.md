# #1052 P2k8a — native Config/HOSTLIST read-only lock-coupled snapshot

**Source candidate:** `v0.6.5_31`, 13 November 2026. **Follow-up:** `_32` [P2k8b](P2K8B_OWNED_SOURCES.md) replaces the single final-file read with one root-protected read of final **and** separate known-owned components under the same destination flock, still `commit_authorized=false`. The `_31` proof below is retained for its original read-only snapshot behavior. **Nonactivating first piece of the P2/P3 authoritative snapshot gate.** This is source/CI qualification, not owner's installed OPNsense acceptance.

## Actual user risk before the change

The dormant P2k4 `commit_verified_fallback()` takes an *injected* tuple `(all manual hostlists, all auto-owned sources, global excluded domains)` from a test adapter. No native code can currently prove that the tuple represents the same original `config.xml` generation as the protected `auto-domains.txt` bytes, or that automatic provenance is complete. Creating a new, independent `config.xml` parser would not solve it. A stale policy decision could append a domain just excluded by a contemporaneous Strategies/Voice Config save.

The original OPNsense `Config::lock()` provides the model's native shared Config inode flock. `Config::save()` **itself releases the lock**; the original Apply recovers by reacquiring and rereading rather than trusting a stale snapshot. P2k4's existing destination flock does not also lock original Config and must not be used as substitute.

## Implemented bounded source seam

`src/opnsense/scripts/OPNsense/Zapret/auto_detect_config_snapshot.php` adds `OPNsense\Zapret\Native\AutoDetectConfigSnapshot::capture(config, modelFactory, finalReader)`. A single `try/finally` acquires the **actual provided native Config::lock()**, constructs a **fresh original Zapret MVC model via `getNodes()` under that same lock**, extracts exactly the **registered manual HOSTLIST** fields `hostlist.youtubedomains` and `hostlist.userdomains` plus global `hostlist.excludedomains`, then invokes the root P2k5 protected final-hostlist reader **without releasing the Config lock**. The final reader itself takes the existing P2k4/P2k5 root `flock` and reads only `/usr/local/etc/zapret2/ipset/auto-domains.txt`; it never uses the obsolete `zapret-hosts-auto.txt`. The only registered HOSTLIST identities currently are `youtube`, `user`, `auto` (no IPSET mixed in).

The root-only FreeBSD PHP `read` CLI uses `script/load_phalcon.php`, `OPNsense\Core\Config::getInstance()`, `new OPNsense\Zapret\Zapret()`, and a fixed `proc_open` argv to the **existing** protected `python_runtime.sh .../auto_detect_gui_hostlist.py read`, not a new lexer, configd action or Config writer. It compares the native `missing\0`/`present\0` SHA256 revision with exact bytes, rejects missing/incorrect model scalars, malformed P2k5 response, inconsistent empty/missing/populated statuses and oversized evidence. Model field strings are retained without normalization or Config mutation. All lock/error paths release original Config; Python's existing target lock releases on read completion. No domain strings are printed in errors.

Every emitted result deliberately states:

- `status=read_only_unqualified`; `commit_authorized=false`.
- `auto_owned_components=null` and `auto_owned_complete=false`, **not `{}`**: persistent known-HOSTLIST automatic ownership is not implemented yet.
- A full native Model baseline digest from the original `VoiceSettingsSnapshot::digest`, and exact new `auto-domains.txt` content/status/revision.

**No P2k4 write caller, native collector, root mutation API, FD9 owner, IPFW rule, cron/configd worker or pending ACK is enabled.** The current Config and final-file locks overlap **during this read only**, not across any future destination transaction. This returned object is therefore **not an authoritative writable P2k4 callback**. Do not interpret a digest as a serializable snapshot or read the file again later outside the Config owner. The next step must bind the **complete auto-owned provenance** and hold native Config ownership through the *whole* P2k4 policy-and-destination transaction, with fail-closed release/child-death proof. A native `Config::save()` can release its own lock, so do not silently extend this read-only adapter into an unguarded write.

## Focused acceptance

`scripts/test-auto-detect-config-snapshot.php` asserts the registered HOSTLIST set has not grown silently, a fresh model and physical final reader are both called **while Config::lock is held**, original `!/^ ` strings are unchanged, missing/empty/populated final states have distinct valid revisions, incomplete fields/option dictionary/oversize/mismatched revision/error return are refused, exceptions release the lock, no `save()` or serialized XML occurs, and non-FreeBSD CLI refuses native authority. Sixteen real PHP scenarios passed locally, with an injected test Config/Model and local digest stand-in; exact-head CI uses the real repository `VoiceSettingsSnapshot` and original `registry.sh`. No owner appliance proof is inferred from either source test.

The original common `dvtws2`/FD9, WAN-first, IPFW ownership, Voice/Strategies shared Apply, and no-Strategy-Lab contract remain untouched. No `_31.pkg` is published or owner installed; stable owner-installed `0.6.5_1.pkg` unchanged.

[Approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P0–P5 ordered plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k4 protected fallback](P2K4_LOCKED_FALLBACK_COMMIT.md).
