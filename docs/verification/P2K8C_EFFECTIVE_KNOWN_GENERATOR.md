# #1052 P2k8c — effective known-HOSTLIST composition on original builder

**Source:** `v0.6.5_33`, 13 November 2026. **Changed product path: detached generated managed files**, not a native event collector or installed acceptance.

## User scenario and changed path

Existing YouTube/User manual GUI domains pass through the original `targets_prepare_managed()` and canonical `domain_policy.py single` before `dvtws2` arguments are built. The builder now invokes `auto_detect_effective_known.py compose` on the two actual normalized output files. When a complete, explicitly sealed root-private `auto-detect-owned/{youtube,user}.txt` exists, the composer obtains the **same destination flock** as the Auto Hostlist GUI and P2k4 and merges only plain automatic entries into those detached generated files. Manual order, `!`/`^` modifiers and any cross-list negative exclusions remain intact. Duplicate entries are skipped. The original manual Config values and root-owned automatic sources are never rewritten.

When the owned store is missing/uninitialized, the original generated files remain byte-identical and no new lock or store is created. Unsafe symlinks, corrupt/foreign/partial storage, noncanonical generated files and concurrent GUI lock ownership reject the entire detached build. The product never reads the retired `zapret-hosts-auto.txt` source.

## Minimal source gate and limitations

The focused `scripts/test-auto-detect-effective-known.py` exercises actual `domain_policy.py single` → staged file → protected compose; verifies empty/uninitialized no-op, manual exclusions and duplicates, idempotence, refusal on corruption, shared lock and symlink, and checks the composer call precedes managed-file publication in `targets.sh`. Native installed evidence and exact-head CI belong to their real runs; they are not inferred from this record.

**Not completed:** original generation-authenticated additions to private known-list files, per-generation P2k2b receipts, original OPNsense Config-held P2k4 policy/commit lock, old-pending ACK, native observer, engine hot reload and minute cron/configd worker. This is **not** owner-appliance acceptance and no `_33.pkg` has been published.

[Approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k8b storage](P2K8B_OWNED_SOURCES.md).
