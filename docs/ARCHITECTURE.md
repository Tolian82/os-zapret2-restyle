# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the system built?

Purpose:
Describe the technical architecture, runtime model, interfaces, and component
responsibilities.

Updated when:
The system architecture or component responsibilities change.

Read after:
DEVELOPMENT_GUIDE.md

Do not store here:
Current task status, decision rationale, roadmap, or development history.

==================================================
REPOSITORY
==================================================

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Branch:
main

Baseline tag:
restyle-start

Development checkout:
/root/os-zapret2-restyle

This repository is the source of truth and is an independent project.

The project originated from zapret by bol-van and an earlier OPNsense plugin
code base by Umur Gorur.

Copyright notices and licenses are preserved in LICENSE and NOTICE.

Current architecture, package identity, repository, releases, documentation,
maintenance, and ongoing development belong to os-zapret2-restyle.

==================================================
HIGH-LEVEL PIPELINE
==================================================

OPNsense configuration
        ↓
Config loader
        ↓
Strategy parser
        ↓
Target Mode resolver
        ↓
Runtime Profile Normalizer
        ↓
Generic placeholder index
        ↓
Target registry and resolver
        ↓
Exclude resolver
        ↓
Blob resolver
        ↓
Port extractor
        ↓
Argument generator
        ↓
Release validator
        ↓
Atomic activation
        ↓
Launcher
        ↓
Firewall
        ↓
Supervisor

==================================================
CONFIRMED GUI-TO-RUNTIME INTERFACES
==================================================

Settings Apply:

/ui/zapret
        ↓
IndexController::indexAction()
        ↓
general.volt
        ↓
/api/zapret/settings/get and /api/zapret/settings/apply
        ↓
OPNsense/Zapret template reload
        ↓
configctl zapret reconfigure
        ↓
zapret_service.sh
        ↓
Backend v2 candidate build, validation, activation, and lifecycle

Diagnostics — domain test:

/ui/zapret/diagnostics
        ↓
IndexController::diagnosticsAction()
        ↓
diagnostics.volt
        ↓
/api/zapret/diagnostics/testdomain
        ↓
configctl zapret testdomain
        ↓
test_domain.sh

Diagnostics — blockcheck:

/ui/zapret/diagnostics
        ↓
IndexController::diagnosticsAction()
        ↓
diagnostics.volt
        ↓
/api/zapret/diagnostics/blockcheck
        ↓
configctl zapret blockcheck
        ↓
blockcheck.sh

Audit classifications and broken-chain details are maintained in AUDIT.md.

==================================================
ENTRY POINTS
==================================================

Service entry point:

src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh

Backend v2 coordinator:

src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh

zapret_service.sh exposes service actions and loads backend modules.

orchestrator.sh coordinates:

- Candidate build.
- Validation.
- Activation.
- Rollback.
- Launcher lifecycle.
- Firewall lifecycle.
- Supervisor lifecycle.

==================================================
BACKEND MODULES
==================================================

common.sh
Shared helpers.

config.sh
Generated configuration and interface resolution.

parser.sh
Traffic Strategy profiles and generic placeholders.

registry.sh
Supported target type and target name registry.

target_mode.sh
Implicit targets for placeholder-free profiles.

profile_normalizer.sh
Expands a parsed profile containing multiple unique HOSTLIST/IPSET selectors into
one runtime profile per selector. User-authored `--new` boundaries remain valid,
non-selector strategy lines are copied unchanged, selector order is preserved, and
normalization is staged before parser output is replaced.

profile_pipeline.sh
Provides the count-carrying adapter contract for parsed-profile preparation. Each
step accepts WORKDIR and PROFILE_COUNT and prints the resulting positive count. The
ordered steps are parse, registry, Target Mode, normalization, and placeholder index.
Specialist modules retain their own focused APIs behind these adapters.

targets.sh
HOSTLIST/IPSET normalization, validation, managed files, and resolution.

exclude.sh
Global domain exclusions.

storage.sh
Logical, staged, and active file mapping.

blobs.sh
Blob resource resolution.

ports.sh
TCP and UDP extraction from strategy filters.

generator.sh
Final dvtws2 argument generation.

validator.sh
Candidate release validation.

atomic.sh
Active runtime switch and restore.

launcher.sh
Single dvtws2 process and startup stability check.

firewall.sh
ipfw lifecycle.

supervisor.sh
Monitor lifecycle.

stage.sh
Execution status reporting.

orchestrator.sh
Lifecycle coordination.

==================================================
COUNT-CARRYING PROFILE PIPELINE
==================================================

The profile collection is prepared through one explicit state transition contract:

