# Dual-stack IPv4/IPv6 and global Exclude IPSet — implementation specification

**Project:** `os-zapret2-restyle`  
**Specification ID:** `DS-EXCLUDE-2026-10-28`  
**Status:** Owner-directed **current first-priority development specification**; implementation, installed-system qualification, and any new package are **not yet complete**.  
**Baseline:** published stable `v0.6.0`, `VERSION=0.6.0`, `PLUGIN_REVISION=1`; immutable released artifacts are not modified.  
**Execution plan:** [ZAPRET2_EXCLUDE_IPSET_PLAN.md](ZAPRET2_EXCLUDE_IPSET_PLAN.md).  
**Owner's final clarification (28 October 2026):** `0.0.0.0/0` and `::/0`, including equivalent full-family unions, are forbidden in **every user-controlled IP list**, both inclusion and exclusion, including Voice.

## 1. Objective and boundaries

Make existing managed targets, all five shared Voice IPSETs (Telegram, Discord, X, SIP, Custom), ordinary Strategies, native FreeBSD 15 IPFW capture, the one `dvtws2` engine, and relevant Strategy Lab endpoints genuinely dual-stack. Add one mixed-family `Exclude IPSet` field directly below `Exclude Domains` on the Strategies page, available in ordinary and Advanced modes, and enforce it against every executable Strategies and Voice profile.

Keep `Exclude Domains` strictly domain-based: no implicit DNS A/AAAA lookup, no domain-to-IP transformation, no hostlist exclusion in Voice/STUN. `Exclude IPSet` is the only global destination-address exclusion for Voice.

**Explicitly out of scope:** all deferred Voice/P2P page redesign from the 28 October engineering discussion: additional per-service `UDP ports` inputs, shared Voice-page IPv6 checkbox, destination-any P2P branch/rules, P2P-only activation without a destination IPSET, new Discord/SIP/RTP/media protocols or broadened STUN-only allowlist. Do not create a separate Voice process, Config store/writer, IPFW owner, cron, DNS cache/watcher, or new Strategy Lab engine. Do not rework NAT/WAN routing, IPv6 network provisioning, Additional Resources Install/Remove architecture, or third-party Lua/BIN content. Historical ideas remain in [`docs/DECISIONS.md`](../DECISIONS.md), not in this delivery.

## 2. Binding requirements

