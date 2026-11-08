# G05 / LC-06 — независимо сохраняемый WAN (native OPNsense)

**Current candidate:** `v0.6.3_11` SOURCE, **not a published package**. Immutable stable stays `v0.6.3_1`. The owner has NOT tested this candidate in the physical OPNsense browser, and RUNNING WAN rollback remains a separate outstanding acceptance criterion.

## Single native Config and runtime ownership

The GUI remains the original `POST /api/zapret/settings/apply` with `zapret[sync][telegramips_baseline]`; the browser does not write `config.xml`. `SettingsApply::prepareStrategies()` and the existing changed-field whitelist classify **exactly `general.waninterface`** as WAN-only. Unchanged user lists, intentionally empty Traffic Strategy/YouTube Domains and ordinary `Enabled=OFF` are not prerequisites for saving WAN. For all other edited fields, use the unchanged full native Strategies Apply and full validation.

The source-only WAN branch uses **the existing** `zapret_service.sh` lifecycle FD9 (not a second lock or Config writer), via `configd [shared_apply_wan]` and the source-owned `shared_apply_wan.php` probe. Under FD9, verify original shared-journal readiness, no pending Additional Resources, exact stopped ordinary runtime, no PID files, independent dvtws2 engine census, no orphan supervisor, and either **both IPFW modules absent with exact ENOPROTOOPT** or both loaded with no Zapret2/Strategy Lab rule in reserved ranges 19000–19131. Foreign rules outside the reserved zones are not deleted or changed. Unknown, partially loaded or foreign-occupied kernel, an orphan process, a stale baseline or invalid WAN all refuse before a Config write.

The actual WAN write reuses **`SharedConfigCommit::persist()`**: existing OPNsense model, scoped `general.waninterface` alone, snapshot-locked consistency, native `Config::save()` (one actual revision), native Config readback, fail/uncertain-save distinction. There is no template, `dvtws2`, upstream installer, IPFW or independent persistence owner in the stopped branch.

If a committed shared Apply journal or RUNNING legacy runtime exists, WAN changes **MUST go through the original full shared Apply/rollback**. A stopped common owner with an existing sealed journal is not eligible for a blind Config-only write because the journal contains the previous WAN snapshot. This scenario must be tested and accepted separately; do not claim complete G05/A17 or bypass the sealed-owner journal.

## Measured acceptance, not assumptions

**SOURCE/S0/S1:** `php scripts/test-g05-wan-config.php` exercises the existing shared Config writer with allowed logical WAN, deliberately invalid unrelated lists, blank strategy/domain, stale baseline, forged Voice/other page input, unchanged WAN no extra revision, uncertain Config save. `sh scripts/test-g05-wan-route.sh` extracts the real service function and simulates cold/warm engine, common owner, old running owner, orphan dvtws2/supervisor, stale PID, pending resources, foreign/managed IPFW, partially loaded kernel and unreadable kernel. Both should pass before the PR is considered.

**INSTALLED-NATIVE/S2 target, NOT YET PASS:** one disposable genuine OPNsense 26.7 VM, official Mk-generated `v0.6.3_11.pkg`, authentic `/ui/zapret` cookie+CSRF and API. Verify stale Telegram baseline and unassigned logical WAN reject without Config/IPFW mutation. With `installed=0` upstream and no engine, POST only WAN=`lo0`; require `saved/ok`, `applied=false`, native saved `config.xml`, fresh `settings/get` after F5, no engine/PID/IPFW changes. Explicitly save blank Traffic Strategy and YouTube Domains as a user would; POST WAN=`wan`; again no runtime compile/launch, still blank lists. Force reinstall **the identical physical package** and compare saved WAN plus blanks and package SHA. The native test fails closed if any receipt, mapping, ownership or runtime observation disagrees.

**Remaining G05 acceptance:** installed upstream but STOPPED before first Start; common committed owner STOPPED with sealed journal, and active RUNNING WAN swap with exact rollback/Voice preservation; actual owner browser click and physical real WAN/TUN/OPT mapping. None is implied by the first cold Config-only witness. Do not change global firewall policy, skip FD9, or claim no installed service means a valid WAN selection without a successful model/interface mapping.

**CI resource budget:** only one targeted G05 OPNsense guest on an exact-head functional PR. Four S0–S3 levels do not mean four checks. No unnecessary old Stage2 matrices, workflow push echo or revision-only VM.