```text
profile_pipeline_<step> WORKDIR PROFILE_COUNT [STEP ARGUMENTS...]
    -> resulting PROFILE_COUNT on stdout
```

The parser begins with count `0`; all later steps require a positive count. Steps that
do not change the collection return the incoming count. The normalizer may return a
larger count. Every transition validates the result before the orchestrator continues.

This contract applies only to modules that operate on the parsed profile collection.
Release artifacts, validation, atomic activation, launcher, firewall, and supervisor
retain typed APIs appropriate to their different responsibilities.

==================================================
RUNTIME PROFILE NORMALIZATION
==================================================

The user-facing Traffic Strategy may place multiple target selectors in one
profile. The backend does not require users to duplicate strategy text or insert
extra `--new` separators solely for target isolation.

After parsing and Target Mode processing, `profile_normalizer.sh` applies these
rules:

- zero supported selectors: keep the profile unchanged;
- one unique supported selector: keep the profile unchanged;
- multiple unique supported selectors: clone the profile once per selector;
- each clone contains exactly one unique `HOSTLIST:*` or `IPSET:*` selector;
- every non-selector line, blank line, and line order is preserved;
- selector clones follow first-use order;
- duplicate occurrences of the same selector do not create duplicate profiles.

Only `HOSTLIST:*` and `IPSET:*` are supported selector families. There is no
`GROUP`, `TARGETSET`, or generic future selector family in this architecture.

The normalizer builds a complete staged profile set before replacing parser
output and restores the original set if replacement fails. A second run over an
already normalized set does not change it. The Target Resolver later emits
runtime `--new` separators between all resulting profiles.

==================================================
RUNTIME
==================================================

Engine root:

/usr/local/etc/zapret2

Generated active runtime:

/usr/local/etc/zapret2/runtime-v2

Important generated files:

