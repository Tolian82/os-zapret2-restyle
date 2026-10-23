# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.7_21`. `VERSION=0.5.7`, `PLUGIN_REVISION=21`. **Source development candidate; not published or owner-tested.** Previous `v0.5.7_10` testing package remains published but failed owner-installed lifecycle checks. Previous owner authorization for a full Web/pkg release applied to the earlier prepared candidate and remains separately pending from accepted Strategy Lab + bounded GUI fixes. [Release plan](releases/v0.5.7.md) (publishing pending verification). The last owner-accepted installed Stage-6 testing asset was `v0.5.6_17`; the owner also reported installed `v0.5.7_1` during the ECH investigation. **Stage-5 GUI testing package published:** [direct `.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.6_17/os-zapret2-restyle-0.5.6_17.pkg), [publication record](verification/evidence/testing-publications/v0.5.6_17.md), immutable source/tag `b735b0bb55933f0abab007f3165cbb733ceb6d33`, SHA-256 `efc30af18df4104895f17eefec1294d057a7180d2c5e3b900cbca53703295948`. [Project/Voice/FreeBSD15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39779317362); [publisher FreeBSD/manifest/digest/tag validation](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39780767016) PASS. Publisher failed only when GitHub Actions could not create a PR; authorized connector opened [record PR #484](https://github.com/Tolian82/os-zapret2-restyle/pull/484). Owner confirmed `_16` read-only retrieval of `job.OK9Mn5` and `job.jAQJMx`. The owner subsequently [reported that Strategy Lab works as expected](verification/evidence/2026-10-22-v0.5.6_17-owner-gui-acceptance.md) after `_17` delivery: bounded GUI acceptance **PASS (owner report)**. The owner has since **explicitly confirmed F5 and RU/EN PASS** ([updated acceptance record](verification/evidence/2026-10-22-v0.5.6_17-owner-gui-acceptance.md)); copied clipboard bytes, installed pkg hash, negative auto-Apply and raw Stage90 recovery remain individually unverified. Stable `v0.5.6` and Pages/pkg unchanged.

**Release preparation:** bundle [RU/EN Result summary correction](patches/v0.5.6_18.md), [independent upper/lower Strategies Apply indicators](patches/v0.5.6_19.md), verified owner-accepted Strategy Lab Stages 1–6, the [README capability audit](../README.md), star invitation and [lexiforest upstream attribution](../CONTRIBUTORS.md). Pre-release source/FreeBSD CI and full Web/pkg publication must PASS before declaring release success. This is not proof of owner-installed `v0.5.7_1` GUI operation.

## Just completed in source — global ECH-off Chrome policy (`v0.5.7_10`)

Owner-approved on 23 October 2026: the installed Chrome-profile client is used for accessibility testing, not ECH compatibility testing. An owner-live A/B comparison of `rutracker.org` on pinned `104.21.32.39` produced ECH-on timeout and ECH-off verified TLS 1.3 / HTTP/2 301 at ~1.17 seconds. `scripts/run-curl-impersonate.sh` forces `--ech false` after all supplied arguments, covering both Domain Connectivity and Strategy Lab private-client paths. `scripts/test-curl-impersonate-ech-policy.sh` checks the wrapper policy for HTTPS, HTTP3 and attempted caller overrides. Do not claim owner-installed `_10` acceptance; the [testing package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.7_10/os-zapret2-restyle-0.5.7_10.pkg) was built, published and verified in [workflow 39857587580](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39857587580), with an automatic documentation-PR permission failure resolved through the separate publication-record PR. **Pending owner-live acceptance for this defect:** after installing `_10`, test `rutracker.org` in Domain Connectivity and Strategy Lab; verify Stage 40 `TARGET_ACCESSIBLE` and Stage 90 restoration. The existing Additional Resources development priority below remains unchanged.

## Critical owner-installed issue — absent IPFW kernel in 0.5.7_10

23 October 2026 owner evidence: installed `0.5.7_10` had a sealed,
committed shared-Apply owner but a stopped engine/supervisor and *neither*
FreeBSD `ipfw` nor `ipdivert` module loaded; `ipfw -q list` returned
"Protocol not available", exit 71. The prior observer incorrectly called
this "foreign-or-modified-rules"; package PRE-INSTALL could not determine
service state and refused replacement. Source `v0.5.7_18` classifies only
this exact unloaded-kernel case as a stopped committed owner. However, the
OLD installed package PRE-DEINSTALL will still call its old broken status
then Stop when that status returns 2; new PRE-INSTALL explicitly refuses
the unresolved transition until controlled owner-side recovery. This is NOT
a seamless in-place upgrade or a completed owner-live repair. An operator
can subsequently use
a subsequent explicitly requested native Start prepare firewall via the
existing original FD9 lifecycle. It does not reset journals, unload modules,
clear rules or auto-repair the appliance. ECH-off `--ech false` from
`v0.5.7_10` is retained. Source and FreeBSD CI plus owner installed testing
are still required before any new package release.

