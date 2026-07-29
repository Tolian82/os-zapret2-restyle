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
Generic placeholder index
        ↓
Target Mode resolver
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
must not require an SSH-only setup step. Because pkg maintainer scripts must not
start nested pkg transactions while the package database is locked, runtime
bootstrap is performed by the normal configd lifecycle after package installation.
On the first GUI Apply or Start, zapret_service.sh detects a missing dvtws2 binary,
runs setup.sh under the existing lifecycle lock, verifies the binary, and only then
continues service startup. Subsequent starts do not repeat setup while the binary
exists. Start, restart, and reconfigure configd actions allow enough time for the
one-time dependency installation and compilation.
