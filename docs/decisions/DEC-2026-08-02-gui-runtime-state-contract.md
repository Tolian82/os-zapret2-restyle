# DEC-2026-08-02 — GUI runtime state and selected-release operation contract

Status: Approved and implemented
Date: 2026-08-02

## Decision

The `Zapret2 Service` Settings block reports and controls the bol-van/zapret2 runtime,
not package installation and not configd itself.

Runtime installation evidence is the executable file:

`/usr/local/etc/zapret2/binaries/my/dvtws2`

The displayed states are:

- executable dvtws2 present and canonical service status running: `Started`, exact
  installed release tag when available, and `Stop`;
- executable dvtws2 present and canonical service status stopped: `Stopped`, exact
  installed release tag when available, and `Start`;
- executable dvtws2 absent or runtime state incomplete: `Error`, `not installed`, and
  no Start/Stop control.

Stopped and not-installed are passive states. Opening the page, querying either state,
or successfully starting/stopping dvtws2 does not create an error dialog. A real HTTP
backend failure is rendered only by the standard OPNsense error path. The plugin-owned
dialog is retained only for a setup operation that was accepted asynchronously and
later completed with setup state `failed`.

The runtime line uses fixed desktop columns. The version slot reserves `14ch`, the
Start/Stop slot reserves `12ch` even while its button is absent, and a separate `4ch`
spacer follows that slot. Therefore `Repository Releases`, the release selector, and
runtime `Apply` remain in the same position for Started, Stopped, Error, and
`not installed`.

Release install, reinstall, upgrade, and downgrade continue through the one approved
backend:

`setup.sh install VERSION`

The MVC controller invokes the existing configd `zapret setup` action with a quoted
parameter list and detached execution. Configd returns an operation UUID immediately;
the controller validates that UUID and returns it to the GUI. The GUI then polls the
read-only runtime status until completion.

## Reason

Live package `0.2.8_5` evidence showed three separate contract defects:

- inherited OPNsense Start/Stop endpoints return `{response: ...}`, while the custom
  JavaScript incorrectly required `{status: "ok"}` and displayed a false failure after
  successful state changes;
- detached configd execution returns a UUID, while the controller used a synchronous
  concatenated command and required literal `OK`, so selected-release setup was rejected;
- missing runtime and API failures were not distinguished, and flexible layout moved
  controls as version and button content changed.

The approved contract separates runtime presence, service health, and setup-operation
state while retaining setup.sh as the only installer.

## Consequences

- setup status explicitly reports `installed=0|1` before service and version fields;
- service status is not queried when executable dvtws2 is absent;
- the controller exports installed state and forces Error with no version when absent;
- selected releases are passed through `Backend::configdpRun()` parameters rather than
  shell concatenation;
- the detached configd UUID is the acceptance token for a started setup operation;
- Start/Stop success follows the standard base-controller HTTP contract;
- duplicate AJAX failure dialogs are removed;
- focused tests cover absent, running, and stopped runtime states, version detection,
  fixed layout, Start/Stop response handling, and detached selected-release launch;
- package candidate advances to `0.2.8_7`.

## Affected files and documentation

- `Makefile`
- `src/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh`
- `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php`
- `src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt`
- `scripts/test-gui-runtime-management.sh`
- this decision record
