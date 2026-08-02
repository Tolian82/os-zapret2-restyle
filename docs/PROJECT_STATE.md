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
10

Current package candidate:
os-zapret2-restyle-0.2.8_10

Current milestone:
Milestone 8 — GUI maintenance and managed upstream components

Latest live-verified package behavior:
Package 0.2.8_9 upgrades an installed and running runtime without killing configd
or the Web GUI. The pre-existing configd watcher is preserved, only its worker is
reloaded, configd actions remain available after the pkg transaction, lighttpd
keeps listening on ports 80/443, and the previously running Zapret service returns
to Started with upstream version v1.0.4.

Current implementation candidate:
Package 0.2.8_10 corrects selected-release launch and adds a resilient stable-release
cache. The GUI uses one dedicated one-parameter configd action, waits for a real OK
from the short-lived launcher, reuses the existing busy-state polling, serves repeated
release-list reads from a local cache, and contains passive discovery failure without
a red exception dialog.

Current priority:
Build and live-verify 0.2.8_10 by selecting v1.0.3 in the GUI and confirming that the
runtime reaches Started v1.0.3 while the release selector remains usable during a
simulated or naturally occurring temporary GitHub API failure.

Known blockers:
No source blocker is known. The package candidate requires focused live OPNsense
verification.

==================================================
LATEST COMPLETED WORK — 2026-08-02
==================================================

Configd package lifecycle:

- package 0.2.8_9 no longer starts a replacement configd watcher inside `pkg add`;
- `+POST_INSTALL` preserves the existing watcher and sends SIGTERM only to its current
  `configd.py console` worker;
- the same watcher creates a replacement worker;
- continuation requires a different worker PID and a successful
  `configctl system status` request;
- package installation does not restart the global Web GUI;
- live evidence preserved watcher PID 46333, replaced the worker with PID 61632,
  kept configd responsive after the package process ended, retained lighttpd PID
  65346, and restored the running Zapret service.

GUI selected-release diagnosis:

- selecting v1.0.3 previously produced configd `Parameter mismatch`;
- ServiceController passed two arguments, `install` and `v1.0.3`, to an action with
  one `%s` placeholder;
- detached configd execution returned a UUID before the action failure, so the GUI
  incorrectly treated the operation as started;
- setup.sh, setup_launcher.sh, setup log, setup status, PID state, runtime tree, and
  installed v1.0.4 were unchanged;
- later `setup.sh show` failures were temporary GitHub API failures; a subsequent CLI
  request returned v1.0.4, v1.0.3, v1.0.2, and v1.0.1 normally.

Package 0.2.8_10 implementation:

- configd action `setup_install` binds launcher mode `install` and exposes exactly
  one `%s` placeholder for the selected version;
- ServiceController passes only the version and requires synchronous configd `OK`;
- setup_launcher.sh remains the short-lived launcher and detaches the long setup
  worker through FreeBSD daemon(8);
- passive release discovery returns `status=unavailable` instead of raising a
  UserException dialog when neither GitHub nor a valid cache is available;
- stable releases are cached in
  `/var/db/zapret2-restyle/releases.cache` for 60 minutes;
- refreshes are serialized by
  `/var/run/zapret2-restyle/releases.lock`;
- cache replacement is atomic and occurs only after successful download, JSON parsing,
  draft/prerelease filtering, tag validation, deduplication, and non-empty output;
- a failed refresh preserves and returns a previously validated stale cache;
- exact selected-version installation validates against the cache and does not issue
  another GitHub Releases API request;
- repeated GUI release-list reads, including the read after Apply, use the cache.

Focused validation:

- POSIX shell syntax passes for setup.sh and both focused tests;
- PHP syntax passes for ServiceController.php;
- release-selection tests cover first fetch, fresh-cache reuse, exact-install reuse,
  latest selection, stale-cache fallback, failed-refresh preservation, no-cache
  failure, filtering, deduplication, malformed/unpublished rejection, strict fetch
  arguments, lock use, atomic replacement, and both Git checkout paths;
- GUI tests enforce one configd placeholder, one controller parameter, synchronous
  exact OK, removal of the old UUID/two-argument contract, non-modal unavailable
  response, and retained runtime/layout behavior.

==================================================
OPEN VERIFICATION WORK
==================================================

Package 0.2.8_10 focused live test:

1. install 0.2.8_10 over the running v1.0.4 runtime;
2. confirm configd watcher identity remains unchanged and ordinary GUI/configd
   services remain available;
3. select v1.0.3 and press Apply;
4. confirm controls enter Applying and Start/Stop remains disabled during setup;
5. confirm setup.log records selected v1.0.3, checkout/build, and service refresh;
6. confirm final GUI state is Started v1.0.3;
7. confirm `configctl zapret setup_status` reports installed=1, service=started,
   version=v1.0.3, setup=ready, busy=0;
8. confirm repeated release-list reads do not refresh GitHub within 60 minutes;
9. simulate or observe a temporary API failure and confirm a validated stale cache
   keeps the selector populated without a red release-error dialog;
10. remove the cache and repeat API failure to confirm the selector shows Недоступно
    without a red dialog or runtime alteration.

Retained regression backlog:

- selected-release installation while the service is initially stopped;
- repeat installation of the currently installed upstream release;
- first runtime installation when dvtws2 is absent;
- full reboot and automatic service start;
- controlled dvtws2 crash and supervisor cleanup/recovery;
- remaining CFG-001, lifecycle, GUI/API, and diagnostics evidence recorded elsewhere.

==================================================
IMMEDIATE NEXT ACTIONS
==================================================

1. Complete PR validation and FreeBSD package build for 0.2.8_10.
2. Install the package candidate on OPNsense.
3. Execute the focused v1.0.4 to v1.0.3 GUI downgrade test.
4. Verify fresh-cache reuse and stale-cache fallback on the live appliance.
5. Record exact live evidence before classifying this GUI path as verified.

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
