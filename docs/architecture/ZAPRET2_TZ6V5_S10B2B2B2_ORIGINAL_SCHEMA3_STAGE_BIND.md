# TZ6v5 S10b2b2b2 — one original FD9 writer for final schema3 root + PREPARED binding

**Input:** source-accepted [S10b2b2b1 #1325](https://github.com/Tolian82/os-zapret2-restyle/pull/1325), `main v0.6.5_204 bbbe2611`; [S10 #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319) remains OPEN. Candidate `v0.6.5_205` is **source-only**, no public package and no owner appliance change.

## Original single-writer design — no alternate staging or durable operation

The existing S10a `neutral_root_stage._stage_candidate()` is the **only** atomic `shared-work/<generation>/manifest.json` sibling-root writer. Its exact O_EXCL pending→hardlink→unlink→fsync, inode/nlink/mode/UID checks, double original seal, plan and PREPARED journal verification, crash refusal, and rejection of a second release-local root are reused without changing its ordering. For **explicit `schema3=True` only**, the existing `_original_preflight()` invokes the accepted S10b2b2b1 physical four-ref verifier and compares its genuine canonical schema-2 bytes exactly to the proposed candidate. The old S09 schema-1 preflight remains the default and intentionally cannot parse schema 2. A root from synthetic S08d-final argv SHA cannot pass.

The existing S10b1 `SharedApplyOperation.bind_prepared_manifest()` remains the **only** original FD9 durable writer. It accepts a guarded `schema3=True` option **only for `mode=auto`** and calls the same S10a staged-root reader with the new truthful final schema3 physical preflight before and after the *same* `_persist_record()` atomic fsync write. The existing `operation.json` manifest binding permits schema 1 (unchanged legacy) or schema 2 with the identical exact keys `schema,generation,root_sha256,seal_sha256,candidate_sha256`; no additional journal, schema writer, seal, lock, external root witness, Config serializer or GUI route. No setting/migration changes are applied to historical records.

Before binding, S10b2b1's source bridge **still refuses** any manifest. To permit a *post-fsync* reread only, explicit `allow_bound_schema3=True` requires one original valid **schema-2 PREPARED** journal with exactly matching freshly recomputed root, original seal and PHP logical candidate SHA, and compares all original physical files and the journal again. Bare forged schema-2 metadata, mixed owner, wrong ref bytes/modes and missing seal cannot pass. The existing read-only original S10b2a bound receipt reuses the same verified schema-2 source, and is **not** an activation ticket.

## Intentional stop boundary

This candidate **stages and binds** a schema-2 immutable root, but it **does not promote, activate, restart or stop** anything: no user-route invocation, no service shell change, no new physical PID/IPFW action, no Config or P1/Found writes. The original `SharedApplyOperation.advance("activating")` still **unconditionally refuses any bound root**; the existing unbound-root fence in `zapret_service.sh` still blocks the old launcher. After a crash following the original fsync, the single journal remains bound PREPARED and cannot be silently re-bound or activated. WAN-only Save and prestart Strategy Lab remain independent.

**Not proved:** saved WAN/Config preimages, previous active process/IPFW/root attestation, positive original FD9 `PREPARED→ACTIVATING`, true atomic promotion/old-owner rollback after interrupted changes, uncertain `Config::save`, mutable P1/Found CAS/ACK. These are next **S10b2b2b3/S10c**, with S11 physical Start/Stop/Reload still pending. Do not mark overall S10 GO.

## Actual regression and release boundary

`scripts/test-tz6v5-s10b2b2b2-original-schema3-staging-binding.py` reuses the accepted real original P2e/S08c/S08d/Voice/profile+learning promoter, its one full seal and one PREPARED operation journal. It asserts exact source-root SHA, unique sibling, original **0600** root, absence of release-local root, immutable original files, schema-2 journal, unchanged phase, and nonauthorizing repeated bound source proof. Negative tests cover FD9 absent, schema1/2 mix, wrong native final mode/bytes, altered root, crashed pending, duplicate stage, stale/forged journal, post-fsync fault and continued original source bridge default refusal. Exact-head CI and scoped FreeBSD source policy are required for source-only acceptance; CI-built pkg is not an owner-installed package.

Source CI and staging/binding acceptance **do not** constitute tested physical engine/IPFW/Config lifecycle.
