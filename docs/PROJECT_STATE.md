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

Current-work state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Repository and release facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.5.0`;
- package revision: `_1`;
- current stable Web/pkg release/tag: `v0.5.0`;
- current stable package: `os-zapret2-restyle-0.5.0_1.pkg`;
- package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- release-preparation merge/tag target: `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- exact-head pre-merge CI / FreeBSD-15 qualification: `31915884270`, PASS;
- release trigger: `31916249900`, PASS;
- full release workflow: `31916256043`, PASS;
- stable GitHub Release assets: package + `SHA256SUMS`;
- stable GitHub Pages/pkg repository: deployed from release commit `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- internal service key: `zapret`.

Full release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

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
- `v0.5.0` is the stable promotion of the owner-live accepted `v0.4.x` runtime boundary; release preparation introduced no new runtime behavior.

## Release acceptance

The full `v0.5.0_1` release boundary is complete:

- source/metadata/documentation release preparation qualified on the exact PR head;
- FreeBSD 15 package qualification passed;
- exact release-preparation merge completed;
- semantic `v0.5.0` tag points to that merge;
- stable GitHub Release published `os-zapret2-restyle-0.5.0_1.pkg` and `SHA256SUMS`;
- full release package digest is `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- Pages release artifact contains the same package bytes plus `meta.conf`, `data.pkg`, `packagesite.pkg`, `SHA256SUMS`, and `zapret2-restyle.conf`;
- Pages deployment succeeded and GitHub reports the project Pages site public and HTTPS-enforced.

Key owner-live evidence:

- [`verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md)
- [`verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-quic-preference-persistence-owner-live-pass.md)

Release notes: [`releases/v0.5.0.md`](releases/v0.5.0.md).

## Current boundary

**No new development task is selected after the successful `v0.5.0` release.**

The roadmap retains future regression/product directions. The next active boundary is whichever item the owner explicitly selects, or a new concrete defect. Accepted work is not reopened by inertia.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