## Active implementation override — Additional Resources

Stage 4 v0.5.7_18 extends the existing native Stage-60 graph with bounded data-driven, CandidateSpec-normalized TLS fake BIN and reviewed fake+split Lua candidates. The job-local classifier checks actual files, SHA-256, TLS record / Lua export signatures and dependencies. Both cold and warm Stage-60 execution models receive the same graph; the original golden corpus is unchanged. Source tests validate native runtime argument rendering, dynamic add/remove/tamper and pruned/unsupported/missing results; no owner-live execution proof yet. In `_19` the shared job inventory additionally excludes symbolic links (without resolving their targets), so linked Lua/BIN cannot become Stage-60 candidates; focused source regression covers a linked managed BIN and a foreign Lua link. This is source-level protection, not installed OPNsense acceptance. In `_20`, Additional Resources GUI completion uses a per-click 128-bit operation token from POST through configd, launcher and worker to persistent status. A quick job with no observed busy=1 is recognized by its matching terminal receipt; a stale result cannot finish a new click. Installed OPNsense acceptance remains pending. In `_21`, the guarded upstream release transaction discards ONLY the new, incomplete backup when preparation fails before runtime/service mutation; it records setup=failed instead of leaving a false recovery-required snapshot. Existing interrupted rollback evidence is preserved, and interrupted-upgrade recovery remains unimplemented. Chrome ECH-off and cold-IPFW safeguards remain unchanged from _15.


