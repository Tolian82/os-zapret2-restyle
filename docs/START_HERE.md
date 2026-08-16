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
- active corrective candidate: `v0.5.0_2` / `os-zapret2-restyle-0.5.0_2.pkg`;
- current stable Web/pkg release remains `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable release-preparation merge/tag target: `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- stable full release workflow: `31916256043`, PASS.

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

## Fresh defect selected after `v0.5.0`

The owner supplied direct GUI evidence that in English OPNsense localization the visible browser-native Generic UDP file input still displays Russian browser/OS chrome (`Выбор файла`, `Не выбран ни один файл`).

Root cause: the visible `<input type="file">` delegates its button/empty-selection labels to browser/OS localization, so those labels are not controlled by Strategy Lab's deterministic RU/EN UI localization.

`v0.5.0_2` corrects that boundary without changing Generic UDP upload semantics:

1. keep the real file input as the file-selection owner but hide its browser-native chrome;
2. expose a Laboratory-owned button and selected-filename surface;
3. localize them deterministically from the same active OPNsense HTML language used by the rest of Strategy Lab;
4. English strings: `Choose file` / `No file selected`;
5. Russian strings: `Выбрать файл` / `Файл не выбран`;
6. preserve current file reading, 1–4096-byte validation, Base64 staging, busy-state disabling and Generic UDP request contract;
7. add a regression contract preventing the visible native `form-control` file picker from returning.

## Immediate next action

Qualify the exact `v0.5.0_2` source head with full applicable CI and FreeBSD-15 package build, squash-merge the exact verified head, publish the testing package from the candidate-defining merge, complete the bounded publication-record tail, and then request only the focused owner-live RU/EN visual verification if still needed.

The stable Pages/pkg repository remains on `v0.5.0_1`; this corrective does not silently promote a new stable release.
