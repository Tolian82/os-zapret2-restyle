# Native Auto-detect, Target Mode, HOSTLIST and Auto Restart — specification v1.0

**Status:** APPROVED CURRENT WORK / PARTIAL SOURCE IMPLEMENTATION. Production Auto-detect automation, Auto Hostlist and scheduled restart are not complete; [PROJECT_STATE](../PROJECT_STATE.md) owns exact progress.
**Primary owner authority:** [Issue #1052 and the 13 November 2026 owner correction](https://github.com/Tolian82/os-zapret2-restyle/issues/1052). The [earlier consolidated comment](https://github.com/Tolian82/os-zapret2-restyle/issues/1052#issuecomment-6798093626) remains historical wherever superseded.
**Execution companion:** [P0–P5 development plan](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). P0 native feasibility completed with [immutable receipt](https://github.com/Tolian82/os-zapret2-restyle/issues/1052#issuecomment-6838843832); [P1 policy/source and package boundary](../verification/P1_AUTO_DETECT_DOMAIN_POLICY.md). P2–P5 are only partially implemented in source; production observation, live ownership and installed acceptance are not established.
**Related scopes:** [completed #936 HOSTLIST/RU-EN/preview specification](ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md) and separate [future #1040](https://github.com/Tolian82/os-zapret2-restyle/issues/1040). Preserve original owner-accepted #936 behavior and all existing WAN-first, FD9, shared Voice, IPFW, Config, Apply and native package contracts.

The original #1052 issue body remains intact as **discussion history**. Superseded historical ideas (HOSTLIST changes awaiting restart, staged/active list pairs, skipping scheduled restart on unchanged lists, read-only Auto Hostlist and Strategy Lab involvement) are **not** requirements. Consult the [official upstream Zapret2 manual](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md) and actual qualified installed engine source for native semantics. **Strategy Lab must remain untouched at every stage.**

## 0. Mandatory file and selector separation

Native `--hostlist-auto=<filename>` accepts a user-specified filename: the engine does **not** mandate a basename. It is distinct from this product's `<HOSTLIST:auto>` placeholder.

| Role | Accepted source |
| --- | --- |
| Native raw discovery input | Protected **`inbox.txt`**, a separate file for `--hostlist-auto` |
| Durably rotated, unprocessed raw events | **`pending/<id>.txt`**, on the same filesystem |
| Normalized shared final HOSTLIST | **`/usr/local/etc/zapret2/ipset/auto-domains.txt`** |
| Explicit `<HOSTLIST:auto>` in Traffic Strategy | **Only final `auto-domains.txt`**; generated as ordinary `--hostlist`, never `--hostlist-auto` |
| Editable GUI `Auto Hostlist` / «Найденные домены» | Read/edit **only final `auto-domains.txt`**, never raw inbox/pending/debug |

The final file is an editable intermediate accumulation of **verified normalized** domains, including manual `!` exclusions. If a profile explicitly opts into the file, **successful bypass is not guaranteed**. Without such a selector the file may accumulate for manual sorting, but no profile may implicitly use it. Detection by itself does **not** create a universal strategy.

**Owner decision (13 November 2026; supersedes the earlier migration requirement):** `zapret-hosts-auto.txt` is an obsolete pathname from the historical registry/runtime code, **not a source of useful data for this feature**. Its prior contents have **no retention or migration requirement**. The new implementation MUST NOT read, copy, merge, migrate, import, recreate or use this file, including on first GUI read, normal Apply, upgrade, reinstall or Auto-detect startup. No legacy merge button, import API, migration journal or legacy fallback is part of the approved product. The native raw `--hostlist-auto` inbox/pending and the new editable final `auto-domains.txt` are independent, as shown in the table above. **Preservation still applies to actual new `auto-domains.txt` user edits, canonical manual HOSTLIST/Config values and new verified discoveries**, not obsolete legacy data. Source `v0.6.5_27–_28` historically contained first-copy and user-triggered legacy merge; these contradicted the corrected specification and **were removed from active code in source `_30`**. The historical proof remains non-normative. Historical source/verification evidence remains available as chronology, not product authority. Any on-disk retirement of an existing legacy pathname must be scoped to proven plugin-owned files and the native package/cleanup contract; do not delete unrelated user files by guessing ownership.

## 1. Goal, boundary and non-goals

Use actual **native `dvtws2` discovery**, append events to the dedicated raw input, have one short **Python worker run once per minute**, normalize each candidate to its registrable root and apply exclusions/deduplication, then route it either to a known HOSTLIST's auto-owned component or to the shared final `auto-domains.txt`. Add an **editable** Auto Hostlist to Strategies and an independent, optional **Auto Restart** scheduler.

Do **not** change Strategy Lab; test or choose working DPI bypass profiles; convert DNS to IPSET; infer HOSTLIST origin from matching IP; spawn another production `dvtws2`; add a competing `config.xml` writer; independently mutate IPFW/PF; or ship an SH installer. A detected domain is **not proof of a working bypass**.

## 2. Target Mode — existing facts and required transition

Existing `target_mode.sh` accepts `all`, `list`, `auto`. Target policy applies **to each original source profile without explicit `<HOSTLIST:...>` / `<IPSET:...>`**. Explicit selectors survive; `--new` separates profiles. The Python `profile_policy.py` may expand one source profile with multiple selectors into sequential native profiles: **first matching profile wins**, so order is material. Historical source before P2k5: `all` injected no lists, `list` injected YouTube/Telegram/User, and `auto` additionally injected `<HOSTLIST:auto>` (ordinary `--hostlist`, **not** real detection). Source `_27` has already stopped implicit `auto` injection. The remaining obsolete legacy import is explicitly rejected in section 0.

The **required** new contract:

- `Target Mode=auto` **enables observation/discovery**, not automatic assignment of unknown domains to a profile.
- **Remove implicit `<HOSTLIST:auto>` injection** when `auto` is selected. Only **an explicit `<HOSTLIST:auto>` in the Traffic Strategy text** authorizes that particular profile to process final `auto-domains.txt` as an ordinary HOSTLIST.
- Preserve `all/list`, native `--new` and native filters, explicit user selectors, ordered first-match behavior and manually maintained lists.
- **No Auto-detect in IPSET-only, `<IPSET:telegram>` or mixed HOSTLIST+IPSET profiles**. IPSET address membership says nothing about a domain's HOSTLIST. Do not change IPSET, Voice or their rules.
- Do not invent a global unknown-domain bypass strategy; native profile selection retains priority.

### 2.1 Owner clarification: Target Mode choices are not simultaneous operating modes (13 November 2026)

The Strategies GUI selects **one** Target Mode at a time. Do not use the `all` mode's intentionally broad, port-based strategy as though it were a second default strategy concurrently activated by choosing `auto`. This was an illustrative but **inapplicable default-mode conflict**, not a new issue in the owner's accepted product logic.

| Selected Target Mode | Intended behavior for a source profile without explicit targets | Native Auto-detect |
| --- | --- | --- |
| **All traffic on specified ports** (`all`) | No default HOSTLIST/IPSET restriction; an authorized broad DPI profile can handle all matching traffic | **Not enabled by this mode**; missing auto discoveries are not a fault of `all` |
| **Only specified domains** (`list`) | Apply established YouTube/User HOSTLIST and Telegram IPSET default targets, subject to their existing profile expansion | **Not enabled by this mode** |
| **Auto-detect blocked domains** (`auto`) | Retain applicable default known targets, **remove implicit** `<HOSTLIST:auto>` and enable separately isolated native detection | **Enabled**, but finding a domain does not authorize a DPI profile to use the shared fallback |

**Concrete example:** if `video.example.com` is genuinely discovered in `auto` mode and no sole permitted source HOSTLIST can be proven, the native engine records the raw hostname in `inbox.txt`; the minute Python worker validates it, normalizes it to `example.com` via PSL eTLD+1 and writes it to `auto-domains.txt`. **Without explicit** `<HOSTLIST:auto>` **no strategy applies to that shared entry**. With an unambiguous source `<HOSTLIST:X>`, the normalized entry instead belongs to that list's distinct auto-owned component. This example assumes a confirmed native discovery, not universal detection of every failed connection.

**Technical scope:** Target Mode is a **per-source-profile default**, not a ban on advanced strategy composition. An explicit `<HOSTLIST:...>` or `<IPSET:...>` suppresses default target injection for that source profile; manually authored `--new` profiles, native filters, `--template`/`--import` and Python profile expansion still determine actual ordered profiles. Thus a generic `all`-mode first-match example is **not evidence of an `auto`-mode defect**. P0 must verify only **real generated `auto` configurations** and distinguish their limited discovery coverage, if any, from domain-routing semantics. Do not reopen this settled GUI-mode distinction without a reproducible generated-profile counterexample.

## 3. Required attribution and routing matrix

| Event or state | Required result |
| --- | --- |
| Native event unambiguously originates in permitted `<HOSTLIST:youtube>`, `<HOSTLIST:user>` or another `<HOSTLIST:X>` | Immediately add to **that HOSTLIST's auto-owned component**, never its manual list |
| Source strategy/HOSTLIST unknown, stale or ambiguous | Add to shared **`auto-domains.txt`** fallback |
| Shared file populated but no explicit `<HOSTLIST:auto>` | Continue accumulation and display; **do not** implicitly process |
| Explicit `<HOSTLIST:auto>` in a particular profile | Only that profile uses the shared final file through ordinary `--hostlist` |
| IPSET-only or mixed HOSTLIST+IPSET source | **No Auto-detect** |
| IP matches any IPSET | No domain assignment based on IP |
| Global Exclude Domains or applicable approved user `!` | No new positive auto entry |
| User simply deletes a positive shared-list line | A **new** later detection may re-add it; no permanent deletion blacklist |

When a known HOSTLIST attribution is sound, insert **without Strategy Lab, testing whether the bypass works, or waiting for user approval**.

## 4. Native event evidence and generation-bound profile attribution

Configure native `--hostlist-auto=<raw-inbox>` for discovery and `--hostlist-auto-debug=<debuglog>` as **supporting** profile number/name evidence. Upstream [`nfq2/desync.c`](https://github.com/bol-van/zapret2/blob/master/nfq2/desync.c) writes `adding to ...` debug text **before** the actual `append_to_list_file`. A log line alone is **not proof** of successful raw append. Fail-counter, reset, retransmission, error and `NOT adding` records do not count as positive discoveries.

The generator must produce a map **bound to the exact generated-profile generation**: final native profile → source strategy → single HOSTLIST or unknown. Never assume profile numbers survive `--new`, `--template`, `--import`, Python expansion, Target Mode changes or Apply. If old-generation evidence cannot be safely correlated, use shared fallback; **never guess** by IP, domain or similar strategy. Correlate native debug logs by file identity, offsets, partial lines and matching rotated segments; persist the confirmed reader cursor.

**P0 is a mandatory technical feasibility gate:** Native `--hostlist-auto` both writes discovered domains into its file **and uses that file as an including HOSTLIST in the same native profile**. Therefore the raw inbox is **not passive logging**, and rotation alone does not guarantee isolation. **Before editing any production strategy**, prove on the actual qualified `dvtws2` and our first-match rules that discovery does **not** covertly activate any profile using an unapproved target and does not include IPSET. If no safe solution exists without a separate owner decision, **do not release/implement an unsafe workaround**; stop at proven facts and report the blocker. A second production engine or upstream source patch is not authorized.

## 5. Once-per-minute native cron/configd worker

**Current source boundary, P2k8j (`_40`):** only the original OPNsense `actions_zapret.conf` configd command `auto_detect_minute` is registered. The short `auto_detect_minute.py` checks an inactive original release (no raw/debug native-auto options and no active generation map) or refuses unqualified forged/unsafe release state, with no queue/Config/HOSTLIST mutations. **No native cron schedule is installed; no active native observer is authorized.** Activating a real 60-second cron entry must be coupled to the already-approved bounded, locked, generation/FD/debug-proven durable worker and ACK. [Exact incremental evidence](../verification/P2K8J_CONFIGD_MINUTE_INGRESS.md).

The owner's selected schedule is final: **every 60 seconds**, using normal OPNsense **cron → registered configd action → one short Python worker**, not a long-running kqueue watcher/second daemon. Do not restart `dvtws2` or call common Apply for every new event. Missed ticks keep the queue for the next run. One pass may take longer than a minute; other invocations must not overlap its exclusive lock.

Multiple discoveries in a minute, repeated hosts, arbitrarily deep subdomains, competing sources and crash retries must normalize/deduplicate **idempotently**, not blindly copy raw lines.

### 5.1 Storage and ownership

- **`inbox.txt`:** raw native producer, not the final HOSTLIST.
- **`pending/<unique-id>.txt`:** hard-linked old-inode segments still awaiting acknowledged processing.
- **`debuglog` + acknowledged read state:** attribution/diagnostics, not a second persistent HOSTLIST.
- **`auto-domains.txt`:** the only general editable unknown-domain HOSTLIST.
- **Known HOSTLIST auto components:** separate from user's YouTube/User Domains saved in `config.xml`.

Qualify actual paths, identities, file modes and permissions against the installed package and storage registry. Inbox, prepared replacement and pending **must share a filesystem**. `/var/db/zapret2-restyle/auto-detect/` is illustrative; follow approved storage policy for the exact location.

### 5.2 Approved atomic rotation protocol: hardlink + replace

1. Obtain an **exclusive single-worker lock** and coordinate GUI/final-file conflicts without breaking the **original shared-service FD9**. Resume all pending segments from prior runs.
2. Prepare a new **empty, safe regular file** with verified `dvtws2` write permissions; check directory, type, ownership, unsafe symlinks and size limits.
3. **`os.link(inbox, pending/<unique-id>)`** on one filesystem preserves the **old inode**. Verify dev/inode and durable directory metadata; never remove its final name before processing confirmation.
4. **`os.replace(prepared-empty, inbox)`** and persist directory changes. Upstream [`nfq2/helpers.c`](https://github.com/bol-van/zapret2/blob/master/nfq2/helpers.c) opens with `fopen(filename,"at")` and closes with `fclose`; a new writer open reaches the new inode, an existing open FD still writes to **old pending**.
5. **Before parsing is final or removing pending**, prove that the **verified `dvtws2` owner process** has **no writer FD on the old dev/inode**. Qualify FreeBSD `procstat -f` / `fstat` or equivalent. If process identity, FD closure or last-line completeness is unproven, **keep pending and retry**. **Do not delete pending based on age.**
6. Recover **crash after link but before replace**: pending can still refer to the **current live inbox** and cannot be closed/removed. Also recover crash after replace/before fsync, after result commit/before unlink, re-entrant cron and reboot.
7. Parse only complete pending data, correlate confirmed debug/profile attribution, normalize/exclude/deduplicate and write appropriate permanent destination lists.
8. Require durable success for **all processed valid results** (file and directory fsync where needed). If any destination write remains incomplete, **retain source pending**. Retry is **at-least-once + idempotent**, not exactly-once.
9. Delete **only fully acknowledged pending** and persist deletion. **Never zero the live inbox. `truncate` and `copytruncate` are forbidden.**

Explicitly qualify `fopen` before replace, writer FD persisting after replace, concurrent appends, incomplete final line, disk/write errors, interrupted operations, reboot, wrong ownership and corrupt or oversized pending. **Never start/restart `dvtws2` to clear input.**

## 6. One existing Python domain policy: roots, depth and exclusions

Extend existing **`backend/domain_policy.py`**, not a competing PHP/shell parser. The [P1 implementation](../verification/P1_AUTO_DETECT_DOMAIN_POLICY.md) extends its existing syntax normalizer with qualified eTLD+1 and multilist planning; it does not yet run the production worker.

- Use qualified [Public Suffix List](https://publicsuffix.org/) data with **ICANN and PRIVATE** entries. `video.example.co.uk` → **`example.co.uk`**, never `co.uk`. `user.github.io` → **`user.github.io`**, not `github.io`. Never simply take the last two labels.
- `domain.com`, `www.domain.com`, `voice.domain.com` and `a.b.domain.com` → **one `domain.com`** row even with many events in one minute. **Do not automatically prefix `^`**. `*.domain.com` is not supported native HOSTLIST syntax.
- [Official native filtering rules](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md#filtering-by-lists): `domain.com` matches the name and arbitrarily deep subdomains; `^domain.com` matches exactly; `!domain.com` is a local HOSTLIST exclusion; `!^domain.com` and `^!domain.com` are exact local exclusions. **Preserve manual `!`/`^`.**
- Validate Unicode/IDNA/ASCII, length, labels/dots, blank/broken values, IP literals and bare public suffixes. Unknown/invalid PSL or host data must **not** become an unsafe broader root: reject safely and retain diagnosable failure/unprocessed state as required by durable recovery policy.
- Attribute **profile first**, then normalize and deduplicate **in the destination HOSTLIST**, never through IPSET. Conflicting origins for the same root follow **ambiguous → shared fallback**, without contradictory automatic records.
- Check **all user HOSTLISTs**, shared Auto Hostlist and auto-managed components before positive insertion. A broad **`!domain.com` in any** prevents a matching new positive in any list, although upstream `!` remains local **when processed by its own profile**. Exact `!^domain.com` / `^!domain.com` blocks only the appropriate exact name, respecting the originally discovered host and normalized candidate; do not spread it to all subdomains. Never rewrite or relocate manual entries.
- A plain deleted positive may be re-added by a **new** detection; there is no perpetual deletion blacklist. Do not add a candidate already covered by a positive entry in the target list.
- **Global Exclude Domains** remains a separate policy from any HOSTLIST's native local `!`.

## 7. Final files and editable Strategies GUI

- Immediately **after User Domains** on the **Strategies** page, display an equivalent **editable multiline `Auto Hostlist` / «Найденные домены»** field backed by **`/usr/local/etc/zapret2/ipset/auto-domains.txt`**. Show collected data even if `<HOSTLIST:auto>` is absent; never show raw inbox/pending/debug.
- Allow user **addition and deletion**, including `!`. No restart needed. Do not write directly to `config.xml` or create another writer. Protect updates against a concurrent worker.
- Guard against **stale open GUI forms** silently overwriting new worker/user entries: check revision, merge safely or return a clear conflict. In RU/EN distinguish an **empty**, **missing** and **unreadable/error** file.
- Preserve data across Apply, native `.pkg` upgrade, normal GUI uninstall/reinstall. Approved full purge clears it. Never overwrite current user data from a startup default.
- Effective known HOSTLISTs combine manual plus separate auto-owned content, **without background writing into YouTube/User Domains text or `config.xml`**. Generator/validator and storage permissions must support native hot reload. **Current implementation boundary:** P2k8b keeps the prospective known-list automatic components in root-private `/var/db/zapret2/auto-detect-owned/{youtube,user}.txt` with an explicit sealed clean-baseline manifest. Source `_33` composes these components into the genuine detached generator; source `_34` adds an **unregistered, source-tested durable relocation bridge** for previously sealed automatic rows from known lists to shared fallback. Source `_35` adds the **source-tested original native Config-held synchronous Model/P1/durable-commit callable**; source `_36` connects the existing P2a original queue lock, native PHP Config handle and Python P2k8d/P2k2b transaction with OS-inherited same-open-file-description FDs and independent queue/Config inode/lock verification. The original Config lock remains held while PHP waits for the child to finish; the generated files still use the existing destination flock. Source `_37` adds a **dedicated native OPNsense/FreeBSD qualification in the existing disposable P2e/P2g/P2i VM**: actual native `Config` object and `config.xml` flock, inherited FD queue/PHP/Python process chain, Config early-unlock refusal without actual `save()`, killed PHP parent while child retains both locks, and unchanged config.xml inode/hash. The genuine guest has `/conf` and `config.xml` owned by UID 789 / GID 0 with protected 0755/0640 modes; the original root-only assumption was false and is now corrected **only for that fixed original Config path**, accepting a dynamically matched file/parent/FD UID with GID 0 and no group/other write. The queue, pending and root-private receipts remain strictly root-owned. Source `_38` extracts the FreeBSD-tested P2i post-credential-drop root reownership into an import-only backend with exact per-inode before/after, `O_NOFOLLOW`+`fchown` and genuine PID/birth/executable guard, run by the **existing single disposable P2i test before its IPFW**. Source `_39` installs the original shared Apply **fail-closed** observer preflight and single-launcher/rollback handoff ordering under inherited original FD9, and adds a restricted same-FD9 original inode CLI with no duplicate lock or witness store. The future `authorize` operation remains absent deliberately until genuinely bounded cron/configd worker, pending ACK and sealed schema-2 source proof are ready; forged generation/inline native auto flags fail before engine startup. The existing native P2i guest exercises that original FD9 CLI; installed Auto-detect remains OFF. It is not yet called from installed original FD9; the observer and worker remain inactive, so no unbounded discovery data is created. Native guest [#43543536132](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43543536132) proved that `posix_geteuid()` is absent from stock OPNsense PHP. The shared root-only PHP CLI now checks effective UID through POSIX when present or exact native `/usr/bin/id -u` without shell and with fail-closed command/file checks. P2k8g fixture only passes the qualified checkout Python policy and private hold markers via an explicit test-only `/usr/bin/env` invocation; production PHP retains its scrubbed subprocess environment. Exact-head native PASS is a separate gate from portable source tests. This does **not** authorize installed native writer operations: the test uses a synthetic Model/inert receipt and does **not** prove original FD9/schema-2 activation, installed P2k8d destination writes, generation-attributed new insert receipts, post-drop ownership repair, pending ACK or the minute worker. Do not silently seed empty files or infer ownership from manual Config rows.
- Zapret2 **automatically reloads modified HOSTLIST/IPSET files**. Normalized inserts and GUI additions/deletions must take effect for matching profiles **without Restart or Apply**. No artificial active/staged buffers, delayed activation or internal restart-to-reload setting. A shared-file edit with no explicit selector does not activate anything.

## 8. Independent Auto Restart: native Advanced Mode only

**Binding owner correction, 12 November 2026:** **Both label and dropdown** of «Автоперезагрузка» / `Auto Restart` are shown **only when the existing standard OPNsense Advanced Mode switch is ON**. OFF hides **both**. Under ON, place the label/dropdown **in the same top row, to the right of the existing Enabled checkbox**. Use native Form advanced field support (`<advanced>true</advanced>` or verified equivalent), **not a second toggle or a different section**.

There are **exactly five options**:

| RU choice | EN | Default |
| --- | --- | --- |
| Выключено | Off | **Yes, for new installations** |
| Раз в час | Every hour | No |
| Раз в день | Every day | No |
| Раз в неделю | Every week | No |
| Раз в месяц | Every month | No |

**Hidden is a presentation state, never a function-off state.** Disabling Advanced Mode must **not** clear the saved interval, submit `Off`, alter schedule or suspend periodic restarts. Re-enabling Advanced Mode displays the prior choice. An unrelated GUI Save while the field is hidden cannot reset it. Only explicitly selecting **Off** disables the scheduler. It is independent of Auto-detect.

For an enabled interval, perform the **normal shared service restart on schedule EVEN WITH NO HOSTLIST CHANGES**. Never optimize away an unchanged-list restart. Off means no periodic restart; native HOSTLIST hot reload still applies. Manual Restart/Start/Stop remains. The scheduler must **not start a deliberately stopped or disabled service**. Respect original single `dvtws2`, FD9, WAN-first, IPFW/Voice and concurrent Apply. Correctly handle date changes, missed jobs and reboot. Exact calendar anchors/native OPNsense cron implementation are engineering qualification details; **no extra GUI fields**.

## 9. Safety invariants

- Native `config.xml` has **one** legitimate writer. The Python worker does not write it; `SharedConfigCommit` is used only by authorized UI configuration saves.
- One Strategies+Voice `dvtws2`, original FD9, WAN-first, atomic Apply/rollback, IPFW ownership, **no `pfctl -d/-e`**. Native `.pkg` only; no SH companion installers.
- Strict file/entry/log size bounds and no publication of user traffic. Unsafe ownership, inode, symlink or damaged pending **fail closed without deleting unprocessed events**.
- Never write domains to IPSET or DNS-convert them. **Do not call, test or modify Strategy Lab** at any stage.
- The active-profile side effect of native `--hostlist-auto` is an **unwaivable P0 integration blocker** until a safe real-engine solution is proven.

## 10. Mandatory acceptance matrix

1. **Target Mode:** `all/list/auto`, explicit/implicit selectors, `--new`, multiple native profiles from one source and first-match; `auto` does **not** inject hidden `<HOSTLIST:auto>`.
2. **Native engine:** real installed `dvtws2`, supported TCP/UDP events, confirmed raw append versus preceding debug, correct native profile, **no unauthorized bypass-profile activation**.
3. **Routing:** known HOSTLIST → its auto source; unknown/ambiguous → shared; IPSET-only/mixed excluded; no IP→HOSTLIST inference.
4. **Normalization:** subdomains of depth 3–N, multiple findings/minute, `example.co.uk` and PRIVATE `github.io`, malformed data, unsafe/unknown PSL, ordinary root without auto-`^`.
5. **Exclusions:** global Exclude Domains, `!domain.com` in any HOSTLIST, exact `!^domain.com` / `^!domain.com`, manual list preservation and normal deletion followed by rediscovery.
6. **File races:** old open FD, concurrent append/link/replace, crash before/after replace/fsync, concurrent cron, partial line, damaged/oversized pending, write failure and reboot; no input loss or duplicate output.
7. **GUI:** placement and RU/EN, editing final Auto Hostlist, displaying accumulated data without selector, no stale form silent overwrite, concurrent worker/user changes.
8. **Auto Restart:** label and dropdown visible **only with standard Advanced ON**; hidden under OFF while saved choice and schedule remain; restored selection when Advanced ON; all five values, default Off, restart without list changes, STOPPED stays stopped, hidden-field unrelated GUI Save does not reset, no shared Voice/FD9/IPFW/Apply regression.
9. **Preservation:** normal Apply, RUNNING, in-place native `.pkg` update, GUI uninstall/reinstall preservation, clean install and approved full purge on real FreeBSD/OPNsense.
10. **Isolation:** zero Strategy Lab modifications, zero domains→IPSET, no second `dvtws2`, no second `config.xml` writer, no unsafe profile coupling.

11. **Obsolete-path exclusion:** confirm no live reference to `zapret-hosts-auto.txt` in the generator, GUI, root configd routes, setup, packaging, worker or update/cleanup paths, no legacy first-copy/merge and no impact on genuine new `auto-domains.txt` data. Existing historical references are allowed only as explicitly superseded evidence.

**Evidence tiers are separate:** source/unit, native CI, built/published `.pkg`, and actual owner OPNsense acceptance. **No row becomes PASS merely because this specification exists.**

## 11. Future development phases and evidence-only questions

**P0:** read-only native detection/first-match/implicit-activation proof; stop with a technical blocker rather than relax requirements.
**P1:** existing Python `domain_policy.py` PSL ICANN+PRIVATE and domain/multilist exclusion rules.
**P2:** cron/configd minute worker, generation+debug correlation, hardlink/replace, FreeBSD FD drain and pending recovery.
**P3:** durable auto-owned HOSTLIST parts, shared fallback, generator/storage/validator and native reload.
**P4:** editable RU/EN Auto Hostlist; Advanced-only Auto Restart control with persistent hidden value and independent scheduled restarts.
**P5:** real native OPNsense/FreeBSD, `.pkg`, GUI/lifecycle/Voice/FD9/IPFW and owner acceptance.

Remaining issues are **technical proof, not owner policy**: safe non-activating native observation, FreeBSD writer FD closure, inode durability/permissions, PSL provisioning and native cron calendar. Do **not** involve Strategy Lab.

**Execution boundary:** This is the approved behavior specification; PROJECT_STATE separately identifies partial source implementation and the remaining production boundary. The [consolidated comment](https://github.com/Tolian82/os-zapret2-restyle/issues/1052#issuecomment-6798093626) remains the verbatim Russian source; the original issue history remains unchanged. This English document is its engineering specification for the repository; the latest owner correction in [Issue #1052](https://github.com/Tolian82/os-zapret2-restyle/issues/1052) overrides superseded portions of the earlier consolidated comment.
