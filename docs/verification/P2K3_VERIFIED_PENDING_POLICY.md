# #1052 P2k3 — genuine current-owner/FD/pending gate before canonical P1 planning

**Historical/supersession status (source `v0.6.5_46`):** The old `auto_detect_verified_batch.py` one-intent reader and standalone test were removed in `_46` per DEV-050. Native raw/debug/provenance and P1 policy are now composed only through the original v2 Model transaction. This document describes the historical `_25` experiment, not active code. The replacement contract is [P2k8p](P2K8P_ORIGINAL_CONFIG_HELD_V2.md).


**Source candidate:** `v0.6.5_25`, import-only, no published `_25.pkg` and no installed native worker. Owner stable `0.6.5_1.pkg` remains unchanged.

## Observable scenario and bound

P2k2b can durably write already validated effects but the existing API does **not** prove where an `effects` object came from. A native log "adding to" predates native file append, and a stale PID or old historical receipt cannot authorize a new destination. Directly passing raw lines to that writer would bypass the approved P1 PSL/exclusion rules and could cause a wrong-list positive or incorrect pending acknowledgment.

The new import-only `backend/auto_detect_verified_batch.py` performs one **read-only** proof-bound planning cycle under the original `DurableInbox.exclusive()` lock. Defaults call the actual `attest_running_generation()` and `probe_pending_fd()`; on non-FreeBSD/root or on a non-activated original schema-2 generation they fail closed. Only tests may inject synthetic callbacks and cannot use the public native CLI.

1. Obtain authentic **current** original P2c owner and validate the protected P2k2a epoch/intent, exact raw/debug and observer, and same-generation pending basename/inode/size/SHA256. Old generation cannot be relabelled as the new running PID.
2. Require P2b `FDState.DRAINED` for the exact old pending inode and that original owner. Busy, unknown, replaced, partial or foreign pending refuses, without advancing the cursor or deleting anything.
3. Replay the **real P2k1** debug/native-raw one-to-one comparison, checking proposed end offset/hash and candidate count against the durable original P2k2a intent. Require exactly the trailing passive native observer; no source IPSET, Voice, prior HOSTLIST or inferred origin.
4. Call the existing **canonical P1** `domain_policy.plan_auto_additions()` with the supplied complete user HOSTLIST, auto-owned and global exclusion snapshots. An observer's origin is explicitly `None`, not guessed from hostname. PSL ICANN+PRIVATE, IDNA, positive dedup and `!/^ ` rules remain in P1. Reject partial/unprocessed results and any auto-owned relocation or nonshared destination until P3 has a protected durable ownership ledger.
5. Reattest the original owner and return `VerifiedBatch(..., ack_authorized=False)`, an **ephemeral** policy preview only. It is not a new durable receipt, not a P2j `committed=True` callback and cannot call P2k2b's writer.

## Proof and limits

`scripts/test-auto-detect-verified-batch.py` exercises actual P2a/P2k1/P2k2a/P1 modules with temporary protected files and *injected* native owner/FD callbacks: PSL `video.example.co.uk → example.co.uk`, shared fallback, other-HOSTLIST `!`/global exclusions, FD BUSY/UNKNOWN, changed common owner, tampered pending/debug and auto-owned relocation refusal. It must run in the existing **fast affected CI** after the pre-existing IDNA install step. Local S0 compiled real candidate Python and executed the production adapter's candidate/FD/relocation/exclusion paths on a real temporary file using **synthetic dependency stand-ins**. That is neither a successful integrated test nor native FreeBSD evidence. Exact-head CI, package builds and owner-installed results remain separate.

**Still unimplemented:** original FD9 post-credential-drop inode reownership, authorized schema-2 source generation, genuine live FD evidence for this path, old-generation sealed/proven replay, P1 whole-file GUI coordination and durable auto-owned relocation, shared editable GUI lock and stale-form detection, bound P2k2b commit/ack and 60-second cron→configd consumer. Public `run_native_verified_batch_worker()` always refuses. No `dvtws.args`, Config writer, IPFW, Voice, Strategy Lab, GUI or real HOSTLIST mutation is added in P2k3. P2 partial; P3–P5 open.

[Owner specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P2 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k2a](P2K2A_IMMUTABLE_EPOCH_INTENT.md) · [P2k2b](P2K2B_DESTINATION_CHECKPOINT.md).
