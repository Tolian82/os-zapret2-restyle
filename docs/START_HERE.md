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
**Current handoff identity:** `v0.5.0_1` full-release preparation

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.0`;
- `PLUGIN_REVISION=1`;
- release candidate: `v0.5.0_1` / `os-zapret2-restyle-0.5.0_1.pkg`;
- target ABI: `FreeBSD:15:amd64`;
- previous stable Web/pkg release: `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- owner-authorized second-component transition: `v0.4.x -> v0.5.x`;
- exact release-preparation merge must use subject `v0.5.0_1: Prepare release v0.5.0`.

The exact current `main` SHA is resolved at execution time under `GH-004`.

## Accepted release basis

The completed `v0.4.x` line is the live-tested runtime basis for `v0.5.0`.

Accepted owner-live product facts include:

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
- **Enable QUIC preference persistence across a real Laboratory reload/revisit is owner-live accepted and closed**.

Owner-live closeout evidence:

- [`verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md)
- [`verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md)

## Release scope

The `v0.5.0_1` release-preparation change is metadata/documentation only. It does not alter the accepted `_23` runtime behavior.

It must:

1. advance `VERSION` from `0.4.1` to `0.5.0`;
2. reset `PLUGIN_REVISION` from `23` to `1`;
3. complete the `v0.4.x` final-state archive and initialize `v0.5.x` current state;
4. complete the README release gate and prominently present Strategy Lab as a primary project feature;
5. pass complete applicable CI and FreeBSD-15 package qualification;
6. merge only the exact verified head with subject `v0.5.0_1: Prepare release v0.5.0`;
7. verify immutable tag `v0.5.0`, stable GitHub Release assets, checksum and the deployed `FreeBSD:15:amd64` Pages/pkg repository.

Release notes: [`releases/v0.5.0.md`](releases/v0.5.0.md).

## Immediate next action

Complete exact-head release qualification, merge the release-preparation PR, then verify the full `v0.5.0` GitHub Release and Web/pkg repository publication. Do not claim the full release complete until the package repository is deployed and the release assets/tag identity are verified.
