# TZ6v5 S10c2b3i — exact original installed engine version input (read-only)

**Status: candidate `v0.6.5_224`, NOT S10 GO.**
Baseline accepted `main v0.6.5_223 c7779b7ef0b4c870edd15637d868856cdf9b4f40`,
[PR #1344](https://github.com/Tolian82/os-zapret2-restyle/pull/1344),
[tracker #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319).
This is a bounded handoff towards S10 immutable-root activation, not a new
producer, journal, Config writer, physical executor or engine installation.

## Problem and original source boundary

S08d needs an **independently checked upstream engine version**, not the
plugin version or a test-supplied string, before typing the sealed effective
snapshot. The original `runtime.release` writer now publishes exact three-line
`vTAG/commit/engine_sha256` bytes after the **genuine native make** both
on first install and on upgrade. The existing
`extra_resources_upstream_guard.native_installed_engine_identity()` already
requires the **original FD9**, fixed root-owned native paths, absence of
pending setup transactions and repeated stable nofollow Git-tag/HEAD/ELF
readback. A legacy one-line release is still a display-only observation.

This step adds **only** an importable `native_bound_engine_for_s10_readback()`
method on that same guard. It calls the existing original FD9 reader, insists
on an exact-bound marker (never silently accepts legacy), exact fixed
receipt fields, no forged authorization, correct version/OID/SHA grammar, and
returns `engine_version/source_commit/engine_sha256` and
`S10_ORIGINAL_BOUND_ENGINE_VERSION_READ_ONLY`. Both
`authorization=NONE`, `physical_transition_allowed=false` and
`build_provenance_verified=false` remain explicit. The readback **must not**
be interpreted as independent proof of historic make, or permission to Start.
The actual make provenance comes exclusively from the single original setup
parent, not from observing Git and an ELF later.

## Testing and next owner boundary

The existing original setup guard fixture tests legacy/unfinished/changed
ELF/forged receipt failures and byte-for-byte absence of writes; the genuine
FreeBSD 15 G03 remains the original post-make receipt acceptance. A single
mode guard in G03 fast preflight requires the original setup and rollback
scripts to remain executable, preventing a repeat of the `100755→100644`
packaging regression. No new test VM or engine reread experimentation.

**Not yet implemented:** original `shared_apply_prepare_service` passing
this input to S08d and staging its exact sealed root; genuine old active
owner, Config/Found P1, IPFW/PID/WAN projection and crash-safe physical
PREPARED→ACTIVATING, including rollback. The existing
`manifest-unbound` and bound PREPARED activation refusals **stay closed**.
Complete these inside the single original FD9 operation, not by invoking
this detached readback as an activator.

## CI correction after exact-head native observation (25.11.2026)

The first candidate G03 and the previously merged `_223` postmerge no-git
Guest D both reproduced an independent, non-mutating
`strategies-preflight-lifecycle-guard` refusal on the second immediate
stale-tab HTTPS Apply after the first has already returned saved. The original
`strategy_lab_guard.sh` protects FD9 and rejects a busy owner. The disposable
**test harness only** now waits up to 30 × 0.5s for the existing
`configctl zapret strategy_lab_guard` to say exactly owner=none, state=idle,
reason=available, busy=false, checking the actual original shared journal
remains committed and the service remains STOPPED with no PID. Any unknown
owner, Strategy Lab job, missing response, unstable runtime or held lock still
refuses. No retry of a rejected Apply, no lock release, no new production
behavior, no physical runtime action or extra native guest.
