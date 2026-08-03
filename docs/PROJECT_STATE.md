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
11

Current package candidate:
os-zapret2-restyle-0.2.8_11

Current milestone:
Milestone 8 — GUI maintenance and managed upstream components

Latest live-verified package behavior:

- package 0.2.8_9 preserves the pre-existing configd watcher across forced package
  installation, reloads only its worker, keeps configd actions available after the
  pkg transaction, and does not restart the Web GUI;
- package 0.2.8_10 creates and reuses the stable-release cache without repeating the
  GitHub Releases API request inside the 60-minute freshness window;
- after a reboot with ipdivert absent, dvtws2 fails before the existing later
  firewall preparation step with `Address family not supported by protocol family`;
- manually loading ipdivert makes the same unchanged service start succeed, after
  which the current code loads ipfw, installs rule 19000, starts dvtws2, and starts
  its supervisor.

Current implementation candidate:
Package 0.2.8_11 prepares the complete firewall prerequisites before either start or
reconfigure can enter the orchestrator runtime-launch path. The preparation is
idempotent within one lifecycle process, so the existing orchestrator firewall stage
remains safe without repeating PF and sysctl changes.

Current priority:
Build and live-verify 0.2.8_11 from a cold boot where ipdivert and ipfw are initially
absent. Confirm automatic boot start and an explicit Start both reach Started without
manual kldload.

Known blockers:

- package 0.2.8_11 requires focused live cold-start and reboot verification;
- the separate forced `pkg add -f` running-state preservation defect remains open and
  is intentionally not part of this firewall-order patch;
- selected-release downgrade to v1.0.3 remains pending after the runtime start path is
  stable again.

==================================================
LATEST COMPLETED WORK — 2026-08-03
==================================================

Cold-start failure diagnosis:

1. OPNsense rebooted with no dvtws2, supervisor, ipfw rules, or ipdivert module.
2. `configctl zapret start` failed at launcher stability stage.
3. dvtws2 logged:
   `socket (DIVERT4): Address family not supported by protocol family`.
4. `ipfw list` returned:
   `Protocol not available`.
5. `kldstat -q -m ipdivert` returned absent.
6. Manual `kldload ipdivert` succeeded.
7. The same `configctl zapret start` then returned OK.
8. The unchanged later firewall stage loaded ipfw and installed:
   `19000 divert 989 tcp from any to any 80,443,5222 ...`.
9. Runtime status became Started v1.0.4 and dvtws2 plus supervisor processes were
   present.

Confirmed defect:
The lifecycle attempted to start dvtws2 before the firewall module responsible for
DIVERT4 sockets was prepared. The later `firewall_prepare` call could never be reached
when dvtws2 exited during its startup stability window.

Package 0.2.8_11 implementation:

- `start_service` prepares firewall prerequisites after configuration generation and
  before `orchestrator_native_start`;
- `reconfigure_service` applies the same ordering before
  `orchestrator_native_reconfigure`;
- `firewall_prepare` is idempotent within one lifecycle process;
- the existing later orchestrator call remains as a defensive boundary but becomes a
  no-op after successful pre-launch preparation;
- no kernel module is unloaded during rollback or stop;
- plugin-owned process and rule cleanup behavior remains unchanged;
- focused regression coverage requires both service launch paths to prepare the
  firewall first.

==================================================
OPEN VERIFICATION WORK
==================================================

Package 0.2.8_11 focused live test:

1. install 0.2.8_11;
2. reboot OPNsense;
3. confirm ipdivert and ipfw are absent before the plugin boot hook, where observable;
4. confirm Zapret2 starts automatically without manual kldload;
5. confirm dvtws2 passes its startup stability window;
6. confirm ipdivert and ipfw are loaded;
7. confirm rule 19000 is installed;
8. confirm supervisor and dvtws2 processes are present;
9. stop and start from GUI and confirm Started v1.0.4;
10. continue the v1.0.3 selected-release GUI test only after this path passes.

Retained regression backlog:

- forced `pkg add -f` preservation of a previously running service;
- selected-release installation while initially running and initially stopped;
- repeat installation of the current upstream release;
- first runtime installation when dvtws2 is absent;
- controlled dvtws2 crash and supervisor cleanup/recovery;
- remaining CFG-001, lifecycle, GUI/API, and diagnostics evidence recorded elsewhere.

==================================================
IMMEDIATE NEXT ACTIONS
==================================================

1. Complete PR validation and FreeBSD package build for 0.2.8_11.
2. Install the package candidate on OPNsense.
3. Reboot and execute the cold-start acceptance test without manual module loading.
4. Record exact module, rule, process, service, and stage evidence.
5. Address forced package running-state preservation as a separate logical change.
6. Resume selected-release downgrade verification after the service path is stable.

==================================================
WORKING RULES FOR RESUMPTION
==================================================

Before changing code:

1. read docs/INDEX.md;
2. follow the complete mandatory reading order;
3. inspect the current repository tree and exact GitHub main SHA;
4. identify whether relevant unpublished owner state exists;
5. use one logical change, one squash result, one build, and one focused verification,
   except where an explicit owner-approved exception is recorded;
6. update all affected documentation with the logical change;
7. do not infer current state only from chat history.

All OPNsense console commands target the default root csh shell unless a block
explicitly enters POSIX sh and explicitly returns with exit.
