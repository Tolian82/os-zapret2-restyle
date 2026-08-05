# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source baseline on `main`:
`os-zapret2-restyle-0.3.2_36.pkg`
Active integration candidate: none.

Patches 1–13 of the initial Strategy Lab delivery, corrective patches through revision 24,
and Strategy Lab hardening revisions 25–36 are complete on `main`.

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

Revision 36 integration:

- PR #86 delivered the remaining generic UDP-input contract as one correctly titled
  `v0.3.2_36:` commit based on the verified revision-35 `main`;
- PR title and commit-subject validation passed;
- complete project validation passed, including the focused dynamic UDP-input contract,
  the mandatory domain-diagnostics suite, end-to-end Strategy Lab coverage, GitHub
  governance, and repository hygiene;
- FreeBSD package `0.3.2_36` built and was inspected successfully in CI;
- PR #86 was squash-merged as
  `f7ddb1ed0ca4c1f39e7196e9a919946789e2589c` with the exact subject
  `v0.3.2_36: Expose validated generic UDP input`;
- push CI run 273 successfully verified the committed diff, versioned title identity, and
  core project identity on `main`;
- the temporary revision-36 task branch was deleted automatically;
- no tag, release, release asset, or pkg-repository publication was created.

Completed hardening contracts in revisions 25–36:

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
- separate TLS 1.3-only circular candidate set;
- supported extended-mode generic UDP input through the GUI/API;
- decimal port validation in range `1..65535`;
- canonical Base64 and decoded payload-size validation in range `1..4096` bytes;
- fixed private `0600` job-local payload storage with no arbitrary server-path input;
- payload cleanup after success, cancel, timeout, error, failed launch, and stale-worker
  recovery;
- backward-compatible start calls with generic UDP disabled.

GitHub governance state:

- `docs/GITHUB_PUBLICATION.md`,
  `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and
  `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` are the active
  delivery authority;
- every PR title, work or repair commit subject, and final squash subject uses the exact
  package-candidate prefix derived from that PR head;
- same-scope repairs may remain in one PR;
- `main` receives one logical squash commit;
- CI validates the latest mergeable PR state and post-merge `main` integrity;
- documentation is updated in the same logical patch;
- documentation-only follow-ups keep package metadata unchanged;
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

`VERSION=0.3.2`; `PLUGIN_REVISION=36` is the current verified source baseline.

Next product action: begin revision 37 as a separate logical patch that isolates circular
validation state and evidence from the completed parent job. Release preparation remains
blocked until the full corrective plan, live OPNsense evidence, and explicit release
authorization are complete.
