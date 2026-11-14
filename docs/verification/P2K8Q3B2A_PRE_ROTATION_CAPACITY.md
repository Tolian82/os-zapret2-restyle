# #1052 P2k8q3b2a — original 4 MiB bound before raw rotation

**Candidate:** source `v0.6.5_51`, 14 November 2026. **Scope:** a source-only, currently nonactivating safety change to the existing ONE P2a original `DurableInbox.rotate()`; not a new producer, service, raw format, scheduler, or separate queue. This stage does **not** claim continuous lossless collection.

## Reproduction, cause and changed behavior

The physical raw queue `rotate()` formerly called `_stat_regular(self.inbox, ...)` with no size bound. A >4 MiB live inbox therefore passed P2a, received a new hardlink in root-private `pending`, and was atomically replaced. But the existing P2k1 raw/debug validator, `detached_original_raw()` and `DurableInbox.acknowledge()` all enforce a 4 MiB maximum. This yielded an unprocessable detached original pending, not a functioning minute cycle. The same issue applied to a crash state with a same-generation pending hardlink to the oversized live inode.

The correction adds `max_size=MAX_SEGMENT` to the **same existing** P2a live-file stat under the original exclusive queue lock, before listing/recovering pending and before creating any new temp/hardlink/replace. For a live oversized inode it raises `QueueSafetyError("oversized_segment")` without changing its device, inode, size or bytes. For a pre-existing same-inode pending hardlink, the link and live original inode remain intact, without pretending recovery succeeded or attributing it to another generation. Exact 4 MiB remains a P2a size-valid input, subject to separate content/native-FD checks. Post-rotation native append races are still guarded by downstream size/FD/commit checks, **not** solved by this precheck.

## Test scenario and evidence limits

- `scripts/test-auto-detect-queue.py`: a real sparse oversized live inode refuses *before* hardlink/replace and leaves pending empty; crash-created same-generation oversized hardlink refuses with exactly two links and unchanged live name; existing below-limit/old-open-FD and after-rotation oversized ACK tests remain mandatory.
- `scripts/test-auto-detect-original-v2-prepare.py`: the actual original P2k8o/v2 preparation retains the oversized live inode, creates no pending/v2 intent and makes no P2b FD inquiry; prior bounded first/two event cycles and historical-pending refusal remain unchanged. Its P2c/P2b native witnesses are deliberately injected in portable tests, not installed engine acceptance.

No active schema-2 argv/map is emitted. The existing `authorize` refusal, inactive configd ingress and absent 60-second cron are unchanged. `commit_authorized=false`. An already oversized live file is **retained and refused, not automatically recovered**. Continuous lossless 4 MiB raw/debug rollover, 512 cursor-slot rollover, prior-generation writer-FD ancestry, genuine native first-match, full worker/ACK, native FreeBSD integration and owner-installed acceptance all remain explicitly open.

The exact-head CI job and its result will be recorded separately; a source change or synthetic test alone is **not** native/owner proof.

[Normative plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [original P2a queue](../../src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_queue.py) · [prior original FD9 barrier](P2K8Q3B1_NONTERMINAL_EPOCH_COMMIT.md).
