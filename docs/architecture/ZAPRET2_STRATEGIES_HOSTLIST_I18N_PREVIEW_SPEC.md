# Zapret2 Strategies / Hostlist / bilingual UI / read-only preview — approved specification

**Status:** CURRENT CONTRACT / #936 COMPLETED AND OWNER ACCEPTED, 12 November 2026. The technical requirements below remain active. Historical intermediate OPEN/BLOCKED states are preserved separately.

## 1. Goal and non-negotiable principles

Extend native Zapret2 strategy authoring, checks, explanations and diagnostics, while completing RU/EN localization of the entire existing **Strategies** page and **Voice** page. Preserve all current saved configuration, running behavior, original OPNsense model and Config ownership, shared Strategies/Voice Apply, original FD9 lifecycle, WAN-first policy, native IPFW ownership, and ordinary .pkg installation/update/uninstall/purge contracts.

- Keep Zapret2 native syntax and semantics; do not introduce a compulsory strategy-builder, invented DSL, a duplicate full parser or a second process/service/configuration owner.
- All new human-facing text anywhere in this plugin introduced by this specification must display in Russian or English according to the OPNsense user-profile language.
- The selected/installed engine's **verified capabilities**, not an optimistic GUI version selection or a hard-coded per-version guess, determine syntax acceptance.
- Preserve a valid empty Traffic Strategy and existing clean-install defaults and user settings. Updates must never seed/overwrite an existing configuration.
- Treat documentation, code, CI/package qualification and observed physical-owner OPNsense acceptance as distinct states.

## 2. HOSTLIST modifiers and domain input

### 2.1 Supported expressions

In **YouTube Domains** and **User Domains**, support and preserve:

| Expression | Meaning |
| --- | --- |
| `example.com` | Existing native domain matching, including its normal subdomain behavior |
| `^example.com` | Exact domain only; do not match subdomains |
| `!example.com` | Local exclusion from the corresponding HOSTLIST |
| `!^example.com` | Exact-domain local exclusion |
| `^!example.com` | Same exact-domain local exclusion, when equivalence is verified in the native engine |

Both ordering forms must be accepted, subject to actual installed engine support, without silently losing either modifier. Canonicalize equivalent orderings only after proving native equivalence. Distinguish all semantically different entries during deduplication: ordinary, exact, locally excluded, exact locally excluded.

### 2.2 Validation and normalization

- Parse modifiers **before** domain normalization; validate the remaining domain by the existing supported domain rules.
- Lowercase the domain, retain intended modifiers and existing input behavior for plain domains, pasted `http://`/`https://` URLs, wildcard domains, line breaks, whitespace, duplicate handling and safe punctuation stripping, insofar as the normalized meaning remains unchanged.
- Make complex modifier+wildcard/URL combinations explicit, not guess-and-strip: unsupported combinations (for example `^*.example.com`) and empty/malformed values fail with the field, line and reason.
- Reject repeated or malformed prefixes (`!!`, `^^`, `!^!`, etc.), IP addresses/networks in domain lists, and invalid hosts. Do not silently transform an invalid domain into a valid but different policy.
- Never silently delete a leading `!` or `^`, merge opposing rules, invert policy or rewrite saved user data merely because a GUI page was opened.
- One canonical `backend/domain_policy.py` owns domain normalization for YouTube, User and global Exclude Domains. The PHP `DomainSetPolicyBridge.php` and shell `targets.sh` are thin callers without a second domain grammar; `IPSetPolicyBridge.php` remains the IPSET-only bridge. Test complete round trips through Config save, reload, managed HOSTLIST and the existing `dvtws2 --dry-run` validation. This is the owner's later approved Python unification, superseding any previous PHP/awk parity implementation wording.
- The official upstream Zapret2 manual is the authority for `!/^` and native profile semantics. The existing native `dvtws2 --dry-run` is the accepted validation boundary; **no additional isolated engine semantic re-tests or duplicate capability experiments** are required (binding owner decision and DEV-003 «Суслик»). If a known incompatible older runtime is selected, reject unsafe activation rather than silently discarding modifiers, keeping saved data and existing running state.

