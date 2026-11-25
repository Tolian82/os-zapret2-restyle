# TZ6v5 S10b2b2b1 — original FD9 physical schema3 native references

**Entry:** accepted [S10b2b2a PR #1324](https://github.com/Tolian82/os-zapret2-restyle/pull/1324), `main v0.6.5_203 c1c19fb5`; [S10 #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319) stays OPEN. Candidate `v0.6.5_204` is source-only; no public package or owner device action.

## User observable boundary and implementation

The final schema3 root proposed by S10b2b2a names four immutable native artifacts. The old S10b2b1 source bridge verified the true original/promoted SHA values and original full seal but deliberately allowed original-promoter `0600/0644` modes. A detached root with four claimed exact modes is not physical authorization: the *actual original* owner must read and pin those precise artifacts and compare them to the single PREPARED generation.

`backend/neutral_schema3_physical_refs.py` is an **import-only** read-only adapter under inherited **original FreeBSD root FD9**, using only fixed `shared_apply_seal.WORK` and `SharedApplyOperation.DEFAULT_ROOT`. It uses S10b2b1 `_attest_original_schema3`, the original `verify_seal`, original S10a journal read, S10b2b2a canonical `compile_final_schema3`/`validate_final_schema3`, and original descriptor-relative no-follow physical readers.

It proves exactly, in this order:

1. `dvtws.args`, the **postpromotion final** native argv, root-owned mode `0644`;
2. `dvtws.original.args`, the **prepromotion original** argv, root-owned mode `0644`;
3. `auto-detect-source-map.json`, original generator map, root-owned mode `0600`;
4. `auto-detect-generation.json`, original promoter active map, root-owned mode `0644`.

Every source is a regular single-link file, with bounded reads, inode/size/mode/owner/mtime/ctime pins, original seal and SHA, exact original PHP logical candidate and PREPARED journal. Two checks of all four artifacts, unchanged sealed inventory, pinned parent/release directories and repeated S10b2b1 original source attestation refuse races and altered profile identity. The resulting schema-2 `RootCandidate` contains only exact fixed root refs and remains **untrusted until future stage/binding**.

## Explicit no-transition outcome

`PhysicalSchema3Receipt` has `authorization=NONE`, `physical_transition_allowed=False`, `promotion_allowed=False`, and requires original FD9 and runtime preimage re-attestation. This PR **does not** stage, write, bind or activate `manifest.json`; change `operation.json`, Config, IPFW, P1/Found or processes; expose a public CLI; alter `zapret_service.sh`; or permit `PREPARED → ACTIVATING`. Existing unbound-root fence and legacy schema-1 operation remain unchanged. WAN-only Save and prestart Lab do not depend on a manifest.

## Regression and next gate

`scripts/test-tz6v5-s10b2b2b1-original-physical-schema3-refs.py` runs the **genuine original P2e/S08c/S08d/Voice promoter** and one original sealed PREPARED journal, asserting exact four physical modes, byte-preserving positive read and fixed no-authorization. Negative cases include each wrong mode, changed old/final argv or maps, symlink/hardlink, stale journal, incorrect native/effective input, in-read race, missing FD9 and invalid generation/enablement. Exact-head CI validates the real source, with no owner appliance action.

**Next S10b2b2b2:** adapt the **single existing S10a root writer and S10b1 original journal binding** to the attested schema-2 candidate with no second writer, seal or journal; then original FD9 positive preactivation proof must attest saved WAN/Config/previous active process, IPFW and root and preserve crash rollback. S10c retains Config::save uncertainty/P1 CAS/ACK/restore. S11 owns physical service Start/Stop/Reload. **Full S10 remains NO-GO.**
