# DEC-2026-08-02 — GUI selected-release launch and stable-release cache

Status: Approved and implemented
Date: 2026-08-02

## Decision

The GUI selected-release operation and stable-release discovery are one approved
corrective patch by explicit project-owner exception to the normal one-change rule.

Selected-release launch uses a dedicated configd action:

- action name: `zapret setup_install`;
- command: `setup_launcher.sh install`;
- parameters: exactly one `%s` placeholder containing the validated release tag;
- MVC call: `configdpRun(..., [$version], false, 30)`;
- acceptance result: exact synchronous `OK` from configd.

Configd detach and UUID acceptance are not used. setup_launcher.sh remains responsible
for detaching the long-running setup.sh worker through FreeBSD daemon(8). After `OK`, the existing GUI status refresh observes the PID/status written by the
short-lived launcher and continues its normal polling while setup remains busy.

Stable release discovery uses a validated file cache:

- cache: `/var/db/zapret2-restyle/releases.cache`;
- refresh lock: `/var/run/zapret2-restyle/releases.lock`;
- freshness interval: 60 minutes;
- cache contents: all accepted stable numeric `vX.Y...` tags in GitHub API order;
- GUI output: first four cached tags;
- replacement: temporary file in the state filesystem followed by atomic rename;
- failed download, invalid JSON, invalid/empty tag output, or interrupted refresh must
  not overwrite the previous cache;
- one lock owner refreshes a stale cache; waiters reuse the refreshed file;
- a validated stale cache is returned when GitHub is temporarily unavailable;
- exact selected-version installation reads the validated cache and does not issue a
  second GitHub Releases API request;
- when no valid cache exists and GitHub is unavailable, passive GUI discovery returns
  `status=unavailable` and renders `Недоступно` without a UserException dialog.

A GUI refresh after Apply is satisfied from the cache and therefore does not create a
second GitHub Releases API request.

## Reason

Live GUI testing showed that selecting v1.0.3 never launched setup. ServiceController
passed two parameters (`install`, `v1.0.3`) to a configd action declaring one `%s`, so
configd logged `Parameter mismatch`. Detached execution returned a UUID before that
failure and the GUI incorrectly treated the operation as started. No setup PID, status,
log update, checkout, build, or version change occurred.

The same click path also caused redundant GitHub Releases API requests from controller
validation, setup.sh validation, and GUI list refresh. Two temporary API failures then
turned the selector into `Недоступно` and raised a red release-error dialog even though
a later CLI request returned the release list normally.

One explicit action parameter plus synchronous launcher acceptance removes the contract
mismatch. A locked atomic cache removes redundant API traffic and makes transient
GitHub availability independent from already known stable releases.

## Consequences

- package candidate advances from 0.2.8_9 to 0.2.8_10;
- one page load normally performs at most one GitHub Releases API request per hour;
- Apply normally performs no GitHub Releases API request when the cache is valid;
- temporary GitHub failure does not erase or replace a valid cache;
- passive list failure is non-modal; a later page/API refresh can retry discovery;
- selected-release launch is not considered accepted until configd returns `OK`;
- the existing busy-state polling controls Start/Stop during an active setup operation;
- setup.sh remains the single release validation, checkout, build, and service-state
  preservation backend;
- live downgrade/reinstall/upgrade and stale-cache fallback evidence remains required.

## Affected files and documentation

- `Makefile`
- `src/opnsense/service/conf/actions.d/actions_zapret.conf`
- `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php`
- `src/opnsense/scripts/OPNsense/Zapret/setup.sh`
- `scripts/test-gui-runtime-management.sh`
- `scripts/test-setup-release-selection.sh`
- `docs/PROJECT_STATE.md`
- this decision record
