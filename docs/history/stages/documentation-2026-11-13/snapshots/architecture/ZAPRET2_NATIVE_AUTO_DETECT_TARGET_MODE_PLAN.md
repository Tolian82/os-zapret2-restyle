# Historical source — docs/architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md

**ARCHIVED / LEVEL 3.** Original text at `277ef0536b217841ab6728ae9561dbc4792fef01` (`v0.6.5_14`), relocated during the 13 November 2026 documentation review. Its dated statuses, commands, proposed work and duplicated rules are historical, not current instructions. Local links are rebased; original prose is preserved. Current authority: [documentation index](/docs/INDEX.md).

# Native Auto-detect, Target Mode, HOSTLIST and Auto Restart — ordered plan P0–P5

**Status:** P0/P1 complete, P2a–P2d source/proof merged. P2e `v0.6.5_14` tests original `orchestrator_build_release()` in a disposable offline candidate instead of inferring P2d producer success from synthetic P0 or `.pkg` build ([P2e boundary](../verification/P2E_ORIGINAL_SHARED_BUILDER.md)); P2 STILL OPEN for native FreeBSD original builder, real observer/owner/raw/debug, durable destination and minute configd. P3–P5 open (13 November 2026).
**Normative specification:** [Issue #1052 approved feature contract v1.0](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md), translated from the [owner's full consolidated issue comment](https://github.com/Tolian82/os-zapret2-restyle/issues/1052#issuecomment-6798093626).
**Boundary:** The owner authorized continuation after P0 success. P1 adds pure policy/data and package qualification to the existing domain parser; no production observer/cron/worker, GUI/scheduler or Strategy Lab change. The prior accepted [#936 feature](ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md), shared service/FD9/Config ownership and published stable package remain unchanged.

## 1. Unchanged architecture and stage order

Preserve native OPNsense `pkg`/configd/cron, one shared Strategies+Voice `dvtws2`, FD9, WAN-first, native IPFW ownership, one Config writer and common atomic Apply. Never add a second production engine/daemon, permanent watcher, second PHP/shell parser, DNS→IPSET conversion, read-only Auto Hostlist or Strategy Lab work.

**P0 must precede production Auto-detect modification.** Native `--hostlist-auto` both records domains and treats its file as an including native HOSTLIST. Prove that observation can occur without violating explicit-only `<HOSTLIST:auto>`/first-match semantics. If native behavior makes that impossible within the approved architecture, **stop and report the concrete technical blocker to the owner**; do not weaken the requirement silently.

**Current proven blocker repair:** the first generated native witness rejected a global Exclude IPSet already inherited from a template when the generator re-added it after import. Preserve the approved mandatory exclusion on every executable Strategies/Voice profile by generating it only there, after imports; templates are nonexecutable. This repairs the existing policy without enabling production observation or changing the accepted Auto-detect contract. Require the original-generator red→green regression, the same focused native witness and the native package build; do not dispatch unrelated historical S3 campaigns.

### Owner-clarified operating-mode boundary (13 November 2026)

The GUI's **All traffic on specified ports**, **Only specified domains**, and **Auto-detect blocked domains** are mutually exclusive **Target Mode choices**, not three simultaneously active default modes. A broad DPI profile expected in `all` is **not** evidence that Auto-detect is defective in `auto`; `list` does not perform native discovery either. In `auto`, a confirmed `video.example.com` detection is normalized to `example.com`, attributed to an unambiguously known HOSTLIST or saved to the shared `auto-domains.txt`; the shared file is **not** used for bypass absent explicit `<HOSTLIST:auto>`.

**Implementation qualification, not a new owner question:** Mode defaults apply independently to each source profile **without explicit selectors**. Explicit selectors, user-defined `--new` and eventual expanded native profiles retain their existing semantics. P0 should inspect the **actual compiled `auto` profile set** rather than invent a simultaneous `all` mode; any real first-match coverage limitation needs a generated-profile witness. See [normative operating-mode clarification](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md#21-owner-clarification-target-mode-choices-are-not-simultaneous-operating-modes-13-november-2026).

## 2. Stage map

| Stage | Observable deliverable | Exit evidence |
| --- | --- | --- |
| **P0** | Read-only native capability/first-match and generation attribution proof | Real qualified `dvtws2` establishes no covert inclusion of another strategy or IPSET; otherwise written blocker and **no further implementation** |
| **P1** | Extend existing canonical `domain_policy.py` | Qualified PSL ICANN+PRIVATE eTLD+1, deep roots, `!/^`, global/list exclusions, conflicts, safe invalid input and idempotent dedup |
| **P2** | Cron → configd → one short minute Python worker | Generated profile map, confirmed raw/debug correlation, hardlink+replace, native FreeBSD FD-drain, locking, durable pending recovery under crash/race |
| **P3** | Durable known-list auto-owned components and final shared fallback | Correct `auto-domains.txt` and explicit-selector-only usage, preserve manual components and Config, native hot reload without Apply/restart |
| **P4** | Editable Strategies Auto Hostlist and independent scheduled Auto Restart | RU/EN and stale-save conflicts, native Advanced ON-only control, saved hidden interval, exactly five options and normal restart even with no list changes |
| **P5** | Native installed/package and owner acceptance | All ten normative acceptance groups, safety/non-regression/lifecycle and owner observed OPNsense results; Strategy Lab unchanged |

Stages are **logical gates, not promised commit counts or an invitation to expand unrelated verification**. Record source, exact-head CI, native packaged and owner-installed evidence independently; a new build does not prove the user's GUI or traffic.

## 3. P0 — source audit and generated native feasibility completed

**Current P0 evidence:** [source analysis and native witnesses](../../../../../verification/P0_NATIVE_AUTO_DETECT_FEASIBILITY.md). Direct auto-on-existing-action-profile is rejected. The trailing no-action observer passed both the earlier two-profile experiment and the final actual-generated native first-match/map/raw-debug witness. P0 is complete within the bounded TCP/HTTP/IPSET/STUN scope; production persistence, UDP/QUIC coverage and owner acceptance belong to P2/P5.

**Generation-attribution boundary:** the [noninstalled map/full-generator fixture](../../../../../verification/P0_NATIVE_AUTO_DETECT_FEASIBILITY.md#p0-generation-bound-attribution-13-november-2026) captures raw sources, Target Mode, normalized/resolved order, Voice/Extra and exact argv identity, preserving mixed-IPSET ancestry and refusing stale/uncertain imports/tails. The [actual native generated witness](../../../../../../scripts/test-p0-native-generated-observer.py) passed on [run 43327217834](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43327217834), including isolation and confirmed raw/debug generation attribution. This establishes feasibility, not a persisted production map or universal traffic coverage. The steps below describe that completed gate.

1. Compare the [official upstream manual](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md), actual selected engine [`nfq2/desync.c`](https://github.com/bol-van/zapret2/blob/master/nfq2/desync.c) and [`nfq2/helpers.c`](https://github.com/bol-van/zapret2/blob/master/nfq2/helpers.c) with real current `target_mode.sh` / `profile_policy.py` / dvtws generator.
2. Map source profiles to final native profile numbers and sole HOSTLIST/unknown by **generation**; account for `--new`, templates, import, Python expansion, Target Mode and Apply.
3. Check native first-match, raw successful append versus earlier `adding to ...` debug and actual `--hostlist-auto` inclusion side effect on qualified engine. Confirm IPSET-only/mixed exclusion and no unauthorized use of the shared fallback.
4. If safe non-activating observation is not established, **stop**, produce a factual blocker and obtain an explicit design decision. Never start another production `dvtws2`, patch upstream or touch Strategy Lab as a workaround.

## 4. P1 — one canonical Python domain policy

Extend **`backend/domain_policy.py`**, not a new parser. Qualify PSL delivery/update including PRIVATE and ICANN; derive eTLD+1 for `example.co.uk` and `user.github.io`, collapse arbitrary subdomain depth to a plain root without adding `^`. Preserve user's original `!/^` syntax, distinguish broad from exact local exclusions, separately check global Exclude Domains, and inspect **all** HOSTLISTs before positive auto-add. Attribute source before normalizing; ambiguous roots go to shared fallback without contradictory records. Verify Unicode/IDNA, bad/public-suffix hosts, multi-event dedup, normal deletion followed by new discovery and fail-closed invalid input. **Source status:** implemented in the same canonical module; [qualified PSL update path, API and executed checks](../../../../../verification/P1_AUTO_DETECT_DOMAIN_POLICY.md). Native archive/provider qualification is mandatory before moving to P2; no live discovery is enabled by P1.

## 5. P2 — short, durable cron/configd worker

One native cron tick every **60 seconds**, configd registered action and one locked Python worker. No kqueue daemon, new long-running process, per-event global Apply or per-event restart. Protect raw `inbox.txt`, old `pending/<id>.txt` and prepared replacement on one filesystem. Use approved **`os.link` → `os.replace`**, confirm correct directory sync and old dev/inode writer-FD closure of the verified FreeBSD `dvtws2` with qualified `procstat -f`/`fstat`, then correlate native debug/profile generation, parse and write durable final results before deleting completed pending. Recover all interrupted boundaries, particularly pending still hard-linked to live inbox after link-before-replace. **At-least-once + idempotency**; never `truncate`/`copytruncate` or expire unprocessed segments by age. Test open writer FD, partial line, concurrent cron, corrupt/oversized input, disk errors and reboot.

**P2a evidence boundary:** the import-only `auto_detect_queue.py` enforces a single lock, fsynced hard-link/replace and protected acknowledgement; portable test proof cannot substitute for FreeBSD native engine FD, generation or committed ownership. No production cron/observer activated. Continue remaining P2 gates above.

**P2b checkpoint:** the FreeBSD `fstat` inspector reports only `BUSY`/`DRAINED`/`UNKNOWN` and is not connected to the queue; no real shared dvtws2 owner or durable generation map was supplied. Native surrogate testing alone does not meet the P2 engine-owner gate. See [scoped evidence](../../../../../verification/P2B_AUTO_DETECT_FREEBSD_FD.md).

**P2c boundary:** source-only original common owner/argv verifier cannot assert a genuine source→native map until its producer is integrated into the original generator, sealed by FD9 Apply. Never infer an origin from native argv alone or promote a synthetic map fixture to live ownership. See [P2c proof contract](../../../../../verification/P2C_AUTO_DETECT_OWNER_GENERATION.md).

**P2d boundary:** real original generator source-stage capture and a schema=1 map can be sealed before FD9 Apply without changing `dvtws.args`. It is deliberately **not** P2c's schema=2 `auto-detect-generation.json`; missing/invalid origin refuses Auto-detect but does not abort an ordinary shared Apply. Details: [P2d same-build proof](../../../../../verification/P2D_ORIGINAL_GENERATOR_ORIGIN.md).

## 6. P3 — lists, migration and native reload

Route an attributed discovery immediately to that known HOSTLIST's **auto-owned** component, separate from manual YouTube/User text and Config. Unknown/ambiguous events go to final **`/usr/local/etc/zapret2/ipset/auto-domains.txt`**; no duplicate shared unknown store. Migrate any existing accumulated entries safely and idempotently without losing `!/^` or overwriting destination content. Remove current implicit `<HOSTLIST:auto>` from `Target Mode=auto`. **Only the explicitly authored placeholder** enables a specific profile to use the final shared file through ordinary `--hostlist`; detection can still collect without this selector. Preserve unchanged IPSET, Voice, WAN-first, FD9, IPFW/Apply and native file hot reload. Never use raw `inbox.txt` as a GUI/readable final HOSTLIST.

## 7. P4 — editable GUI and independent scheduled restarts

On Strategies, insert **Auto Hostlist / «Найденные домены»** immediately **after User Domains**, editable with RU/EN diagnostics and safe form-save versus concurrent worker changes. Empty/missing/access-error are distinct; normal Apply/pkg update/uninstall/reinstall preserve user data, approved full purge removes it. Do not write worker results into `config.xml`, invoke Lab or make HOSTLIST changes wait for restart.

In the **same upper row to the right of Enabled**, show **label and dropdown** for Auto Restart **only while the standard OPNsense Advanced Mode is ON** (`<advanced>true</advanced>` or qualified equivalent). When OFF hide **both** without changing the saved interval or scheduled task; switching ON restores choice. Exactly **Off (default), every hour, day, week, month**. An unrelated Save while hidden cannot clear the value. Selected schedule invokes **normal shared restart even if no list changed**; Off has no planned restart but native list hot reload works. Do not start a STOPPED/disabled service. Keep independent of Auto-detect and preserve Voice/FD9/WAN-first/IPFW/Apply.

## 8. P5 — proportionate verification and actual package/owner acceptance

Follow [GH-016, GH-062 and GH-069](../GITHUB_PUBLICATION.md) with [DEV-061/DEV-062](../PROJECT_PRINCIPLES.md): focused S0 source/parser/rotation/UI checks before PR, fast S1 current-head version/docs/link/identity gates, S2 truly required native first-match/FreeBSD FD/OPNsense checks and scoped S3 real native `.pkg`/owner acceptance. Do not turn unrelated historical VM matrices into mandatory gates, and do not report unexecuted checks as PASS.

The **ten acceptance groups** in [the normative specification](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md#10-mandatory-acceptance-matrix) must all receive applicable real evidence, including IPSET exclusion, all file races, PSL/private suffixes, GUI concurrency, native advanced visibility with hidden-value persistence, scheduled unchanged-list restart, stopped service, upgrade/remove/purge behavior and **no Strategy Lab change**. A testing package is the input for owner's real verification, not proof of it.

**P5 preparation identified during P1:** the historical installed-receipt shape readers in `scripts/stage5-native-single-artifact.py` and `scripts/stage5-native-running-voice-artifact.py` still assume seven dependencies. Adapt them to the qualified archive/provider identity before their P5 installed campaigns; IDNA is now a declared eighth provider. Their obsolete-head metadata refusals are not P1 policy/package-execution failures or a completed P5 proof. The current P1 copyback gate already compares exact actual dependencies rather than a fixed count.

## 9. Open engineering checks and execution boundary

The remaining integration questions concern persisted generation/debug correlation and additional UDP/QUIC observation scope, FreeBSD FD closure, inode durability/ownership and calendar/cron mechanics. P1 fixes offline PSL provision/update through normal packages. These are not permission to reopen agreed routing, repeat the completed P0 bounded witness or involve Strategy Lab.

**Current authorized task:** qualify actual original shared builder P2d origin map in isolated source/native FreeBSD; then generate approved no-action observer and schema=2 current real engine/raw-debug linkage before any durable destination/cron or P3–P5 activation.