| ID | Requirement |
|---|---|
| DS-01 | Accept single IPv4 and IPv6 addresses and strict IPv4 `/1..32` / IPv6 `/1..128` CIDRs in **all** user-managed IP address lists; use one reusable Python semantic compiler. No user-managed `/0`, including Voice. |
| DS-02 | YouTube Domains and User Domains remain name-based HOSTLISTs. Correct IPv6 packet interception must be tested independently of the domain list. |
| DS-03 | Exactly one mixed-family `Exclude IPSet` input appears immediately below `Exclude Domains` in Strategies, with native RU/EN help, in both ordinary and Advanced modes. |
| DS-04 | Reject explicit `0.0.0.0/0`, `::/0` **and any set effectively covering the entire address family**, including two complementary `/1` networks, in each include or exclude user list. Never infer `any` from an empty list. |
| DS-05 | Destination-address `Exclude IPSet` applies to **every** executable `dvtws2` profile: ordinary TCP/UDP/QUIC Strategies and all enabled Voice profiles. Later profiles cannot bypass the exclusion. |
| DS-06 | If an address matches both an inclusion filter, domain/mode selection, or Voice IPSET and `Exclude IPSet`, no DPI desynchronization/modification is performed on that destination. IPv4 and IPv6 remain separate address spaces. |
| DS-07 | `Exclude Domains` is domain-only in applicable ordinary Strategies; it is **never applied to Voice/STUN** and is not translated to A/AAAA or merged with the IP exclusion. |
| DS-08 | Do not inject `--hostlist-exclude` into any generated Voice/STUN profile. Do not break hostless ordinary UDP or IP-only profiles by blindly inserting a hostname-dependent filter. |
| DS-09 | `--ipset-exclude` is a native **profile-scoped** option; inserting it once at the end of combined `dvtws2` arguments is insufficient. Respect `--new`, named profiles, `--template`, `--import`, and Extra Arguments. |
| DS-10 | Template inheritance and later user-supplied profiles must not remove mandatory global IP exclusions. Preserve supported native profile semantics; reject ambiguous/unverifiable constructions before Apply rather than weakening the exclusion. |
| DS-11 | Existing Voice profiles become mixed-family with `--filter-l3=ipv4,ipv6` and a mixed `--ipset` file, still requiring nonempty user destinations, still STUN-only, and still running in the **one** shared `dvtws2`. Refresh all profile fingerprints and capture proofs accordingly. |
| DS-12 | Extend existing Voice IPFW `type addr` tables and attestation to IPv4 plus IPv6. Preserve current table names, owned rule range, WAN, divert guards, FD9/setup locks, stage/swap, transaction and rollback. An IPv4-only WAN must remain usable. |
| DS-13 | Detect Voice conflicts by **same address family + network overlap + UDP port overlap**. Different families do not overlap. Reject conflicts before any live mutation; no hidden collapse or duplicate-profile priority shadowing. |
| DS-14 | Strategy Lab accepts a domain, fixed IPv4, or fixed IPv6; where applicable it preserves explicit Host/SNI. Prove actual IPv6 A/AAAA endpoint pinning, baseline, TLS, selected QUIC, candidate, source attribution, replay and restoration through existing Lab paths. |
| DS-15 | Tests use the same real compiler, engine and IPFW entrypoints as normal service activity; no separate fake production path, duplicate owner or independent profile generator. |
| DS-16 | An IPv4-only installation continues working. Unavailable IPv6 connectivity is shown as `SKIPPED`/`UNAVAILABLE` for affected diagnostics, never as an IPv4 failure or fabricated IPv6 PASS. |
| DS-17 | Preserve one native OPNsense `/conf/config.xml`, one established `Config::save()` owner, common Strategies/Voice Apply, and internal service namespace **`zapret`**. Config persists across F5, reboot, Start/Stop and upstream changes. |
| DS-18 | Failure before commit leaves previous Config, PID/service, managed release and IPFW state unchanged. A save attempted but not conclusively attested is reported as uncertain; never claim an unproven rollback. |
| DS-19 | Existing Additional Resources Install/Remove use the same **updated** saved-Config-to-common-build-to-native-Start path. No separate parsing, state store or recovery architecture is introduced. |
| DS-20 | Source tests and CI do not substitute for installed FreeBSD 15 / OPNsense evidence of mixed-family IPFW/divert, real IPv6 TCP/UDP/QUIC, or global exclusions. Each level of evidence is reported separately. |
| DS-21 | Enforce the full-family prohibition **independently for each** user IP list; inspect the effective union even when an include list retains its original non-collapsed representation. Internal wildcard sentinels used solely for native profile analysis are **not** user IPSETs. |
| DS-22 | Close all supported user-supplied IP inputs: Strategies and Voice fields, managed Targets, IPSET placeholders, and native `--ipset-ip` or referenced `--ipset` data where accepted by the plugin. Reject unverifiable external files or full-coverage bypass attempts before Apply. |
| DS-23 | Voice migration changes only the **existing** shared IPSET and `enabled`/`args` fields and their IPv4/IPv6 handling. No per-service port field, new IPv6 checkbox, destination-any P2P rule/profile, media behavior or layout redesign. |
| DS-24 | An enabled Voice service with an empty/absent IPSET remains invalid; OFF drafts remain editable without implicit activation. Do not synthesize `/0`, a two-`/1` equivalent, `to any` or a second Voice path. |

## 3. Input, canonicalization and full-family rejection

