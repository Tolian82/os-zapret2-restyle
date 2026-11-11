# P0 — source-verified upstream HOSTLIST/profile evidence and remaining native witness

**Status:** P0 IN PROGRESS — immutable upstream tag/source inspection completed; installed native FreeBSD `dvtws2` runtime and OPNsense GUI not yet exercised. P1–P6 NOT STARTED.
**Baseline:** project `main` `20e8705f5dc058b1dd3ad5d81feaee95f01ed24e` (`v0.6.4_8`) before this source-only research record.
**Scope:** Approved [specification](../architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md) and [P0–P6 plan](../architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md), [Feature #936](https://github.com/Tolian82/os-zapret2-restyle/issues/936).
**Proof boundary:** upstream *source* at a particular immutable tag is not proof that a particular owner's installed executable has those semantics. This report records observed source semantics and precise remaining native acceptance work; it does not claim a passed native functional test or executable capability probe.

## 1. Exact upstream sources inspected

| Upstream object | Tag / Git blob | Direct evidence |
| --- | --- | --- |
| `nfq2/hostlist.c` | `v1.0.6` / `f4e7d290e072ef7b2f5971dd18c08c8b935d2cd8` | strict-match `^` exists; no local-exemption `!` flag path |
| `nfq2/hostlist.c` | `v1.0.7` / `959dc49c6d8613c3541c067c4703588a365c1936` | modifier flag scan, matching behavior, resolved-file duplicate check |
| `nfq2/pools.c` | `v1.0.7` source | `HostlistPoolAddStrLen` indexes only host name; flags set only on first insert |
| `docs/manual.en.md` | `v1.0.7` / `9a8a99862e5b5c031f186e448c25bab541beae98` | `!/^ `, first-match profiles, actions, no native `*` wildcard, duplicate domains |
| `nfq2/nfqws.c` | `v1.0.7` | real `RegisterHostlist` parameter path and `--hostlist`/exclude option boundaries |

References: [1.0.6 hostlist](https://github.com/bol-van/zapret2/blob/v1.0.6/nfq2/hostlist.c), [1.0.7 hostlist](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/hostlist.c), [1.0.7 pool](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/pools.c), [1.0.7 English manual](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md).

## 2. Source-confirmed HOSTLIST and profile semantics

| Case | Upstream-source result | Implementation consequence |
| --- | --- | --- |
| `example.com` | Implicit subdomain search | Preserve current ordinary-domain behavior |
| `^example.com` | `HOSTLIST_POOL_FLAG_STRICT_MATCH`, no subdomains | Preserve exact flag in the managed list |
| `!example.com` | Local exemption flag **in v1.0.7**, absent from v1.0.6 | Missing-capability runtime must fail closed before activation |
| `!^example.com`, `^!example.com` | Scanner accepts `^` and `!` in any order, combines same bit flags | Both valid; canonical order may be `!^` after verification |
| `!!example.com`, `^^example.com`, `!^!example.com` | Raw upstream scanner allows repeated modifier chars; flags remain idempotent | Approved plugin contract explicitly rejects these as malformed, with field+line |
| `*.example.com` | Native `*` wildcard **not supported** | Existing plugin normalization may remove `*.` to yield `example.com`; label this as a transformation that also matches apex domain |
| Same hostname with different flags | `ADD_HOSTLIST_POOL` searches by hostname and sets flags on first insert only | **Do not silently merge** contradictory entries; reject same-host conflicts with clear line and first-entry context |
| `^!example.com` and `!^example.com` repeated | Same flags and same hostname | Treat as equivalent duplicates, optionally canonicalize to `!^` |
| `!example.com` versus global Exclude Domains | Local exemption remains within its own list; exception auto-hostlist behavior explicitly special | Do not convert local exemption to global exclusion |
| Same file repeated in one include/exclude list | `RegisterHostlist_` applies `realpath` then `hostlist_collection_search` and rejects duplicates in the same collection | Detect same resolved-file duplicates within one profile/collection before applying |
| File used by distinct profiles or separate include/exclude collections | Those collections are separate in upstream | Do not reject legitimate cross-profile or include-versus-exclude reuse |
| `--new`, multiple `--payload` / `--lua-desync` | First matching profile selected; multiple Lua instances and intra-profile filters supported | Preserve original profile order and action chains |
| Multiple *different* HOSTLIST/IPSET references in one user profile | Current plugin `profile_normalizer.sh` clones the profile per distinct selector | P2 must establish whether this transformation preserves user intent; never assume clone == native one-profile semantics |

**Native-source details:**
- `v1.0.7` `nfq2/hostlist.c` lines 16–32 parse flags. Lines 203–244 perform exact/subdomain/exemption matching. Lines 267–302 separately check exclude and include lists.
- `v1.0.7` `nfq2/hostlist.c` lines 313–348 resolve real file paths and reject duplicate inclusion **within the same collection**.
- `v1.0.7` `nfq2/pools.c` `ADD_HOSTLIST_POOL` uses `HASH_FIND` by name; only a missing entry receives `flags`. File order wins for exact conflicting same-name entries; pretending two rules coexist would mislead users.

## 3. Current project integration map (read-only)

| Area | Existing entrypoint / limitation | Planned next step |
| --- | --- | --- |
| GUI Apply & domain input | `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php::normalizeDomainList`; plain domain/URL/wildcard normalization with `preg_match` label checks rejects `!` and `^` | P1 PHP modifier-aware parser and stable field/line validation |
| Candidate field scoping | `Api/StrategySettingsPayload.php`; only owner-supported fields may be overlaid; unchanged lists remain untouched | Retain optimistic concurrency and no Config second writer |
| Backend managed hostlists | `backend/targets.sh::targets_normalize_hostlist` (awk), `targets_prepare_managed` for YouTube/User | P1 same corpus and semantically identical normalization |
| Strategy parsing | `backend/parser.sh` splits `--new`; placeholder index deduplicates references | P2 inspect repeated raw references before index loses occurrence count |
| Target/profile pipeline | `backend/target_mode.sh`, `profile_normalizer.sh`, `profile_pipeline.sh`, `generator.sh`, `validator.sh` | P2 validate native profile order/handler preservation and aliases |
| GUI labels and inline help | `forms/general.xml`, `forms/voice.xml` | P3 OPNsense stock translation catalog and popup help |
| GUI dynamic messages | `general.volt`, `voice.volt`, `diagnostics.volt` use `document.documentElement.lang` and inline RU/EN choices | P3 verify actual OPNsense user-profile locale propagation, not browser-only detection |
| Installed runtime | separately installed upstream `dvtws2`, managed through current setup/service | P0/P1 must implement verified capability guard; no version-number guess and no silent failure on `!` |

## 4. Exact P0 native verification still required

**No native executable was available in the current analysis environment.** The following cases must be run as a scoped, safe verification against actual candidate `dvtws2` on supported OPNsense/FreeBSD, or a proven identical installed engine artifact:

1. Validate positive `^, !, !^, ^!` behavior with controlled hostlist and distinguish `v1.0.6` (no local exemption) from supporting runtime, without modifying a running service or IPFW.
2. Test lookup for apex vs subdomains and local exclusion within include versus global exclude; record observed output, not only process exit status.
3. Duplicate hostname with conflicting flags: ensure first-entry native effect is understood and ensure plugin rejects ambiguity instead of falsely claiming both records were applied.
4. Same-realpath duplicate within one include collection, different profiles, include/exclude collection, and symlink aliases.
5. Preserve the intended handler/first-match behavior and run native `dvtws2 --dry-run` for generated candidate profiles as part of P2.
6. Confirm actual installed runtime identity/capability rather than treating `--dry-run` as proof of HOSTLIST `!` matching (the old parser could silently treat it as an unmatched literal).

**Gate status:** P0 source inspection documented; **P0 NATIVE WITNESS OPEN**. P1 cannot be marked accepted until a safe installed-runtime capability check is in place. This report is an evidence record, not a change to the normative specification or approved development plan.

## 5. Test matrix for P1 (prepared, not executed)

Positive: ordinary, exact, locally exempted, exact+exempt in both orders, case normalization, trailing punctuation, empty lines, repeated same-meaning entries, ordinary and modifier+pasted HTTP(S) URLs, existing wildcard-only legacy input, two different hosts.

Negative: doubled/modifier-conflict on the same hostname, missing domain, exact+wildcard, broken domain labels/length, IP/CIDR pasted into domain-only fields, unsupported effective engine, and any attempt to mutate global excluded-domain handling via new local-list syntax.

Compare PHP normalization, shell normalization, saved Config round-trip, managed target text and native runtime behavior. Error diagnostics must identify field/line and never disclose large user strategies in logs.

## 6. Handoff

Continue P0 with isolated native capability proof; then P1 modifiers and shared PHP/shell test corpus; then P2 profile/dedup semantics. The owner has already approved P0–P6. Escalate only actual contract/architecture conflicts and optional improvements proposed openly.

**State after this report:** native P0 verification OPEN; P1–P6 implementation NOT STARTED; no new native package or stable release.