### 2.3 Local versus global exclusions

`!example.com` is a **local HOSTLIST exclusion**, not an instruction to add a domain to global **Exclude Domains**. The global **Exclude Domains** and **Exclude IPSet** fields retain their separate existing native policies and validation. No accidental inversion or propagation into other profiles. Help must make this distinction understandable in both languages, including exact-match effects on subdomains. Exclusion fields must not silently start accepting the include-field modifier grammar.

## 3. Native profile and filter semantics

- Explicit `--new` separates independent profiles; a flow chooses the first eligible profile according to native engine ordering. Different flows can match different profiles.
- Two profiles, such as TCP 443/TLS and TCP 80/HTTP, may legitimately use the same `<HOSTLIST:user>` reference. Do **not** reject distinct profiles just because their targets overlap.
- A single profile may contain several `--payload` and `--lua-desync` actions with their own successive filter/range context. Do not automatically split the profile using `--new` or reinterpret action ownership.
- Preserve the difference between IPFW interception port coverage and engine per-profile selection: `--filter-tcp/udp` affects profile selection and influences intercepted ports, `--filter-l7` selects protocol, and `--payload`, `--in-range`, `--out-range` and `--lua-desync` govern actions inside the selected profile.
- Detect the engine's prohibited duplicate **reference to the same file of the same list type within one profile**. Differentiate include/exclude, HOSTLIST/IPSET, resolved absolute file identities, managed placeholders and profile boundaries. Reusing it in different profiles remains valid. Warn about overlaps without banning all overlaps.
- For complicated `--template` / `--import` expansion, defer authoritative complex semantics to the existing native `dvtws2 --dry-run`; do not implement a competing full Zapret2 interpreter.
- Validation rejection happens before activation, and names the profile, parameter/reference and cause where technically available.

Examples below illustrate **native valid structures**, not a new strategy language:

```text
--filter-tcp=80,443
--filter-l7=http,tls
<HOSTLIST:user>
--out-range=-d10
--payload=tls_client_hello
--lua-desync=multisplit:pos=midsld:seqovl=1
--payload=http_req
--lua-desync=multisplit:pos=1:seqovl=1
```

```text
--filter-tcp=443
--filter-l7=tls
<HOSTLIST:user>
--out-range=-d10
--payload=tls_client_hello
--lua-desync=multisplit:pos=midsld:seqovl=1
--new
--filter-tcp=80
--filter-l7=http
<HOSTLIST:user>
--out-range=-d5
--payload=http_req
--lua-desync=multisplit:pos=1:seqovl=1
```

## 4. Full RU/EN localization — Strategies

All existing and newly added human-facing text on the rendered **Strategies** page must reflect the selected **OPNsense user-profile language**: section headings, field names, help text, native help-popup source, Advanced controls, select options, Full Help, buttons, tooltips, status, Additional Resources status, validation results, summaries, confirmations, API/AJAX failures and preview output.

Representative translations (keep technical identifiers unchanged):

| English | Russian |
| --- | --- |
| General Settings | Основные настройки |
| Enable | Включён |
| WAN Interface | Интерфейс WAN |
| Divert Port | Порт Divert |
| DPI Bypass Strategy | Стратегия обхода DPI |
| How to find your strategy | Как подобрать стратегию |
| Traffic Strategy | Стратегия обработки трафика |
| Extra Arguments | Дополнительные аргументы |
| Targets | Целевые ресурсы |
| Target Mode | Режим выбора целей |
| YouTube Domains | Домены YouTube |
| Telegram IPs | IP-адреса Telegram |
| User Domains | Пользовательские домены |
| Exclude Domains | Исключить домены |
| Exclude IPSet | Исключить IP-адреса и сети |

