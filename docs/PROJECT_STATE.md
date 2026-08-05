# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`:
`os-zapret2-restyle-0.3.2_35.pkg`
Current source candidate proposed for integration:
`os-zapret2-restyle-0.3.2_36.pkg`

Patches 1–13 of the initial Strategy Lab delivery, corrective patches through revision 24,
and Strategy Lab hardening revisions 25–35 are complete on `main`.

Revision 35 integration:

- accumulated historical PR #83 was replaced because its revision 25–35 commit subjects
  predated universal package-candidate title enforcement;
- replacement PR #85 reconstructed the verified product tree as one correctly titled
  commit on current `main`;
- PR title, commit subject, complete project validation, repository governance, FreeBSD
  package build, squash subject, and post-merge `main` integrity all passed;
- `main` commit `89e63786f6728bc99dc10fb3ea351e467b69cbbf` is the verified revision-35
  source baseline;
- current `.github` workflows and `AGENTS.md` from revision 24 remained unchanged;
- no tag, release, release asset, or pkg-repository publication was created.

Completed hardening contracts in revisions 25–35:

- dedicated IPFW range `19100–19131`;
- proof-based candidate cleanup and startup readiness;
- reserved-residue cleanup before baseline;
- whole-worker deadline and bounded termination;
- stale-worker recovery;
- serialized state and irreversible terminal state;
- local-only automatic interception;
- endpoint-bound requests, strict redirect handling, and IPFW counter evidence;
- complete self-contained Traffic Strategy profiles with exact three-attempt replay;
- deterministic TLS 1.3, TLS 1.2, HTTP, QUIC, and configured UDP shortlist;
- separate TLS 1.3-only circular candidate set.

Revision 36 scope:

- expose the existing generic UDP branch through extended-mode GUI/API input;
- accept only a decimal UDP port and selected payload-file bytes;
- reject arbitrary server-side paths;
- validate canonical Base64 and decoded size `1..4096` bytes;
- create fixed `0600` files only inside the current job directory;
- record only non-sensitive request metadata in status;
- remove payload bytes on success, cancellation, timeout, error, failed launch, and
  stale-worker recovery;
- preserve legacy start calls with generic UDP disabled;
- cover the complete request and cleanup boundary with a focused mandatory test.

GitHub governance state:

- `docs/GITHUB_PUBLICATION.md`,
  `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and
  `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` are the active
  delivery authority;
- revision-36 PR titles, every work or repair commit subject, and the final squash subject
  must begin with `v0.3.2_36:`;
- same-scope repairs may remain in one PR;
- `main` receives one logical squash commit;
- CI validates the latest mergeable PR state;
- documentation is updated in the same logical patch;
- `main` is never force-updated.

Current product authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md`;
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`;
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`;
- `docs/architecture/STRATEGY_LAB_UDP_INPUT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-hardening-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=36` in the proposed package candidate.

Next product action after revision 36 is merged and verified: isolate circular validation
state and evidence from the completed parent job in revision 37. Release preparation
remains blocked until the full corrective plan, live OPNsense evidence, and explicit
release authorization are complete.
