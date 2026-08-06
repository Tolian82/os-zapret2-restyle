# 2026-08-06 — Evidence-first GitHub operations

## Trigger

Publication of testing candidate `v0.3.3_4` produced unnecessary GitHub churn after a
real Actions outage. A verified FreeBSD 15 package already existed, but publication was
repeatedly attempted through new workflows, branches, runners, PR synchronization runs,
and scheduled tracking.

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

## Conflict audit

The governance audit found these current-document conflicts:

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
- version-specific prerelease workflows accumulated in `main`.

## Resolution

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
- aligned the full release trigger with `vX.Y.Z_1: Prepare release vX.Y.Z`;
- synchronized current GitHub authorities and governance tests.

## Product state

`v0.3.3_4` remains a testing prerelease only. Strategy Lab live scenario 1 and the rest
of the owner-assisted matrix remain pending. Stable release and pkg-repository promotion
remain blocked on live evidence.
