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
- active package revision: `_2`;
- package candidate: `os-zapret2-restyle-0.5.0_2.pkg`;
- testing prerelease/tag: `v0.5.0_2`;
- testing source/tag target: `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- testing package SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- testing publication workflow: `31917806438`;
- current stable Web/pkg release/tag remains `v0.5.0`;
- current stable package remains `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable release-preparation merge/tag target: `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- stable full release workflow: `31916256043`, PASS;
- stable GitHub Pages/pkg repository remains the `v0.5.0_1` release repository;
- internal service key: `zapret`.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

Stable release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

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
- The native OPNsense Laboratory layout and deterministic Strategy Lab RU/EN text localization contract remain accepted.
- `v0.5.0` is the stable promotion of the owner-live accepted `v0.4.x` runtime boundary; release preparation introduced no new runtime behavior.

## Completed stable release boundary

The full `v0.5.0_1` release boundary remains complete:

- exact-head project CI and FreeBSD 15 package qualification passed;
- semantic `v0.5.0` tag points to the exact release-preparation merge;
- stable GitHub Release published package and checksum;
- stable Pages/pkg repository was deployed and verified.

Release notes: [`releases/v0.5.0.md`](releases/v0.5.0.md).

## `v0.5.0_2` file-picker localization corrective

Owner GUI evidence after the release exposed one localization leak in Strategy Lab Extended mode: under English OPNsense localization, the visible Generic UDP native file picker showed Russian browser/OS strings (`Выбор файла`, `Не выбран ни один файл`).

The correction is now source-qualified, merged and published as a testing package:

- browser-native file-input chrome is hidden while the real input remains the underlying selection mechanism;
- visible Strategy Lab-owned labels are EN `Choose file` / `No file selected` and RU `Выбрать файл` / `Файл не выбран`;
- the real filename is displayed after selection;
- FileReader/Base64 staging, 1–4096-byte validation, busy-state behavior and Generic UDP API semantics remain unchanged;
- localization regression coverage forbids return of the old visible native file picker;
- source PR `#269` exact final head `4674da5da39a642cf3761662e3599497d68c0522` passed complete applicable CI plus FreeBSD-15 package qualification in run `31917466421`;
- exact squash merge/source target is `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- testing prerelease `v0.5.0_2` contains `os-zapret2-restyle-0.5.0_2.pkg`, SHA-256 `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- stable Pages/pkg repository promoted: **no**.

Publisher run `31917806438` successfully built, verified, published and re-verified the package/tag contract. Its terminal FAILURE is limited to the GitHub Actions account being forbidden from creating the publication-record PR; the generated record branch/file exists and this documentation-only PR completes that required tail.

## Current boundary

Complete the bounded publication-record merge, then perform focused owner-live verification of the RU/EN file-picker presentation and successful filename/file selection path. Do not mark `_2` owner-live accepted until the appliance check is confirmed.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)
