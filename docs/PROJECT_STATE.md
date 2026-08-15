# os-zapret2-restyle — Current state for `v0.4.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-08-15
State-line scope: **`v0.4.x`**

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md);
- project-development rules: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md);
- chat rules: [`CHAT_RULES.md`](CHAT_RULES.md);
- GitHub rules: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology/proof: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

Current-work state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Repository and package facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.4.1`;
- current source/package revision: `_23` / `PLUGIN_REVISION=23`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_23.pkg` / `v0.4.1_23`;
- `_23` testing-package SHA-256: `37bd4c19bacc48f17aeb4e497c1058e675df067adf2ecd00334708e995bcb283`;
- `_23` source merge/testing-tag target: `3cd3ecc8b9976b1ec8000e2eccfa48f6898d1e73`;
- `_23` exact-head source CI run: `31909623049`;
- `_23` publication workflow run: `31909994148`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_23`;
- internal service key: `zapret`.

Machine `_23` publication evidence: [`verification/evidence/testing-publications/v0.4.1_23.md`](verification/evidence/testing-publications/v0.4.1_23.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- Automatic normal-production Model B/A replay remains removed.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence remains accepted.
- `_14` established explicit Enable QUIC as the sole QUIC candidate execution gate; Stage-30 measured QUIC reachability remains diagnostic only.
- `_15` owner-live QUIC ON observability remains accepted: four attempted QUIC IDs are visible while ordinary QUIC is blocked.
- `_16` Generic UDP browser-to-job path is **OWNER-LIVE PASS** with exact 140-byte payload evidence.
- `_16` Enable QUIC OFF execution semantics are **OWNER-LIVE PASS**: OFF suppresses QUIC candidates while independent UDP remains active.
- already-accessible target is **COMPLETE by owner confirmation**.
- Settings Apply validation/guards and post-Apply service-state correctness are **COMPLETE by owner confirmation**.
- `_21` Laboratory native perimeter/grid and Russian cross-page navigation localization are **OWNER-LIVE PASS**.
- the current Strategy Lab / Laboratory Russian-presentation task is **CLOSED by owner instruction**; GitHub issue `#155` is completed.
- Enable QUIC OFF/default persistence across an actual reload/revisit is still live-pending; `_23` preserves the existing source persistence contract.

Owner-live `_21` presentation evidence: [`verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md).

## `_20` owner-live Laboratory follow-up — historical rejected perimeter/navigation

The owner installed `_20` and directly compared Laboratory, Strategy and a native OPNsense page.

Confirmed defects at `_20`:

- Laboratory had no normal OPNsense outer content perimeter/frame;
- Strategy/native comparison retained the normal platform spacing;
- Russian `Стратегия` / `Лаборатория` was visible while Laboratory was active but reverted to `Strategy` / `Laboratory` after navigating to Strategy.

The accepted `_20` 25% field grid and mode-label typography contract was not the rejected part. The root cause was the redundant Laboratory page wrapper plus `.page-content-main` neutralization, and navigation localization being applied only by Laboratory JavaScript.

Durable evidence: [`verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md).

## `_21` implementation / acceptance status

`_21` is source-merged, published and owner-live accepted for the selected presentation scope:

- Laboratory no longer creates or overrides `.page-content-main`; OPNsense owns the outer page perimeter;
- the two Laboratory sections render as normal `content-box` blocks inside that platform wrapper;
- accepted common `25%` Diagnostics field grid and mode-label computed typography synchronization are retained;
- canonical menu names remain `Strategy` / `Laboratory`, while both Laboratory and Strategy apply deterministic RU/EN labels from the active OPNsense HTML language;
- owner-live verification accepted the corrected native perimeter and `Стратегия` / `Лаборатория` persistence.

Source patch record: [`patches/v0.4.1_21.md`](patches/v0.4.1_21.md).

## `_22` implementation status — Laboratory IPv4 targets + optional Host / SNI

`_22` established the IPv4-first target/runtime architecture:

