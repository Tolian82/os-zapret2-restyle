# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules (`DOC-*`):** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules (`DEV-*`):** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules (`CHAT-*`):** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules (`GH-*`):** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-16
**Current handoff identity:** `v0.4.1_23` published testing candidate; Laboratory IPv4 / Host-SNI target support owner-live accepted

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source/package revision: `PLUGIN_REVISION=23` / `v0.4.1_23`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_23.pkg` / `v0.4.1_23`;
- `_23` testing-package SHA-256: `37bd4c19bacc48f17aeb4e497c1058e675df067adf2ecd00334708e995bcb283`;
- `_23` source merge/testing-tag target: `3cd3ecc8b9976b1ec8000e2eccfa48f6898d1e73`;
- `_23` exact-head source CI run: `31909623049`;
- `_23` publication workflow run: `31909994148`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_23`: **no**.

Machine `_23` publication evidence: [`verification/evidence/testing-publications/v0.4.1_23.md`](verification/evidence/testing-publications/v0.4.1_23.md).

Owner-live IPv4 / Host-SNI closeout evidence: [`verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted current live boundary

Do not repeat accepted Model-C, QUIC-ON, QUIC-OFF execution, Generic UDP, already-accessible-target, Settings Apply, `_21` Laboratory presentation, or `_23` Laboratory IPv4 / Host-SNI target-support work without fresh contradictory evidence.

Accepted owner-live/product facts include:

- Generic UDP exact-byte path on `_16` with `udp-140.bin`, port `53`, all three current UDP candidates and truthful no-reply semantics;
- Enable QUIC ON with all four current QUIC candidates visible;
- Enable QUIC OFF execution semantics: OFF suppresses QUIC candidate execution while independent Generic UDP remains active;
- visible Stage-90 restoration on the tested flows;
- already-accessible target is complete by owner confirmation;
- Settings Apply validation/guards and post-Apply service-state correctness are complete by owner confirmation;
- `_21` Laboratory outer frame/perimeter matches normal OPNsense presentation by owner confirmation;
- `_21` Russian `Стратегия` / `Лаборатория` remains localized across Laboratory ↔ Strategy navigation;
- the current Strategy Lab / Laboratory Russian-presentation task is closed by owner instruction; future concrete localization regressions are new defects;
- `_23` ordinary-domain regression is owner-live accepted (`rutracker.net`, `rutracker.org`, plus negative `telegram.org` control);
- `_23` authenticated/intercepted HTTP `4xx`/`5xx` final replay remains valid DPI-path evidence and no longer creates the Stage-85 false negative;
- `_23` bare IPv4 certificate-identity failure truthfully produces `PARTIAL` + Host/SNI guidance;
- `_23` bare IPv4 QUIC without Host/SNI is skipped with zero tested candidates while Generic UDP remains independent;
- `_23` IPv4 + Host/SNI keeps destination fixed to the entered IP, produces `--ipset-ip=<target>` in the exact final profile/replay, and performs real fixed-IP hostname-verified QUIC attempts;
- selected `_23` closeout jobs all preserve clean Stage-90 semantic restoration.

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_23` preserves the existing model-backed default/load/save source contract.

Owner-live `_21` presentation evidence: [`verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md).

## `_20` owner-live UI follow-up — historical rejected perimeter/navigation

The owner installed `_20` and supplied direct screenshots of Laboratory, Strategy and a native OPNsense page.

Confirmed then:

- the `_20` Laboratory page lost the normal OPNsense outer content perimeter/frame;
- Strategy and the native OPNsense comparison page retained the normal platform spacing;
- on Laboratory with Russian OPNsense language the submenu was `Стратегия` / `Лаборатория`;
- after navigating to Strategy the same submenu reverted to English `Strategy` / `Laboratory`.

Root cause was bounded to presentation code: `_20` neutralized `.page-content-main` inside `diagnostics.volt`, affecting the platform-owned wrapper, while deterministic submenu localization existed only on Laboratory and not on Strategy.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md).

## `_21` implementation / acceptance status

`_21` is source-merged, published and owner-live accepted for the selected presentation scope:

- removes the redundant Laboratory page wrapper and all Laboratory `.page-content-main` spacing overrides;
- renders Laboratory content boxes directly inside the platform-owned OPNsense page frame, matching the Strategy/native page structure rather than styling away the platform perimeter;
- preserves the accepted shared `25%` Diagnostics field grid and `Режим:` / `Mode:` typography synchronization;
- makes Strategy apply the same active-language submenu labels as Laboratory, so Russian stays `Стратегия` / `Лаборатория` on both pages and English stays `Strategy` / `Laboratory`;
- keeps Strategy Lab runtime/search, Generic UDP, QUIC, circular and settings semantics unchanged;
- owner-live verification accepted the native perimeter/grid and Russian cross-page menu persistence.

Source patch record: [`patches/v0.4.1_21.md`](patches/v0.4.1_21.md).

## `_22` implementation / delivery status — Laboratory IPv4 targets

`_22` established the IPv4-first Laboratory target architecture:

1. the Laboratory target accepts either a normal domain or a canonical IPv4 address; IPv6 target input remains intentionally deferred;
2. IPv4 targets expose a conditional/optional `Host / SNI` service identity, persisted separately from destination identity;
3. Stage 00 records `target_type=ip`; with Host/SNI the endpoint identity is the hostname while the fixed destination remains the entered IPv4;
4. Stage 40 skips DNS for IPv4 and performs a real TLS 1.3 request pinned to the entered IP; plain TCP connectivity is never accepted as TLS/DPI-bypass proof;
5. the search epoch keeps `endpoint=<service hostname>` and `selected_ip=<entered IPv4>` distinct when Host/SNI is present;
6. Stage-50/60 IP candidates are destination-IP/firewall scoped and do not add hostlist target binding; Model-C attribution and lifecycle ownership remain unchanged;
7. TLS 1.3, TLS 1.2 and HTTP candidate probes use protocol-aware requests against the fixed IP;
8. Generic UDP remains direct-IP and does not require Host/SNI;
9. final IP recommendations use `--ipset-ip=<target>` and normal exact three-pass profile replay;
10. temporary circular browser validation remains domain-only;
11. Model C, budgets, source-port attribution, lifecycle locking, cleanup and exact Stage-90 restoration remain unchanged.

Source patch record: [`patches/v0.4.1_22.md`](patches/v0.4.1_22.md).

## `_23` implementation / owner-live acceptance status

`_23` preserves the `_22` domain/IPv4 architecture and corrects the three owner-live result-classification problems found while qualifying `_22`:

- authenticated/intercepted HTTP `4xx`/`5xx` remains valid DPI-path evidence after exact profile replay, fixed-epoch endpoint success and firewall interception, so an application-layer error such as `502` no longer erases an otherwise stable finalist at Stage 85;
- bare-IPv4 QUIC without Host/SNI is skipped before candidate execution and reports `host_sni_required` with zero tested QUIC candidates rather than presenting non-executed candidates as tested;
- bare-IPv4 TLS certificate verification failure (`curl` exit `60`) is treated as incomplete HTTPS service identity; an otherwise-empty terminal result becomes `PARTIAL` with explicit Host/SNI guidance rather than a misleading `NO_CANDIDATE`;
- Generic UDP remains independent and valid for bare IPv4;
- Model C, search epochs, candidate catalogs, budgets, lifecycle cleanup and mandatory Stage-90 restoration are unchanged.

Delivery proof:

- source PR: `#264`;
- exact final source head: `e26156fff27ba3c05bcb91972d2ba47085b1e995`;
- exact-head complete source CI + FreeBSD-15 qualification: run `31909623049`, PASS;
- source squash merge/testing-tag target: `3cd3ecc8b9976b1ec8000e2eccfa48f6898d1e73`;
- tag/release: `v0.4.1_23`;
- package: `os-zapret2-restyle-0.4.1_23.pkg`;
- SHA-256: `37bd4c19bacc48f17aeb4e497c1058e675df067adf2ecd00334708e995bcb283`;
- publication workflow run: `31909994148`;
- stable Pages/pkg repository promoted: no.

Owner-live closeout on the exact published `_23` package is **PASS**. The accepted closeout jobs prove the `rutracker.net` HTTP-502 classifier correction, ordinary-domain regression, bare-IP PARTIAL identity guidance, bare-IP QUIC skip with Generic UDP independence, IPv4 + Host/SNI fixed-destination behavior, final `--ipset-ip=` exact replay, real Host/SNI QUIC execution, and clean Stage-90 restoration.

Owner-live closeout evidence: [`verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md`](verification/evidence/2026-08-16-v0.4.1_23-ipv4-host-sni-owner-live-pass.md).

The publisher completed FreeBSD build, manifest/digest verification, release publication and release/tag verification. GitHub Actions policy blocked only automatic publication-record PR creation, so publication-record PR `#265` was opened manually from the workflow-created branch; this is documentation-only and does not alter the package or source identity.

Source patch record: [`patches/v0.4.1_23.md`](patches/v0.4.1_23.md).

## Immediate next boundary

**Laboratory IPv4 / Host-SNI target support is complete.** Do not repeat its owner-live matrix without fresh contradictory evidence.

The next selected live boundary is the already-pending **Enable QUIC OFF/default persistence across an actual Laboratory page reload/revisit**. Verify that the persisted setting survives a real reload/revisit and that OFF still suppresses QUIC candidate execution after the reload. Treat any failure as a new bounded defect; otherwise close that backlog row without changing package source.

IPv6 target input remains intentionally deferred as a separate future scope. Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
