# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the current system built?

Purpose:
Describe the active technical architecture, runtime ownership, interfaces, and
component responsibilities.

Updated when:
The system architecture or component responsibilities change.

Read after:
DEVELOPMENT_GUIDE.md

Do not store here:
Current task status, decision rationale, roadmap, or chronological history.

==================================================
IDENTITY AND SOURCE OF TRUTH
==================================================

Repository: `https://github.com/Tolian82/os-zapret2-restyle`
Primary branch: `main`
Project/package: `os-zapret2-restyle`
Internal service and configd namespace: `zapret`
Version source: `VERSION`

The repository is independent and contains every project-owned file required to
build and install the plugin on a supported clean OPNsense system. Generated
runtime, binaries, logs, PID files, backups, and appliance configuration are not
source files.

==================================================
CONFIGURATION AND RUNTIME PIPELINE
==================================================

```text
OPNsense model
  -> generated zapret.conf
  -> parser and count-carrying profile pipeline
  -> Target Mode and profile normalization
  -> HOSTLIST/IPSET resolver and exclusions
  -> blob and port resolution
  -> dvtws2 argument generation
  -> candidate validation
  -> atomic activation or rollback
  -> launcher
  -> target firewall rules
  -> supervisor
```

The active generated runtime is `/usr/local/etc/zapret2/runtime-v2`. One supervised
dvtws2 process owns the active strategy. Invalid candidate configuration must not
change the active runtime, child PID, supervisor, or plugin-owned firewall rules.

Only `HOSTLIST:name` and `IPSET:name` target selectors are supported. A user profile
with multiple unique supported selectors is normalized into one runtime profile per
selector while preserving non-selector lines and first-use order. User-authored
`--new` boundaries remain valid.

==================================================
SETTINGS APPLY
==================================================

```text
/ui/zapret
  -> Settings API validates and normalizes the model
  -> persistent save
  -> configctl zapret reconfigure
  -> zapret_service.sh reloads the template
  -> Backend v2 candidate build and validation
  -> atomic runtime switch or rollback
```

Only an exact successful configd response completes Apply. On failure, the previous
persistent model, generated template, and runtime are restored.

==================================================
DIAGNOSTICS INTERFACES
==================================================

Short domain connectivity probe:

```text
/ui/zapret/diagnostics
  -> /api/zapret/diagnostics/testdomain
  -> configctl zapret testdomain
  -> test_domain.sh
```

Strategy finding uses only the asynchronous Strategy Lab path:

```text
/ui/zapret/diagnostics
  -> POST /api/zapret/strategy_lab/start
  -> immediate job_id
  -> POST status once per second
  -> structured stages and partial results
  -> POST result after terminal state
  -> optional POST cancel
```

The synchronous `blockcheck.sh` wrapper, configd `blockcheck` action,
`DiagnosticsController::blockcheckAction`, synchronous API URL, and long browser
request are not active or fallback interfaces.

The detailed GUI and API contract is defined in
`docs/architecture/STRATEGY_LAB_ACTIVATION.md`.

==================================================
STRATEGY LAB TRANSACTION
==================================================

An automated job owns the shared Zapret2 lifecycle lock from initial snapshot through
mandatory restoration. The normal service is stopped only after its exact initial
state is recorded. Temporary dvtws2 processes and target-scoped firewall rules are
fully removed between candidates and before restoration.

Stages are persisted atomically:

```text
00 target initialization
10 lifecycle snapshot
20 normal service stop
30 network capability precheck
40 clean baseline
50 TLS 1.3 family screening
60 accepted-family parameter expansion
70 three-of-three stability confirmation
80 extended protocol branches
85 shortlist
90 cleanup and exact service restoration
99 final report
```

Different strategies run strictly sequentially. Screening may probe two different
endpoints of the same service concurrently with one strategy. Stability confirmation
uses fresh sequential connections and requires every required endpoint to pass three
of three attempts.

Standard mode searches TLS 1.3. Extended mode adds TLS 1.2, plain HTTP,
capability-gated QUIC, and configured request-response UDP. IPv6 and QUIC branches are
skipped when their independent capability gates are unavailable.

Cancellation marks the current work cancelled, preserves completed structured results,
stops temporary probes/runtime, and always executes stage 90. A restoration failure
changes the terminal result to `restore_failed`; it is never reported as success.

==================================================
SHORTLIST AND CIRCULAR VALIDATION
==================================================

A completed domain job may expose three to five stable candidates, ordered with
recommendation number one first. Strategy Lab never writes a candidate to the saved
Traffic Strategy.

Temporary circular validation is a separate bounded lifecycle transaction:

```text
completed domain shortlist
  -> one target-scoped dvtws2 profile
  -> upstream Zapret2 circular orchestrator
  -> bidirectional TCP/443 interception
  -> browser/application validation
  -> explicit stop or TTL
  -> temporary cleanup
  -> exact restoration of initial Zapret2 state
```

Circular validation and automated Strategy Lab jobs cannot run concurrently because
they share the lifecycle lock. The saved configuration remains immutable.

==================================================
SERVICE LIFECYCLE
==================================================

All public mutating operations converge on `zapret_service.sh` and share
`/var/run/zapret2-lifecycle.lock`:

- start;
- stop;
- restart/reconfigure;
- automated Strategy Lab job;
- temporary circular validation.

Status operations are read-only. Long-lived dvtws2 and supervisor processes must not
inherit the lifecycle lock descriptor. Runtime-failure callbacks use a non-blocking
try-lock so a stale supervisor cannot tear down a replacement runtime.

The supervisor only detects runtime failure and reports it to the service lifecycle.
It does not independently regenerate configuration, restart the service, or own a
second watchdog lifecycle.

==================================================
PACKAGE AND UPSTREAM RUNTIME BOUNDARY
==================================================

The FreeBSD package owns plugin files and immediate OPNsense integration. Package
upgrade stops and verifies the old service before replacement, refreshes plugin and
Web GUI integration, and restarts only when the service was initially running.

`setup.sh` owns upstream bol-van/zapret2 acquisition, selected stable release checkout,
dvtws2 compilation, verification, and preservation of the initially running or stopped
service state. Service Start, Apply, and Reconfigure never install dependencies or
compile the engine.

Package removal stops packet interception but preserves runtime content,
configuration, logs, and dependencies. Destructive cleanup requires a separate explicit
maintenance operation.

==================================================
TECHNICAL CONSTRAINTS
==================================================

- FreeBSD `/bin/sh` compatibility; no Bash-only syntax.
- OPNsense configuration and configd are the integration boundary.
- Candidate validation precedes activation.
- Generated runtime is never committed.
- Lifecycle mutation is serialized and fail-closed.
- Temporary diagnostics use target-scoped firewall rules.
- No automatic permanent strategy modification.
- Ordinary package patches do not create tags, releases, or pkg-repository publication.

Audit evidence is maintained in `AUDIT.md`, approved rationale in `DECISIONS.md`,
delivery order in `ROADMAP.md`, and completed implementation records in `docs/devlog/`.
