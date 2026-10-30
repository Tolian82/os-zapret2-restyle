# Dual-stack IPv4/IPv6 and Exclude IPSet — staged, per-file development plan

**Primary specification:** [ZAPRET2_EXCLUDE_IPSET_SPEC.md](ZAPRET2_EXCLUDE_IPSET_SPEC.md) (`DS-EXCLUDE-2026-10-28`).
**Status:** Owner-approved **first-priority current execution plan**. Stage 1 (`v0.6.1_1`) is merged and passed applicable source/CI/FreeBSD 15 package-build gates. **Stage 2 `v0.6.1_2` source/CI gate is CLOSED**; [PR #683](https://github.com/Tolian82/os-zapret2-restyle/pull/683) passed the [Project/Voice/FreeBSD 15 checks](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40653479292), was merged as [21f564d](https://github.com/Tolian82/os-zapret2-restyle/commit/21f564d64d70480dfd66c4c6229cdca53878c6ef) and passed post-merge main CI. **Stage 3 `v0.6.1_3` source/CI gate is CLOSED** ([PR #685](https://github.com/Tolian82/os-zapret2-restyle/pull/685), [Project/Voice/FreeBSD 15 CI attempt 2 PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40657793778), [merged main 2b5f102](https://github.com/Tolian82/os-zapret2-restyle/commit/2b5f1029bf53b74b9526b62aecf243eb456c246d), [post-merge main CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40659404426)). **Stage 4 is next**. Stages 4–8 are not yet implemented. Stage 0 was documentation publication.
**Published baseline:** stable `v0.6.0` (`0.6.0_1` package). Current testing-only package published: `VERSION=0.6.1`, `PLUGIN_REVISION=9`, [exact FreeBSD15 asset](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.1_9/os-zapret2-restyle-0.6.1_9.pkg). Source/FreeBSD CI and post-merge main CI PASS; owner-installed `_9` GUI and native IPv6/exclusion remain OPEN. Stages 1–5 have qualified source gates; **Stage 5 installed hardware gate remains OPEN**.
**Release/version policy:** The owner started implementation, so Stage 1 opens `v0.6.1_1` under `DEV-034`. Later packaged-source patches increment `PLUGIN_REVISION`; any stable full release still requires separate explicit owner approval.

## 0. Execution rules and scope

- Row markers: **CHANGE** = source modification required when that stage executes; **NEW** = create; **REVIEW** = inspect and modify only for demonstrated need; **BOUNDARY** = regression check, no expected edit; **DOC** = reconcile current documented facts. Every path is repository-root relative.
- Only existing Voice IPSETs/STUN profiles become dual-stack. New Voice page `UDP ports` fields, shared Voice IPv6 checkbox, destination-any P2P path, P2P IPFW rules and media classifier expansion are **deferred** in [DECISIONS.md](../DECISIONS.md), not part of stages 1–8.
- **Ban explicit and effective full-family `/0` in every user-supplied include/exclude list**, including all Voice IPSETs; no implicit `any` for an empty enabled service. Internal analytic wildcard for a hostless native profile is not an IPSET.
- One batch Python IPSET compiler per candidate; prepared immutable manifest and hashes reused downstream. Native Config, shared Apply, `zapret` service, FD9 and IPFW rule owner remain unique. Separate trust-boundary checks are required, never a second address-parser policy.
- **Owner-approved forward-only test stand (29 October; [DEV-050](../PROJECT_PRINCIPLES.md)):** Only the current approved implementation runs. Remove obsolete sealed-owner/layout compatibility, fallback branches, unused old wrappers and obsolete old-version tests as part of their corresponding source fix. Do not expand the acceptance matrix with legacy automatic-upgrade/reversion cases. GitHub history is for product-level reversal; keep current-transaction Config/IPFW cleanup and ownership safeguards.
- **Scope cancellation (30 October 2026):** Python interpreter/runtime unification is explicitly **CANCELLED within stages 0–8 and this per-file plan**, not deferred as a task within them. Do not introduce a common Python resolver or broad path/shebang/configd/PHP refactor as a dependency or extra stage. A future implementation needs a separate owner-approved technical specification and plan after the Exclude IPSet/IPv4/IPv6 work. Keep the already-approved Python IPSET semantic compiler and fix proven, feature-local defects as necessary; [DEV-052](../PROJECT_PRINCIPLES.md) remains a general principle, not authorization for the cancelled work.
- At every stage: exact current `main`, scoped regression scenarios, rapid local syntax/contract verification **before** long CI, full appropriate CI/FreeBSD gates, native installed proof where required, and truthful **same-operation** cleanup/restoration evidence. Source PASS, CI/package PASS and owner-installed OPNsense PASS are distinct.

## Stage 0. Approve baseline, authoritative docs and current task priority

**Outcome:** Publish the approved specification and this executable per-file plan. Reconcile only active authority and priority; do not claim that implementation is done.

| Scope | File | Planned change or check |
|---|---|---|
| NEW | `docs/architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md` | Create authoritative current dual-stack and global Exclude IPSet specification, banning `/0` in all user IP lists and deferring Voice/P2P redesign. |
| NEW | `docs/architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md` | Create detailed stage-by-stage per-file engineering plan, entry/exit gates, regression and installed evidence. |
| DOC | `docs/START_HERE.md` | Make this task the single next action at the unchanged `v0.6.0_1` handoff; link both documents. |
| DOC | `docs/PROJECT_STATE.md` | Mark the newly owner-approved task as first priority; distinguish not-yet-implemented target behavior from published code. |
| DOC | `docs/ROADMAP.md` | Place dual-stack/Exclude IPSet first in the master roadmap; link the specification and plan without duplicating their detail. |
| DOC | `docs/INDEX.md` | Add a prominent Level-2 navigation group for the two current documents. |
| DOC | `docs/REQUIREMENTS.md` | Reconcile active Targets/Voice/Lab requirements and remove superseded IPv4-only prospective language; keep actual implementation status clear. |
| DOC | `docs/DECISIONS.md` | Append the owner's final universal `/0` prohibition and current-priority decision; retain deferred Voice/P2P discussions as history. |
| BOUNDARY | `AGENTS.md` | Read as mandatory bootstrap; no change to the general rule map. |
| BOUNDARY | `docs/DOCUMENTATION_RULES.md` | Follow existing DOC rules, especially DOC-024, DOC-031, DOC-053, DOC-055; do not invent a fifth rule book. |
| BOUNDARY | `docs/PROJECT_PRINCIPLES.md` | Apply DEV owner-canon, one-owner, evidence and version semantics; do not edit rule canon. |
| BOUNDARY | `docs/CHAT_RULES.md` | Follow owner request, persistence and truthful verification conventions; no rule changes. |
| BOUNDARY | `docs/GITHUB_PUBLICATION.md` | Follow GitHub docs-only PR/CI/merge, exact-head and release constraints; no rule change. |
| REVIEW | `docs/ARCHITECTURE.md` | Inspect architecture summary for contradictory current claims; update only on a verified inconsistency. |
| DOC | `docs/architecture/VOICE_TRANSMISSION_GUI.md` | Reconcile current Voice architecture with pending dual-stack target, preserving known IPv4 baseline and deferred P2P UI. |
| REVIEW | `docs/architecture/STRATEGY_LAB.md` | Inspect Lab design for IPv6 limitation, keep unimplemented work explicitly pending. |
| BOUNDARY | `docs/architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md` | Read historical Remove exclusions as its own scope; preserve its existing implementation behavior. |
| BOUNDARY | `docs/architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md` | Read historical Remove implementation plan, avoid creating duplicate Config/compiler/runtime owner. |
| DOC | `docs/history/current/v0.6.x.md` | Record chronological doc-approval and later stage evidence, not a parallel source of truth. |
| BOUNDARY | `docs/history/archive/v0.5.x.md` | Preserve the archived v0.5.x snapshot without retroactive rewrites. |
| BOUNDARY | `docs/releases/v0.6.0.md` | Preserve published stable v0.6.0 release notes and immutable package identity. |

**Exit gate 0:** Both docs are linked from active handoff/state/roadmap/navigation; `DECISIONS` retains history; docs links and rule contracts pass CI. `VERSION` and `PLUGIN_REVISION` unchanged. No feature PASS claimed.

## Stage 1. One Python IPSET compiler and immutable manifest

**Outcome:** Establish canonical, deterministic dual-stack IP semantics and artifact ownership before changing user-facing or live firewall behavior.

| Scope | File | Planned change or check |
|---|---|---|
| NEW | `src/opnsense/scripts/OPNsense/Zapret/backend/ipset_policy.py` | Create sole bounded batch IPv4/IPv6 IPSET compiler and versioned manifest; collapse excludes, reject explicit/effective `/0` independently per include/exclude list, preserve family separation. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/targets.sh` | Replace inline IPv4 normalizer with one batch call from targets_prepare_managed; retain a shell wrapper only while a verified current caller exists; never a separate parser. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/storage.sh` | Check whether existing managed storage catalog needs to register the extra exclude output; no second storage authority. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/registry.sh` | Check named IPSET placeholder registrations, adding only an actually required generic mapping. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/target_mode.sh` | Verify Target Mode `all/list/auto` still works with dual-stack and no global-exclude bypass. |
| NEW | `scripts/test-ipset-policy.py` | Add pure tests for IPv4/IPv6/`::`/host CIDRs, malformed/zone/host bits, exclude collapse, full-family `/0` and `/1`-pair rejection for every user list, deterministic digests. |
| CHANGE | `scripts/test-voice-targets-integration.py` | Cover existing Voice-target formats and candidate-to-managed output compatibility. |

**Generated runtime artifacts (not tracked source):** `<candidate-release>/managed/ipset-telegram.txt`, `ipset-discord.txt`, `ipset-x.txt`, `ipset-sip.txt`, `ipset-custom.txt`, new `ipset-exclude.txt`, plus `<candidate-release>/ipset-manifest.json`. The manifest is an immutable candidate witness, not a Config owner or mutable second cache.

**Stage 1 source gate CLOSED (28 October 2026):** [PR #681](https://github.com/Tolian82/os-zapret2-restyle/pull/681) merged as [merged main 02fa191](https://github.com/Tolian82/os-zapret2-restyle/commit/02fa191436da2d22100ba20c0ac236d8ff531a72). [successful source/FreeBSD CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40648449795) passed the project, Voice, real shared Targets and FreeBSD 15 package-build checks, including all six lists' `/0` and complementary `/1` cases; [post-merge main CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40649565509) also passed. Earlier eight local Python tests and reconstructed shell checks remain distinct narrower evidence. Installed OPNsense IPv6 or active exclusion is **not** claimed here.

**Exit gate 1: SOURCE/CI PASS.** One real Targets batch per candidate, original IPv4 compatibility, deterministic mixed-family manifest and explicit/effective `/0` refusal passed on the exact head. Installed OPNsense evidence is a separate later-stage gate.

## Stage 2. OPNsense model, GUI, native Config and persisted inputs

**Outcome:** Add the single new field, migrate existing IP inputs safely and keep standard native OPNsense persistence and concurrency.

| Scope | File | Planned change or check |
|---|---|---|
| CHANGE | `src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml` | Add hostlist.excludeipset TextField and dual-stack field constraints; reject `/0` in every include/exclude IPSET without adding Voice controls. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/general.xml` | Insert `Exclude IPSet` immediately after `Exclude Domains` in ordinary/Advanced Strategies; bilingual help and updated shared Telegram IPSET text. |
| REVIEW | `src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt` | Inspect rendered Strategies GUI, field errors, localizations, persistence and F5; change Volt only for a demonstrated gap. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/voice.xml` | Change help text for existing five Voice IPSET fields to IPv4/IPv6 and full-family ban; preserve every field and checkbox. |
| CHANGE | `src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt` | Update RU/EN Voice help, errors and read-only IPv6 status handling, preserving all layout and shared Apply controls. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php` | Add new Strategies field to allowed payload; replace authoritative PHP IPv4 normalization with Python candidate results, retaining size/error safety. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategySettingsPayload.php` | Allow `excludeipset` only in Strategies scope; preserve shared Telegram optimistic concurrency. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateXml.php` | Keep new field in Strategies-owned detached XML and outside Voice-editable fields; preserve entire candidate snapshot. |
| REVIEW | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceSettingsPayload.php` | Audit Voice-only whitelist for lossless IPv6 colons and no unintended Exclude editing. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceApplyCandidate.php` | Remove independent VoiceApplyCandidate IPv4 parsing; reuse prepared candidate semantics and preserve changed-fields/draft guards. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateValidator.php` | Remove authoritative PHP Voice IPv4 network/overlap parsing; delegate IP semantics to the one Python compiler, retaining structural/argument validation and field errors. |
| BOUNDARY | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceModelValues.php` | Check existing scalar/textarea extraction is already IPv6-safe; no new model-value storage. |
| REVIEW | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceController.php` | Audit Voice API for IPv4-only assumption; keep shared concurrency and native Apply. |
| BOUNDARY | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceSettingsSnapshot.php` | Check snapshot includes the relevant shared hostlist scope; no second digest store. |
| BOUNDARY | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php` | Preserve common prepareStrategies/prepareVoice/mergeForCommit and single writer; adjust only proven whitelist/validation gap. |
| BOUNDARY | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php` | Preserve bounded payload envelope and size limits; test large mixed-family lists. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php` | Verify root-side detached candidate, errors, old saved Config and single compilation witness. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php` | Verify saved-model preflight, uncertainty handling, and exactly one native Config write. |
| BOUNDARY | `src/opnsense/scripts/OPNsense/Zapret/apply_settings.php` | Preserve SharedConfigCommit::persist, readback and uncertain-save safeguards. |
| CHANGE | `src/opnsense/service/templates/OPNsense/Zapret/zapret.conf` | Render EXCLUDE_IPSET through existing zapret.conf template; absent old saved node maps to empty value. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_native_saved_pair_guard.py` | Include EXCLUDE_IPSET in saved XML/template pair guard, comparing values without reparsing raw IP. |
| BOUNDARY | `src/opnsense/scripts/OPNsense/Zapret/backend/shared_apply_render.py` | Verify existing detached render/targets mapping; do not add a second template engine. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/config.sh` | Check config_load EXCLUDE_IPSET and logical WAN resolution; preserve existing loader. |
| BOUNDARY | `src/opnsense/service/templates/OPNsense/Zapret/+TARGETS` | Do not add a new global OPNsense renderer target for staged runtime IPSET; audit template surface only. |
| BOUNDARY | `src/opnsense/service/templates/OPNsense/Zapret/hostlist.txt` | Keep hostlist.txt domain-only and independent of address families. |
| BOUNDARY | `src/opnsense/service/templates/OPNsense/Zapret/hostlist-exclude.txt` | Keep hostlist-exclude.txt domain-only; no DNS-to-IP transformation. |
| CHANGE | `scripts/test-strategy-voice-settings-scope.php` | Test cross-page edit isolation, new Strategies field and Voice shared target protection. |
| CHANGE | `scripts/test-shared-apply-request.php` | Test native candidate/envelope and stale editor prevention. |
| CHANGE | `scripts/test-shared-apply-config.php` | Test single persist/readback, unchanged apply and old/new IPv4/IPv6 values. |
| CHANGE | `scripts/test-voice-candidate-xml.php` | Test detached XML new field in correct scope, with Voice retaining existing fields. |
| CHANGE | `scripts/test-voice-native-config-commit.php` | Test saved model/digest and single writer under native Config. |
| CHANGE | `scripts/test-voice-settings-payload.php` | Test Voice IPv6 input accepted without permitting unrelated fields. |
| CHANGE | `scripts/test-voice-apply-candidate.php` | Test Voice draft/Apply with IPv6 and snapshot equality. |
| CHANGE | `scripts/test-voice-candidate-validator.php` | Test Voice preflight IPv6/CIDR and full-family rejection, accurate field and line failures. |
| REVIEW | `scripts/test-voice-draft-selection.php` | Verify disabled Voice draft with IPv6 is not activated on separate Strategies Apply. |
| REVIEW | `scripts/test-voice-inspect-config-runtime.php` | Check read-only Voice inspect reflects saved dual-stack configuration and true runtime. |
| REVIEW | `scripts/test-voice-ui-route.php` | Regression-test opening the Voice page, help and unchanged route structure. |
| CHANGE | `scripts/test-voice-api-concurrency.php` | Exercise cross-tab Strategies/Voice races when Exclude and shared IPSET change. |
| CHANGE | `scripts/test-shared-apply-render.py` | Test existing native template rendering and new EXCLUDE_IPSET block. |
| REVIEW | `scripts/test-voice-gui-contract.py` | Check Voice GUI original structure, bilingual IPv6 help, F5 and `/0` rejection; no P2P controls. |

**Stage 2 source gate CLOSED (28 October 2026):** Model, Strategies-owned GUI Exclude IPSet, unchanged Voice GUI structure, F5 localization, detached XML/native renderer, saved Config witness, shared Python IP grammar, cross-page optimistic concurrency and applicable candidate tests passed CI at the exact PR head. Original common Apply and single writer are preserved. Live installed GUI/IPv6 Voice and working `--ipset-exclude` profile behavior are **not** proven by Stage 2; attach exclusions at Stage 3.

**Exit gate 2:** GUI/Config and native candidate validation preserve original writer and no-op semantics, proper cross-page ownership, IPv6 text, localized errors and disabled Voice drafts.

## Stage 3. Targets/Exclude generation and final profile argv policy

**Outcome:** Make the global IP exclusion effective in every compiled profile while keeping domain-only exclusions out of Voice/STUN.

| Scope | File | Planned change or check |
|---|---|---|
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/exclude.sh` | Preserve domain exclude_prepare; stage ipset-exclude via common compiler only, no DNS/TTL or alternate settings. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh` | Integrate manifest, staged paths, Voice/Strategies profiles and final sealing through existing orchestrator pipeline. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/generator.sh` | Attach --ipset-exclude to every executable profile; attach --hostlist-exclude only to applicable ordinary domain-aware Strategies; handle --new/template/import/Extra, never Voice/STUN. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/parser.sh` | Audit named --new, templates, native --ipset-ip and externally referenced --ipset for a `/0` policy bypass; edit parser only if proved necessary. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/profile_pipeline.sh` | Preserve count-carrying profile pipeline; add one global-exclusion overlay step before final sealing only if needed. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/profile_normalizer.sh` | Check normalized copies of placeholders inherit mandatory exclusions without mutating user strategy text. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/ports.sh` | Preserve TCP/UDP port semantics; check source-port handling does not regress under dual-stack. |
| BOUNDARY | `src/opnsense/scripts/OPNsense/Zapret/backend/blobs.sh` | Retain dynamic Lua/BIN/blob behavior without unrelated changes. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/storage.sh` | Check source-to-active mapped path and digest for new managed exclusion output. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/target_mode.sh` | Verify Target Mode `all/list/auto` cannot erase required global exclusions. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/registry.sh` | Check registry does not publish global exclusions as a user inclusion placeholder. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/validator.sh` | Validate exclude references and mapped/native dry-run, symlink/mode/path/hash safety and native inline/file IP list `/0` bypass prevention. |
| CHANGE | `scripts/test-profile-normalizer.sh` | Test multiple profiles and target placeholder normalization with excludes. |
| CHANGE | `scripts/test-profile-pipeline.sh` | Test pipeline ordering, profile counts, named --new and mandatory excludes. |
| CHANGE | `scripts/test-voice-engine-private-dryrun.py` | Test installed-engine-style mapped private dry-run with excluded targets. |
| NEW | `scripts/test-global-exclusions.py` | Add global exclusion tests for first/middle/last profiles, new/template/import/Extra, Host/SNI, inline IPSETs, user `/0` ban, domain isolation and Voice/STUN without hostlist exclude. |
| CHANGE | `scripts/test-voice-common-runtime.py` | Test one complete shared Voice/Strategies argv and global exclusions. |

**Stage 3 source gate CLOSED (28 October 2026):** A final-profile overlay for every ordinary/Voice profile, template/import/Extra/`--new` and native IPSet file/inline guards, the release-local argv hash witness and original Voice/IPFW binding passed CI. The first identical-head Project attempt had a Strategy Lab Stage90 simulator recovery failure; rerun attempt 2 passed all Project/Voice/FreeBSD15 checks without code or test relaxation. Installed OPNsense operational profile exclusion, actual packet treatment, mixed-family IPFW and rollback remain separate acceptance requirements; Stage 4 and Stage 5 follow.

**Exit gate 3:** Prove no `--hostlist-exclude` in any Voice/STUN profile; all applicable ordinary domain profiles get domain exclusion; every executable profile honors global `--ipset-exclude` after template/import/extra resolution.

## Stage 4. Existing Voice dual-stack compilation, overlap and proof

**Outcome:** Migrate the five existing destination-IPSET Voice profiles to IPv4/IPv6 with unchanged STUN-only behavior and one process.

| Scope | File | Planned change or check |
|---|---|---|
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_profile_compiler.py` | Consume prepared dual-stack IPSET without independent IPv4 parsing; use --filter-l3=ipv4,ipv6, preserve existing STUN/UDP args and final profile hash. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_capture_plan.py` | Generate mixed-family destination-scoped capture plan; compare UDP intervals and networks by family, reject `/0` and empty-to-any. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_traffic_merge.py` | Verify ordinary STUN vs Voice overlaps using correct family, ports and first-match order; analytic internal wildcard is not a user IPSET. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_release_stage.py` | Bind staged Voice release to prepared manifest, actual managed contents, saved-Config witness and final profile digest. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_model_export.py` | Check XML export passes both address families intact for all five services. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_native_saved_pair_guard.py` | Check updated EXCLUDE_IPSET saved-pair witness, without a second parse. |
| CHANGE | `scripts/test-voice-capture-plan.py` | Test mixed-family Voice capture, `/0` and complementary `/1` rejection, same-family port collisions, and absence of mutation. |
| CHANGE | `scripts/test-voice-model-export.py` | Test saved XML Voice export with IPv6, enabled/OFF drafts. |
| CHANGE | `scripts/test-voice-targets-integration.py` | Test compiled candidate → managed IPSET → profile exact contents/digests without independent reparse. |
| CHANGE | `scripts/test-voice-common-runtime.py` | Test real shared Voice+ordinary profiles, final order, hashes and exclusions. |
| CHANGE | `scripts/test-voice-firewall-transaction.py` | Test capture-plan compatibility with firewall transaction and injected failures. |
| NEW | `scripts/test-voice-dualstack-ipset-boundaries.py` | Add specific five-Service boundary tests: IPv4/IPv6 accepted, all `/0` and complementary `/1` rejected; existing IPSET-only `--filter-udp=*`, no P2P rule and no Exclude Domains in Voice. |

**Stage 4 source gate CLOSED (28 October 2026):** [Stage 4 PR #687](https://github.com/Tolian82/os-zapret2-restyle/pull/687), [Project/Voice/FreeBSD15 PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40663744195), [merged main 467886e](https://github.com/Tolian82/os-zapret2-restyle/commit/467886e843f7ebd2b46dbc4e9cc2abf4bf342688), [post-merge main CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40665278981). Existing five Voice STUN IPSETs compile through the one six-list semantic compiler and strict manifest; same-family scope/collision, saved XML, shared native argv and fault-injection tests passed. **Do not assert installed FreeBSD15 IPv6 IPFW/table/divert or real packet success**: Stage 5 is the next mandatory gate.

**Exit gate 4:** Existing Voice `--filter-l3=ipv4,ipv6` matches final IPSET/argv/IPFW candidate; same-family conflicts detected and all user `/0` bypass forms rejected before mutation. No P2P changes.

## Stage 5. Native FreeBSD 15 IPFW mixed-family capture and rollback

**Outcome:** Qualify mixed-family real IPFW tables/rules and exact rollback on FreeBSD 15 without new P2P capture.

| Scope | File | Planned change or check |
|---|---|---|
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_ipfw_adapter.py` | Extend existing IPFW adapter for mixed-family type addr tables and canonical readback/staging/rollback; verify final l3/hash and forbid user `/0` entries. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_firewall_transaction.py` | Remove hardcoded IPv4Network from transaction manifest/table validation; reuse attested mixed-family IPSET and preserve foreign-owner/rollback safeguards. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/backend/voice_capture_plan.py` | Align mixed IPv4/IPv6 destination-table capture with the original rule range and divert guards; never add port-only destination-any P2P. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh` | Check existing ordinary TCP/UDP/Voice IPv6 divert and WAN guards; modify only after proven defect. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` | Preserve boot/start/stop/reconfigure root FD9 and one engine; fix verified IPv4-only assumption only. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh` | Verify final runtime/capture ordering and current transaction's pre-activation state on failed activation, without old-version fallback. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/backend/validator.sh` | Check family/WAN/mode/argv path validation and dry-run behavior for both IP families. |
| CHANGE | `scripts/test-voice-firewall-transaction.py` | Test mixed table staging/swap/revert, foreign entries, injected failures and exact ownership guards. |
| NEW | `scripts/test-dualstack-ipfw.py` | Add FreeBSD fixture/live IPFW tests: IPv4+IPv6 tables, banned user `/0`/`/1` union, legacy ports, counters, reinjection and rollback; no P2P capture. |
| CHANGE | `scripts/test-config-activation-contract.sh` | Preserve root locking, saved Config, fail-closed activation/rollback and boot integration. |

**Stage 5 source/CI gate CLOSED; installed gate OPEN (28 October 2026):** Native table adapter now accepts only canonical mixed-family keys via Stage 1 semantic parser, normalizes IPFW `/32`/`/128` readback, preserves the existing FD9 lock and stage/swap/rollback code, and adds non-mutating regression tests. Source/CI passed: [PR #689](https://github.com/Tolian82/os-zapret2-restyle/pull/689), [exact-head Project/Voice/FreeBSD 15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40667474764), [merged source 5aa4cb4](https://github.com/Tolian82/os-zapret2-restyle/commit/5aa4cb4949cf2e5c32057efdb6cef6c6a02d5c11), [post-merge CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40668766422). Do not mark the full gate PASS without separate installed FreeBSD15 IPv6 IPFW/capture/reinjection and rollback proof.

**Additional native FreeBSD 15 VM evidence (28 October 2026):** [PR #691](https://github.com/Tolian82/os-zapret2-restyle/pull/691) verified the **actual kernel** using the existing `FreeBSDIPFWAdapter`, in an isolated disposable FreeBSD 15 VM. [CI #40675916765](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40675916765), job `Isolated FreeBSD 15 native IPFW IPv4/IPv6 table smoke`, logged `STAGE5_NATIVE_TABLE=PASS: FreeBSD15 live kernel add/list/swap/restore/cleanup`. Mixed IPv4/IPv6 `type addr` keys were added, read back, swapped, swapped back, and both empty tables destroyed without adding/changing any rules. This is **VM kernel evidence**, not proof of installed OPNsense WAN/FD9/divert/reinjection/IPv6 STUN or device rollback. The Stage 5 **installed** exit gate is still OPEN; stable `v0.6.0` and development package identity `v0.6.1_5` are unchanged.

**Native FreeBSD 15.1 VM packet evidence (28 October 2026):** [PR #693](https://github.com/Tolian82/os-zapret2-restyle/pull/693) ran the existing production `FreeBSDIPFWAdapter` on a disposable FreeBSD 15.1 VM. [Exact-head CI #40685416258](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40685416258) logged both `STAGE5_NATIVE_TABLE=PASS` and `STAGE5_NATIVE_IPV6_PACKET=PASS`. A destination-IPSET-scoped rule on `lo0` diverted an actual IPv6 UDP packet carrying a synthetic STUN-format request, reinjected it, and delivered the identical payload; UDP outside ports 596–599 bypassed divert. Scoped rule/table cleanup succeeded. This is **VM kernel/loopback evidence with a test socket**, not the installed OPNsense WAN, real `dvtws2`, native Apply/FD9, live service rollback or Telegram call. The Stage 5 installed acceptance gate remains **OPEN**.

**Installed read-only evidence preparation (unqualified source):** [owner procedure](../verification/STAGE5_INSTALLED_OPNSENSE_READONLY.md), `scripts/stage5-installed-evidence.py` and `scripts/test-stage5-installed-evidence.py` reuse the existing committed Voice inspector, compare two runtime/IPFW counter observations, reject stale/different ownership and **never infer IPv6 PASS from shared IPFW counters**. Exact installed package `0.6.1_5` is required and [published as testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.1_5) but not owner-installed/verified; Stage 5 installed gate remains OPEN.

**Exit gate 5:** **Installed** FreeBSD 15 shows mixed table add/list/swap, destination-scoped IPv6 Voice STUN capture, correct reinjection, no foreign-rule change and exact rollback; CI alone is insufficient.

## Stage 6. Strategy Lab IPv6 end-to-end

**First source increment v0.6.1_21 (31 October 2026):** Independent default-OFF IPv6 GUI checkbox below Mode, native API/configd/launch handoff, immutable saved job selection and opt-in-gated real Stage-30 IPv6 control probe are implemented for source/CI review. Existing IPv6 route-gated domain AAAA/TLS probe is reused only on opt-in. **Stage 6 exit is NOT CLOSED:** IPv6 literal and AAAA-only jobs, end-to-end pinned replay, fixed 150/200/270/350-second job-wide budgets, fully qualified GUI and owner-installed matrix remain to implement/test. [Focused regression](../../scripts/test-strategy-lab-ipv6-opt-in.py).

**Second source increment v0.6.1_22 (31 October 2026):** Strict single job-wide deadline is now computed only from actual Stage-40 family observation, not mere network IPv6 route, optional QUIC/UDP or endpoint count. Standard 150/200 and Extended 270/350, no repeated bonus; [regression](../../scripts/test-strategy-lab-adaptive-budget.sh). **Still OPEN:** IPv6 literal, AAAA-only end-to-end search, actual IPv6 IPFW capture/replay and owner-installed acceptance.

**Outcome:** Use the existing Lab engine for pinned IPv6 endpoints, plus the owner-approved IPv6 checkbox under Mode, dual-family target gating and 150/200 / 270/350-second job budgets.

| Scope | File | Planned change or check |
|---|---|---|
| CHANGE | `src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt` | Add the RU/EN `IPv6` checkbox directly beneath Mode, label left/indicator aligned under dropdown as approved; default OFF, submit selection, keep Run/Stop and standard/extended layout, show per-family results and correct 150/200/270/350 guidance. |
| CHANGE | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php` | Accept IPv6 literal targets and optional Host/SNI; validate the independent IPv6 checkbox and pass the selection through existing job-start contract. Reject an IPv6 literal while unchecked and never infer AAAA opt-in merely from DNS. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/target.sh` | Normalize IPv4/IPv6 literal and domain A/AAAA endpoints, filter eligible target families by saved job checkbox, bind fixed remote addresses, and do not fabricate an alternative-family endpoint. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/request.sh` | Route IPv6 requests through existing Python request helper, without alternative test client. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/request.py` | Support IPv6 DNS, Chrome/curl endpoint pinning and bracketed URLs; retain ECH-off, proxy bypass and timing evidence. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/probe.py` | Prove actual remote IPv6/family matches target, TLS certificate and applicable QUIC semantics; report unsupported cases honestly. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_flow.sh` | Carry immutable IPv6 option, actual eligible families and single job deadline through stages 00–90; ensure IPv4 and IPv6 trials have bounded, non-starved eligibility without disturbing Stop/restore. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/orchestrator.py` | Reconcile the existing authoritative overall deadline and saved job budget with 150/200/270/350 seconds, without a separate timer, family reset or incorrect Stage-80 deadline. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_budget.py` | Reconcile eligible-work scheduling and existing IPv6/endpoint additions with the fixed owner-approved total-job ceilings; avoid double-counting a previous IPv6 increment and never sacrifice cleanup. |
| CHANGE | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/firewall.sh` | Extend bounded Lab IPFW capture to IPv6, isolated from the running service's rules. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/probe.sh` | Audit IPv6 evidence and saved job logs; adjust only when existing protocol schema requires it. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/candidate.sh` | Check IPv6 candidate pinned --ipset-ip expression and preserve existing candidate generators. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/udp_candidate.sh` | Check generic UDP IPv6 path and exact bytes/endpoint identity. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/quic_candidate.sh` | Qualify QUIC IPv6 only when actual Chrome endpoint pinning supports it; never synthesize PASS. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/extended_runtime.sh` | Preserve Stage 70/85/90, replay and cleanup, adding family-aware evidence where necessary. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_model_b_adapter.sh` | Check Model B adapter/state and adaptive candidate compatibility with IPv6 targets. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/resources.py` | Preserve dynamic extra Lua/BIN inventory independent of IP family. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/strategy_lab/result.sh` | Check job result retains requested IPv6 checkbox, actually tested families, explicit unavailable cases, assigned time budget and true final deadline, without reinterpreting saved jobs. |
| NEW | `scripts/test-strategy-lab-ipv6.py` | Add IPv6 integration matrix: unchecked A-only, checked A+AAAA, A-only/AAAA-only domains, IPv4/IPv6 literals, missing IPv6 route, Host/SNI, Chrome pin/proxy, QUIC when supported, replay, faults and restoration. |
| CHANGE | `scripts/test-strategy-lab-time-budget.sh` | Verify actual 150/200 Standard and 270/350 Extended overall deadlines, no bonus for checkbox-only/single-family jobs, and no duplicate per-family timer. |
| CHANGE | `scripts/test-strategy-lab-adaptive-budget.sh` | Verify current eligible-work budget is reconciled to owner-approved mixed-family ceilings, no double IPv6 bonus and preserved stage-80/overall deadline containment. |
| CHANGE | `scripts/test-strategy-lab-gui-status-reconciliation.sh` | Verify RU/EN Mode/IPv6 two-row alignment, default OFF, Run/Stop unaffected, saved job family scope and per-family result/status visibility. |
| CHANGE | `scripts/test-strategy-lab-job-contract.sh` | Verify checkbox payload/API normalization, immutable job selection, IPv6 literal gating and persisted planned/actual families. |
| CHANGE | `scripts/test-strategy-lab-target-contract.sh` | Extend target contract tests to both families and untouched domains. |
| CHANGE | `scripts/test-strategy-lab-ip-targets.sh` | Test fixed IPv6 endpoint identity and no accidental IPv4 fallback. |
| REVIEW | `scripts/test-strategy-lab-python-probes.sh` | Check Python probes' IPv6 baseline, TLS certificate and remote-IP proof. |
| REVIEW | `scripts/test-strategy-lab-interception-evidence.sh` | Check IPv6 IPFW source-port interception attribution. |
| REVIEW | `scripts/test-strategy-lab-extended-tcp.sh` | Check IPv6 Stage60/85/90 TCP replay and cleanup. |

**Exit gate 6:** Installed RU/EN Lab matches approved Mode/IPv6 layout and defaults, selected domain A/AAAA test matrix and literal target rules, saves actual job family selection, proves exact remote address/baseline/candidate/replay/restoration, and enforces 150/200/270/350-second job ceilings without adaptive double count. IPv4-only scenarios remain usable and report missing IPv6 as unavailable, not an IPv4 failure.

## Stage 7. Integrated regression of shared Apply and Extra Resources

**Outcome:** Verify all modified production entrypoints and failure paths together, including unchanged Install/Remove ownership.

| Scope | File | Planned change or check |
|---|---|---|
| CHANGE | `scripts/test-extra-resources-native-saved-build.py` | Verify real saved-Config → common candidate → Install/Remove trial and native health, including Lua/BIN and rollback journals. |
| CHANGE | `scripts/test-shared-apply-render.py` | Test shared detached render against added EXCLUDE_IPSET and saved Config. |
| CHANGE | `scripts/test-voice-engine-private-dryrun.py` | Test native dry-run for mixed managed IPSETs and per-profile exclusion references. |
| CHANGE | `scripts/test-voice-common-runtime.py` | Test one shared process, final argv hashes, excluded Voice targets, IPv4-only fallback and mixed dual-stack. |
| CHANGE | `scripts/test-config-activation-contract.sh` | Test FD9 lock, single Config writer, boot, failed apply and exact restoration. |
| REVIEW | `scripts/test-voice-gui-contract.py` | Check Voice GUI page, F5, ordinary/Advanced, RU/EN and native Apply status. |
| REVIEW | `src/opnsense/scripts/OPNsense/Zapret/setup.sh` | Audit that ordinary install/update does not overwrite staged candidate or add a second boot hook. |
| BOUNDARY | `src/opnsense/service/templates/OPNsense/Zapret/+TARGETS` | Verify no unnecessary template-set changes. |
| BOUNDARY | `src/opnsense/scripts/OPNsense/Zapret/backend/blobs.sh` | Verify extra Lua/BIN loading works unchanged under the new profile argument filtering. |
| BOUNDARY | `docs/architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md` | Preserve historical Remove transaction boundaries and reuse common future compiler. |

**Mandatory integrated scenarios:** Standard/Extended Laboratory IPv6-checkbox OFF/ON and 150/200/270/350-second budgets; IPv4-only input in the current Config schema; mixed IPv4/IPv6; explicit/effective `/0` refusal in all lists; Voice STUN without P2P scope; domain exclusion only in ordinary applicable Strategies; IP exclusion in every profile; `--new`/template/import/Extra; target modes `all/list/auto`; IPv4-only WAN; mixed IPFW/rollback; Install/Remove; and IPv6 Lab. Do not claim successful media/calls or broad P2P traffic handling.

**Exit gate 7:** Full shared Config/Voice/Strategies/Extra Resources paths preserve identity, exclusion semantics, rollback and original Lua/BIN, no extra owner/parser/service.

## Stage 8. Versioned GitHub delivery and installed acceptance

**Outcome:** Publish incremental source through normal GitHub workflow; version only for actual packaged changes and never infer stable release authorization.

| Scope | File | Planned change or check |
|---|---|---|
| CHANGE | `VERSION` | At first actual new development stage, change VERSION from 0.6.0 to 0.6.1 once per DEV-034; **never** for docs-only planning. |
| CHANGE | `Makefile` | Reset PLUGIN_REVISION to 1 with new VERSION, then advance `_N` one step for packaged changes; keep PLUGIN_NAME and `zapret` service name. |
| REVIEW | `.github/workflows/ci.yml` | Run applicable tests and FreeBSD15 package matrix; amend workflow only if registration requires it, no weakened gates. |
| DOC | `docs/architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md` | Maintain accepted specification; document only new explicitly approved clarifications and evidence. |
| DOC | `docs/architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md` | Record staged progress, source/CI/installed evidence and next stage without claiming missing PASS. |
| DOC | `docs/START_HERE.md` | Update exact candidate handoff and one next action after real stage completion. |
| DOC | `docs/PROJECT_STATE.md` | Reconcile proven current state, installed evidence gaps and links. |
| DOC | `docs/history/current/v0.6.x.md` | Record real changes and verification chronology in the v0.6.x line ledger. |
| DOC | `docs/ROADMAP.md` | Keep roadmap concise and current as stage priorities change. |
| DOC | `docs/REQUIREMENTS.md` | Update requirements only where approved/implemented contracts actually change. |
| DOC | `docs/INDEX.md` | Keep active navigation valid and current. |
| REVIEW | `docs/CHANGELOG.md` | Add changelog only for actual new behavior/package publication, not anticipated work. |
| REVIEW | `README.md` | Update human README when implementation is qualified for a separately approved full release. |
| BOUNDARY | `docs/releases/v0.6.0.md` | Preserve immutable already published v0.6.0 notes and evidence. |
| BOUNDARY | `docs/GITHUB_PUBLICATION.md` | Apply GitHub exact-head branch/PR/CI and publication rules, no self-authorized stable release. |

**Exit gate 8:** All A01–A24 acceptance results documented with their actual evidence level; no release or live PASS inferred from source code or green CI. Exact package identity and owner-live gates remain explicit.

## 9. Referenced runtime paths and intentional non-changes

| Referenced path | Treatment |
|---|---|
| `/conf/config.xml` | Retain the one native OPNsense saved Config; never create a separate user IPSET config. |
| `/usr/local/etc/zapret2/zapret.conf` | Generated from existing `zapret.conf` template, never a manually edited authority. |
| `/usr/local/etc/zapret2/hostlist-exclude.txt` | Retain the domain-only rendered hostlist; no DNS-to-IP conversion. |
| `/usr/local/etc/zapret2/runtime-v2/managed/ipset-exclude.txt` | New output owned by the staged/common runtime; not a manually edited global file. |
| `<candidate-release>/ipset-manifest.json` | New immutable candidate verification artifact; versioned schema and per-list full-family proof. |
| `/usr/local/etc/zapret2/exclude.txt` | **Do not create** a second config source merely because a native syntax example uses `--ipset-exclude=exclude.txt`. |
| `docs/DECISIONS.md` (28 Oct Voice/P2P discussion) | Retain as history and deferred ideas, superseded for current IP-list `/0` policy by this approved specification. |
| `src/opnsense/scripts/OPNsense/Zapret/backend/voice_handoff_preflight.py` | **Does not exist** in checked baseline. Use real Voice release/adapter/saved-pair guards. |
| `src/opnsense/scripts/OPNsense/Zapret/backend/voice_native_compiler.py` | **Does not exist**. Do not create a duplicate compiler. |
| `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/target.py` | **Does not exist**. Actual target path is `strategy_lab/target.sh` plus request/probe. |

The rest of previously mentioned paths are explicitly assigned to the stage tables above. Merely being named in an inventory is **not** permission to change an unaffected source file.

## 10. Completeness and ownership checks

The stage tables explicitly cover:

- **GUI/Config:** `Zapret.xml`, both forms and Volt views, Settings/Strategy/Voice payload and controllers, detached XML, saved Config, OPNsense templates, rendered candidate guards, concurrency and native commit.
- **Compiler/runtime:** new `ipset_policy.py`; Targets, Exclude, parser, profile pipeline/normalizer, native generator, validator, managed storage and registry, port logic, orchestrator and one service/firewall owner.
- **Existing Voice:** model export, profile compiler, capture plan, traffic merge, release staging, IPFW adapter and firewall transaction, **without** new P2P profile or GUI controls.
- **Existing Lab:** controller, target, request/probe, firewall and worker stages, standard/generic-UDP/QUIC candidate generation, adaptive adapter, saved result and dynamic resource inventory.
- **Verification:** all stage-specific Python/PHP/shell regression contracts, new IPSET/exclusion/IPFW/Voice-boundary/Lab IPv6 tests, shared Apply and Extra Resources scenarios.
- **Governance:** unchanged four canonical rule books and AGENTS, updated active architecture/current state/handoff/requirements/roadmap/index, existing archived release records and current-line chronology only where its bounded role requires it.

Check stage table rows against the current pinned Git tree before implementation: a non-existent *planned* test marked NEW is normal; an invented *existing* path is not. Do not use old helper names as alternate implementations.

## 11. Completion definition

Close only after recorded evidence for [acceptance A01–A26](ZAPRET2_EXCLUDE_IPSET_SPEC.md#10-acceptance-criteria), including actual installed OPNsense dual-stack managed targets and Voice, all-profile IP exclusion, domain-only hostlist isolation, universal user `/0` refusal, unchanged IPSET-scoped STUN, Lab IPv6, rollback/boot, valid IPv4 values under the current Config schema and native Extra Resources lifecycle. A failed/unrun check is never PASS; an explicitly accepted residual limitation must remain visible. Deferred Voice/P2P/UDP-port/IPv6-toggle work is a separate future project.

**Native FreeBSD 15.1 transaction/rollback VM evidence (28 October 2026):** [PR #694](https://github.com/Tolian82/os-zapret2-restyle/pull/694), [native kernel CI run #40692393152](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40692393152) logged `STAGE5_NATIVE_TRANSACTION=PASS`. The existing production capture planner, firewall transaction and `FreeBSDIPFWAdapter` ran against actual IPFW kernel objects in a disposable FreeBSD 15.1 VM. Telegram/Discord mixed IPv4/IPv6 rules/tables were installed, a deliberately rejected `ipfw add` operation during cutover restored exactly the previous owned state, a successful cutover was rolled back before commit, a subsequent commit removed stage snapshots, and Discord retirement/cleanup preserved non-plugin rules. This is **real isolated VM kernel evidence**, not installed OPNsense Apply/FD9, WAN, real `dvtws2`, voice call or appliance failure recovery. **Stage 5 installed acceptance OPEN.** The source candidate has an exact `v0.6.1_5` testing prerelease; this is neither installed acceptance nor a stable release.\n\n**Stage 5 owner-installed regression and remediation (28 October 2026):** The real `0.6.1_5` package was owner-installed but `POST-INSTALL` failed to restart the previously committed Strategies owner (`Error 69`). The sole observed native Config snapshot difference was the new absent-in-old `hostlist.excludeipset` field. Candidate `_6` adds an exact-empty-only legacy compatibility check to `shared_apply_config.php saved` with fail-closed tests. Source/CI and live owner acceptance must be distinguished; Stage 5 remains OPEN.\n

**Published remediation `v0.6.1_6` (28 October 2026):** [PR #697](https://github.com/Tolian82/os-zapret2-restyle/pull/697) and [exact-head Project/Voice/FreeBSD15 CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40729567559) qualified the legacy empty Exclude IPSet saved Config fix. [Testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.1_6) is available, not owner-installed/accepted. Stage 5 on real OPNsense remains OPEN.

**Stage 5 upgrade-compatibility blocker (28 October 2026):** Owner-installed `_6` passed native Config witness `RC=0`, but POST-INSTALL returned 70, as the old sealed release has only eight managed files and lacks `managed/ipset-exclude.txt`. `_7` source correction keeps original sealed release, uses the existing FD9 and old-digest witness to accept that exact legacy file layout solely during boot, never during new Apply. Tests and installed confirmation required before Stage 5 close.

**`v0.6.1_7` Stage 5 upgrade remediation published (28 October 2026):** Source [PR #699](https://github.com/Tolian82/os-zapret2-restyle/pull/699), [exact-head CI #40752605894](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40752605894), source commit `57dd8594bac964b017b0729eb77f7249de065e07`, [testing prerelease](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.1_7) with FreeBSD15 `.pkg` SHA-256 `0bb234363e7b3a518ca997c0249ec73b3973b49ab64ca418bd62c49190514a50`. Only installed owner-live `start/status/inspector` can confirm fix; Stage 5 installed native IPv6 and Voice remains OPEN.

**`v0.6.1_8` published owner-observed GUI correction (28 October 2026):** Native `_7` runtime now owner-confirmed RUNNING/ready with IPFW attested, but GUI displayed a false `common-config-mismatch` due to the empty new Exclude IPSet field and duplicated right-side help. Corrective [PR #701](https://github.com/Tolian82/os-zapret2-restyle/pull/701) passed [CI #40760232959](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40760232959) and published [testing pkg](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.1_8/os-zapret2-restyle-0.6.1_8.pkg) SHA-256 `34a2c0f10fe5f27354893c51efbbc18d143375e9eed0dcdd2de4ca6115492ae3`. No native Config/FD9/IPFW/runtime change. GUI installation/visual acceptance, actual Telegram media/call, IPv6 wire and rollback installed Stage5 still OPEN.
