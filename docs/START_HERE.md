# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-16
**Current handoff identity:** stable `v0.5.0` / package `0.5.0_1` released

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.0`;
- `PLUGIN_REVISION=1`;
- current stable Web/pkg release: `v0.5.0`;
- current stable package: `os-zapret2-restyle-0.5.0_1.pkg`;
- package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- release-preparation merge/tag target: `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- exact-head release-preparation CI: `31915884270`, PASS including FreeBSD-15 qualification;
- release trigger: `31916249900`, PASS;
- full release workflow: `31916256043`, PASS;
- GitHub Pages/pkg repository: published from the same release commit.

Full release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted stable product boundary

The completed `v0.4.x` line is now promoted into stable `v0.5.0`.

Accepted owner-live/product facts include:

- Model C is the only normal production Stage-60 runtime;
- Strategy Lab domain and IPv4 targets are complete;
- optional Host/SNI keeps service identity separate from a fixed IPv4 destination;
- fixed-IP final profiles include `--ipset-ip=<target>` and exact replay;
- authenticated/intercepted HTTP `4xx`/`5xx` remains valid DPI-path evidence;
- bare IPv4 TLS identity failure reports `PARTIAL` + Host/SNI guidance;
- bare-IP QUIC without Host/SNI is skipped before execution;
- Host/SNI QUIC performs real fixed-IP hostname-verified attempts;
- Generic UDP remains independent;
- Russian/English Laboratory presentation and native OPNsense layout are accepted;
- selected jobs preserve clean Stage-90 restoration;
- Enable QUIC defaults OFF, is explicit/persisted, and its reload/revisit persistence is owner-live accepted;
- Settings Apply validation/guards and post-Apply service-state correctness remain accepted.

Owner-live evidence:

- [`verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md)
- [`verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md)

## `v0.5.0` publication boundary

The owner-authorized second-component transition is complete:

1. `VERSION` advanced from `0.4.1` to `0.5.0`;
2. `PLUGIN_REVISION` reset from `23` to `1`;
3. the completed `v0.4.x` state was archived and `v0.5.x` initialized;
4. README passed the release review and presents Strategy Lab as the project flagship feature;
5. exact-head project CI and real FreeBSD-15 package qualification passed;
6. release preparation merged exactly as `v0.5.0_1: Prepare release v0.5.0`;
7. immutable semantic tag `v0.5.0` points to that exact merge;
8. stable GitHub Release contains the package and checksum;
9. matching `FreeBSD:15:amd64` GitHub Pages/pkg repository was built and deployed from the same commit.

Release notes: [`releases/v0.5.0.md`](releases/v0.5.0.md).

## Immediate next action

**The `v0.5.0` release is complete. No new engineering scope is selected by this handoff.**

Continue only from the next explicit owner-selected roadmap/backlog item or a fresh concrete defect. Do not reopen accepted Model-C, Laboratory IPv4/Host-SNI, QUIC persistence, BLOB/Lua/discovery, or presentation work without new contradictory evidence or an explicit new scope.