On 22 October 2026 the owner instructed implementation of the approved
[Additional Resources plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md).
The source catalog Stage 1 descriptor/validation foundation is merged at
[`ccdd8fae`](https://github.com/Tolian82/zapret2-extra-resources/commit/ccdd8fae375e9d3fcb2592a803e10a10d52c49f2),
with [catalog CI success](https://github.com/Tolian82/zapret2-extra-resources/actions/runs/39830826402).
The external catalog descriptors remain *data*, not an executable strategy list.
Plugin development through `v0.5.7_9` now includes immutable-commit catalog
verification, managed Lua/BIN transaction/rollback, manually invoked asynchronous
configd backend under setup.lock → original FD9, process-replacement proof,
upstream file-collision/retention guards, and the source-wired bilingual Settings
button directly below Status. It uses explicit POST install/status actions and
finite polling. No automatic resource fetch occurs on pkg/upstream updates,
normal service startup, or page load.

**Acceptance boundary:** The source GUI is **not owner-tested on installed OPNsense**;
neither the native restart nor complete power-failure recovery of the upstream
release transaction has live proof. An interrupted upstream setup leaves a
RECOVERY_REQUIRED snapshot (preserved, not automatically recovered). Strategy Lab
candidate generation is source-wired, but actual installed-host execution remains unverified.
Do not claim that a CI-built package is a released/installed feature.

**Current single next action:** finish source/FreeBSD GUI gate, then validate
manual install, real Stop → Start/PID replacement, errors, F5 and RU/EN on the
owner's OPNsense. Complete bounded upstream recovery, then owner-verify the new Stage-60 TLS Lua/BIN candidates with real jobs,
including Model-C fallback, budgets and unsupported-resource diagnostics.

**Release boundary:** The prior owner-authorized `v0.5.7_1` full release
remains pending its own exact-head publication checks. This new owner-directed
development work does not itself authorize or claim a release.

## Previous task — approved Strategy Lab modernization

The [detailed English development plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) and [requirements](REQUIREMENTS.md) (`BH-01`–`BH-12`) now specify an explicit independent-OR reachability rule: **verified target TLS handshake OR verified target QUIC handshake OR genuine final target HTTP response is sufficient**. An HTTP response counts as accessible, including 4xx/5xx and without requiring a complete body; a separate handshake report is not necessary if the response is genuine. Stages 1–6, Model C, attribution and Stage 90 remain unchanged.

Chrome-default TLS 1.2/1.3 is allowed; HTTP/1.1 and HTTP/2 are equally acceptable. Direct HTTPS success by **either TLS handshake or real HTTPS response** skips QUIC. Forced TLS 1.2 stays in Extended. For every build, fetch the available FreeBSD `latest` package using ugorur's approach, referencing lexiforest; do not pin or select by version. Use one Chrome profile supported by the actual binary. These decisions are settled.

**Stage 1 earlier `_2` evidence:** [CI run 39583956850](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39583956850) qualified the FreeBSD 15 package and ran the actual private binary under FreeBSD 15.0. The [testing prerelease v0.5.6_2](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_2) is tied to source `4166a38d6653e7faa560c86205af25519895e989` and [publication evidence](verification/evidence/testing-publications/v0.5.6_2.md). Its bundled Chrome profile is `chrome150` (upstream `2.2.3_1` was observed, **not pinned**). Owner confirmed `pkg info -x os-zapret2-restyle` -> `os-zapret2-restyle-0.5.6_2` and the read-only check -> `CURL_IMPERSONATE_READY profile=chrome150` on OPNsense on 21 October 2026 ([evidence](verification/evidence/2026-10-21-v0.5.6_2-private-curl-readiness-owner.md)). Network TLS/QUIC handshakes have NOT been reported. Stage 2/3 production probe migration is not implemented. Source audit is not installed OPNsense acceptance. See [PROJECT_STATE](PROJECT_STATE.md).

**Stage 1 `_3` installed evidence:** [FreeBSD15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39588528210), [published testing package](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_3) and [owner-live TLS/QUIC results](verification/evidence/2026-10-21-v0.5.6_3-owner-live-chrome-tls-quic.md): CA PEM `/usr/local/etc/ssl/cert.pem`, `chrome150`, successful certificate-verified HTTP/2 200 for example.com, GitHub, Google and Cloudflare without ECH; real Google `--http3-only` HTTP/3 204; all five `EXIT=0`, `CERT=0`. Cloudflare with ECH previously timed out; no causal blocking claim. The installed `_3` Standard/Model C is unchanged; the `_6` native-lifecycle correction has owner-live Standard and Stage 90 GUI PASS.

## Earlier release-publication handoff (pending, not the current development action)

**Previously requested release task:** Publish authorized full `v0.5.7_1` candidate through the existing exact-subject GitHub release-preparation PR and triggered FreeBSD15 GitHub Release + Pages/pkg deployment, **only after exact-head CI including runtime/lifecycle suites is green**. Verify tag/source/asset/digest/pkg metadata/Web install path; then record actual publication results and close only PRs superseded by the released files. Existing stable `v0.5.6` tag/assets are immutable. Stages 1–6 owner acceptance remains limited to observed `_17` scenarios and does not establish winning blocked-target QUIC candidate. [Release notes](releases/v0.5.7.md).

Previous testing publication boundary: `_17` exact source merge `b735b0bb55933f0abab007f3165cbb733ceb6d33`, [source CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39779317362), [testing asset](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.6_17/os-zapret2-restyle-0.5.6_17.pkg), [record](verification/evidence/testing-publications/v0.5.6_17.md), [publisher package/tag validation](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39780767016) PASS; GitHub Actions permission denied automatic record-PR creation, reconciled through PR #484. Owner-reported bounded `_17` GUI acceptance **PASS** ([record](verification/evidence/2026-10-22-v0.5.6_17-owner-gui-acceptance.md)); F5 and RU/EN owner-reported PASS; clipboard bytes, installed digest and kernel-level recovery are not separately established.

## Minimum stage-specific reading

1. [REQUIREMENTS](REQUIREMENTS.md) — разделы Strategy Lab и `BH-01`–`BH-12`.
2. [Подробный план](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) — текущий Chrome baseline/Stage 40 и границы приёмки этапов 1–6.
3. Для изменения поиска: [основная архитектура](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [adaptive search](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [budgets](architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md).
4. Для Extended/результатов: [QUIC control](architecture/STRATEGY_LAB_QUIC_CONTROL.md), [unified shortlist](architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md), [прежняя live-матрица](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).

## Сохранённые границы

- Полный [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) опубликован из `b319aafe748c1363712f5d7d6cbaaf40396bb64c`; GitHub/FreeBSD15/Pages проверены, установка `0.5.6_1` через GUI владельцем не подтверждена. Это не блокирует документационную работу. [Запись публикации](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md).
- Telegram Voice-исследования закрыты владельцем с отрицательным результатом в его прямом тракте. Новые звонки, STUN/capture, TTL/fake и маршрутные опыты не входят в текущую работу. [Заключение](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).
