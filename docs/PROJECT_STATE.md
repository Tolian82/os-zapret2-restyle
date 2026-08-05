# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current verified source candidate on `main`: `os-zapret2-restyle-0.3.2_24.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–11
are complete in source on `main`.

Completed corrective contracts:

- atomic localized cancellation and bounded termination of active stage 60, 70, and 80
  process trees;
- one explicit monotonic stage sequence with truthful terminal state, outcome, and
  localized messages;
- one 150-second standard deadline and one optional 120-second extended allowance with a
  shared stage-80 budget;
- semantic service, process, runtime, effective-strategy, firewall, and temporary-state
  restoration verification;
- backend-authoritative circular eligibility after completed `SUCCESS`, shortlist PASS,
  and restoration PASS;
- one normalized domain-only target contract across API, shell, probes, and GUI;
- complete mock-driven API/configd-to-worker integration coverage for stages 00–99,
  polling recovery, result persistence, circular validation, lifecycle outcomes, and
  cleanup;
- repository artifact hygiene enforced by CI;
- stale tracked backups and superseded remote task/release branches removed;
- historical delivery records separated from current behavioral authority.

GitHub governance state:

- `docs/GITHUB_PUBLICATION.md`,
  `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and
  `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` are the active
  delivery authority;
- the strict one-commit/one-check-set serial gate is superseded;
- same-scope repairs remain in one PR, and squash merge provides one logical `main`
  commit;
- CI gates the latest PR state while independent analysis or separate preparation may
  continue;
- pull-request concurrency cancels obsolete runs;
- documentation/governance-only PRs skip the FreeBSD package build;
- `main` receives a lightweight integrity check instead of a duplicate package build;
- every PR title, every work or repair commit subject, and every final squash commit
  subject must begin with the exact current package-candidate prefix;
- for the current source candidate the required prefix is `v0.3.2_24:`;
- governance/documentation/CI-only work keeps `VERSION=0.3.2` and
  `PLUGIN_REVISION=24` unchanged while reusing that prefix;
- PR title and branch-commit subjects are checked before merge, and the final squash
  subject is checked after merge on `main`;
- repository-native auto-merge, squash-only settings, and automatic head-branch deletion
  remain preferred settings; the connector and cleanup workflow remain the current
  fallback where repository settings are not available through the active integration.

Historical correction:

- PR #82 unintentionally weakened the universal title rule and was squash-merged as
  `governance: modernize GitHub delivery`;
- that commit remains immutable and is not rewritten;
- the current corrective patch restores the universal rule forward and adds CI
  enforcement so the same mistake cannot pass again.

Transition note:

- open PR #81 predates this governance change and is a transitional accumulated series;
- do not add another unrelated logical patch to that PR;
- any serial-delivery decision introduced only by PR #81 is superseded by the active
  governance decision and must not be treated as current authority;
- before PR #81 can merge, its title, every branch commit subject covered by current CI,
  and its intended squash subject must comply with the exact package-candidate prefix;
- finish, split, or reconcile PR #81 against current `main` using the new workflow.

Source status:

- no tag, release, release asset, or pkg-repository publication has been made for the
  corrective source candidate;
- normal steady-state branch authority is `main`; `recovery/base` is preserved separately
  by decision;
- temporary task branches are cleaned after squash merge.

Current product authority:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/decisions/DEC-2026-08-05-repository-artifact-hygiene.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

`VERSION=0.3.2`; `PLUGIN_REVISION=24`. This GitHub governance/CI correction is outside the
packaged plugin contents, so package metadata remains unchanged.

Next product action: run the consolidated owner-assisted live OPNsense verification
matrix. Release preparation remains blocked until that evidence is recorded and explicit
release authorization is given.