1. PHP/API and shell target handling accept either a domain or canonical IPv4; IPv6 target input remains deliberately unsupported in this first scope;
2. an IPv4 target exposes an optional `Host / SNI` service-identity field, persisted per job separately from the destination IP;
3. Stage 00 keeps `target_type=ip`; when Host/SNI exists, the endpoint identity is the hostname while the actual destination remains the entered IPv4;
4. Stage 40 skips DNS for IP targets and performs a real TLS 1.3 request pinned to the entered IP; it no longer treats TCP/443 reachability as TLS evidence;
5. the search epoch for IP + Host/SNI binds `endpoint=<service hostname>` to `selected_ip=<entered IPv4>`;
6. Stage-50/60 IP candidate specs remove hostlist target binding because firewall routing is already destination-IP scoped; Model-C ownership/attribution is otherwise unchanged;
7. candidate TLS 1.3/TLS 1.2/HTTP probes use protocol-aware requests against the selected IP; the prior IP plain-TCP candidate shortcut cannot create a false TLS PASS;
8. Generic UDP remains direct-IP and does not require Host/SNI;
9. final IP profiles use `--ipset-ip=<target>` and normal exact three-attempt profile replay;
10. temporary circular browser validation remains domain-only;
11. Model C, budgets, lifecycle lock, cleanup and Stage-90 exact restoration are unchanged.

Source patch record: [`patches/v0.4.1_22.md`](patches/v0.4.1_22.md).

## `_23` implementation / delivery status — truthful result classification

`_23` is exact-head qualified, source-merged and persistently published. It preserves the `_22` target architecture and corrects three owner-live classification defects:

1. authenticated/intercepted HTTP `4xx`/`5xx` is retained as valid DPI-path evidence after exact profile replay, fixed search epoch endpoint success and firewall interception; an application error such as `502` does not erase an otherwise stable finalist at Stage 85;
2. enabled QUIC on bare IPv4 without Host/SNI is short-circuited before candidate execution with `status=skipped`, `reason=host_sni_required`, `tested=[]`;
3. bare-IPv4 `curl` exit `60` is classified as incomplete TLS service identity; an otherwise-empty result becomes `PARTIAL` with explicit Host/SNI guidance instead of false `NO_CANDIDATE`;
4. a later run with Host/SNI clears that missing-identity condition;
5. Generic UDP remains independent and valid for bare IPv4;
6. Model C, fixed search epochs, candidate catalogs, budgets, cleanup and mandatory Stage-90 restoration remain unchanged.

Delivery proof:

- source PR: `#264`;
- exact final source head: `e26156fff27ba3c05bcb91972d2ba47085b1e995`;
- exact-head source CI + FreeBSD-15 qualification: `31909623049`, PASS;
- source squash merge/testing-tag target: `3cd3ecc8b9976b1ec8000e2eccfa48f6898d1e73`;
- tag/release: `v0.4.1_23`;
- package: `os-zapret2-restyle-0.4.1_23.pkg`;
- SHA-256: `37bd4c19bacc48f17aeb4e497c1058e675df067adf2ecd00334708e995bcb283`;
- publication workflow run: `31909994148`;
- stable Pages/pkg repository promoted: no.

The publisher completed FreeBSD build, manifest/digest verification, release publication and release/tag verification. GitHub Actions policy blocked only the final automatic PR-creation step, so publication-record PR `#265` was opened manually from the workflow-created branch; this documentation-only tail does not alter the published package or source identity.

Focused regression: `scripts/test-strategy-lab-truthful-results.sh`, included automatically by the Strategy Lab corrective matrix.

Source patch record: [`patches/v0.4.1_23.md`](patches/v0.4.1_23.md).

## Current verification boundary

Owner-live `_23` verification is now the selected next boundary:

1. `rutracker.net`, Standard: Stage-60/70 stable intercepted evidence survives Stage 85 when the final HTTP application response is `4xx`/`5xx`;
2. `rutracker.org`, Standard: existing successful domain behavior remains unchanged;
3. bare canonical IPv4 with certificate-verification failure ends `PARTIAL` with Host/SNI guidance instead of `NO_CANDIDATE`;
4. IPv4 + real Host/SNI stays pinned to the entered destination IP;
5. final working IP profile contains `--ipset-ip=<entered IPv4>` and exact replay passes;
6. Extended bare IPv4 with QUIC enabled reports QUIC `SKIPPED` / Host-SNI-required with zero tested QUIC candidates while Generic UDP remains independent;
7. Stage 90 restores the exact original Zapret2 state and cleans temporary runtime/rules.

Enable QUIC OFF/default persistence reload/revisit proof remains separate.

## Accepted owner-live evidence retained

- Generic UDP: [`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md)
- QUIC OFF execution/UI follow-up: [`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md)
- `_21` Laboratory frame/localization owner-live pass: [`verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md)

## Documentation authority note

The owner’s latest instruction is current truth. Earlier hypotheses remain historical evidence only and do not override newer controlled owner-live results.

## Current architecture entry points

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md)
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md)

## Current documentation/governance facts

The four canonical general rule books remain `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`. Package-affecting source changes continue through persistent testing publication and the required publication-record tail. `START_HERE.md` owns the exact revision handoff, this file owns current `v0.4.x` facts, and the version-line ledger preserves chronology.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).
