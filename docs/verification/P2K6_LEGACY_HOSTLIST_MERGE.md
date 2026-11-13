# #1052 P2k6 — safe, explicitly reviewed two-populated Auto HOSTLIST migration

**Candidate:** source `v0.6.5_28` (13 November 2026). Source-level follow-up to [P2k5](P2K5_GUI_AUTO_HOSTLIST.md). No `_28.pkg` release or owner-installed change; original native detection still disabled.

## Exact observable scenario

A normal upgrade may leave both the native legacy `/usr/local/etc/zapret2/ipset/zapret-hosts-auto.txt` and the new explicitly selected `/usr/local/etc/zapret2/ipset/auto-domains.txt` **already populated with different lines**. P2k5 deliberately refused to silently overwrite the new file, so the owner could not safely merge the old discoveries from Strategies. Blindly copying on every read would resurrect positive rows the owner had intentionally deleted.

## Implemented native source path

The P2k5 `auto_detect_gui_hostlist.py` root-native editor now supports a third operation: **`migrate <new-revision> <legacy-revision>`**. Native OPNsense `configd` registers the bounded `auto_hostlist_migrate` action; the existing Settings API exposes only a POST action `autoHostlistMigrateAction` with strict SHA256 revision tokens and read-only mode denial. The Strategies RU/EN Auto Hostlist row adds an **Import Legacy List / Перенести старый список** button visible only if the root read finds an eligible explicit union. The UI retains unsaved text and requires confirmation; it does not call shared Apply, Config::save or restart. The existing Auto Hostlist text and P2k5 Save/Reload remain independent.

All source and destination file checks, canonical `domain_policy.normalize(..., 'user')`, and the durable edit run **under the exact P2k5/P2k4 root-owned `exclusive_destination_lock`**. The old file remains on disk. Candidate rows are normalized individually; existing target file bytes and manual `!/^ ` modifiers are retained. Only absent rows are appended. A duplicate hostname with different modifiers or overlapping positive and negative match scopes is **refused**, not silently resolved. Unreadable/symlinked, untrusted, oversized, changed or conflicting inputs fail closed. Both list content and the independent legacy file are compared against the exact revisions shown to the user at the instant of confirmation.

A root-private directory `ipset/.auto-domains-legacy-migration` contains **write-once, fsynced `plan.json` and `done.json` receipts**. Before any destination replacement, the intent durably pins old/new digests, expected final digest and insertion count. If interrupted after replacing the destination but before the done receipt, a confirmed follow-up click can finish the same transaction **without repeating additions**; any intervening user edit instead refuses. The legacy source digest is rechecked before and after replacement because the old native producer may not honor the GUI flock.

**Idempotent deletion guarantee:** once an original legacy digest is committed, later GUI deletions in `auto-domains.txt` do **not** reappear on read or repeat migrate. If the old source later changes, its existing sealed receipt does not authorize a second automatic merge; the UI says **manual review required**. This includes P2k5's safe first-copy case: when old and new are provably identical on read, a no-change done receipt is seeded before a future manual deletion. This is a one-time reconciliation, **not a periodic synchronization** or unrestricted merging of two actively written files.

The existing 40 KiB GUI transfer bound remains. Larger sources or merged result require a separate qualified transport and are rejected, never truncated.

## Bounded verification and limits

`scripts/test-auto-detect-legacy-merge.py` uses actual root-owned temporary files to cover separate-populated merge, same-row dedup, `!^ ` preservation, stale GUI/new and legacy revisions, lock contention, modifier/exclusion conflict refusal, first-copy receipt, crash-after-replace recovery, post-crash user-edit refusal, symlink refusal and non-FreeBSD CLI gating. Before GitHub push, a local `py_compile` plus eight physical file scenarios with **injected stand-ins for external import dependencies** passed; the real P2k5/P2k2a/P2k2b/domain_policy imports are verified only by exact-head CI, not by that local test. A dedicated affected CI fast step runs the new test under actual canonical modules after IDNA installation, plus PHP lint and unaffected source checks. Actual GUI acceptance remains separate from CI native package/build and browser tests.

**Not solved by this migration:** P2k4 still lacks an authoritative native Config + all manual/owned HOSTLIST snapshot held under the same GUI/Config writer coordination; proven auto-owned known-list provenance and relocation, original FD9 schema-2 after post-drop ownership repair, historical owner/FD and pending acknowledgment, and the minute worker are not connected. P2/P3 partial; P4 partial, P5 open. P2k6 does not activate native Auto-detect, touch runtime/Voice/Lab/IPFW or publish a package.

[Approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k4 original commit](P2K4_LOCKED_FALLBACK_COMMIT.md).
