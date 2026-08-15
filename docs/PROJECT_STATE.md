# os-zapret2-restyle — Current state for `v0.5.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-08-16
State-line scope: **`v0.5.x`**

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- rule books: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md), [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md), [`CHAT_RULES.md`](CHAT_RULES.md), [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology: [`history/current/v0.5.x.md`](history/current/v0.5.x.md);
- completed `v0.4.x` archive: [`history/archive/v0.4.x.md`](history/archive/v0.4.x.md).

## Repository and release facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version candidate: `0.5.0`;
- package revision: `_1`;
- package candidate: `os-zapret2-restyle-0.5.0_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- release transition is explicitly owner-authorized;
- previous stable Web/pkg release remains `v0.4.1` until the `v0.5.0` release workflow completes;
- internal service key: `zapret`.

## Locked product facts carried into `v0.5.x`

- DNS is working; historical DNS timeout investigation is closed absent fresh evidence.
- Model C is the only normal production Stage-60 Strategy Lab runtime.
- Automatic Model-B/Model-A production fallback remains removed.
- Lua/BLOB/discovery/readiness optimization questions closed by accepted measurements remain closed for the current architecture.
- Strategy Lab supports domains and canonical IPv4 targets; IPv6 Laboratory target input remains deferred.
- IPv4 targets may use separate optional Host/SNI while traffic stays pinned to the entered IP.
- Working fixed-IP profiles use `--ipset-ip=<target>` and exact final replay.
- HTTP application `4xx`/`5xx` does not erase otherwise valid authenticated/intercepted DPI-path evidence.
- Bare-IP TLS identity failure reports `PARTIAL` + Host/SNI guidance.
- Bare-IP QUIC without Host/SNI is skipped before candidate execution; Host/SNI QUIC performs real fixed-IP hostname verification.
- Generic UDP remains independent of Host/SNI and QUIC.
- Enable QUIC is explicit, persisted, defaults OFF, and its reload/revisit persistence is owner-live accepted.
- Strategy Lab cleanup/restoration remains mandatory and selected live jobs preserve exact initial service state.
- Settings Apply validation/guards and post-Apply service-state correctness remain accepted.
- Laboratory native OPNsense layout and RU/EN presentation remain accepted.

## Release basis

`v0.5.0_1` promotes the completed `v0.4.x` feature line; the release-preparation patch changes version/release metadata and documentation only.

Key owner-live evidence:

- [`verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md)
- [`verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md)

Release notes: [`releases/v0.5.0.md`](releases/v0.5.0.md).

## Current boundary

The active boundary is full release qualification/publication for `v0.5.0_1`:

- exact-head complete CI;
- FreeBSD 15 package qualification;
- exact release-preparation squash merge;
- immutable tag `v0.5.0` at that merge;
- stable GitHub Release package/checksum assets;
- matching GitHub Pages `FreeBSD:15:amd64` pkg repository.

No new runtime behavior is part of this transition.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