1. One address or CIDR per line; allow CRLF and blank lines. Reject hostname, URL, IPv6 zone index (`%iface`), malformed address, range syntax, wrong prefix, and CIDR with nonzero host bits, reporting field name, source line and reason. **Never trim `:` from the ends of IPv6 values**, including `::`.
2. Any legacy harmless punctuation tolerance for old IPv4 fields may be retained **only after a regression test** proves it is needed and cannot corrupt IPv6. Do not replace the existing saved Config format merely for normalization.
3. Canonicalize IPv6 with Python `ipaddress` compressed lowercase form. Treat `/32` IPv4 and `/128` IPv6 as equivalent to corresponding hosts for de-duplication; never coerce a family.
4. For `Exclude IPSet`, apply `ipaddress.collapse_addresses()` **separately per family**: deduplicate, remove contained prefixes and combine adjacent CIDRs only if the resulting union is identical. Order deterministically by family/network/prefix; enforce no `/0` **both before and after** collapse.
5. For **each include list**, normalize/deduplicate its output but also use a separate copy-only collapsed view for the effective full-family test. A two-`/1` union fails even when the actual output is not collapsed. Do not merge different services or conceal genuine Voice overlap.
6. Explicitly test `::`, IPv4-mapped IPv6 and other ambiguous textual forms against the selected `ipaddress` policy; do not normalize IPv4 and IPv6 network sets into one accidental family. Reject noncanonical or unsafe inputs at the established validation boundary and preserve compatible saved values where they are valid.
7. Apply documented byte, item-count and path limits **before** allocation/work or writing staged files. Invalid input must not partially replace prepared artifacts.
8. Use a dedicated temporary staging directory and deterministic atomic writes; no writer may modify active release files during validation.

### Canonical example

```text
Exclude IPSet input:
192.0.2.0/25
192.0.2.128/25
2001:db8:abcd::/48
2001:db8:abcd::1

Expected normalized exclude file:
192.0.2.0/24
2001:db8:abcd::/48
```

Both `0.0.0.0/1` plus `128.0.0.0/1`, and `::/1` plus `8000::/1`, are **invalid** whenever supplied together in one user-managed include/exclude list. This constraint does **not** remove internal logical address-universe representations used in hostless conflict analysis; those never become user files or bypass the policy.

## 4. One IPSET compilation per candidate

- Implement one bounded reusable Python module `backend/ipset_policy.py`; one **batch** operation consumes the candidate's six user lists: Telegram, Discord, X, SIP, Custom and global Exclude. Retain current published managed file paths (`ipset-telegram.txt`, `ipset-discord.txt`, `ipset-x.txt`, `ipset-sip.txt`, `ipset-custom.txt`) and add `ipset-exclude.txt`.
- Emit an immutable candidate `ipset-manifest.json` with a versioned schema, normalized SHA-256 hashes, per-family networks, cardinalities and any bounded interval evidence necessary to compare Voice destination scopes. This is an **output witness**, not a second mutable cache or alternate Config owner.
- All downstream compiler, capture-plan, validation and IPFW consumers reuse the single **prepared** semantic result. Verify file content, identity/hash, and the **actual installed** table/rule state at their trust boundaries; do not blindly trust an external JSON file. `targets_normalize_ipset()` may remain as a compatibility wrapper, but not a second parser with different semantics.
- The native template `zapret.conf` exposes the new saved `EXCLUDE_IPSET` value. Native root staging, model XML, detached-save evidence and final engine arguments must refer to the **same** candidate and digest. Preserve atomic `SharedConfigCommit` semantics, saved-draft behavior, race protection and native Apply rollback.

## 5. Strategies GUI and persistence

- Add a multiline `Exclude IPSet` field immediately after `Exclude Domains` in the OPNsense Strategies form/model. Make it visible in normal and Advanced modes; default is empty and preserves existing behavior.
- RU help: "IPv4/IPv6-адреса и CIDR-сети, исключённые из DPI-обработки для всех стратегий и голосовых профилей. Одна запись в строке. `0.0.0.0/0` и `::/0` (включая полное покрытие несколькими сетями) запрещены."  
  EN help: "IPv4/IPv6 addresses and CIDR networks excluded from DPI processing in all Strategies and Voice profiles. One entry per line. `0.0.0.0/0` and `::/0` (including an equivalent union) are forbidden."
- Preserve `Exclude Domains` directly above it. Do not resolve or reinterpret domain exclusions as IP addresses. The new input belongs to the Strategies settings scope and must not be silently overwritten by a stale Voice form. Continue using one OPNsense model, Config writer, common Apply and standard errors.
- Update the existing five Voice IPSET help strings to explain dual-stack and `/0` rejection. **Do not** add, move, or reinterpret Voice controls or its existing UDP-port parameters in this phase.

## 6. Profile-wide exclusion semantics

