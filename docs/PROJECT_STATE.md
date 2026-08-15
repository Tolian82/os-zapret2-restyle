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
- current source candidate: `_23`;
- current packaged revision: `_22` / `PLUGIN_REVISION=22`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_22.pkg` / `v0.4.1_22`;
- `_22` testing-package SHA-256: `07a82529a824b84894541d59c1eabddd56500b5efad9205f6bd9e9e6b4f811d9`;
- `_22` source merge/testing-tag target: `71baa9d0e7cd3e04535ff9b9ba87aefe8f4e8cfe`;
- `_22` publication workflow run: `31903303820`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_22`;
- internal service key: `zapret`.

Machine `_22` publication evidence: [`verification/evidence/testing-publications/v0.4.1_22.md`](verification/evidence/testing-publications/v0.4.1_22.md).

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
- Enable QUIC OFF/default persistence across an actual reload/revisit is still live-pending; `_22` preserves the existing source persistence contract.

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

## `_22` implementation / delivery status — Laboratory IPv4 targets + optional Host / SNI

The owner selected IP-address targets as the next Laboratory product task. The IPv4-first implementation has passed exact-head source qualification, been squash-merged, built under FreeBSD 15, and published as the persistent testing candidate `v0.4.1_22`.

Implemented boundary:

1. PHP/API and shell target handling accept either a domain or canonical IPv4; IPv6 target input remains deliberately unsupported in this first patch;
2. an IPv4 target exposes an optional `Host / SNI` service-identity field, persisted per job separately from the destination IP;
3. Stage 00 keeps `target_type=ip`; when Host/SNI exists, the endpoint identity is the hostname while the actual destination remains the entered IPv4;
4. Stage 40 skips DNS for IP targets and performs a real TLS 1.3 request pinned to the entered IP; it no longer treats TCP/443 reachability as TLS evidence;
5. the search epoch for IP + Host/SNI binds `endpoint=<service hostname>` to `selected_ip=<entered IPv4>`;
6. Stage-50/60 IP candidate specs remove hostlist target binding because firewall routing is already destination-IP scoped; Model-C ownership/attribution is otherwise unchanged;
7. candidate TLS 1.3/TLS 1.2/HTTP probes use protocol-aware requests against the selected IP; the prior IP plain-TCP candidate shortcut cannot create a false TLS PASS;
8. QUIC uses Host/SNI when supplied; bare-IP QUIC is unsupported rather than falsely successful because hostname verification is unavailable;
9. Generic UDP remains direct-IP and does not require Host/SNI;
10. final IP profiles use the existing `--ipset-ip=<target>` selector and normal three-attempt exact profile replay;
11. temporary circular browser validation remains domain-only;
12. Model C, budgets, lifecycle lock, cleanup and Stage-90 exact restoration are unchanged.

Delivery proof:

- source PR: `#262`;
- exact latest source head complete CI + FreeBSD-15 package qualification: PASS;
- exact source squash merge/tag target: `71baa9d0e7cd3e04535ff9b9ba87aefe8f4e8cfe`;
- tag/release: `v0.4.1_22`;
- package: `os-zapret2-restyle-0.4.1_22.pkg`;
- SHA-256: `07a82529a824b84894541d59c1eabddd56500b5efad9205f6bd9e9e6b4f811d9`;
- publication workflow run: `31903303820`;
- stable Pages/pkg repository promoted: no.

The publisher completed package/release verification and machine-evidence creation. GitHub Actions policy blocked only the final automatic PR-creation step, so publication-record PR `#263` was opened manually from the workflow-created branch; this is documentation-only and does not alter the published package or source identity.

Focused regression: `scripts/test-strategy-lab-ip-targets.sh`, included automatically by the existing Strategy Lab corrective matrix.

Source patch record: [`patches/v0.4.1_22.md`](patches/v0.4.1_22.md).

## Current verification boundary

Owner-live `_22` verification is now the selected next boundary:

1. ordinary domain regression after IP support;
2. bare canonical IPv4 accepted with no false TCP-connect → TLS PASS;
3. IPv4 + real Host/SNI pinned to the entered destination IP;
4. final working IP profile contains `--ipset-ip=<entered IPv4>` and exact profile replay passes;
5. Extended Generic UDP works against IPv4 without Host/SNI;
6. QUIC uses Host/SNI when supplied and bare-IP QUIC cannot falsely pass;
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
