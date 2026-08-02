# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Current version, branch, phase, priority, last completed work, blockers, or next actions change.

Read after:
INDEX.md

Do not store here:
Decision history, permanent rules, detailed workflow, architecture details, or product requirements.

==================================================
QUICK CONTEXT
==================================================

Project:
os-zapret2-restyle

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Branch:
main

Version source:
VERSION

Current version:
0.2.8

Current package revision:
2

Current package candidate:
os-zapret2-restyle-0.2.8_2

Latest completed implementation commit:
e3a9ffcf10ffe1e39917141c0ed1989592a4a7eb

Current milestone:
Milestone 8 — GUI maintenance and managed upstream components

Current phase:
Command-line bol-van/zapret2 release selection is implemented in setup.sh.

Current priority:
Live-verify the release-selection paths on OPNsense, then add installed runtime-version
detection and reporting before implementing the GUI controls.

Known blockers:
No source blocker is known. Real installation, repeat installation, upgrade, downgrade,
and service-state preservation still require focused OPNsense evidence.

==================================================
LATEST COMPLETED WORK — 2026-08-02
==================================================

The existing runtime setup backend now manages published stable bol-van/zapret2
releases instead of using one source-pinned constant.

Implemented command interface:

- `setup.sh` installs the latest published stable release;
- `setup.sh install` installs the latest published stable release;
- `setup.sh show` prints up to the four latest published stable release tags;
- `setup.sh install VERSION` installs an exact published stable release;
- the same `install VERSION` path performs first installation, repeat installation,
  upgrade, and downgrade;
- `setup.sh --help` and `setup.sh -h` describe the command interface.

Release discovery behavior:

- GitHub Releases is queried before runtime mutation;
- draft and prerelease entries are excluded;
- accepted tags use `v` followed by two or more dot-separated numeric components;
- malformed and unpublished requested versions fail before the setup lock and runtime
  replacement path;
- numeric tags such as `v1.0.3` and `v0.9.5.2` are supported;
- failure to reach GitHub or obtain usable stable releases is reported explicitly.

Installation behavior:

- the selected release is passed through the existing setup lock to the internal
  installation operation;
- an existing runtime Git tree fetches and resets to the selected tag;
- a missing runtime tree clones the selected tag;
- tracked runtime source files are replaced by the selected release;
- existing dependency, compile, dvtws2 verification, and service-state preservation
  behavior remains in the same backend;
- a previously running service is refreshed and verified;
- a previously stopped service remains stopped and is verified as stopped.

Package and validation evidence:

- VERSION remains 0.2.8;
- PLUGIN_REVISION advanced from 1 to 2 because packaged behavior changed;
- focused release-selection tests cover stable filtering, four-release output, help,
  latest default selection, exact-version propagation through lockf, malformed values,
  unpublished values, and both Git checkout paths;
- full project validation passed in GitHub Actions CI run 30737096920;
- the FreeBSD package job passed;
- CI produced artifact `os-zapret2-restyle-0.2.8_2`;
- PR #24 was squash-merged into main as commit
  e3a9ffcf10ffe1e39917141c0ed1989592a4a7eb;
- no tag, GitHub Release, GitHub Pages repository update, or package publication was
  requested or performed.

==================================================
CURRENTLY CONFIRMED
==================================================

Project and distribution:

- independent repository and package identity;
- package/plugin name `os-zapret2-restyle`;
- internal OPNsense service and configd namespace `zapret`;
- VERSION is the single version source;
- GitHub Release assets and GitHub Pages pkg repository are the approved distribution
  architecture;
- repository mode remains `signature_type: "none"` by active decision.

Runtime and backend:

- modular Backend v2;
- unified Traffic Strategy;
- placeholders limited to `<HOSTLIST:name>` and `<IPSET:name>`;
- automatic one-selector-per-runtime-profile normalization;
- user-authored `--new` boundaries are retained;
- candidate build, validation, activation, and rollback paths exist;
- launcher, firewall, dvtws2, and supervisor lifecycle exists;
- lifecycle mutation is serialized with lockf;
- setup is the single runtime preparation and upstream release-management backend;
- release selection is implemented without adding a second installer path.

Package lifecycle:

- pkg installation does not download, compile, or install runtime dependencies;
- `+POST_INSTALL` prints the explicit setup command;
- package upgrade preserves prior complete running/stopped state;
- package removal stops the service and preserves runtime and shared dependencies;
- destructive runtime cleanup remains a separate explicit maintenance action.

==================================================
OPEN VERIFICATION WORK
==================================================

Release-selection matrix:

1. run `setup.sh show` against the real GitHub API on OPNsense;
2. run no-argument setup and confirm the latest stable release is selected;
3. repeat installation of the same release;
4. install a newer published release;
5. install an older published release;
6. verify each applicable path while the service is running;
7. verify each applicable path while the service is stopped;
8. verify that malformed and unpublished versions leave runtime and service state
   unchanged.

Retained focused regression backlog:

- full OPNsense reboot and automatic service-start behavior;
- remaining CFG-001 persistence evidence;
- forced package-stop failure behavior;
- controlled dvtws2 crash and supervisor cleanup/recovery;
- complete GUI/API live matrix;
- blockcheck timeout-chain behavior;
- direct diagnostics route behavior;
- currently unused reconfigure endpoint classification.

These are unperformed or incomplete evidence tasks, not proof that the implemented
architecture is broken.

==================================================
IMMEDIATE NEXT ACTIONS
==================================================

1. Install or update to package candidate 0.2.8_2 only when a focused OPNsense test is
   intentionally started; this development task did not publish it to the pkg repository.
2. Execute the release-selection matrix above and record exact evidence.
3. Add read-only installed runtime-version detection.
4. Expose installed and available version data through the backend API.
5. Add update notification and GUI release controls that reuse setup.sh rather than
   duplicate release discovery or installation logic.
6. Continue reporting runtime presence separately from runtime/service health.

==================================================
WORKING RULES FOR RESUMPTION
==================================================

Before changing code:

1. read docs/INDEX.md;
2. follow the complete mandatory reading order;
3. inspect the current repository tree and exact GitHub main SHA;
4. identify whether relevant unpublished owner state exists;
5. use one logical change, one squash result, one build, and one focused verification;
6. update all affected documentation with the logical change;
7. do not infer current state only from chat history.

All OPNsense console commands target the default root csh shell unless a block explicitly
enters POSIX `sh` and explicitly returns with `exit`.
