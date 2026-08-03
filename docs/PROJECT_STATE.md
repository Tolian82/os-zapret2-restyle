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

Current version:
0.2.8

Current package revision:
12

Current package candidate:
os-zapret2-restyle-0.2.8_12

Current milestone:
Milestone 8 — GUI maintenance and managed upstream components

Latest live-verified package behavior:

- package 0.2.8_9 preserves the existing configd watcher during package replacement
  and reloads only its worker;
- package 0.2.8_10 creates and reuses the validated stable-release cache;
- package 0.2.8_11 is live verified after a cold reboot: ipdivert and ipfw are loaded
  before dvtws2 launch, rule 19000 is installed, dvtws2 and supervisor run, GUI shows
  Started v1.0.4, and execution state reaches `13|13|ready|ok` without manual kldload.

Current implementation candidate:
Package 0.2.8_12 removes the remaining dependency on `PKG_UPGRADE` for service-state
handoff. Incoming `+PRE_INSTALL` records running state in a replacement-specific
marker before the installed package hook stops service. Incoming `+POST_INSTALL`
restores and verifies replacement code whenever that marker exists, including forced
`pkg add -f` and `pkg install -f` paths.

Current priority:
Build and live-verify 0.2.8_12 by forcing replacement over a running 0.2.8_11 service
and confirming that pkg completes with Zapret already Started, new runtime PIDs,
healthy configd and Web GUI, and no reboot or manual service manipulation.

Known blockers:

- package 0.2.8_12 requires the focused live forced-replacement matrix;
- selected-release downgrade to v1.0.3 remains pending after package state transfer
  is verified.

==================================================
LATEST COMPLETED WORK — 2026-08-03
==================================================

Cold-start/reboot verification for package 0.2.8_11:

- configd remained healthy;
- GUI rendered the correct state;
- `setup_status` reported installed=1, service=started, version=v1.0.4,
  setup=ready, busy=0;
- `configctl zapret status` reported a running PID;
- ipdivert and ipfw were loaded automatically;
- plugin rule 19000 was installed;
- dvtws2 and supervisor processes were present;
- dvtws2 bound its DIVERT4 socket and dropped to UID/GID 65534;
- execution state reached `13|13|ready|ok`.

Forced replacement diagnosis:

- `pkg add -f` does not reliably provide `PKG_UPGRADE` to the current hooks;
- current incoming `+PRE_INSTALL` therefore skips state capture;
- installed `+PRE_DEINSTALL` stops service and removes only the legacy marker;
- incoming `+POST_INSTALL` also requires `PKG_UPGRADE`, so it leaves service stopped;
- reboot hides the defect by invoking the ordinary boot-start hook later.

Package 0.2.8_12 implementation:

- added replacement marker `/var/run/zapret2-restyle/pkg-replacement.restart`;
- incoming pre-install classifies, records, stops, and verifies installed service state
  for every replacement path, not only an exported upgrade context;
- the new marker survives the first transition from the older 0.2.8_11 pre-deinstall;
- post-install restores when the replacement marker exists and retains legacy-marker
  compatibility for interrupted true upgrades;
- stopped and incomplete states are not promoted;
- fresh install clears stale transient state;
- post-deinstall remains service-free and cannot erase an active replacement handoff;
- focused tests execute forced replacement, stopped, retry, incomplete, stop-failure,
  fresh-install, legacy-hook-transition, and configd-worker contracts.

==================================================
OPEN VERIFICATION WORK
==================================================

Package 0.2.8_12 focused live test:

1. confirm 0.2.8_11 is Started and record dvtws2/supervisor/configd PIDs;
2. install 0.2.8_12 with `pkg add -f` without stopping service manually;
3. confirm the package transaction finishes successfully;
4. confirm configd watcher identity remains unchanged and actions answer;
5. confirm Zapret is already Started before any reboot or manual service command;
6. confirm dvtws2 and supervisor PIDs differ from their pre-install values;
7. confirm execution state is ready/ok and rule 19000 is present;
8. confirm both transient marker files are absent after successful restoration;
9. repeat while initially stopped and confirm it remains stopped;
10. retain failed-stop and interrupted-retry scenarios as focused regression evidence.

Retained regression backlog:

- selected-release installation while initially running and initially stopped;
- repeat installation of the current upstream release;
- first runtime installation when dvtws2 is absent;
- controlled dvtws2 crash and supervisor cleanup/recovery;
- remaining CFG-001, lifecycle, GUI/API, and diagnostics evidence recorded elsewhere.

==================================================
IMMEDIATE NEXT ACTIONS
==================================================

1. Complete PR validation and FreeBSD package build for 0.2.8_12.
2. Install 0.2.8_12 over running 0.2.8_11 with `pkg add -f`.
3. Verify automatic Started-state restoration without reboot or manual service work.
4. Repeat the replacement while initially stopped.
5. Resume the GUI downgrade test from v1.0.4 to v1.0.3.

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
