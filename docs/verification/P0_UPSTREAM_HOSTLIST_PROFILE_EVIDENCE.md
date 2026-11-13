# P0 — source-verified upstream HOSTLIST/profile evidence and remaining native witness

**Status (owner-reconciled 11 November 2026):** P0 COMPLETE from canonical upstream/source review; owner forbids extra engine verification. P1 Python source implementation in progress, P2–P6 not implemented.
**Baseline:** project `main` `20e8705f5dc058b1dd3ad5d81feaee95f01ed24e` (`v0.6.4_8`) before this source-only research record.
**Scope:** Approved [specification](../architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md) and [P0–P6 plan](../history/stages/strategies-2026-11-12/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md), [Feature #936](https://github.com/Tolian82/os-zapret2-restyle/issues/936).
**Authority:** official upstream Zapret2 documentation is canon, and the established `dvtws2 --dry-run` is the accepted validation method. This source study adds no extra engine-test obligation, and no physical owner package acceptance is claimed.

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

## 4. Owner decision supersedes extra native-engine verification

**11 November 2026 — binding DEV-001/DEV-003 («Суслик») reconciliation:** The owner confirms that the [official Zapret2 English manual](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md) and upstream implementation are authoritative. Existing native `dvtws2 --dry-run` is accepted as the strategy validation contract. **Do not schedule extra actual-engine semantic tests, isolated FreeBSD witness experiments or re-proof of published upstream behavior.** P0 is complete for the feature integration/design purpose; P1 proceeds immediately.

The underlying upstream tag/version findings in sections 1–3 remain useful historical context; they are NOT an authorization for more native dvtws2 testing.

**Architecture correction:** the single domain-normalization authority is Python `backend/domain_policy.py`; PHP `DomainSetPolicyBridge.php` and shell `targets.sh` delegate to it. The previous PHP/awk dual-grammar is superseded by the owner's decision. Existing `IPSetPolicyBridge.php` remains and continues to call Python `ipset_policy.py`.

## 5. Test matrix for P1 (prepared, not executed)

Positive: ordinary, exact, locally exempted, exact+exempt in both orders, case normalization, trailing punctuation, empty lines, repeated same-meaning entries, ordinary and modifier+pasted HTTP(S) URLs, existing wildcard-only legacy input, two different hosts.

Negative: doubled/modifier-conflict on the same hostname, missing domain, exact+wildcard, broken domain labels/length, IP/CIDR pasted into domain-only fields, unsupported effective engine, and any attempt to mutate global excluded-domain handling via new local-list syntax.

Compare one Python normalizer across PHP GUI bridge, shell adapter, saved Config and managed target text, with the current standard native dry-run. No separate engine experiments. Error diagnostics must identify field/line and never disclose large user strategies in logs.

## 6. Handoff

P0 completed under the owner decision; proceed with P1 single Python domain policy, then P2 consider safe Python profile parser/normalizer migration, retaining shell entrypoint compatibility. The owner has already approved P0–P6. Escalate only actual contract/architecture conflicts and optional improvements proposed openly.

**Current owner-reconciled state:** P0 integration/source review COMPLETE (no additional engine witness required); P1 Python implementation SOURCE CANDIDATE; P2–P6 not implemented. No new native package or stable release.
