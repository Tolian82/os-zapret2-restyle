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
**Current handoff identity:** `v0.5.0_2` Strategy Lab file-picker localization corrective

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.0`;
- `PLUGIN_REVISION=2`;
- testing corrective: `v0.5.0_2` / `os-zapret2-restyle-0.5.0_2.pkg`;
- testing source/tag target: `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- testing package SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- testing publication workflow: `31917806438`;
- current stable Web/pkg release remains `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository remains on `_1`; `_2` did **not** promote it.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

Stable release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted stable product boundary

The completed `v0.4.x` line is promoted into stable `v0.5.0`. Accepted owner-live/product facts remain locked unless fresh evidence contradicts them.

Key facts include:

- Model C is the only normal production Stage-60 runtime;
- Strategy Lab supports domain and canonical IPv4 targets;
- optional Host/SNI keeps service identity separate from a fixed IPv4 destination;
- fixed-IP final profiles include `--ipset-ip=<target>` and exact replay;
- authenticated/intercepted HTTP `4xx`/`5xx` remains valid DPI-path evidence;
- bare IPv4 TLS identity failure reports `PARTIAL` + Host/SNI guidance;
- bare-IP QUIC without Host/SNI is skipped before execution;
- Host/SNI QUIC performs real fixed-IP hostname-verified attempts;
- Generic UDP remains independent;
- Enable QUIC defaults OFF, is explicit/persisted, and its reload/revisit persistence is owner-live accepted;
- Strategy Lab cleanup/restoration remains mandatory;
- Settings Apply validation/guards and post-Apply service-state correctness remain accepted.

## `v0.5.0_2` corrective state

Fresh owner GUI evidence showed that in English OPNsense localization the visible browser-native Generic UDP file input displayed Russian browser/OS chrome (`Выбор файла`, `Не выбран ни один файл`).

The source correction is merged and the testing package is published:

1. the real file input remains the selection owner but its browser-native chrome is hidden;
2. Strategy Lab owns the visible button and selected-filename surface;
3. English strings are `Choose file` / `No file selected`;
4. Russian strings are `Выбрать файл` / `Файл не выбран`;
5. the actual selected filename is shown after selection;
6. FileReader, 1–4096-byte validation, Base64 staging, busy-state disabling and Generic UDP request semantics are unchanged;
7. the regression contract rejects return of the old visible native file picker.

Exact-head source qualification passed in CI run `31917466421`, including the FreeBSD-15 package build. Source PR `#269` squash-merged as `1ae952185dbae80ec34c0a89b441feddbe8b403a`.

Testing prerelease `v0.5.0_2` was then built, manifest-verified and published by workflow `31917806438` with SHA-256 `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`. The workflow's only final failure was the known GitHub Actions policy restriction preventing the bot from opening its documentation PR; package publication and release/tag verification had already passed. This publication-record branch completes that bounded documentation tail manually.

## Immediate next action

Finish the documentation-only publication-record PR, then perform the focused owner-live visual check on OPNsense:

- English: `Choose file` / `No file selected`;
- Russian: `Выбрать файл` / `Файл не выбран`;
- after selection, the real filename is displayed and the Generic UDP file path remains usable.

Do not claim owner-live PASS for this corrective until that focused appliance check is confirmed.
