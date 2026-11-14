# #1052 P2k8d — durable known auto-owned → shared fallback relocation

**Historical/supersession status (source `v0.6.5_46`):** The original standalone one-intent `auto_detect_verified_owned_commit.py` and tests were removed in `_46`. Proven automatic-owned relocation now uses the canonical P1 policy from the original Config-held v2 model path only, including interrupted multi-target plan checks. This is historical implementation evidence, not a second active worker. The replacement contract is [P2k8p](P2K8P_ORIGINAL_CONFIG_HELD_V2.md).


**Candidate source:** `v0.6.5_34`, 14 November 2026. **Import-only, not an enabled native worker, not a live origin qualification.**

## Observable behavior and original path

P2k8b physically distinguishes root-private automatic `youtube/user` rows from the manual GUI/Config values. P2k8c composes them in the real detached managed generator. Previously, P2k3 detected an authentic trailing unknown native observer but refused any P1 decision containing known-auto-owned removals, even when the real P1 domain policy correctly required relocating those specific owned rows to the editable shared `auto-domains.txt`. Raw native events are **never** attributed to YouTube/User by hostname.

New `auto_detect_verified_owned_commit.py::commit_verified_owned_relocation()` now uses the original P2a queue lock, P2k4/P2k5 GUI destination flock, P2k8b sealed `read_owned()`, P2k3 exact-generation/old-inode/FD/debug + PSL policy, and the existing P2k2b multi-target immutable plan, checked atomic replacements and cursor checkpoint. The only permitted effects from the genuine unknown trailing observer are **shared Auto additions and removals from proven known-auto-owned private files**. All three target file paths must match a complete sealed `youtube/user` store and an independent shared final file. The supplied current manual+owned/exclude snapshot must match the physical canonical owned files and exact shared bytes under the same lock; missing, stale, partial, corrupt, foreign or mutable ownership refuses. No manual YouTube/User Config or `!/^ ` rows are ever written. No second destination journaling mechanism is added.

If the operation is interrupted after adding a shared row, after removing the known automatic row or before the durable checkpoint, it revalidates the existing P2k2b `plan.json` against current P1/physical target content and either resumes safely or retains pending. An already checkpointed result does not restore a user's subsequent deletion. The immutable checkpoint has **`ack_authorized=false`**; original pending is never removed by this source primitive.

## Scoped verification and authorization boundary

Focused tests extend the existing `scripts/test-auto-detect-verified-commit.py` and run in its already present fast affected-source CI after domain-policy IDNA setup. They exercise full original P2a/P2k1/P2k2a/P2k3/P1/P2k2b fixture with physically sealed `youtube/user` files: relocation and manual preservation, idempotent replay after two crash positions, protected-source or stale-snapshot refusal, GUI flock collision, global exclusions, unchanged pending and disabled public entry. P2k3's optional `allow_owned_relocation=True` is private to this authorized bridge; its default still refuses known relocation and the genuine trailing observer never creates new known-list additions.

**Not authorized:** the current PHP `Config::lock()` snapshot releases native Config and destination locks after a read. No original held native Config owner yet spans P1 and physical destination commit, and the test callback does not confer such authority. Genuine original schema-2/FD9 observer activation, attribution for new known-hostlist discoveries, old-generation FD closure, pending ACK, native hot reload, post-drop inode repair and 60-second cron/configd worker remain open. No product GUI/API/Config writer, runtime, IPFW, Voice/WAN/Lab or published `_34.pkg` is changed. Existing stable `0.6.5_1.pkg` is unchanged.

[Approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k4 fallback](P2K4_LOCKED_FALLBACK_COMMIT.md) · [P2k8b physical components](P2K8B_OWNED_SOURCES.md).