Use native OPNsense gettext/i18n facilities for form-rendered text wherever applicable. Give runtime-generated JS messages a consistent locale-aware translation mechanism compatible with the same profile locale. Eliminate fragile text scraping, regex replacement of visible English labels and dependency on browser geolocation/language as the only locale authority. Unsupported languages fall back predictably (prefer English). Keep form IDs, commands, CIDRs, actual domains and user-entered strategy bytes unchanged across RU ↔ EN, refresh and save/apply.

Prefer **structured backend error codes with safe field/profile/line details**, translated at the GUI boundary. Technical diagnostics may remain verbatim; user-facing messages must be localized. Both visible inline help **and** OPNsense's real hidden/popup help source must be translated so F5 and expanded/help-mode state remain correct.

## 5. Strategy help, Full Help and native resources

Update actual rendered `forms/general.xml` and `general.volt`, and current documentation where relevant:

1. Explain `--new`, profile order, first match, legitimate overlapping target lists and supported multi-`--payload`/Lua behavior.
2. Explain the two filtering layers (IPFW interception versus engine profile selection), L7 filters, range/payload/action scopes, and duplicate file paths.
3. Explain YouTube/User `!/^ ` modifiers, errors, local versus global exclusions, wildcard/URL examples and older-engine capability restrictions.
4. Clarify **Extra Arguments**: being appended after Traffic Strategy does **not** make every argument global; profile-specific options may apply to the last profile.
5. Explain safe transfer of `blockcheck2` and Strategy Lab results: add a handler within one profile when appropriate, or a separate profile with `--new`, without blindly overwriting existing strategies.
6. Deliver RU/EN Full Help with concise, engine-checked examples for HTTP, TLS/HTTPS, QUIC, UDP, STUN and WireGuard where natively supported.
7. Preserve the existing **dynamic installed Lua/BIN inventory** and cache-only Full Help reads; opening help must not run Git/download/install actions. Missing optional inventory must be truthfully described, not fabricated as available.

## 6. Read-only “Validate and Preview” / «Проверить и показать»

Add a separate user action on Strategies; do not replace normal Apply. It must call the **current** generator/validator and existing actual `dvtws2 --dry-run` pathway (not another strategy compiler).

Show a bounded, understandable representation of the eventual configuration: effective profile count and order; applicable TCP/UDP IPFW interception ports; L7 filters; explicit/default Target Mode and HOSTLIST/IPSET selectors; applicable exclusions; `--payload` → `--lua-desync` sequences; duplicated references and profile overlap warnings; missing capabilities/resources and precise profile/line/option failure where available.

**Strict read-only contract:** the preview never changes `config.xml`, saved Preferences/Voice, active IPFW rules/tables, process/PID, engine state, FD9 ownership, Additional Resources permanent files/state or shared Apply metadata. Scoped private temporary candidate material is permitted only with guaranteed cleanup and no durable mutation. Preserve concurrent RUNNING and STOPPED services, successful apply and failure/rollback semantics. If runtime or an essential resource is absent, report the exact unsupported/unavailable checks rather than claiming success. `--dry-run` is syntax/runtime validation only: it does **not** certify that Lua executes successfully on real traffic or that DPI bypass succeeds.

## 7. Strategy Lab / Diagnostics documentation

Update `diagnostics.volt`, help and user guide as needed so every new human-facing string is RU/EN. Explain which profile, L7 and `--payload`/Lua action were actually tested and how to transfer exactly that handler or an independent profile to Strategies, preserving the rest. Surface first-match/overlap warnings without silently changing the user's strategy. Maintain present live/restoration, strategy lab isolation and shared runtime/FD9/IPFW contract. Do not equate a preview/diagnostic success with real network bypass.

## 8. Voice — full RU/EN localization and shared lifecycle

