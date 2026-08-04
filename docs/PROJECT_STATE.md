# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Version, package revision, delivery stage, verification state, priority, blockers, or
next action changes.

Read after:
`docs/INDEX.md`.

Do not store here:
Detailed decision history, permanent procedures, full architecture, or product
requirements.

==================================================
QUICK CONTEXT
==================================================

Project:
`os-zapret2-restyle`

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Primary branch:
`main`

Current published release:
`v0.3.2`

Current published package:
`os-zapret2-restyle-0.3.2_1.pkg`

Current source/package candidate:
`os-zapret2-restyle-0.3.2_6.pkg`

Current delivery stage:
`DEVELOPMENT`

Patch boundary:
Strategy Lab Patch 4 is an ordinary package patch. `VERSION=0.3.2` remains unchanged
and `PLUGIN_REVISION` advances from `5` to `6`. No tag, GitHub Release, release asset,
or pkg-repository publication is authorized.

==================================================
VERIFIED BASELINE
==================================================

The project owner verified release/package `v0.3.1` /
`os-zapret2-restyle-0.3.1_1.pkg` and confirmed that its functionality works correctly.
DIAG-002 remains resolved and owner live verified.

Strategy Lab delivery baseline:

- Patch 1 merged as `76bd0f0818223e1d3b3d3eebaaaf4c12a59e95da`;
- Patch 2 merged as `962f8de7728477ab8d47c375aec24cb147381c0f`;
- Patch 3 clean replacement PR #53 passed title validation, Validate Project, and the
  FreeBSD package build;
- Patch 3 squash merged as `100f324d09539e672586b12e3cd96c26baf351b2`;
- its task branch was removed and `main` was verified before Patch 4 preparation.

The first Patch 3 delivery attempt, PR #52, was closed without merge because the
branch-hygiene regression test incorrectly required stale `PLUGIN_REVISION=3`. The clean
replacement fixed that test to accept a positive numeric revision and passed completely.

==================================================
CURRENT WORK PACKAGE
==================================================

Strategy Lab — asynchronous replacement of synchronous Diagnostics Blockcheck.

Specialist authority:
`docs/architecture/STRATEGY_LAB.md`

Current patch:
Patch 4 — target initialization, network capability precheck, and clean baseline.

Implemented in the candidate:

- domain and IPv4 target normalization and classification;
- rejection of malformed targets and invalid numeric IPv4-like input;
- explicit required-endpoint lists, including the approved Telegram pair
  `telegram.org` and `web.telegram.org`;
- stage 00 persistence of normalized target type and endpoints;
- concurrent IPv4, IPv6, and fixed QUIC/IPv4 control probes;
- IPv6 eligibility only when a default IPv6 route and control connection both work;
- fixed QUIC precheck against `yandex.ru:443`, ALPN `h3`, two-second operation timeout,
  and classification only from command exit status;
- stage 30 six-second budget independent from individual operation limits;
- clean TLS 1.3 baseline for domain endpoints using explicit GET/curl settings;
- up to two required endpoints under the same baseline stage;
- direct TCP/443 baseline for an IPv4 target without inventing DNS or SNI semantics;
- stage 40 five-second budget independent from individual operation limits;
- `TARGET_ACCESSIBLE` early completion when every required endpoint works cleanly;
- valid negative DNS, IPv4-control, TLS, TCP, and timeout results separated from
  internal `ERROR`;
- exact bilingual progress summaries and mandatory stage 90 restoration.

Patch 4 does not launch a candidate dvtws2, add candidate firewall rules, search any
strategy family, connect the dormant Strategy Lab GUI shell, or replace legacy
Blockcheck.

==================================================
AUTOMATED VERIFICATION
==================================================

Focused mocked coverage passes for:

- target normalization and domain/IP classification;
- Telegram two-endpoint contract;
- IPv4-only with IPv6 unavailable and QUIC closed;
- complete IPv4/IPv6/QUIC capability;
- QUIC result determined only by command status;
- clean TLS 1.3 failure for both required Telegram endpoints;
- directly accessible target and early `TARGET_ACCESSIBLE` result;
- DNS failure as a valid stage-40 failure rather than internal error;
- IPv4-control failure before baseline;
- IPv4 target using TCP/443 with DNS skipped;
- stage-level timeout, final `TIMEOUT`, and successful mandatory restoration;
- all previous lifecycle, cancellation, async-job, API/configd, and legacy-path
  regression contracts.

Owner-assisted OPNsense checks remain deferred until all 13 Strategy Lab patches are
published and fully processed by GitHub.

==================================================
SERIAL DELIVERY STATE
==================================================

Patch 1: COMPLETE

Patch 2: COMPLETE

Patch 3: COMPLETE

Patch 4: IN DELIVERY

Patch 5:
BLOCKED until Patch 4 completes every PR check, squash merge, post-merge workflow,
automatic branch cleanup, `main` verification, branch-absence verification, and all
remaining GitHub processing.

==================================================
NEXT ACTION
==================================================

Publish and completely process Patch 4. Do not prepare Patch 5 before the complete
serial delivery gate for Patch 4 is satisfied.
