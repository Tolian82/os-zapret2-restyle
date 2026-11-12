# P5b1 — bounded native validator handoff for a prebuilt private preview

**Feature:** #936. **Revision:** source candidate v0.6.4_37. This is an internal verification adapter, **not** the complete P5 Validate and Preview. No .pkg publication or owner-appliance change.

## Why a separate step is necessary

The existing `orchestrator_build_release()` is already the **single canonical** native builder. Its ordinary Apply path uses persistent status and shared-work state; invoking it from GUI just to inspect a candidate would violate the approved read-only P5 contract. We must create a short-lived workspace, use the existing native detached template and orchestrator to generate a preview, and ensure exact cleanup and semantic before/after fingerprints before exposing any user-facing action. That orchestration belongs to the next P5b2 step, not to an invented alternative builder.

This stage introduces **import-only** `backend/strategy_preview_native.py`, with no CLI, configd action, HTTP endpoint, public GUI button or Config writer. It consumes only an *already prepared* disposable release within a validated root-only `/tmp/zapret-p5b-<16 hex>` directory. It does not create or populate that workspace. The directory must be 0700, owned by the current process, without a symlink or hardlinked candidate files. Expected artifacts are the existing canonical `release/dvtws.args`, `traffic-user.conf`, `tcp-ports.txt`, `udp-ports.txt` and `release/managed`. It bounds input file sizes and refuses wrong origin, type, owner or permissions.

The **actual original shell implementation** is called twice, rather than copied:

1. `validator_validate_build_mapped` checks the assembled candidate's port scope, list references and duplicate resolved resources against the static upstream and staged release roots.
2. If, and only if, the installed native engine is executable, `validator_validate_engine_mapped` calls the existing `dvtws2 --dry-run` with the existing read-only managed-file remapping and its own bounded engine timeout. The adapter enforces an outer timeout, killing only its own isolated subprocess group, and discards stdout/stderr to avoid leaking user strategy/hostlist content.

The production branch is pinned to installed static root `/usr/local/etc/zapret2`, the installed backend module path, root FreeBSD and the **original inherited FD9 lifecycle ownership**. No extra runtime/process owner or second grammar is allowed. Parameter overrides and a dummy executable are available in **unit tests only** through an import-only API.

The returned machine status differentiates `native_mapped_validation_failed`, `native_mapped_valid`, plus `engine_native_dry_run=not_run|unavailable|failed|passed`. Even `passed` means the native installed parameter parser accepted the disposable mapped candidate, **not** live ISP bypass, valid Voice calls or a complete P5 operation. The report explicitly says lifecycle fingerprints are not yet attested, Config was not measured by this adapter and Apply is never safe or public.

## Verification and remaining gates

`scripts/test-strategy-preview-native.py` exercises the real `validator.sh` with tiny local generated-file fixtures and a **fake test-only binary** that checks `--dry-run`. This qualifies the handoff and return-status policy, not the actual upstream engine. Negatives cover failed engine, missing engine, mismatched ports, reference escape, private directory permissions, symlink/hardlink, arbitrary location and lack of lifecycle ownership; the Linux native-owner path refuses execution. There are no writes to Config or owned IPFW; the engine helper's temporary copy is cleaned by the existing validator. CI scope is narrow.

**Next mandatory P5b2:** secure temporary candidate creation under original FD9, read-only OPNsense Config generation check, detached **existing native template** plus **existing orchestrator** invocation with all stages directed exclusively into private temporary workspace, actual installed `dvtws2 --dry-run` and before/after Config/history, FD9, managed and foreign IPFW, processes, Voice, and resource semantic fingerprints. Explicit absent runtime, RUNNING, STOPPED and failures/cancellation. Only then P5c RU/EN unsaved form button and owner A11/A16 witness.

**Scope:** v0.6.4_37 source-only; full P5/A11/A16, physical owner A17 and release P6 remain OPEN. Stable published `v0.6.4_1.pkg` remains unchanged.
