# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified package baseline: `os-zapret2-restyle-0.3.3_4.pkg`
Current source candidate on `main`: `os-zapret2-restyle-0.3.3_5.pkg`

Hardening revisions 25–47 and prerelease revisions `0.3.3_1`–`0.3.3_4` are recorded on `main`.

## Version 0.3.3 revision 5

- one shared PID-file reader accepts valid numeric PID files ending with a newline or directly at EOF;
- Strategy Lab semantic evidence, launcher, and supervisor use the same reader;
- empty, malformed, PID 0, and PID 1 files are rejected;
- regression coverage includes real no-newline PID fixtures;
- the failed `0.3.3_4` live attempt remains recorded without claiming scenario 1 PASS.

The source correction was squash-merged to `main` as commit
`5629615100f9919c57a13fc3c067f90fb8521af8`.

The FreeBSD 15 package and testing prerelease for `_5` are not yet verified. No CI or
package PASS is claimed for `_5` until an exact workflow run and artifact are inspected.

## Completion status

Source correction for `0.3.3_5`: **MERGED, PACKAGE VERIFICATION PENDING**.

Target package ABI: **FREEBSD 15 AMD64 ONLY**.

Live OPNsense matrix: **PENDING OWNER AFTER `_5` PACKAGE PUBLICATION**.

Stable release preparation: **BLOCKED ON LIVE MATRIX**.

Authoritative closure records:

- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md`;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

No live scenario PASS is claimed. GitHub prereleases in the `0.3.3` line are testing
distribution surfaces only and are not stable product releases.

## GitHub governance

Evidence-first GitHub operations are authoritative through:

- `AGENTS.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

The repository uses one generic testing-prerelease workflow. Version-specific publisher
files are forbidden. Existing verified package bytes are published directly when
possible; automated publication uses one temporary `publish/v<VERSION>_<REVISION>`
branch and one active run. External GitHub failures cause no speculative source, runner,
workflow, or branch changes.

`VERSION=0.3.3`; `PLUGIN_REVISION=5`.
