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

The `_5` attempt remains a failed live attempt. It is historical evidence and is not
converted into PASS by later source corrections.

## Version 0.3.3 revision 6 — source/CI corrective line complete

Revision `_6` reconciled the repository and repaired the confirmed stage-50/stage-90
source defects without changing `VERSION=0.3.3`.

### Baseline reconciliation — merged

PR `#111`, `v0.3.3_6: Reconcile repository state after live failure`, was squash-merged
to `main` as `471ad322b805c14423c4cee553e6cb111a569b29` after full CI and FreeBSD 15
package verification.

Its exact PR head produced Actions artifact `8979980843`, package
`os-zapret2-restyle-0.3.3_6.pkg`, with manifest identity
`0.3.3_6 / FreeBSD:15:amd64 / freebsd:15:x86:64 / FreeBSD_version 1500068`.

### Stage 50 — candidate-runtime source correction merged

The first `_6` runtime patch corrected the candidate ownership mismatch:

- the job-owned PID file is the primary ownership and absence proof after executable
  and reserved `--port=9989` identity validation;
- TERM/KILL target that proven owner before any global sweep;
- global process and socket discovery remain secondary evidence;
- teardown still requires disappearance of the owned PID, matching candidate processes,
  and the divert listener before success;
- focused regression covers a valid owned PID omitted by both secondary discovery paths.

PR `#112`, `v0.3.3_6: Fix Strategy Lab candidate runtime`, final head
`1d77cc2a6a6fd9b4a28856e375c107b00f869361`, passed full CI and FreeBSD 15 package
verification. Its exact-head artifact was `8980523385`, package
`os-zapret2-restyle-0.3.3_6.pkg`, manifest
`0.3.3_6 / FreeBSD:15:amd64 / freebsd:15:x86:64 / 1500068`.

The patch was squash-merged to `main` as
`808d77bcdb4f9e5fb63f94985d01144e7f2216a4`.

### Stage 90 — restoration-path source correction merged

The second `_6` runtime patch corrected a bounded-start mismatch. Strategy Lab previously
gave normal restoration only 15 seconds although the native service path can legitimately
consume up to 10 seconds waiting for dvtws2 PID, then a 5-second stability window, then
up to 5 seconds for the supervisor, in addition to runtime generation/activation and
firewall work.

The correction:

- raises the default restoration-start bound to 45 seconds;
- verifies actual service state after a nonzero outer start result;
- accepts healthy RUNNING if native start completed at the boundary;
- otherwise normalizes `INCOMPLETE` to verified STOPPED and permits exactly one bounded
  recovery start;
- after a second failure, best-effort normalizes to STOPPED instead of deliberately
  retaining a known incomplete runtime;
- retains exact semantic verification and truthful `RESTORE_FAILED` when healthy RUNNING
  and the initial runtime/config/firewall evidence cannot be restored.

Focused regression covers successful one-retry recovery, late healthy completion, and
two-start failure with safe STOPPED normalization. Existing e2e restoration-failure
coverage still requires `error/RESTORE_FAILED` when final semantic evidence is corrupted.

PR `#113`, `v0.3.3_6: Fix Strategy Lab restoration path`, final head
`e7380ddf01077a6e7b6acb9302e8c9aa07bfd6c0`, passed full CI run `31144038425` and
FreeBSD 15 package verification.

Its exact-head artifact is:

- artifact ID `8980876980`;
- name `os-zapret2-restyle-0.3.3_6`;
- artifact ZIP digest `sha256:bac8a77c6e01024c2e0b9e899689c1e22821abd39ab7349ec313156c714f151f`;
- manifest `0.3.3_6 / FreeBSD:15:amd64 / freebsd:15:x86:64 / FreeBSD_version 1500068`.

The patch was squash-merged to `main` as
`4fca1fccbdd92237c76d84e11f864090fc4d1a9d`. Post-merge `main` CI run
`31144323095` completed successfully.

## Current verification boundary

The `_6` source/CI corrective sequence is complete in `main`.

No `_6` testing prerelease was published as part of this sequence. No `_6` owner-assisted
OPNsense test has been performed yet. Repository CI therefore does **not** mark scenario 1
PASS.

The live gate is now **owner retest required for scenario 1 on `_6`**. The `_5` failed
attempt remains evidence; scenario 1 becomes PASS only after new owner evidence proves a
truthful terminal result, successful stage-90 restoration of the original RUNNING service,
and absence of Strategy Lab residue. Dependent scenarios remain blocked by scenario 1.

The complete recovery ledger is:
`docs/devlog/2026-08-07-v0.3.3_6-repository-reconciliation.md`.

## Current GitHub state

Stale temporary publication branches removed during recovery:

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

Live OPNsense matrix: **PENDING OWNER — SCENARIO 1 RETEST ON `_6`**.

Stable release preparation and pkg-repository promotion: **BLOCKED ON LIVE MATRIX**.

Current product authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

`VERSION=0.3.3`; `PLUGIN_REVISION=6`.