The existing **Voice** GUI, not just new feature text, must be completely localized in the selected OPNsense profile language. This includes section titles, all five service rows (Telegram, Discord, X (Twitter), SIP (VoIP), Custom), parameter help, five IPSET editors/help, status, Apply/Validate/Save inactive draft, preview, info notices, progress/warnings/validation/API errors, and all new descriptions. Use the same i18n contract as Strategies; no fragile visible-English-string matching. Preserve actual user-entered parameters and IPSET data on language changes.

Voice and Strategies remain one common `dvtws2`, one effective WAN from Strategies, one model/config owner, one serialized Apply/rollback lifecycle and existing IPFW ownership. Voice does not gain an independent process, service, config writer, synthetic grammar or WAN selector. Help must explicitly say that non-STUN remains in Strategies, that Voice uses the common engine, and that an enabled Voice profile is **not** proof of a successful voice call.

## 9. Universal translation rule for this scope

Every **new** human-facing GUI text introduced in **any** plugin section by work under this specification (including Lab, Voice, resources, status and backend errors shown to users) requires both RU and EN and follows the user-profile locale. Translation does not mutate technical tokens, input values, raw engine diagnostics or system identifiers. Existing text on **Strategies and Voice** is included in the complete-localization requirement, not exempted as legacy text.

## 10. Compatibility, safety and packaging

- No changes to existing user settings on package upgrade; no re-seeding already initialized Config. Existing empty Traffic Strategy remains valid.
- Preserve WAN-first errors and precedence for actual start/apply when relevant; maintain safe WAN-only save/Stop/setup behavior.
- Preserve normal GUI uninstall/reinstall with retained parameters and full self-removing `--purge` contract.
- Preserve original FD9, only one shared Config writer, one Apply/restore owner, safe atomic rollback, native port/rule ownership and current Voice semantics.
- Native FreeBSD/OPNsense support and physical OPNsense GUI acceptance are explicit final gates. No unrelated speculative platform compat migration.
- Release/testing package uses the native OPNsense `.pkg` path only; do not add SH installers. Do not replace published immutable `v0.6.4_1.pkg`.

## 11. Acceptance matrix (all mandatory)

| ID | Observable acceptance |
| --- | --- |
| A01 | Existing plain domain, wildcard and URL normalization remains correct |
| A02 | `!example.com` preserves verified local-exclusion semantics |
| A03 | `^example.com` restricts matching to the exact domain |
| A04 | `!^example.com` and `^!example.com` both work with verified equivalence |
| A05 | Invalid/repeated modifiers fail with field/line; no silent policy reversal |
| A06 | Reusing the same prohibited file/list type within one profile fails before activation |
| A07 | Reusing the same managed target in distinct valid profiles succeeds |
| A08 | One HTTP+TLS profile retains its two payload/action handlers |
| A09 | Two TCP profiles separated by `--new` retain native first-match order |
| A10 | A runtime lacking `!/^ ` support fails closed, preserving saved/active state |
| A11 | Preview changes no Config/engine/FD9/IPFW/Voice/Additional Resources state |
| A12 | All Strategies labels, visible+popup help, Full Help, messages are Russian for RU profile |
| A13 | The same complete Strategies surfaces are English for EN profile |
| A14 | All existing and new Voice labels, help, actions and errors are RU/EN |
| A15 | RU/EN change, F5, open/help/edit cycles do not modify entered values |
| A16 | Model/backend validation returns detailed errors with user-facing RU/EN rendering |
| A17 | Strategy Lab guidance accurately transfers handlers/profiles without lifecycle regression |
| A18 | Native .pkg update preserves service, user data and ordinary uninstall/reinstall behavior |
| A19 | Existing shared Voice+Strategies actual appliance scenarios continue working |

**Test requirements:** Python is the one normalization authority; PHP and POSIX shell adapter tests use its same corpus; include managed generator output, engine capability negatives, list-resolution duplicate scope, single/multiple handlers, safe read-only preview before/after snapshots, RUNNING/STOPPED, same-app shared Voice, and browser RU/EN screenshots/interaction with OPNsense profile locale. Keep fast source/unit S0/S1 per change, narrowly triggered native S2 where actually necessary, and end-to-end S3 with one proven candidate physical .pkg at release/test-delivery boundary. Record source, CI/package, physical owner acceptance independently; no invented PASS or claim of real DPI success from dry-run.

