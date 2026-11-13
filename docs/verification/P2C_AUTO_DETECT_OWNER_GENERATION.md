# #1052 P2c — common owner and generation provenance gate (not active)

**Development candidate:** `v0.6.5_12`. Follows [P2a durable pending](P2_AUTO_DETECT_QUEUE.md) and [P2b genuine FreeBSD kernel FD inspection](P2B_AUTO_DETECT_FREEBSD_FD.md). Authorized scope is the original [P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). Source-only step, **not completed P2**.

## Why this is needed

A native profile number or domain filename alone does not reveal which Traffic Strategy/HOSTLIST originally produced it: the original normalizer splits mixed HOSTLIST+IPSET sources and the engine has native templates, imports, Voice, Extra and a default profile. Equating final `--hostlist` with an originating source is unsafe. An engine PID and `fstat` check alone do not authenticate a common runtime generation, either.

`backend/auto_detect_owner.py` is read-only and **never calls `DurableInbox.acknowledge`**. It reuses the existing terminal Shared Apply journal and its committed owner (including restored predecessor), the existing `shared_apply_seal.verify_seal()` release integrity proof and existing shared launcher/PID/monitor identity. It refuses nonroot/non-FreeBSD, pending/review-required Apply, missing seal, missing/modified active release, missing or foreign PID/supervisor, changed process start/command, duplicate or orphan engine and incomplete native process inventory. The running command must exactly equal the launcher executable + every token of the sealed `dvtws.args` + its two fixed flags. Process and journal identity are read twice to catch observed changes. This does **not** add a process owner, SQLite, external witness, Config writer or FD9 holder.

The **mandatory** `auto-detect-generation.json` is required to be created by the *original generation pipeline* **inside the sealed release before shared activation**, and copied into its active runtime. It must carry the exact original owner transaction ID/config digest, final argv SHA-256, Target Mode=auto, unique final native profile numbers, non-inferred status/source labels, a trailing no-Lua/no-import/no-IPSET observer, raw inbox/debuglog paths **matching the actual native flags** and the implicit profile 0. The gate accepts only marker `ORIGINAL_SHARED_GENERATOR_CAPTURE`, rejecting the P0 detached fixture marker. P2c's validator is not a replacement domain parser; profile origin capture must use the **already verified P0 original-generator transformation stages**, not guess origins from argv.

**Critical shipping boundary:** This PR introduces the *consumer/validator* only. The actual product generator has not yet been modified to capture and seal this P2 map. A genuine installed product therefore cannot produce a positive proof from this source. Portable tests use a **synthetic locally sealed test bundle and simulated process output**, not evidence of a real daemon. A manually fabricated map, even if it matches an argv, must never be treated as proof that the original profile pipeline generated it. Original-producer capture, real installed runtime, real `dvtws2` start/exec identity and corresponding raw/debug events are the **next P2 gate**.

No production observer is appended and no new auto raw/debug files, cron action or final HOSTLIST writes exist. Stable owner-installed `0.6.5_1.pkg` remains untouched. No new `.pkg` published.

## Proportionate check selection

S0/S1: `python3 -m py_compile src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_owner.py scripts/test-auto-detect-owner.py` and `PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-auto-detect-owner.py`. Focused ten-case fixture covers exact stable synthetic owner, nonterminal/stale owner, sealed/active bytes, wrong native argv/PID birth, foreign or duplicate engine, monitor loss, missing map, stale source/ambiguous profile, wrong raw/debug and action-bearing observer, untrusted provenance and off-target public refusal. CI runs these under the existing fast affected path plus regular Project/Voice/native archive build for changed packaged Python. Native original dvtws2 shared owner acceptance is **NOT** claimed by such a portable suite; no separate historical VM campaign is justified.

## Next necessary work before enabling collection

1. Inside existing original `orchestrator.sh` / Target Mode/profile normalization/resolver/Voice/Extra/global exclusion stages, capture the P0-proven source ancestry, append **only** the approved trailing observer, produce protected generation map from the **same build** and include in shared release before its original FD9 seal. Record raw/debug generation and do not convert IPSET, Voice, STUN or unknown into known HOSTLIST.
2. Bind the actual original launcher start identity and sealed execution, and qualify native real-`dvtws2` map/debug/raw + P2b held writer-FD behavior together. A pure read-side snapshot cannot prevent future races; the final worker must reattest across processing and before `pending` deletion.
3. Add durable auto-owned destination+relocation and idempotent crash replay; only after that connect fd-drained and committed callbacks and the 60-second native cron → configd short worker. Then P3 final explicit-only HOSTLIST wiring and P4/P5.

**Status at authoring:** source staged in PR; final exact-head CI results, native real owner and installed device acceptance are separate. Issue #1052 stays open.