- Compare `Exclude IPSet` against the **remote destination IP**, in both families, even when a broader inclusion filter, hostlist or Target Mode would otherwise select that packet. An IPFW divert counter may still increase: the guarantee is **no DPI modification**, not necessarily avoiding capture overhead.
- Implement global IP exclusion on **each** executable native profile, after resolving template/import/new/extra semantics. Check the final profile/argv fingerprint; a protected profile cannot be shadowed by a later unprotected fallback.
- `--hostlist-exclude` remains a **domain** policy only in appropriate ordinary Strategies profiles. Existing append-once behavior is insufficient for multiple profiles; do not inject into Voice/STUN or hostless UDP in a manner that disables its selection. Do not perform DNS A/AAAA expansion or add TTL/cache logic.
- Check supported user-supplied native inline `--ipset-ip`, reference `--ipset`, and named host/IP placeholders. Any path that could bypass mandatory `Exclude IPSet` or universal `/0` rejection must be validated or rejected before Apply. Normal internal `any` constructs for ordinary IPFW or Target Mode are outside the user-IP-list ban.
- Keep existing runtime ordering, user-supplied non-STUN strategy behavior and Extra Lua/BIN functionality except where the mandatory safety policy explicitly rejects an ambiguous input.

## 7. Existing Voice and native IPFW dual-stack

- Set existing Voice profile L3 selection to `--filter-l3=ipv4,ipv6`. One named service IPSET may hold IPv4 and IPv6 simultaneously; no separate mandatory IPv6 input or second service is introduced.
- Update `voice_profile_compiler.py`, `voice_capture_plan.py`, `voice_traffic_merge.py`, `voice_release_stage.py`, `voice_ipfw_adapter.py`, and `voice_firewall_transaction.py` consistently. Check same-family network/port overlap, common output paths, profile hashes, final argv identity, and destination-scoped IPFW rules.
- Prove FreeBSD 15 `type addr` mixed-family add/list/readback, canonical `/32` and `/128`, stage/swap/cleanup, foreign-owner protection and exact rollback. Do not silently change current table names, plugin-owned rule range or `out not diverted not sockarg` WAN loop protections.
- Existing `--filter-udp=*` means **all UDP destination ports only to that service's IPSET addresses**, not all UDP to the internet. An empty enabled service IPSET is rejected. Do not add destination-any P2P capture, a new Voice IPv6 checkbox or any new protocol/media classifier.
- Distinguish verified STUN processing from successful bidirectional call media. MEDIA/CALL bypass results are not requirements of this IPSET/dual-stack release.

## 8. Strategy Lab dual-stack

- Support an IPv6 literal endpoint and domains returning A and/or AAAA. For every test fix exactly one family/remote address plus optional domain Host/SNI identity; preserve certificate, proxy-bypass and **ECH-off** behavior between baseline, candidate and replay.
- Use correctly bracketed IPv6 URLs and verified curl/Chrome pinning (`--resolve`/`--connect-to` where appropriate), never silently fall back to IPv4 or substitute a different remote IP.
- Update existing Lab target, request, probe, firewall, worker, candidate and results paths rather than inventing a parallel IPv6 tester. Verify the same bounded IPFW Lab owner/counters/source-port attribution and Stage 40/60/70/85/90 cleanup/restoration.
- Enable IPv6 QUIC and generic UDP evidence only where the production probes truly support them. Missing IPv6 routes, unsupported browser cases or a target without a valid TLS identity return honest `UNAVAILABLE`/`SKIPPED`/technical errors; they do not become fake candidate success.

## 9. Native lifecycle and security

The only live Apply is existing `shared_apply_prepare_service()` → `orchestrator_build_release(..., shared-candidate)` → native validator → managed activation/health → native Config commit. Keep existing safeguards for global OFF/stopped service, FD9/setup locking, FreeBSD cold-IPFW initialization and previous-owner restoration. `RESTORE_FAILED` is a blocker. Installation and removal of Additional Resources must use the same real saved Config and common compiler, never a duplicate field parser or second recovery mechanism. Do not mutate immutable published `v0.6.0` assets. A new development stage/package follows `DEV-027`–`DEV-040`; stable publication still requires an explicit owner instruction.

## 10. Acceptance criteria

