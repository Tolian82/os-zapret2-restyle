# 2026-08-06 — Evidence-first GitHub operations

## Trigger

Publication of testing candidate `v0.3.3_4` produced unnecessary GitHub churn after a
real Actions outage. A verified FreeBSD 15 package already existed, but publication was
repeatedly attempted through new workflows, branches, runners, PR synchronization runs,
and scheduled tracking.

The review also confirmed that repository work became unreliable whenever the connected
GitHub plugin was not used first. Available repository state and plugin capabilities were
missed, and generic or improvised transports were used too early.

## Evidence

- source candidate commit: `34f69490f57f50aca85c9aa8e684a7f9bc72ca81`;
- verified package: `os-zapret2-restyle-0.3.3_4.pkg`;
- package manifest: version `0.3.3_4`, ABI `FreeBSD:15:amd64`, architecture
  `freebsd:15:x86:64`;
- final prerelease: `v0.3.3_4`;
- prerelease target: exact corrective commit above;
- asset digest recorded by GitHub:
  `sha256:8a16aa24fd07ce45b45068778a36b475b4e263f6f808e692045a89775f37cc17`;
- GitHub Pages and the pkg repository were not published.

The successful operation was direct attachment of the already verified package to the
owner-created prerelease. No new package build was required.

Connector verification on 2026-08-07 established:

- the repository API returned no configured rulesets;
- the connected GitHub plugin remained able to read and change ordinary repository
  objects;
- repository Actions-permission settings and branch-protection settings returned
  `403 Resource not accessible by integration` through the plugin;
- the `403` represents a connector permission boundary, not proof that those controls are
  disabled.

These connector and repository-state observations are time-sensitive and must be
re-verified before later use.

## Conflict audit

The governance audit found these current-document and workflow conflicts:

- the GitHub plugin was not consistently treated as the mandatory first repository
  interface;
- fallback wording did not distinguish one missing plugin function from complete plugin
  unavailability;
- Draft PR wording remained in `WORKING_CONVENTIONS.md` and `DEVELOPMENT_GUIDE.md` while
  Ready-by-default was already active elsewhere;
- one-atomic-branch-commit wording conflicted with same-scope repairs in one PR;
- full-document rereading for every operation conflicted with the risk-based root
  `AGENTS.md` preflight;
- `release-trigger.yml` expected unversioned `release: prepare vX.Y.Z`, conflicting with
  universal versioned titles;
- documentation-only text implied an unconditional package job although CI is path-gated;
- blanket tag/asset blocking before the live matrix did not distinguish an explicitly
  authorized testing prerelease from stable release/pkg-repository promotion;
- version-specific prerelease workflows accumulated in `main`;
- the initial repair overreached by making exact plugin-first wording and line placement
  a shell-test invariant.

## Resolution

- made the connected GitHub plugin mandatory as the first interface for every repository
  inspection and mutation;
- restricted fallback transports to the exact operation whose plugin function or
  permission is confirmed missing while the plugin is responding;
- defined plugin unavailability as an immediate stop condition: stop GitHub work, inform
  the owner, and wait for explicit direction instead of switching transports;
- recorded the current connector permission limits and the absence of repository
  rulesets as dated, re-verifiable evidence;
- kept the plugin-first rule in authoritative documentation without testing its exact
  text or line placement in shell CI;
- added `DEC-2026-08-06-evidence-first-github-operations.md`;
- made pre-mutation inventory mandatory;
- separated ordinary PR delivery, testing prerelease publication, and full release;
- limited a candidate to one active publication run;
- required job-log evidence before workflow/source changes;
- froze source on external infrastructure failures and limited recovery to one unchanged
  rerun;
- prohibited speculative runner switching, replacement branches, duplicate trackers,
  and unbounded retries;
- replaced version-specific prerelease workflows with one generic FreeBSD 15 publisher;
- added a manual dispatch path to permanent CI and prerelease publication workflows;
- aligned the full release trigger with `vX.Y.Z_1: Prepare release vX.Y.Z`;
- retained the existing repository-hygiene script only for technical workflow and
  publication invariants, not for policing prose wording or placement.

## Repository cleanup

The previous eight-commit governance PR was closed without merge. A clean replacement
was rebuilt from the exact current `main` through the connected GitHub plugin. The owner
then corrected the over-strict prose enforcement in the same PR rather than creating a
replacement branch or sibling PR.

No background automation or active Actions run remained before the replacement work
started.

## Product state

`v0.3.3_4` remains a testing prerelease only. Source correction `0.3.3_5` is merged, but
its FreeBSD 15 package and testing prerelease remain unverified until an exact successful
workflow run and artifact are inspected. Stable release and pkg-repository promotion
remain blocked on live evidence.
