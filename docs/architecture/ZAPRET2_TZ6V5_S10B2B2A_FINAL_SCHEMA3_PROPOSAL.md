# TZ6v5 S10b2b2a — truthful final schema3 root proposal (detached)

**Input:** [S10b2b1 merged PR #1323](https://github.com/Tolian82/os-zapret2-restyle/pull/1323), accepted `main v0.6.5_202 bf9f5a19`, and the still-open [S10 acceptance issue #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319). **Candidate:** source-only `v0.6.5_203`. This increment is **not S10 GO, not physical FD9 authorization, and not the S11 service implementation**.

## Actual original producer boundary

The original P2e/S08c/S08d attest **prepromotion** native arguments, while the original `auto_detect_origin_map.promote_learning_release()` preserves those arguments as `release/dvtws.original.args` and replaces `release/dvtws.args` with the genuinely promoted schema3 working-plus-learning sequence. The original `auto-detect-source-map.json` still describes the prepromotion source; original `auto-detect-generation.json` describes the promoted native profile identities. The two native argument SHA-256 values **must differ**. S08d deliberately refuses the promoted `--hostlist-auto` arguments.

The accepted S09a schema-1 root must therefore **never** be relabelled as proof of final schema3 argv. S09b/S10a/S10b1 likewise remain valid for their original exact prepromotion contract, not as automatic postpromotion authorization. The accepted S10b2b1 original-FD9 source bridge attests the actual producer and sealed journal but grants no permission to execute.

## Bounded new proposal

`backend/neutral_schema3_final_root.py` defines pure `compile_final_schema3()` and byte-exact `validate_final_schema3()`. Inputs are the existing typed `NativeParity`, original S08d `EffectiveSnapshot`, accepted S10b2b1 `OriginalSchema3Receipt`, and **actual bytes** from that same candidate: original/final argv and original/active maps. It reuses S09a canonical bounded root encoding/resource grammar and the accepted S10b2b1 source/first-match validator. It does not rebuild engine argv or derive a second native learner.

The resulting proposal has **schema 2** to keep the previous schema-1 consumer fail-closed until a later original-FD9 implementation explicitly supports this schema. It contains only the original top-level `schema/generation/service/resources/refs` shape:

- Original S08d structural SHA stays distinctly identified as `original_structural_sha256`; the proposed final `structural_sha256` hashes the **true** old/final argv SHA, the source/active map SHA, native capture SHA, working/learning counts and original structural SHA.
- Fixed ordered exact same-generation references: final `dvtws.args` (0644), prepromotion `dvtws.original.args` (0644), original `auto-detect-source-map.json` (0600), and promoted `auto-detect-generation.json` (0644). Every ref includes the **one original** seal SHA. The proposed reference modes must later be independently proved from the actual installed original producer.
- Mutable P1/Found/managed **contents never become immutable root hashes**. Existing S08d managed names and `original-p1-cas-ack` ownership are retained, with original schema3 learning native numbers only. No user domains, IP values, arguments or source text are copied inline.

Both proposal functions have **no filesystem, FD9, Config, IPFW, PID, engine, signal, journal or active-manifest side effects**. Their receipts permanently state `authorization=NONE`, `physical_transition_allowed=False`, and `promotion_allowed=False`; they cannot be handed directly to the legacy S10a writer or authorize `PREPARED→ACTIVATING`.

## Genuine original-path regression

`scripts/test-tz6v5-s10b2b2a-final-schema3-root.py` reuses the actual S10b2b1 P2e/S08c/S08d/Voice/original promotion/full-seal/one-PREPARED-journal fixture. It checks real distinct SHA values, exact reference order and modes, deterministic unchanged original workspace, old schema-1 refusal, forged authorization, altered original/final/map bytes, wrong native/S08d source identity and stale PREPARED denial. The new original source test runs in existing fast CI; local portable syntax checks do **not** count as genuine generator, FreeBSD or router acceptance.

## Next strictly ordered boundary

**S10b2b2b (OPEN)** must first integrate the *real physical* schema3 root under the **single original FD9** and original journal, with pinned original full seal and native modes/inodes, saved WAN and Config preimages, existing process/IPFW/previous active root proof, and a **positively** re-attested guarded `PREPARED→ACTIVATING` transition. This schema-2 detached proposal is **not** a second manifest/writer. Incomplete root, modified source, stale epoch or mixed owner must refuse without runtime mutation. **S10c (OPEN)** still owns crash/rollback, uncertain `Config::save`, P1 CAS/ACK and recovery; S11 owns physical Start/Stop/Reload. WAN-only Save and prestart Lab remain independent of the ordinary root.

No public `os-zapret2-restyle-0.6.5_203.pkg`, owner-appliance test, automatic service activation or pfSense migration is requested.