## 12. Execution boundary and document authority

This specification was **explicitly approved in full by the owner on 11 November 2026**, including additions, caveats and wording from the proposed complete ТЗ. It is the **single detailed normative feature contract** for [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936). The earlier issue body is source/rationale; if its wording says “pending separate approval,” this approval supersedes that pending state. The completed ТЗ v1.3 remains completed and unaffected.

**Owner-approved development plan:** The [staged P0–P6 implementation plan](../history/stages/strategies-2026-11-12/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md) was subsequently **approved in full by the owner on 11 November 2026**. P0 is the immediate next engineering task; P1–P6 follow without redundant approval when P0 confirms actual native behavior. Approval of this specification and plan does **not** claim product implementation, successful CI, installed package or physical acceptance, and does not authorize a speculative version-line transition. No product/runtime files change as part of documenting this approval.


## 13. Canonical list validation and native Help

**Single semantic authority:** `backend/domain_policy.py` alone validates/normalizes content in YouTube/User/Exclude Domains; `backend/ipset_policy.py` alone validates/normalizes all six managed IPSET list contents. Remove duplicate Regex `Mask` from these nine OPNsense `Zapret.xml` fields, NOT from WAN, ports or unrelated model types. Native Model retains field/schema/type/interface/port/Boolean/Option validation and `serializeToConfig()` + `Config::save()`. Both the unprivileged form and privileged original-FD9 worker MUST use the same Python bridges to validate *changed* semantic lists before save, including direct/untrusted server invocation; unchanged existing lists must not be silently rewritten. The sole authorized Config writer, atomicity, WAN-first, Voice and rollback are unchanged. Final engine compatibility `dvtws2 --dry-run` is retained, not substituted for policy. Field+line errors are RU/EN and actionable.

**Help and layout acceptance (in addition to A01–A19):** Strategies `Как найти стратегию` and the whole info row appear only with native `справка` ON, hidden when OFF. Voice `Как работают голосовые профили` and its entire info row obey the same switch. Lab gains a comparable `справка` switch, initially OFF; OFF hides all four original long guidance paragraphs (entire `strategyLabGuidance`), ON reveals them. Lab controls, results and working network checks are never gated by Help. All switchable explanatory prose uses the same font family/size/line height as the native Voice UDP/STUN parameter help («Один нативный UDP/STUN-профиль dvtws2. Обязательны…»), including consistently styled inline code. Check true RU and EN OPNsense user-profile locale and native Help OFF/ON/F5. Do not treat superficial translations or a screenshot of only the ON state as acceptance.

## 14. Bounded large-list transport and Help layout

The shared envelope and root request keep their 65,536-byte admission boundaries. For eligible large list edits, transport a bounded byte-span replacement plus saved-field SHA-256 through the same shared Apply envelope. Original FD9 reconstructs against freshly read native Config, rejects stale/unknown/invalid or overlimit input, and sends the resulting full value through the normal Python/Model/detached-XML/Config transaction. Preview uses the same expansion without saving. Arbitrarily large replacements may still be refused clearly; no second writer or daemon is introduced.

Laboratory Help uses the native page-level gray table row above both sections, right-aligned Info/Help controls and initially OFF. It hides only the existing four guidance paragraphs. Strategies, Voice and Lab switchable Help use 13px, including inline code. Functional controls/results remain visible.

## 15. Scope and acceptance record

The owner accepted the full #936 scope and #1084 appearance correction on 12 November. Exact evidence attribution and historical failures/retries are in PROJECT_STATE, owner receipts and the [full source history](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md). General test policy is referenced from DEV-061/DEV-062 and GH-072 rather than duplicated here. Auto Restart belongs only to #1052 and is excluded from this completed feature's exit criteria.
