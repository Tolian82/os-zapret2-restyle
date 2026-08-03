# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Version, package revision, delivery stage, verification state, priority, blockers, or
next action changes.

Read after:
`docs/INDEX.md`.

Do not store here:
Detailed decision history, permanent procedures, full architecture, or product
requirements.

==================================================
QUICK CONTEXT
==================================================

Project:
`os-zapret2-restyle`

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Primary branch:
`main`

Current published release:
`v0.3.1`

Current published package:
`os-zapret2-restyle-0.3.1_1.pkg`

Published-release verification:
Project-owner live verification completed successfully on 2026-08-03. The owner
explicitly confirmed that release/package `0.3.1_1` was checked and everything in it
works correctly.

DIAG-002:
Resolved and live verified by the project owner. Positive and negative Test Domain
Connectivity results render correctly; the negative path no longer produces an empty
result field.

Current delivery stage:
`RELEASE_AUTHORIZED`

Explicitly approved next release:
`v0.3.2`

Expected package:
`os-zapret2-restyle-0.3.2_1.pkg`

Current priority:
Publish v0.3.2 as a forward-only governance and documentation release that makes GitHub
work deterministic, atomic, and less noisy.

Known blockers:
None before pull-request CI. Release publication remains subject to the normal complete
check set and post-release distribution verification.

==================================================
V0.3.2 SCOPE
==================================================

v0.3.2 changes engineering and publication control, not plugin runtime behavior.

Approved results:

- add `GITHUB_PUBLICATION.md` to the mandatory reading order;
- make it the final specialist authority before GitHub mutation;
- replace Draft → Ready with one ready pull request and one check set;
- compute the exact package-candidate PR title before opening the PR;
- distinguish PR title from release squash subject;
- require one blobs/tree/commit publication for multi-file API work;
- close and replace failed delivery cycles instead of incrementally repairing them;
- require explicit named release authority;
- preserve forward-only immutable release history with no version rollback;
- require complete release and pkg-repository verification before installation commands;
- record successful owner verification of v0.3.1 / 0.3.1_1.

==================================================
CURRENT RELEASE PROTOCOL
==================================================

PR title for this release:

`v0.3.2_1: Improve GitHub publication discipline`

Required squash subject:

`release: prepare v0.3.2`

Release automation:

1. merge the verified release-preparation PR;
2. `release-trigger.yml` creates or verifies tag `v0.3.2` at that exact merge;
3. `release.yml` builds and verifies package `0.3.2_1` and the pkg repository;
4. GitHub Release and GitHub Pages are published;
5. all public assets and repository metadata are verified before installation guidance.

==================================================
ACCEPTED PRODUCT BASELINE
==================================================

The accepted plugin baseline includes:

- unified Traffic Strategy;
- HOSTLIST/IPSET target normalization and profile expansion;
- transactional Apply and runtime rollback;
- launcher, firewall, supervisor, and lifecycle serialization;
- project-owned pkg repository;
- Zapret2 Service GUI;
- upstream stable-release discovery and selection;
- install, reinstall, upgrade, and downgrade through the existing setup backend;
- service-state preservation and transactional upstream runtime rollback;
- complete positive and negative Test Domain Connectivity reports.

==================================================
NEXT PRODUCT WORK AFTER v0.3.2
==================================================

1. Implement passive notification when a newer stable bol-van/zapret2 release exists.
2. Design additional BLOB repository management only after the owner supplies and
   approves its repository and technical contract.
3. Continue retained diagnostics timeout-chain and unrelated audit backlog only as
   separate focused changes.

==================================================
RESUMPTION RULE
==================================================

Before any future project action:

1. obey `AGENTS.md`;
2. complete the exact reading order in `docs/INDEX.md`;
3. read `docs/GITHUB_PUBLICATION.md` immediately before GitHub mutation;
4. read the current `main` and record its exact SHA;
5. obey the delivery stage recorded here;
6. do not infer release authority or version from chat phrasing.
