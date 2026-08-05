from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text()


def write(path: str, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def append_once(path: str, marker: str, section: str) -> None:
    text = read(path)
    if marker not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + section.rstrip() + "\n"
        write(path, text)


stale = Path("docs/PROJECT_STATE.md.orig")
if not stale.exists():
    raise SystemExit("expected tracked backup is missing")
stale.unlink()

gitignore = read(".gitignore")
ignore_section = """

# tracked backup, merge and transport artifacts
*.orig
*.rej
*.patch
*.diff
*.b64
*.base64
*.bak
*.part-*
*~
"""
if "# tracked backup, merge and transport artifacts" not in gitignore:
    write(".gitignore", gitignore.rstrip() + ignore_section)

hygiene_test = r'''#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GITIGNORE="${ROOT_DIR}/.gitignore"
CI="${ROOT_DIR}/.github/workflows/ci.yml"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

tracked=$(git -C "${ROOT_DIR}" ls-files)
bad=$(printf '%s\n' "${tracked}" | grep -E '(^|/)([^/]+\.(orig|rej|patch|diff|b64|base64|bak)|[^/]+\.part-[0-9]+|[^/]+~)$' || true)
[ -z "${bad}" ] || {
    printf '%s\n' 'Forbidden tracked repository artifacts:' >&2
    printf '%s\n' "${bad}" >&2
    exit 1
}

[ ! -e "${ROOT_DIR}/docs/PROJECT_STATE.md.orig" ] || fail 'stale PROJECT_STATE backup is tracked'

for pattern in '*.orig' '*.rej' '*.patch' '*.diff' '*.b64' '*.base64' '*.bak' '*.part-*' '*~'
do
    grep -Fqx "${pattern}" "${GITIGNORE}" || fail "missing ignore rule: ${pattern}"
done

grep -Fq 'Version line: **0.3.x**' "${ROOT_DIR}/docs/REQUIREMENTS.md" || fail 'requirements version line is stale'
grep -Fq 'Corrective Patches 1–11 are complete in source' "${ROOT_DIR}/docs/PROJECT_STATE.md" || fail 'project state does not close the corrective source series'
grep -Fq 'Historical delivery record' "${ROOT_DIR}/docs/audit/DIAG-001-strategy-lab.md" || fail 'historical DIAG record has no authority banner'
grep -Fq 'scripts/test-repository-hygiene.sh' "${CI}" || fail 'repository hygiene test is not wired into CI'

echo 'Repository artifact and documentation authority hygiene tests passed.'
'''
write("scripts/test-repository-hygiene.sh", hygiene_test)

ci = read(".github/workflows/ci.yml")
old_step = """      - name: Test GitHub branch hygiene contract
        run: sh scripts/test-github-branch-hygiene.sh
"""
new_step = """      - name: Test GitHub branch hygiene contract
        run: sh scripts/test-github-branch-hygiene.sh

      - name: Test repository artifact hygiene
        run: sh scripts/test-repository-hygiene.sh
"""
if old_step not in ci:
    raise SystemExit("CI branch hygiene step not found")
ci = ci.replace(old_step, new_step, 1)
old_required = """            scripts/test-github-branch-hygiene.sh \\
            .github/workflows/cleanup-merged-branch.yml \\
"""
new_required = """            scripts/test-github-branch-hygiene.sh \\
            scripts/test-repository-hygiene.sh \\
            .github/workflows/cleanup-merged-branch.yml \\
"""
if old_required not in ci:
    raise SystemExit("CI required-file insertion point not found")
ci = ci.replace(old_required, new_required, 1)
old_exec = """          test -x scripts/test-github-branch-hygiene.sh || {
            echo "scripts/test-github-branch-hygiene.sh is not executable"
            exit 1
          }
"""
new_exec = old_exec + """
          test -x scripts/test-repository-hygiene.sh || {
            echo "scripts/test-repository-hygiene.sh is not executable"
            exit 1
          }
"""
if old_exec not in ci:
    raise SystemExit("CI executable insertion point not found")
ci = ci.replace(old_exec, new_exec, 1)
write(".github/workflows/ci.yml", ci)

requirements = read("docs/REQUIREMENTS.md")
requirements = requirements.replace("Version line: **0.2.x**", "Version line: **0.3.x**", 1)
requirements = requirements.replace(
    "IPv6 target lists are outside version 0.2.0 requirements.",
    "IPv6 target lists remain outside the approved target-list contract. Strategy Lab accepts a normalized domain only; IPv6 is detected only as an optional network capability and is not accepted as a Strategy Lab target.",
    1,
)
trace_marker = "\n\n==================================================\nIMPLEMENTATION TRACEABILITY SNAPSHOT — 2026-08-02\n=================================================="
if trace_marker not in requirements:
    raise SystemExit("requirements traceability marker not found")
requirements = requirements.split(trace_marker, 1)[0].rstrip() + """


==================================================
CURRENT IMPLEMENTATION AND VERIFICATION STATE
==================================================

Active product baseline:

- project version line: `0.3.x`;
- published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`;
- current verified source candidate: `os-zapret2-restyle-0.3.2_24.pkg`;
- asynchronous Strategy Lab is the only strategy-finding path;
- the initial 13-patch delivery and corrective source patches 1–11 are complete;
- complete mock-driven API/configd-to-worker regression coverage is mandatory in CI;
- final owner-assisted OPNsense verification remains required before release authorization.

Current Strategy Lab behavior is controlled by:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

Historical audit, devlog, release, and patch records remain evidence only. They do not
override the current specialist authority and current project state.

Blob requirement interpretation:

- shorthand `--blob=<name>` addresses `files/fake/<name>.bin` directly;
- actual preset blob names must correspond to installed files;
- implicit aliases are not a product requirement.
"""
write("docs/REQUIREMENTS.md", requirements)

guide = read("docs/DEVELOPMENT_GUIDE.md")
start = guide.find("==================================================\nCURRENT IMPLEMENTATION PRIORITY\n==================================================")
end = guide.find("\n\n## Package lifecycle verification", start)
if start < 0 or end < 0:
    raise SystemExit("development priority section not found")
priority = """==================================================
CURRENT IMPLEMENTATION PRIORITY
==================================================

The Strategy Lab initial delivery and corrective source series are complete. The active
next gate is one consolidated owner-assisted OPNsense verification matrix recorded in
`docs/ROADMAP.md` and the corrective audit. Do not begin another Strategy Lab feature,
release preparation, tag, GitHub Release, release asset, or pkg-repository publication
before that live evidence is recorded and the owner explicitly authorizes a release.

The additional BLOB repository remains a later GUI work item. Its repository, manifest,
versioning, integrity, and update contract remain undefined until supplied and approved
by the project owner.

Keep process discussion proportional to the project. Existing guidance is sufficient;
prefer implementation and verification over adding methodology unless practice exposes
a concrete repeatable gap.
"""
guide = guide[:start] + priority + guide[end:]
guide = guide.replace(
    "setup.sh install obtains pinned bol-van/zapret2 v1.0.3;",
    "setup.sh install obtains and verifies the selected published stable bol-van/zapret2 release;",
    1,
)
write("docs/DEVELOPMENT_GUIDE.md", guide)

project_state = """# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source candidate: `os-zapret2-restyle-0.3.2_24.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–11 are complete in source.

Completed corrective contracts:

- atomic localized cancellation and bounded termination of active stage 60, 70, and 80 process trees;
- one explicit monotonic stage sequence with truthful terminal state, outcome, and localized messages;
- one 150-second standard deadline and one optional 120-second extended allowance with a shared stage-80 budget;
- semantic service, process, runtime, effective-strategy, firewall, and temporary-state restoration verification;
- backend-authoritative circular eligibility after completed `SUCCESS`, shortlist PASS, and restoration PASS;
- one normalized domain-only target contract across API, shell, probes, and GUI;
- complete mock-driven API/configd-to-worker integration coverage for stages 00–99, polling recovery, result persistence, circular validation, lifecycle outcomes, and cleanup;
- repository artifact hygiene enforced by CI;
- stale tracked backups and superseded remote task/release branches removed;
- historical delivery records explicitly separated from current behavioral authority.

Source status:

- no open Strategy Lab corrective source finding remains;
- no tag, release, release asset, or pkg-repository publication has been made for the corrective source candidate;
- normal steady-state branch authority is `main`; `recovery/base` is preserved separately by decision;
- task branches remain temporary and are removed after squash merge.

Current authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/decisions/DEC-2026-08-05-repository-artifact-hygiene.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=24`. Patch 11 changes repository governance and documentation only, so package metadata remains unchanged.

Next action: run the consolidated owner-assisted live OPNsense verification matrix. Release preparation remains blocked until that evidence is recorded and explicit release authorization is given.
"""
write("docs/PROJECT_STATE.md", project_state)

roadmap = """# os-zapret2-restyle — Roadmap

Current verified source candidate: `0.3.2_24`.

## Initial Strategy Lab delivery

- [x] Patches 1–13 — architecture, asynchronous lifecycle, network precheck, candidate runtime, family search, expansion, stability, extended protocols, circular validation, and Diagnostics activation.

## Strategy Lab corrective series

- [x] Corrective Patch 1 — authoritative corrective contract and audit baseline.
- [x] Corrective Patch 2 — atomic cancel persistence.
- [x] Corrective Patch 3 — active runner cancellation.
- [x] Corrective Patch 4 — explicit monotonic stage machine.
- [x] Corrective Patch 5 — truthful terminal states, outcomes, and messages.
- [x] Corrective Patch 6 — overall and stage-80 time budgets.
- [x] Corrective Patch 7 — semantic restoration evidence.
- [x] Corrective Patch 8 — backend and GUI circular eligibility.
- [x] Corrective Patch 9 — normalized domain-only target contract.
- [x] Corrective Patch 10 — complete API-to-worker integration harness and reload recovery.
- [x] Corrective Patch 11 — repository artifact hygiene, documentation authority cleanup, and obsolete branch removal.

## Final owner-assisted verification gate

- [ ] Install the verified package candidate on the owner OPNsense appliance.
- [ ] Verify a Standard job against a blocked domain.
- [ ] Verify an Extended job against the same blocked domain.
- [ ] Verify an already-accessible domain result.
- [ ] Verify cancellation during active stages 60, 70, and 80.
- [ ] Verify bounded timeout handling and retained partial evidence.
- [ ] Verify initial RUNNING restores to healthy RUNNING.
- [ ] Verify initial STOPPED remains STOPPED.
- [ ] Verify temporary circular start/stop and TTL cleanup.
- [ ] Verify no Strategy Lab dvtws2 process, divert listener, or IPFW rules 19100–19131 remain.
- [ ] Verify the saved Traffic Strategy is unchanged.
- [ ] Verify the final result is recovered after Diagnostics page reload.
- [ ] Record commands and observed evidence in the audit and devlog.

## Release boundary

No new tag, GitHub Release, release asset, or pkg-repository publication is authorized by the corrective development request. Release preparation begins only after the live matrix passes and the project owner explicitly authorizes a release.
"""
write("docs/ROADMAP.md", roadmap)

activation_audit = """# DIAG-001 — Strategy Lab replaces synchronous Blockcheck

Classification: source remediated / automated integration verified / requires live OPNsense verification

This specialist record supersedes the historical synchronous Blockcheck chain. Current behavior is governed by the corrective Strategy Lab contract and its audit.

## Active source chain

```text
Diagnostics GUI
  -> StrategyLabController
  -> short configd action
  -> detached lifecycle-owned worker
  -> stages 00–99
  -> persistent status/result polling
  -> optional backend-authorized circular validation
```

The synchronous `blockcheck.sh` wrapper, configd action, MVC action, and ten-minute browser request are absent from the active and fallback architecture.

## Verified source remediation

Candidate `0.3.2_24` has passed focused tests, the complete mock-driven API/configd-to-worker matrix, project validation, and FreeBSD package build. The source contract includes:

- normalized domain-only targets;
- atomic cancellation and active process-tree termination;
- bounded standard and extended deadlines;
- explicit terminal states and outcomes;
- mandatory semantic restoration and temporary-state cleanup;
- page-reload recovery of the newest persisted job;
- circular eligibility only after completed `SUCCESS`, stages 85 and 90 PASS, verified restoration, and a valid three-to-five-item shortlist;
- saved Traffic Strategy immutability.

## Remaining live verification

DIAG-001 remains open only for the consolidated owner-assisted OPNsense matrix in `docs/ROADMAP.md`. No release is authorized before that evidence is recorded.
"""
write("docs/audit/DIAG-001-strategy-lab-activation.md", activation_audit)

activation_arch = """# Strategy Lab Diagnostics activation

The Diagnostics page uses the asynchronous Strategy Lab API as the only strategy-finding path.

## User flow

1. Enter a blocked domain and select Standard or Extended mode.
2. Start the job; the API returns `job_id` immediately.
3. The page polls status and renders stages 00–99, State, Outcome, and the retained structured result.
4. Stop requests persist cancellation, terminate the active bounded runner, and continue mandatory cleanup and restoration.
5. Reloading the page recovers the active job or newest persisted terminal job.
6. A completed `SUCCESS` job displays the stable shortlist and recommendation number one.
7. Temporary circular validation is available only when backend eligibility confirms a domain target, stages 85 and 90 PASS, verified restoration, and a three-to-five-item shortlist.
8. The user manually reviews a candidate before changing the saved Traffic Strategy.

## Removed path

The synchronous `blockcheck.sh` wrapper, `zapret blockcheck` configd action, `blockcheckAction`, and ten-minute browser request are not part of the active or fallback architecture.

## Safety

Strategy Lab and circular validation share the Zapret2 lifecycle lock, use target-scoped temporary firewall rules, preserve partial structured evidence, and verify semantic restoration. Circular validation never writes the saved Traffic Strategy.
"""
write("docs/architecture/STRATEGY_LAB_ACTIVATION.md", activation_arch)

user_guide = """# Using Strategy Lab

Open **Services → Zapret2 → Diagnostics**.

Enter a domain that your ISP blocks. Use **Standard** for the primary TLS 1.3 search, with an enforced 150-second search budget. Use **Extended** when TLS 1.2, plain HTTP, capability-gated QUIC, or a configured request-response UDP check is also needed; Extended may use one additional shared 120-second allowance.

The page shows State, Outcome, and stages 00–99 and retains completed evidence. **Stop** persists cancellation, terminates the active bounded runner, and still completes cleanup and Zapret2 restoration before another lifecycle operation can run. Reloading Diagnostics recovers the active or newest completed job.

The stable-candidate table shows up to five candidates. Candidate number one is the default recommendation, but Strategy Lab never writes it to Settings automatically.

**Temporary circular validation** is offered only after a completed successful domain job has a valid three-to-five-item shortlist and verified restoration. It starts one temporary target-scoped profile for browser or application testing. Stop it when testing is complete. The saved Traffic Strategy remains unchanged.
"""
write("docs/USER_GUIDE_STRATEGY_LAB.md", user_guide)

diag_history = read("docs/audit/DIAG-001-strategy-lab.md")
banner_marker = "> **Status — 2026-08-05:** Historical delivery record."
if banner_marker not in diag_history:
    title = "# DIAG-001 — Synchronous Blockcheck replacement by Strategy Lab\n"
    banner = """# DIAG-001 — Synchronous Blockcheck replacement by Strategy Lab

> **Status — 2026-08-05:** Historical delivery record. The initial 13-patch delivery and corrective patches 1–11 are source-complete. Statements below about an active legacy path, raw-IP targets, intermediate package candidates, or pending early patches describe their time of writing and are not current authority. Current behavior is governed by `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`, `docs/audit/DIAG-001-strategy-lab-activation.md`, and `docs/PROJECT_STATE.md`.
"""
    if not diag_history.startswith(title):
        raise SystemExit("historical DIAG title not found")
    write("docs/audit/DIAG-001-strategy-lab.md", banner + diag_history[len(title):])

index = read("docs/INDEX.md")
index_old = """`docs/architecture/STRATEGY_LAB_ACTIVATION.md`
How does the asynchronous Diagnostics path replace synchronous Blockcheck?
"""
index_new = index_old + """
`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`
What is the current authoritative Strategy Lab state machine, timing, cancellation, restoration, target, result, and circular-validation contract?
"""
if index_old not in index:
    raise SystemExit("index Strategy Lab insertion point not found")
index = index.replace(index_old, index_new, 1)
precedence_old = "5. Historical records remain evidence but do not override later active decisions.\n"
precedence_new = precedence_old + "6. Historical DIAG, audit, devlog, release, and patch records require an explicit status banner when their wording can be mistaken for current behavior.\n"
if precedence_old not in index:
    raise SystemExit("index precedence insertion point not found")
write("docs/INDEX.md", index.replace(precedence_old, precedence_new, 1))

conventions_section = """==================================================
REPOSITORY ARTIFACT HYGIENE
==================================================

Tracked editor backups, merge rejects, ad-hoc patches, transport fragments, encoded
payloads, and local backup files are forbidden in the authoritative tree. This includes
`*.orig`, `*.rej`, `*.patch`, `*.diff`, `*.b64`, `*.base64`, `*.bak`, `*.part-*`, and
editor `*~` files. Build output remains ignored separately.

Historical records may remain when they are genuine engineering evidence, but a record
whose wording can be confused with current behavior must carry an explicit historical
or superseded status banner and point to the current authority.

`scripts/test-repository-hygiene.sh` is a mandatory CI gate. It rejects forbidden
tracked artifacts and verifies the active documentation authority markers. Exceptions
require a separate recorded decision and a narrow reviewed allowlist; none currently
exist.

Normal steady-state branch authority is `main`. `recovery/base` is preserved as a
separate recovery reference. Ordinary task, repair, release-preparation, and transport
branches are temporary and are removed after their work is superseded or squash merged.
"""
append_once("docs/WORKING_CONVENTIONS.md", "REPOSITORY ARTIFACT HYGIENE", conventions_section)

decision = """# Decision — Repository artifact and authority hygiene

Date: 2026-08-05
Status: accepted

## Decision

The authoritative repository must not track editor backups, merge rejects, ad-hoc patch
or transport fragments, encoded payload carriers, or local backup files. CI enforces a
closed forbidden-suffix list through `scripts/test-repository-hygiene.sh`, and
`.gitignore` prevents routine reintroduction.

Historical engineering records remain valid evidence. When an old record contains
statements that could be mistaken for current product behavior, it must carry an
explicit historical/superseded banner and point to the current specialist authority.

Remote branch steady state is `main` plus the separately preserved `recovery/base`.
Temporary development and release branches are deleted after their work is superseded
or squash merged. No history rewrite or force push is permitted.

## Reason

Tracked backups and transport fragments create competing document authority and can be
accidentally packaged, reviewed, or reused. Large collections of superseded branches
also obscure the current source baseline. A permanent mechanical gate is more reliable
than periodic manual cleanup.

## Consequences

- `docs/PROJECT_STATE.md.orig` is removed;
- obsolete remote branches are removed while `recovery/base` is retained;
- CI rejects forbidden tracked artifacts;
- current Strategy Lab authority is explicit;
- package metadata remains `VERSION=0.3.2`, `PLUGIN_REVISION=24` because this is a repository-governance change outside package contents.
"""
write("docs/decisions/DEC-2026-08-05-repository-artifact-hygiene.md", decision)

audit = """# Audit — Repository artifact and documentation authority hygiene

Date: 2026-08-05
Finding: `REPO-HYG-001`
Status: closed in source

## Evidence

- removed tracked backup `docs/PROJECT_STATE.md.orig`;
- confirmed no tracked `.rej`, `.patch`, `.diff`, `.b64`, `.base64`, `.bak`, `.part-*`, or editor-backup artifacts remain;
- removed all superseded remote development/release refs, retaining only `main`, `recovery/base`, and the active Patch 11 task branch during delivery;
- added permanent ignore rules and `scripts/test-repository-hygiene.sh`;
- wired the hygiene test into mandatory CI and required-file/executable checks;
- synchronized Requirements, Development Guide, Project State, Roadmap, Strategy Lab activation, user guidance, audit authority, decision records, and historical-status banners;
- preserved package metadata because no packaged file or package behavior changed.

## Acceptance

Patch 11 is accepted after PR validation, FreeBSD package build, squash merge, post-merge validation/build, automatic task-branch cleanup, and verification that steady-state refs are only `main` and `recovery/base`.
"""
write("docs/audit/AUDIT-2026-08-05-REPOSITORY-HYGIENE.md", audit)

devlog = """# Devlog — Repository hygiene and Strategy Lab source closure

Date: 2026-08-05
Corrective patch: 11
Package metadata: unchanged (`0.3.2_24`)

Completed:

- removed the stale tracked Project State backup;
- removed superseded remote development and release branches while preserving `recovery/base`;
- added a permanent tracked-artifact hygiene gate and ignore rules;
- separated historical Strategy Lab delivery records from current authority;
- synchronized the active requirements, process guide, project state, roadmap, activation architecture, operator guide, audit, and decisions;
- closed the corrective source series and moved the project to the consolidated owner-assisted OPNsense verification gate.

No tag, GitHub Release, release asset, or pkg-repository publication was performed or authorized.
"""
write("docs/devlog/DEVLOG-2026-08-05-REPOSITORY-HYGIENE.md", devlog)

patch_record = """# Repository governance patch — current candidate `0.3.2_24`

Date: 2026-08-05
Corrective patch: 11

This logical patch changes repository governance, CI, and documentation authority only.
It does not change packaged plugin files or package behavior, so `VERSION=0.3.2` and
`PLUGIN_REVISION=24` remain unchanged.

Changes:

- remove stale tracked backup and superseded remote branches;
- add permanent forbidden-artifact ignore and CI contracts;
- mark historical Strategy Lab records explicitly;
- synchronize current Requirements, Development Guide, Project State, Roadmap, audits,
  decisions, activation architecture, and operator guidance;
- close the corrective source series and define live OPNsense verification as the next gate.
"""
write("docs/patches/v0.3.2_24-repository-hygiene.md", patch_record)

corrective_status = """## Remediation status — 2026-08-05

Corrective Patches 1–11 are source-complete. `SL-COR-001` through `SL-COR-011` are
remediated and covered by focused and complete integration tests. `REPO-HYG-001` is
closed by removal of the tracked backup, permanent CI artifact checks, documentation
authority synchronization, and obsolete branch cleanup.

This audit remains open only for the consolidated owner-assisted live OPNsense matrix.
That gate must verify real blocked-domain Standard/Extended behavior, active-stage
cancellation, bounded timeout behavior, RUNNING/STOPPED restoration, circular cleanup,
Traffic Strategy immutability, and result recovery after page reload.
"""
append_once("docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md", "Remediation status — 2026-08-05", corrective_status)

decisions_entry = """==================================================
DECISION — REPOSITORY ARTIFACT AND AUTHORITY HYGIENE
==================================================

Accepted on 2026-08-05. Tracked backup/merge/patch/transport artifacts are forbidden,
historical records that can be mistaken for current behavior require explicit status
banners, CI enforces the contract, and remote steady state is `main` plus preserved
`recovery/base`. Full rationale: `docs/decisions/DEC-2026-08-05-repository-artifact-hygiene.md`.
"""
append_once("docs/DECISIONS.md", "DECISION — REPOSITORY ARTIFACT AND AUTHORITY HYGIENE", decisions_entry)

audit_entry = """==================================================
2026-08-05 — REPOSITORY HYGIENE AND STRATEGY LAB SOURCE CLOSURE
==================================================

`REPO-HYG-001` is closed in source. The stale tracked backup and obsolete remote branches
were removed, permanent artifact/authority CI checks were added, and current Strategy
Lab authority was synchronized. Corrective source patches 1–11 are complete. The only
remaining DIAG-001 gate is consolidated owner-assisted live OPNsense verification.
Detailed evidence: `docs/audit/AUDIT-2026-08-05-REPOSITORY-HYGIENE.md`.
"""
append_once("docs/AUDIT.md", "2026-08-05 — REPOSITORY HYGIENE AND STRATEGY LAB SOURCE CLOSURE", audit_entry)

devlog_entry = """==================================================
2026-08-05 — CORRECTIVE PATCH 11: REPOSITORY HYGIENE
==================================================

Removed stale repository artifacts and obsolete branches, added permanent CI hygiene
coverage, synchronized current documentation authority, and closed the Strategy Lab
corrective source series. Package metadata remains `0.3.2_24`; the next gate is the
consolidated owner-assisted OPNsense verification matrix. Detailed record:
`docs/devlog/DEVLOG-2026-08-05-REPOSITORY-HYGIENE.md`.
"""
append_once("docs/DEVLOG.md", "2026-08-05 — CORRECTIVE PATCH 11: REPOSITORY HYGIENE", devlog_entry)
