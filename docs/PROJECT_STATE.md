# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_5` / `os-zapret2-restyle-0.3.3_5.pkg`
Current corrective candidate: `os-zapret2-restyle-0.3.3_6.pkg`
Target ABI: **FreeBSD:15:amd64 only**

## Version 0.3.3 revision 5 — verified package, failed live scenario 1

`v0.3.3_5` was built and published by GitHub Actions run `31130265614`.
The FreeBSD 15 build, package manifest verification, prerelease publication, release
contract verification, and temporary publication-branch cleanup all completed
successfully.

Published release target: `68ad848cf62280de23907b0ccb63522be9b7bb15`.
Published asset: `os-zapret2-restyle-0.3.3_5.pkg`.
Asset digest: `sha256:68c96469132dd9b6fd715a782848f24625fbd695f991831cd773f54dec9431a3`.

The `_5` PID-file correction is confirmed live: before Strategy Lab execution,
`strategy-lab-evidence` correctly reported `state=RUNNING`, `child_running=true`, and
`supervisor_running=true`.

The subsequent standard Strategy Lab run against `rutracker.org` exposed the next defect:

- stages 00, 10, 20, 30, and 40 passed;
- stage 50 failed with `Temporary candidate runtime failed internally.`;
- stage 90 failed with `RESTORE_FAILED`;
- after the run, `configctl zapret status` reported an incomplete runtime state;
- semantic evidence reported `state=INCOMPLETE`, `child_running=false`, and
  `supervisor_running=false`;
- saved/effective configuration hashes remained unchanged.

Durable evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md`.

Scenario 1 therefore remains failed pending owner re-verification. Dependent live
Strategy Lab scenarios remain blocked until the `_6` corrective source line is complete
in `main` and scenario 1 is repeated.

## Version 0.3.3 revision 6 — current corrective line

Revision `_6` is the corrective candidate used to reconcile the repository and repair
the confirmed stage-50/stage-90 lifecycle failures without changing `VERSION=0.3.3`.

Baseline `_6` reconciliation merged to `main` as
`471ad322b805c14423c4cee553e6cb111a569b29`. Its exact PR head produced verified
FreeBSD 15 Actions artifact `8979980843` for `os-zapret2-restyle-0.3.3_6.pkg`.

### Stage 50 — source correction merged

The first `_6` runtime patch corrected the candidate ownership mismatch:

- the job-owned PID file is the primary ownership and absence proof after executable
  and reserved `--port=9989` identity validation;
- TERM/KILL target that proven owner before any global sweep;
- global process and socket discovery remain secondary evidence;
- teardown still requires disappearance of the owned PID, matching candidate processes,
  and the divert listener before success;
- focused regression covers a valid owned PID omitted by both secondary discovery paths.

The exact final PR head passed full CI and FreeBSD 15 package verification, producing
Actions artifact `8980523385`, package `os-zapret2-restyle-0.3.3_6.pkg`, ABI
`FreeBSD:15:amd64`, architecture `freebsd:15:x86:64`.

The patch was squash-merged to `main` as
`808d77bcdb4f9e5fb63f94985d01144e7f2216a4` with title
`v0.3.3_6: Fix Strategy Lab candidate runtime`.

This is a source/CI correction, not a live scenario PASS.

### Stage 90 — restoration-path source correction

The second `_6` runtime patch addresses a separate bounded-start defect. Before the
correction, Strategy Lab gave normal restoration only 15 seconds even though the native
service start can legitimately consume up to 10 seconds waiting for dvtws2 PID, then a
5-second stability window, then up to 5 seconds for the supervisor, in addition to
runtime generation/activation and firewall work. The outer restoration timeout could
therefore terminate a valid normal start before its own bounded transaction completed.

The correction:

- raises the default restoration-start bound to 45 seconds;
- verifies actual service state after a nonzero outer start result;
- accepts healthy RUNNING if native start completed at the timeout boundary;
- otherwise normalizes `INCOMPLETE` to verified STOPPED and permits exactly one bounded
  recovery start;
- after a second failure, best-effort normalizes to STOPPED instead of deliberately
  leaving a known incomplete runtime;
- retains exact semantic verification and `RESTORE_FAILED` when healthy RUNNING and the
  initial runtime/config/firewall evidence cannot be restored.

A focused regression covers successful one-retry recovery, late healthy completion, and
two-start failure with safe STOPPED normalization. The retry count is finite and no
unbounded automatic service restart loop is introduced.

Per owner instruction, this patch is merged to `main` only after full repository CI and
FreeBSD 15 package verification; no intermediate manual OPNsense test is required.
Repository CI still does not create a live PASS.

The detailed complete recovery ledger is:
`docs/devlog/2026-08-07-v0.3.3_6-repository-reconciliation.md`.

No `_6` testing prerelease publication or live PASS is claimed by these source patches.

## Current GitHub state

The repository owner removed the stale temporary publication branches:

- `publish/v0.3.3_1`;
- `publish/v0.3.3_2`;
- `publish/v0.3.3_4`;
- `publish/v0.3.3_4-final`;
- `publish/v0.3.3_5`.

Evidence-first GitHub operations are authoritative through:

- `AGENTS.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

The connected GitHub plugin is the mandatory first repository interface. If it is
unavailable, non-responsive, or cannot provide authoritative repository state required
for safe work, GitHub work stops and the owner is informed. A fallback transport is
allowed only for one exact function or permission confirmed missing from an otherwise
responding plugin.

The repository uses one generic testing-prerelease workflow. Version-specific publisher
files are forbidden. A temporary `publish/v<VERSION>_<REVISION>` branch must match the
candidate identity derived from `VERSION` and `PLUGIN_REVISION`, permits one active
publication run, publishes neither GitHub Pages nor the pkg repository, verifies the
release contract, and removes itself after success.

## Release gate

Live OPNsense matrix: **BLOCKED ON SCENARIO 1 OWNER RE-VERIFICATION AFTER `_6` SOURCE CORRECTIONS**.

Stable release preparation and pkg-repository promotion: **BLOCKED ON LIVE MATRIX**.

Current product authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

`VERSION=0.3.3`; `PLUGIN_REVISION=6`.
