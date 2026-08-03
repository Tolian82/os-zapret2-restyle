# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Current version, package revision, phase, priority, verified behavior, blockers,
or next actions change.

Read after:
docs/INDEX.md

Do not store here:
Decision history, permanent rules, detailed workflow, architecture details, or
product requirements.

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

Latest immutable release tag:
v0.3.0

Current project version:
0.3.0

Current package revision:
2

Current package candidate:
os-zapret2-restyle-0.3.0_2

Current milestone:
Milestone 8 — GUI maintenance and managed upstream components

Current milestone result:
Task 1, GUI management of bol-van/zapret2 through the existing setup.sh backend, is
complete and accepted as working by the project owner.

Current priority:
Live-verify the DIAG-002 correction so negative Test Domain Connectivity results show
the complete DNS, HTTPS, and final classification report instead of an empty result.

Known blockers:
No source or CI blocker is known. Focused OPNsense rendering verification of package
candidate 0.3.0_2 remains required before DIAG-002 is classified as fully resolved.
Release publication is not part of this ordinary development change.

==================================================
ACCEPTED ZAPRET2 SERVICE CONSTRUCTION
==================================================

The Settings page contains a native collapsible Zapret2 Service block with:

- Started, Stopped, and Error state;
- the active bol-van/zapret2 stable tag;
- Start/Stop;
- the four latest stable repository releases;
- Apply for install, reinstall, upgrade, and downgrade;
- asynchronous setup polling and failure notification.

Release discovery and selection:

- `setup.sh show` returns up to four latest stable tags;
- exact installation uses `setup.sh install VERSION`;
- stable releases are cached in `/var/db/zapret2-restyle/releases.cache`;
- fresh cache reads avoid repeated GitHub API requests;
- locked atomic refresh preserves a good stale cache during temporary API failure;
- selected release verification does not repeat the Releases API request.

Transactional release activation:

- the managed GUI path uses `setup_launcher.sh` → `setup_transaction.sh` →
  `setup.sh` → `zapret_service.sh`;
- the active stable tag is stored in
  `/var/db/zapret2-restyle/runtime.release`;
- candidate Git HEAD is not displayed as installed before successful activation;
- previous Git commit, compiled binaries, active tag, and service state are captured;
- failure restores the previous checkout, binaries, tag, and Started/Stopped state;
- setup status remains failed after successful rollback so the requested operation is
  not falsely reported as successful.

Runtime permission contract:

- managed checkout and build use `umask 022`;
- Lua and blob data are normalized to 0644;
- runtime directories and compiled executables are normalized to 0755;
- this keeps files readable after dvtws2 drops to UID/GID 65534.

==================================================
LIVE-VERIFIED BEHAVIOR
==================================================

Stable-release cache:

- setup_releases returned v1.0.4, v1.0.3, v1.0.2, and v1.0.1;
- repeated fresh reads retained identical cache mtime;
- no second API refresh occurred.

Cold reboot:

- configd remained healthy;
- GUI rendered Started v1.0.4;
- ipdivert and ipfw loaded automatically;
- rule 19000 was installed;
- dvtws2 and supervisor were present;
- dvtws2 bound DIVERT4 and dropped to UID/GID 65534;
- execution state reached `13|13|ready|ok`;
- no manual kldload or service manipulation was required.

Package replacement while Started:

- `pkg add -f` completed successfully;
- configd watcher identity remained unchanged;
- dvtws2 and supervisor PIDs were replaced;
- Zapret was already Started when pkg completed;
- rule 19000 and ready/ok execution state were present;
- transient lifecycle markers were removed;
- no reboot or manual service command was required.

Package replacement while Stopped:

- `pkg add -f` completed successfully;
- service remained Stopped;
- no dvtws2 or supervisor process was present;
- no plugin-owned ipfw rule was present.

GUI release management:

1. Initially Stopped v1.0.3, select v1.0.4 and Apply:
   - result Stopped v1.0.4;
   - Git HEAD and runtime.release both v1.0.4;
   - required Lua files 0644 root:wheel.
2. Start through GUI:
   - service started successfully.
3. Started v1.0.4, select v1.0.3 and Apply:
   - result Started v1.0.3;
   - setup ready, busy 0;
   - Git HEAD and runtime.release both v1.0.3;
   - required Lua files remained 0644 root:wheel;
   - no reboot or manual restart was required.

Focused CI behaviorally verifies successful candidate activation and automatic rollback
of Git commit, binaries, active release, permissions, and service state after failure.

==================================================
COMPLETED DEFECT CHAIN
==================================================

The completed Service work fixed:

- configd parameter mismatch caused by passing two setup parameters to one `%s`;
- false GUI launch success before detached configd completion;
- repeated and fragile GitHub Releases API reads;
- red modal behavior for passive transient release-list failure;
- firewall prerequisites being loaded after dvtws2 attempted DIVERT4 creation;
- loss of Started state during forced package replacement;
- restrictive Lua permissions after selected Git checkout;
- transient display of candidate Git HEAD as the installed release;
- failed candidate activation leaving the firewall stopped on the candidate checkout.

==================================================
DOMAIN DIAGNOSTICS CANDIDATE — DIAG-002
==================================================

Observed defect:

- the shell diagnostic generated complete timeout, reset, TLS, DNS, refusal, and
  generic failure reports;
- it then exited with curl's non-zero connectivity status;
- configd `script_output` treated that as execution failure and discarded stdout;
- the backend returned an empty string;
- the API incorrectly returned `status=ok`, so the browser cleared the result field.

Implemented in package candidate 0.3.0_2:

- a completed curl probe is treated as diagnostic data and exits zero after printing
  the full report;
- invalid invocation and invalid domain input remain non-zero execution errors;
- the API rejects an empty configd response instead of reporting blank success;
- focused mocked tests cover timeout, connection reset, generic curl failure, invalid
  input, and the controller guard;
- detailed evidence and acceptance criteria are recorded in
  `docs/audit/AUDIT-2026-08-03-DOMAIN-DIAGNOSTICS.md`.

Static verification completed:

- shell syntax checks passed;
- the focused diagnostics contract test passed;
- PHP syntax validation passed;
- CI includes the new focused test and FreeBSD package build.

Live verification required:

- positive result remains unchanged;
- a timeout or connection reset renders the complete multiline negative report;
- the result field no longer becomes empty.

==================================================
RELEASE v0.3.0
==================================================

Release decision:
The project owner accepted the Zapret2 Service construction and authorized v0.3.0.

Immutable tag:
v0.3.0

Release package baseline:
os-zapret2-restyle-0.3.0_1.pkg

Repository target:
FreeBSD:15:amd64

The DIAG-002 correction is a later package-revision candidate and does not modify the
immutable v0.3.0 tag or previously published package.

==================================================
NEXT PRODUCT WORK
==================================================

1. Install package candidate 0.3.0_2 and verify positive and negative Test Domain
   Connectivity rendering.
2. Record live DIAG-002 evidence and close the Finding only after the GUI displays the
   complete negative report.
3. Implement explicit notification when a newer stable bol-van/zapret2 release is
   available as a separate logical change.
4. After the project owner supplies and approves its repository and contract, design
   GUI management of the additional BLOB repository.
5. Continue unrelated retained timeout-chain, controlled-failure, and audit backlog
   only as separate focused work.

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

All OPNsense console commands target the default root csh shell unless a block
explicitly enters POSIX sh and explicitly returns with exit.
