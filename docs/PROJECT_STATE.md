# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Published testing prerelease/package: `v0.3.3_4` / `os-zapret2-restyle-0.3.3_4.pkg`
Testing prerelease target commit: `34f69490f57f50aca85c9aa8e684a7f9bc72ca81`
Current source candidate: `os-zapret2-restyle-0.3.3_4.pkg`

Hardening revisions 25–47 and candidates `0.3.3_1`–`0.3.3_4` are source-verified on
`main`. Candidate `_4` is published only for owner-assisted live verification; it is not
a stable release and did not publish GitHub Pages or the pkg repository.

## Version 0.3.3 revision 4

- preserve the FreeBSD-safe `process_query.sh` binding inside `zapret_service.sh`;
- stop semantic evidence from overriding the wrapper with direct `/bin/ps`;
- make `strategy-lab-evidence` detect running dvtws2 and supervisor consistently;
- retain the independent `_3` correction that returns Diagnostics to idle after terminal
  work while preserving historical evidence;
- repeat live Strategy Lab scenario 1 using the published `_4` package.

## GitHub governance correction

The `v0.3.3_4` publication exposed an inefficient GitHub process: a verified package was
repeatedly routed through new publication workflows, branches, runners, and trackers.
The package was ultimately published correctly by direct owner upload to the exact
prerelease target.

The active governance patch adopts evidence-first GitHub operations:

- inventory current GitHub objects and capabilities before mutation;
- distinguish ordinary PR delivery, testing prerelease publication, and full releases;
- publish an existing verified package directly instead of creating a publication PR;
- permit one active publication run per candidate;
- read job logs before changing source or workflow;
- treat external infrastructure failure as zero source changes and at most one unchanged
  rerun after recovery;
- prohibit speculative runner switching, replacement branches, duplicate trackers, and
  unbounded retries;
- replace version-specific prerelease workflows with one generic publisher;
- align release-trigger titles with the universal versioned-title rule.

Authority:
`docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`.

## Completion status

Source and CI hardening: **COMPLETE**.

Target package ABI: **FREEBSD 15 AMD64 ONLY**.

Testing prerelease `v0.3.3_4`: **PUBLISHED**.

Live OPNsense matrix: **PENDING OWNER**.

Stable release preparation and pkg-repository promotion: **BLOCKED ON LIVE MATRIX**.

Authoritative closure records:

- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

No live scenario PASS is claimed. Testing prereleases in the `0.3.3` line are
distribution surfaces for live verification only.

## Current product authority

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`,
`STRATEGY_LAB_ACTIVATION.md`, `STRATEGY_LAB_PROFILE_OUTPUT.md`,
`STRATEGY_LAB_UNIFIED_SHORTLIST.md`, `STRATEGY_LAB_UDP_INPUT.md`,
`STRATEGY_LAB_CIRCULAR_ISOLATION.md`, `STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`,
`STRATEGY_LAB_SETTINGS_GUARD.md`, `STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md`,
`STRATEGY_LAB_STRUCTURED_RESULTS.md`, `STRATEGY_LAB_PROGRESS_LOCALIZATION.md`,
`STRATEGY_LAB_OBSOLETE_SURFACES.md`, `STRATEGY_LAB_RETENTION.md`,
`STRATEGY_LAB_CORRECTIVE_MATRIX.md`,
`docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`,
`docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`, and
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

## GitHub governance

`docs/GITHUB_PUBLICATION.md`,
`docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`,
`docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`, and
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md` are authoritative.

`VERSION=0.3.3`; `PLUGIN_REVISION=4`.
