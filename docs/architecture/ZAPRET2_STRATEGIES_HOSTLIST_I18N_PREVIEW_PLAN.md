# Strategies / Hostlist / RU-EN / read-only preview — approved development plan P0–P6

**Status:** OWNER APPROVED IN FULL — 11 November 2026. Incremental P0–P4 source/native proofs are recorded separately; P5b2a disposable build coordination is present in the v0.6.4_38 source candidate (not yet a full P5 acceptance). **Full P5 and A11/A16 owner acceptance remain OPEN.** This plan records requirements, not proof of final feature completion.
**Normative requirements:** [Strategies / HOSTLIST / bilingual UI / read-only preview specification](ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md), owner-approved 11 November 2026.
**Issue:** [FEATURE #936](https://github.com/Tolian82/os-zapret2-restyle/issues/936) (remains OPEN until implemented and owner accepted).
**Authority:** owner explicitly approved the entire P0–P6 plan, including all notes, wording, qualifications, suggestions and acceptance gates, on 11 November 2026. There is no remaining approval gate to start P0, P1 or P2 within this agreed scope. Return to the owner for an actual change of architecture/requirements, or proactively propose optional improvements for discussion without silently adding them to scope.
**Identity:** documentation-plan integration is a source-only revision. It does not install/alter runtime, publish a native package, start the development stages or undo the owner-accepted lifecycle ТЗ v1.3 / G01–G11.

## 1. Delivery principles and boundaries

1. Preserve the existing original FD9 lock and one shared Config writer, WAN-first errors, one ordinary Strategies+Voice `dvtws2`, common Apply/rollback, existing owned IPFW rules/tables, non-destructive GUI uninstall and self-removing full purge.
2. Keep native upstream Zapret2 profile grammar and behavior. Do **not** write another full command-line parser, maintain a separate generated-service process or create a competing hostlist data store.
3. Capability-check against the actual installed/selected engine and installed Lua/BIN; do not scatter hard-coded engine versions or silently strip `!` / `^`. An unsupported runtime refuses activation safely, with persisted user text and existing running service unchanged.
4. Keep one exact feature scope per PR; `PLUGIN_REVISION` increments once for each new merged `main` commit, while `VERSION` remains unchanged unless a separately approved real stage change occurs. A source-only revision is not an available `.pkg`.
5. Apply the [sufficient-verification stop rule (DEV-061)](../PROJECT_PRINCIPLES.md) and [tiered CI budget (GH-069)](../GITHUB_PUBLICATION.md): fast S0, exact-head S1, justified changed-path S2 and genuinely required final S3. Select the necessary checks before implementation; after they pass, stop expanding the matrix and move to delivery. An intermediate testing `.pkg` is an input for owner-live acceptance, not contingent on already completing every A01–A19 owner-live row. Never flood unrelated historical VM jobs.
6. Record each stage's **source**, **CI**, **native installed**, and **owner OPNsense** evidence separately. Treat planned, untested, skipped, partial and failed work truthfully.
7. P0–P6 are ordered acceptance gates, not a commitment to a fixed count of commits. Close real blockers before advancing; split a stage into small related PRs if needed, never claim partial acceptance of the entire stage.
8. New/changed user-facing text throughout this scope is bilingual RU/EN based on the OPNsense **profile** locale. Existing Strategies and Voice text is included in the full audit. Preserve user-entered technical strings without translation.
9. Owner approval of this plan authorizes the agreed implementation sequence; **new optional ideas** are suggestions for discussion, not additional approved requirements until separately accepted.

## 2. Ordered stages, evidence and acceptance

| Stage | Core result | Normative acceptance | Stage exit evidence |
| --- | --- | --- | --- |
| **P0** | Confirm canonical upstream manual and actual project ownership | Prerequisite for A01–A10, A12–A17 | Official upstream/source semantics, code call graph, owner-approved no-extra-engine-test boundary |
| **P1** | One Python HOSTLIST domain policy across GUI, Config and backend | A01–A05, A10 | Single `domain_policy.py`, thin PHP/shell adapters, same-input test corpus and existing `--dry-run` |
| **P2** | Native profile/handler order and duplicate-list guard | A06–A09 | Generator/validator cases plus genuine `dvtws2 --dry-run` and no-mutation failure |
| **P3** | Full existing Strategies and Voice RU/EN localization | A12–A16 | Both locales exercised on OPNsense profile settings, help/F5 and API failures; saved values unchanged |
| **P4** | Accurate help, Full Help and Strategy Lab guidance | A17 plus A12–A14 | Native-checked examples, cached resource inventory, bilingual Lab GUI and handler-transfer instructions |
| **P5** | Safe `Validate and Preview` action | A11 plus A16 | Generated-profile snapshot, native dry-run/error classification, before/after permanent-state equivalence |
| **P6** | Product regression and native owner package acceptance | A01–A19 (all) for final stage closure, not as a precondition for an intermediate testing `.pkg` | Exact native `.pkg` identity, controlled upgrade/reinstall tests, owner physical OPNsense GUI acceptance and unchanged stable published asset |

Every stage includes its matching regression checks for existing Voice, Strategies, Lab, WAN-first and shared-service ownership where touched; completing an earlier stage does not imply completing later user acceptance.

## 3. P0 — verified capability and integration design (first action)

**User scenario:** A user enters the approved hostlist syntax, creates one or several native profiles, views help in RU/EN, and later performs a read-only check; we must know what the installed engine and current OPNsense code actually do before implementing.

**Tasks:**

- Accept the official upstream Zapret2 manual as canonical for ordinary domain, `^name`, `!name`, `!^name`, `^!name`, native profile semantics and compatibility. The owner explicitly ruled out further executable-engine semantic experiments; existing `dvtws2 --dry-run` is accepted. Determine only plugin integration and safeguards.
- Verify native `--new` boundaries, first matching profile, multiple sequential `--payload` / `--lua-desync` handlers, list include/exclude and prohibited duplicate references in one profile; check same file in two independent profiles and resolved-file identity.
- Trace PHP candidate-save path in `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php`, shared `StrategySettingsPayload.php`, model `Zapret.xml`; trace `src/opnsense/scripts/OPNsense/Zapret/backend/targets.sh`, `target_mode.sh`, `parser.sh`, `profile_pipeline.sh`, `profile_normalizer.sh`, `generator.sh` and `validator.sh`. Verify call order and existing dry-run entrypoint before changing it.
- Trace `forms/general.xml`, `forms/voice.xml`, `general.volt`, `voice.volt` and `diagnostics.volt`; identify current stock gettext/translation mechanism, existing JavaScript locale handling, popup-help sources and how the OPNsense **user profile locale** propagates to UI/API.
- Review current Voice shared Apply and Lab safeguards, existing native test fixtures, and release/package compatibility checks. Avoid introducing new subsystem owners.

**Deliverable:** bounded evidence table: case → engine version/capability/exact command or fixture → observed native result → required behavior → production entrypoint → candidate test. Record unresolved upstream differences explicitly. No source implementation or package claim at P0.

**Gate:** enough direct evidence to code P1 and P2 without inventing native semantics. If the engine contradicts an approved requirement, stop the affected change and present the exact evidence plus options to the owner; do not weaken the requirement silently.

**P0 evidence and binding update:** [tagged source findings and owner's canonical-manual/no-extra-engine-verification decision](../verification/P0_UPSTREAM_HOSTLIST_PROFILE_EVIDENCE.md). P0 review is completed under the owner instruction; do not create a new native witness gate.

## 4. P1 — HOSTLIST modifiers and normalization parity

**User scenario:** The GUI accepts an approved target line, saves it, reopens it unchanged in meaning, and the managed list ultimately given to `dvtws2` has the same semantics.

**Work:**

- Parse leading `!` and `^` separately from hostname normalization; preserve exact/exclusion flags and support both ordering forms once verified in P0. Validate domains, pasted URLs, wildcard compatibility, whitespace and casing without lossy policy transformation.
- Reject `!!`, `^^`, `!^!`, malformed/empty host, invalid exact+wildcard and non-domain inputs with stable error code, field and line; do not merge semantically distinct entries.
- Implement ONE canonical domain grammar in `backend/domain_policy.py` (alongside `ipset_policy.py`): GUI preflight delegates through a separate `DomainSetPolicyBridge.php`; `SettingsController.php` has no handwritten domain grammar; `backend/targets.sh` calls Python for managed YouTube/User and global Exclude Domains. Preserve the existing `IPSetPolicyBridge.php` unchanged. Test all three entrypoints against one semantics corpus, without creating a second Config writer.
- Keep local HOSTLIST `!name` distinct from global Exclude Domains and Exclude IPSet. Do not introduce modifier parsing into unrelated excluded-target fields.
- Validate actual runtime capabilities before mutation; missing/older engine behavior is explicit and non-destructive. Save/readback and model F5 must preserve existing user data and approved empty strategy behavior.

**Evidence:** S0 Python unit/CLI, PHP-bridge and shell-adapter tests of one policy, invalid-line/atomic-output tests and Config round-trip; focused CI generator/Config tests; current native `dvtws2 --dry-run` as the accepted existing validation mechanism. No supplementary engine semantic experiments.

**Gate:** A01–A05 and A10 demonstrated at the appropriate executable boundary; no automatic conversion of local exclusions into global policy.

## 5. P2 — native filters, profiles and duplicate-list protection

**User scenario:** A user intentionally supplies one multi-handler HTTP+TLS profile, or two `--new` profiles referencing the same target list, without having their order or semantics rewritten.

**Work:**

- Prefer migrating the profile parsing/normalization implementation from `backend/parser.sh` and `profile_normalizer.sh` to an integrated Python component after mapping the existing `profile_pipeline.sh`, `target_mode.sh`, `generator.sh`, `validator.sh`, Voice and FD9 ownership. Keep thin shell entrypoint compatibility and unchanged `--new`/handler semantics. Perform this as a separate P2 logical PR only if the migration has bounded risk; do not replace the whole functioning pipeline blindly.
- Preserve one profile's internal sequence of `--payload` and `--lua-desync`, real first-match behavior, `--filter-tcp/udp`, `--filter-l7`, and the distinction between IPFW interception port set and per-profile engine selection.
- Detect prohibited same-type resolved-file duplicates **within** one profile, distinguishing include/exclude and list type; allow same HOSTLIST/IPSET reference in separate profiles.
- Do not ban all overlapping target profiles; provide a warning when meaningful and use native dry-run for nontrivial `--template` / `--import` expansion. Validation failure must not activate a broken Config or change a running engine.

**Evidence:** specific two-handler one-profile and two-profile positive fixtures, same-file same-profile negative, alias-path negative and other-file/other-profile positives; inspect actual generated invocation and native `dvtws2 --dry-run`, plus failure rollback.

**Gate:** A06–A09 PASS on actual source/native boundaries; no invented secondary parser or engine.

**P2 implementation record:** [Python profile-policy migration and exact shell ABI](../verification/P2_PYTHON_PROFILE_POLICY.md) records the first partial P2 increment. The native resolved-file duplicate guard and full A06–A09 acceptance remain pending; the owner has not accepted P2 as a whole.

## 6. P3 — all Strategies and Voice texts in RU/EN

**User scenario:** A user's OPNsense profile is RU, then EN; each full page and feedback message follows that profile, while strategy/domain/IPSET bytes stay untouched.

**Work:**

- Inventory every visible field/section/select option, help/hide-help/advanced state, popup source, Full Help, status, warning, form save/apply, server/AJAX error and dynamic UI output on both pages.
- Prefer the stock OPNsense localization path in `forms/general.xml` and `forms/voice.xml`; provide a consistent translation lookup for `general.volt` and `voice.volt` dynamic messages, using the actual **profile locale**, not browser geo/browser-language text substitutions.
- Use structured, stable backend errors (with safe field/line/profile metadata) and localized human-facing UI rendering; keep technical diagnostics untranslated when appropriate.
- Verify all existing Voice services (Telegram, Discord, X, SIP, Custom), five IPSET editors, draft actions and common service status; any new strings in other sections under this scope must also be RU/EN.
- Preserve typed settings through language change, F5, help/advanced mode, save/apply and empty values. Verify English fallback for unspecified locales.

**Evidence:** automated text inventory/source assertions plus actual RU and EN OPNsense GUI interactions/screenshots for both pages, inline/popup/full help and intentional API failures. Avoid claim of complete localization from source-string search alone.

**Gate:** A12–A16 PASS; no new custom locale authority or regressed shared Voice lifecycle.

## 7. P4 — help, native strategy examples and Strategy Lab

**User scenario:** Users understand what existing filters and target lists do, and how to transfer an actual Strategy Lab result without accidentally overwriting unrelated strategy profiles.

**Work:**

- Update `general.xml` help and `general.volt` Full Help, including native `!/^ `, local vs global exclusions, `--new`, first-match, repeated list references, multi-handler `--payload`/Lua, and accurate `Extra Arguments` scoping.
- Explain IPFW interception coverage vs `--filter-tcp/udp` vs `--filter-l7`, `--in-range` / `--out-range`, `--payload`, `--lua-desync`, and typical HTTP/TLS/QUIC/UDP/STUN/WireGuard choices **only when supported** by installed engine/resources.
- Keep dynamic installed Lua/BIN catalog with **cache-only help reads**; no hidden Git fetch/install at help-open time. Warn truthfully when resource data is absent.
- In `diagnostics.volt` / lab UI help, describe exact tested profile, L7, payload and handler, and distinguish inserting a handler into an existing profile from creating a separate `--new` profile. No automatic full-strategy overwrite.
- Apply P3 locale machinery to all help, examples, Lab informational and error text introduced here.

**Evidence:** native parsing of example profiles, F5/popup/full-help RU/EN checks, dynamic help with and without optional resources, lab-status/restore regression.

**Gate:** A17 and applicable A12–A14; no misrepresentation of blocked-network real success from a native dry-run.

## 8. P5 — `Validate and Preview` without mutation

**User scenario:** With no runtime or with a running shared Strategies+Voice service, a user may inspect unsaved candidate settings, profile order, port coverage and errors without applying any changes.

**Work:**

- Reuse current generator/validator and actual existing native `dvtws2 --dry-run` where possible. Avoid a second generator, persistent candidate owner, new service or synthetic success.
- Render an effective per-profile summary: profile number/order, TCP/UDP interception ports, L7, HOSTLIST/IPSET/default Target Mode, exclusions, ordered payload→Lua actions, overlaps, unavailable resources/capabilities and actionable errors.
- Separate `syntax/configuration valid`, `native dry-run unavailable`, `native dry-run failed` and `real network bypass not tested`. Native dry-run is **not** evidence that a network or Voice call succeeds.
- Enforce a strict no-mutation preview of Config, persistent target/resources state, FD9 owner, active IPFW rules/tables, PID/process and common Voice state. If temporary candidate artifacts are required, use safely scoped private temporary paths, verify cleanup even on errors/cancel, and do not persist an Apply transaction.
- Confirm the preview never bypasses WAN-first requirements for actual service Start/Apply; read-only inspection itself may explain that WAN/runtime are absent without silently mutating the system.

**Evidence:** before/after semantic fingerprints for Config, owned/foreign IPFW, process identity, Voice and FD9; cases with RUNNING, STOPPED, absent runtime, invalid strategy and cancellation, plus precise UI result for each branch.

**Gate:** A11 and relevant A16 PASS with genuine installed OPNsense native witness.

## 9. P6 — regression, one qualified native package, owner acceptance

**Verification boundary:** Before a requested intermediate testing `.pkg`, run the selected S0/S1, applicable native S2 and package-identity/ABI/changed-safety qualifications; do **not** require the future owner physical GUI/upgrade/purge evidence to exist before delivering the package used to gather it. Subsequent final P6 closure still requires every applicable A01–A19 criterion and its genuinely required evidence. Reuse prior valid baseline proof for unchanged behavior. Native lifecycle or destructive safety checks must be performed whenever the candidate really changes those paths; known critical defects block the affected delivery. An extra VM run needs a written distinct risk and exit decision, not just a possible failure mode.

**User scenario:** An existing installation upgrades using the native `.pkg` procedure and retains settings/working services, and a clean or normal-reinstalled installation also works with the new features.

**Work:**

1. Run relevant S0/S1 integration tests and native S2 focused on changed PHP, shell, GUI and process/lifecycle contracts.
2. Assemble and qualify a **specific physically identical native `.pkg`** through current official OPNsense build paths; record source candidate, ABI, version/revision and actual published package digest. Use only the native `.pkg` delivery mechanism; no shell installer.
3. Verify standard in-place update on a running configured test installation; preserve user-saved settings, WAN selection, Voice state, all existing strategy profiles and owned IPFW process/rule boundaries.
4. Verify separate ordinary GUI uninstall/reinstall preservation, empty-strategy/Voice-only and clean-install defaults, followed by full purge / clean-install only with explicit destructive authorization/backup at real-owner boundary.
5. Exercise full RU and EN browser workflows, local `!/^ ` semantics, profiles/handlers, real dry-run warnings, safe preview and Strategy Lab. Regress genuine native WAN-first/FD9/rollback behavior.
6. Mark each A01–A19 with evidence and environment. Do not mark experimental ISP DPI bypass, all Voice media or physical IPv6 as PASS without those exact measurements. Update current docs/acceptance receipts and close #936 only after required owner acceptance.

**Gate:** all 19 specification acceptance criteria satisfied with truthful source/installed/owner evidence; any requested testing package is a verified persistent GitHub `.pkg`, not a merely generated artifact.

## 10. Traceability and non-goals

- **HOSTLIST:** A01–A05, A10 → P0, P1.
- **Profiles/native grammar:** A06–A09 → P0, P2.
- **RU/EN Strategies and Voice + backend messages:** A12–A16 → P3, retained by P4–P6.
- **Lab help:** A17 → P4.
- **Strict preview:** A11 → P5.
- **Regression and package:** A18–A19 plus all cases → P6.

The plan **does not** authorize: a second WAN chooser, a second Config writer, a replacement general Apply, independent Voice process, new firewall manager, silent strategy rewriting, new product-version stage, stable release, or reinterpretation of the previously completed lifecycle specification.

## 11. Immediate handoff and working agreement

**Current next task (12 November 2026):** P5b2b — qualify the existing original detached native candidate builder/validator on disposable installed OPNsense with a bounded no-mutation witness, then P5c authenticated RU/EN GUI integration and P6 owner testing package. Reuse accepted P0–P4 native proofs; do not restart upstream semantics tests or unrelated Lab matrices. The historical P0/P1 entry conditions are already settled.

The owner welcomes optional engineering ideas. Propose them openly, with value, compatibility/safety impact and whether they alter this scope; do not silently treat a suggestion as an approved requirement.

**Current status:** P0–P4 partial/full source/native evidence recorded under the current state documents; P5b2a source-only, P5b2b/P5c and P6 final acceptance OPEN. No new `v0.6.4_38` package published; stable `v0.6.4_1.pkg` unchanged.