| ID | Observable acceptance |
|---|---|
| A01 | Old IPv4-only Config/Strategies/Voice survives Apply, F5, Start/Stop, reboot; prior DPI functionality is not lost. |
| A02 | `Exclude IPSet` is directly below `Exclude Domains` in both GUI modes, with correct RU/EN help; empty field is behavior-compatible. |
| A03 | Mixed IPv4/IPv6 input is compiled once; deterministic files and bounded manifest hashes agree. |
| A04 | Exclude duplicates/contained/adjacent networks are collapsed without adding or removing any address. |
| A05 | All user include/exclude/Voice lists reject explicit `/0` and effective full-family coverage via two `/1`, with field/reason and **no live mutation**. |
| A06 | IPv6 `::`, trailing `::`, `/128`, zone index, malformed host bits and old IPv4 forms are handled or rejected correctly. |
| A07 | Excluded destination is never modified by first/middle/last Strategies profiles, including `--new`, templates, imports and Extra. |
| A08 | Excluded IPv4/IPv6 destination is never modified by any of the five Voice profiles; eligible non-excluded STUN still works. |
| A09 | `Exclude Domains` affects applicable ordinary domain-aware Strategies only; no DNS conversion and **no Voice/STUN hostlist exclusion**. |
| A10 | Existing YouTube/User Domains HOSTLIST actually works via both routed IPv4 and IPv6. |
| A11 | IPFW `type addr` mixed-family tables support add/read/stage/swap/destroy/rebuild and exact previous-owner restoration on installed FreeBSD 15. |
| A12 | Voice `--filter-l3=ipv4,ipv6`, final argv SHA, IPSET family and IPFW rule/capture attestation agree. |
| A13 | Same-family overlapping Voice destination+UDP scope rejects Apply; distinct address families do not create false overlap. |
| A14 | Real native engine dry-run tests final exclusion paths, identity, permissions, hashes, placeholders and tampering. |
| A15 | Lab IPv6 literal/AAAA with Host/SNI, browser/ECH-off, TLS, applicable QUIC, fixed-IP replay and route/family attribution are real, not synthetic. |
| A16 | IPv4 WAN without IPv6 remains functional; IPv6 checks report unavailable/skipped truthfully. |
| A17 | One OPNsense Config remains authoritative; no extra save or duplicate no-op revisions. |
| A18 | Pre-commit failures and controlled activation faults preserve or correctly restore prior PID, Config, release, IPFW and tables; uncertain saves remain explicitly uncertain. |
| A19 | Extra Resources Install/Remove uses the updated real saved-Config/common-build path without losing dual-stack or Lua/BIN/rollback state. |
| A20 | Run applicable focused unit/contract/integration, full CI/FreeBSD package qualification, and required installed OPNsense acceptance; distinguish execution levels. |
| A21 | Alternate native managed/inline IPSET entries and all five Voice lists cannot bypass `/0` prohibition through multi-prefix representation or an untrusted file. |
| A22 | Empty enabled Voice destinations are rejected on Apply and native saved-draft preview; existing args/ports remain unchanged without IPFW mutation. |
| A23 | Voice GUI layout remains unchanged: only existing IPSET dual-stack/help/errors update, without P2P UDP inputs or shared IPv6 checkbox. |
| A24 | No destination-any Voice P2P profile, P2P IPFW rule or broad-UDP load test is introduced; existing destination-IPSET STUN, single engine and rollback remain intact. |

## 11. Evidence and authority

**Current baseline sources:** [`START_HERE.md`](../START_HERE.md), [`PROJECT_STATE.md`](../PROJECT_STATE.md), [`REQUIREMENTS.md`](../REQUIREMENTS.md), current native backend and [Voice specification](VOICE_TRANSMISSION_GUI.md). **Upstream:** `bol-van/zapret2/docs/manual.en.md` for profile-scoped excludes, IPv4/IPv6 IPSET semantics, template/import/new, and L3 filters; FreeBSD 15 `ipfw(8)` for actual mixed-family table/capture behavior. These external platform facts remain **required live verification**, not claims of installed success.

This specification is **approved intended behavior, not implementation evidence**. The corresponding [per-file plan](ZAPRET2_EXCLUDE_IPSET_PLAN.md) assigns implementation, tests and documentation to stages. Deferred Voice/P2P exploration is preserved only in [`DECISIONS.md`](../DECISIONS.md).
