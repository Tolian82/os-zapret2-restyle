# TZ6v5 S09a — detached immutable root schema and bounded structural inputs

**Scope:** first bounded, nonactivating increment of [S09 #1316](https://github.com/Tolian82/os-zapret2-restyle/issues/1316) under the [S00–S20 plan](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md). This is a **candidate data contract**, not an active runtime manifest or proof of sealed on-disk files.

## Observable boundary

The existing original generator produces `dvtws.args` and, for `auto` mode only, the original `auto-detect-source-map.json`. S08c attests original native source-map order/identity; S08d produces the nonauthorizing `EffectiveSnapshot` structural fingerprint from the same original generator. S09a accepts only those already detached bytes and their input witnesses. The service, saved Config, existing FD9 journal, IPFW, live engine and WAN-only Save are unchanged.

`neutral_root_manifest.py::compile_candidate` emits one canonical UTF-8 JSON buffer at most 16 KiB, with precisely five top-level keys: `schema`, `generation`, `service`, `resources`, `refs`. `validate_candidate` independently checks its canonical bytes against the original detached inputs, expected generation, original seal digest **claim** and owner UID **claim**. Both return `authorization=NONE` and `physical_transition_allowed=False`.

| Field | S09a contract |
| --- | --- |
| `schema` | Integer `1` only; duplicate/extra keys rejected |
| `generation` | Exact 32 lowercase hex characters, must equal the caller's generation |
| `service` | Strict Boolean `enabled`, `target_mode=all/list/auto`, exact S08d `structural_sha256`; no strategy/Voice/native args inline |
| `resources.mutable_refs` | Sorted unique basename entries `hostlist-*.txt`/`ipset-*.txt` for S08d's linked managed refs, with explicit `original-p1-cas-ack` owner; **no contents, SHA pins or editable JSON lists** |
| `refs` | Ordered exact `native_args=dvtws.args`; in auto also `native_source_map=auto-detect-source-map.json`; each has `generation`, `uid`, `mode=0600`, exact `size`, `sha256`, and supplied `seal_sha256` |
| Maximums | Native args 256 KiB, original source map 1 MiB, root 16 KiB, at most 32 linked mutable resource identifiers |

Only fixed flat relative file names are emitted or accepted; no arbitrary paths, recursive graph, includes, fallback generation or private content. `auto` requires same-generation original source-map identity and final-argv SHA; `all/list` must omit it, matching S08c's original output. The S08d effective witness must not claim external references or a physical authorization.

## Verified by S09a unit tests

`scripts/test-tz6v5-s09a-root-manifest.py` checks normal `list` and `auto` proposals, stable/canonical hashes, immutable no-action receipt, structural witness mismatch and 17 deliberately altered reference/root shapes. Malformed, duplicate-key, oversized or noncanonical JSON; extra strategies; owner/mode/SHA/size/seal/generation tamper; wrong original-argv/map proof; mutable-owner substitution and duplicate/path traversal are refused before filesystem access. These are **pure unit cases**, not native ownership/race, installed package or original-generation attestation.

## Required next gate — S09b (S09 remains open)

Use the **actual** original detached `orchestrator_build_release` outputs and original sealed inventory. Under existing owner rules, attest physical artifacts with confined relative-file access, no symlink/hardlink/foreign owner, exact current generation, mode, size, SHA and previous seal binding, rechecking inode/metadata across read. Reject missing, stale, race, cycle, inconsistent original source-map or changed-current-release candidates. Reuse S08c/S08d native parity; do not create a second native argv builder, Config writer or FD9, and do not call S09a descriptors an active seal. S10 alone will stage/promote in the existing original FD9 transaction and provide rollback. The active ordinary Start/Apply prerequisite must not become a prerequisite for WAN-only Save or pre-Start Lab with installed engine.

P1 managed live content remains governed by the original destination flock/CAS/ACK; it is deliberately not pinned by immutable root SHA. Structural ref/generation changes require a later guarded transaction/restart, not a free-form reload or silent root replacement. No testing package is published and no owner appliance transition is authorized by S09a.