traffic.conf
extra.conf
dvtws.args
tcp-ports.txt
udp-ports.txt
managed/*

Generated runtime is never committed.

==================================================
SAFE RECONFIGURE
==================================================

build candidate while old runtime works
        ↓
validate candidate
        ↓
failure → old PID, runtime, and ipfw remain unchanged
        ↓
success → controlled switch
        ↓
post-switch failure → restore previous runtime

Regression input:

999.999.999.999

Expected result:

targets|failed

The existing service remains active.

==================================================
TRANSACTIONAL APPLY
==================================================

Important files:

SettingsController.php
ServiceController.php
general.volt
Zapret.xml
targets.sh
orchestrator.sh

The custom Apply flow validates and normalizes before persistent save.

It returns field-specific errors or normalized values.

It then invokes safe reconfigure.

==================================================
PACKAGING INDEPENDENCE
==================================================

No runtime dependency on another OPNsense zapret plugin is allowed.

The repository must contain every project-owned file required to build and
install os-zapret2-restyle on a clean supported OPNsense system.

External zapret2 engine acquisition and build are handled by this project's own
setup and maintenance logic.

==================================================
STABLE TECHNICAL IDENTITIES
==================================================

Project and repository:
os-zapret2-restyle

Installed package:
os-zapret2-restyle

Internal service:
zapret

Configd namespace:
zapret

Version source:
VERSION

The internal service name is intentionally retained for OPNsense integration
stability.

VERSION is the single source of project version information.

Makefile, build-pkg.sh, CI, and release automation must read or validate VERSION
instead of maintaining independent version values.

==================================================
TECHNICAL CONSTRAINTS
==================================================

- FreeBSD /bin/sh compatibility.
- No Bash-only syntax.
- Repository source is authoritative.
- Generated runtime is not source.
- Candidate validation occurs before activation.
- Invalid configuration must not disturb active service state.

==================================================
LIFECYCLE ARCHITECTURE
==================================================

Automatic startup owner:

OPNsense start syshook
        ↓
configctl zapret start
        ↓
configd action
        ↓
zapret_service.sh
        ↓
Backend v2 orchestrator

Runtime activation:

candidate generation
        ↓
validation
        ↓
atomic activation
        ↓
launcher
        ↓
firewall
        ↓
supervisor
        ↓
ready

Shutdown:

supervisor stop
        ↓
firewall removal
        ↓
launcher stop

The rc.d entry point and package lifecycle policy remain under active audit.

Runtime monitoring responsibility:

- launcher owns dvtws2 start, stop, and child PID handling;
- supervisor_loop.sh is the only runtime failure detector;
- supervisor verifies on every monitoring interval that the PID still identifies
  the configured absolute dvtws2 binary before treating the child as healthy;
- supervisor reports failure through runtime-failure and performs no independent
  restart, reconfigure, configuration generation, or repair;
- zapret_service.sh owns lifecycle serialization and cleanup dispatch;
- no separate watchdog process, cron job, or watchdog script is supported.

Supervisor health checks are added only when proven necessary and in separate focused
commits. Removing inherited watchdog code must not be combined with expanding
supervisor behavior.

==================================================
PROJECT GOVERNANCE FLOW
==================================================

AUDIT.md
Findings and Architecture Debt
        ↓
DECISIONS.md
approved behavior for architectural questions
        ↓
implementation and verification
        ↓
AUDIT.md status update
        ↓
PROJECT_STATE.md and DEVLOG.md
current state and completed work
        ↓
CHANGELOG.md when user-visible or release-relevant

Documentation-system changes are architectural changes and follow the same decision,
implementation, verification, and synchronized-commit discipline as code architecture.

==================================================
LIFECYCLE SERIALIZATION
==================================================

All public mutating lifecycle operations converge on
zapret_service.sh and share one FreeBSD lockf-backed mutex:

/var/run/zapret2-lifecycle.lock

Serialized operations:

- start
- stop
- restart
- reconfigure

These commands wait up to 30 seconds for the current lifecycle owner and fail
without changing runtime state when the lock remains busy.

status is read-only and intentionally does not acquire the exclusive lock.

runtime-failure is an internal supervisor callback and uses an immediate
try-lock. When another lifecycle operation already owns the runtime, the callback
is considered stale and exits without queued cleanup. This prevents an old
supervisor callback from removing firewall rules or stopping a replacement
process after reconfigure.

The lock protects the combined mutation boundary, including active and backup
runtime trees, process and supervisor PID files, execution-stage state, and
plugin-owned ipfw rules. Candidate workspaces remain unique but are not treated
as a substitute for lifecycle serialization.


==================================================
PACKAGE DISTRIBUTION AND GUI-FIRST INSTALLATION
==================================================

Public packages are distributed from the project's own FreeBSD pkg repository,
published through GitHub Pages and backed by GitHub Release assets and checksums.
The first repository targets FreeBSD:15:amd64 / supported OPNsense 26.7 systems.
Repository metadata is generated by pkg repo rather than created manually.

A normal user installation must be complete through the OPNsense GUI. The package
must not require an SSH-only setup step. `+POST_INSTALL` registers the plugin and asks
configd to launch the detached package lifecycle worker. The worker waits until the
outer pkg transaction has released the package database before installing dependencies,
downloading upstream zapret2, compiling dvtws2, and recording lifecycle state. Service
Start, Apply, Restart, and Reconfigure never perform package installation or compilation;
they require the package bootstrap to have produced a usable dvtws2 binary.

## Release transport separation

The pkg repository uses the native `pages/${ABI}` layout. GitHub Pages receives the
complete `pages/` tree through the official Pages artifact action, which first
archives it. GitHub Release receives only the flat `release-assets/` directory with
the package and SHA256SUMS. Generic artifact filesystem restrictions therefore do
not alter the public pkg URL contract.


==================================================
PACKAGE LIFECYCLE ARCHITECTURE
==================================================

`setup.sh` is the single internal backend for package-managed engine installation and
removal. It is not a documented user command.

Install path:

1. pkg installs all project-owned files.
2. `+POST_INSTALL` runs `rc.configure_plugins`, reloads configd/templates, and asks
   configd to launch `setup_launcher.sh install`.
3. The launcher detaches the setup worker from the pkg script process tree.
4. The worker waits for the outer pkg transaction to finish, temporarily enables only
   the required FreeBSD package repository, installs and records missing dependencies,
   restores repository configuration, downloads bol-van/zapret, compiles dvtws2, and
   writes `ready` or `failed` lifecycle state.
5. Service Start/Apply only verify that dvtws2 exists; they never bootstrap it.

Removal path:

1. `+PRE_DEINSTALL` synchronously stops the service while service scripts still exist.
2. For a real uninstall, configd starts a detached copied setup worker.
3. The worker waits until pkg has removed the plugin and released its database, then
   removes `/usr/local/etc/zapret2`, runtime state, logs, locks and PID files.
4. The worker attempts to delete only dependencies recorded as installed by this
   plugin. pkg dependency protection is respected; required packages are retained.
5. `+POST_DEINSTALL` and the worker refresh plugin registration/configd after removal.

Upgrade path:

- `PKG_UPGRADE` causes old deinstall hooks to stop the service but skip destructive
  cleanup. The new post-install reruns the idempotent install backend.
- The uninstall worker also rechecks package presence after the outer pkg transaction;
  if the package is present, destructive cleanup is abandoned.
