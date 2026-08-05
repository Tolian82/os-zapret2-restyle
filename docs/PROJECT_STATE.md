# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified baseline on `main` at reconciliation start:
`os-zapret2-restyle-0.3.2_24.pkg`
Current source candidate proposed for integration:
`os-zapret2-restyle-0.3.2_35.pkg`

Patches 1–13 of the initial Strategy Lab delivery and corrective patches through revision
24 are complete on `main`. Strategy Lab hardening revisions 25–35 are implemented in the
reconciled candidate.

Completed hardening contracts in revisions 25–35:

- documented hardening scope, dedicated IPFW range `19100–19131`, and complete output-
  profile contract;
- proof-based candidate runtime cleanup and startup readiness;
- removal of reserved temporary residue before baseline testing;
- whole-worker hard deadline and bounded termination;
- stale or missing worker recovery with mandatory service restoration;
- serialized job-state mutation and irreversible terminal state;
- automatic probes limited to firewall-originated traffic while circular validation
  remains intentionally client-wide;
- endpoint-bound requests, selected-IP persistence, strict redirect policy, and verified
  IPFW counter growth;
- complete self-contained Traffic Strategy profiles with exact three-attempt replay before
  recommendation;
- one deterministic final shortlist containing verified TLS 1.3, TLS 1.2, HTTP, QUIC, and
  configured UDP results;
- a separate TLS 1.3-only candidate set for temporary circular validation;
- focused tests, end-to-end fixtures, repository-hygiene checks, and FreeBSD package build
  coverage for the resulting candidate.

Verification history:

- the product tree at source SHA `4525b2dc333b1e3bd3b165c587dd68169c09f73d`
  passed the complete project validation and FreeBSD package build;
- integration is accepted only after the reconciled single-commit PR based on the current
  `main` passes the same required checks;
- no tag, release, release asset, or pkg-repository publication has been made for revision
  35.

GitHub governance state:

- `docs/GITHUB_PUBLICATION.md`,
  `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and
  `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` are the active
  delivery authority;
- every PR title, every work or repair commit subject, and every final squash commit
  subject must begin with the exact package-candidate prefix derived from the PR head;
- the reconciled candidate therefore uses `v0.3.2_35:` everywhere;
- same-scope repairs may remain in one PR, and `main` receives one logical squash commit;
- CI gates the latest mergeable PR state while independent analysis or separate
  preparation may continue;
- documentation/governance-only changes do not increment package metadata;
- `main` is never force-updated and published history is corrected only forward.

Reconciliation record:

- accumulated PR #83 was created before the universal commit-subject rule and contained
  historical subjects from revisions 25–35 that cannot satisfy the new head-derived
  `v0.3.2_35:` check;
- simply merging current `main` into PR #83 would preserve the files but leave the PR
  permanently non-compliant;
- the verified product tree is therefore reconstructed once on top of current `main` as
  one versioned commit;
- current GitHub governance files remain from `main`, product source and tests remain from
  the verified revision-35 tree, and overlapping status/index/decision records are merged
  explicitly;
- PR #83 is retained as historical evidence and replaced rather than force-rewritten;
- no Strategy Lab source or documentation from revisions 25–35 is intentionally dropped.

Current product authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md`;
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`;
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-hardening-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=35` in the proposed package candidate.

Next product action after revision 35 is merged and verified: implement revision 36 as one
separate logical patch exposing validated UDP port and job-local payload input through the
Strategy Lab GUI/API. Release preparation remains blocked until the full corrective plan,
live OPNsense evidence, and explicit release authorization are complete.
