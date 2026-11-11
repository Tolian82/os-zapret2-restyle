# P4b — Display native Zapret2 Lua/BIN when optional resources are absent

**Candidate:** `v0.6.4_26` — source-only, not a release. **Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936). **Approved plan:** [P4 Help and Strategy Lab](../architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md). **Baseline:** merged [P4a PR #1059](https://github.com/Tolian82/os-zapret2-restyle/pull/1059) at `374638220d3428940e53b55194c6e9fe51931a2e`.

## Confirmed root cause and narrowly scoped repair

`extra_resources_inventory_cache.py generate()` already records safe **actual on-disk** native Lua/BIN by origin (`upstream` or `other`), independently of `installed.json`. Its `installed=false` boolean reports the **optional Additional Resources bundle** state, not the existence of native engine resources. The existing `general.volt` Full Help renderer incorrectly returned immediately after the optional-bundle installation hint, hiding the real cache entries.

Now when the API confirms `status=ok`, a boolean `installed` and both Lua/BIN arrays, the **same validated, read-only cache** drives both lists. If `installed=false`, the truthful optional-bundle notice remains **above** the lists, without hiding native files. Items keep their upstream/other provenance colors and safe text-only filename rendering. If status is unavailable or the shape is malformed, help displays **cache unavailable**, never `no files` and never a false optional-bundle state. A valid empty cache shows an empty list independently for both categories. No new filesystem scan, Git fetch, install, lifecycle action or alternate cache writer occurs when opening Full Help.

## Required evidence

| Scenario | Expected visible Help | Verification |
| --- | --- | --- |
| Cached native Lua/BIN, optional bundle absent | Optional installation note **plus actual native files** | `scripts/test-extra-resources-help-render.mjs` executes real extracted production renderer, `scripts/test-extra-resources-inventory-cache.py` verifies no-manifest upstream cache |
| Optional bundle installed, mixed origins | All validated files, provenance colors, no false absence note | Renderer source regression + existing native cache tests |
| Cached empty Lua and BIN | Two honest empty lists (optional note when applicable) | Renderer regression |
| Missing/unavailable, invalid or malformed cache | Cache unavailable; no files or optional-install conclusion inferred | Renderer regression; no backend fallback |
| Genuine installed GUI with native user `en_US` and `ru_RU` | Full Help opens via native OPNsense toggle; the real inventory API response and resulting DOM agree | `scripts/p3-browser-i18n.py` (actual installed Chromium, no fake response). Records `resource_help_cache_state` as `ok-native-only`, `ok-optional` or `unavailable`. An unavailable native cache is **not** proof of native file rendering |

**Pre-push source witness:** the exact prepared production JavaScript render function was evaluated with native-only, optional-present, empty, unavailable, and malformed inputs, and all five checks passed. New Node regression makes that same invariant repeatable in CI. Browser/native results remain separate until actually executed.

**Safety & remaining work:** no change to the Python cache generator, inventory API/configd, extra-resource installation, pkg hooks, Config or FD9/IPFW/runtime. Next P4 increments must qualify runnable protocol-specific native examples and installed optional resource variations. Owner A17, physical OPNsense acceptance and release P6 are still OPEN. No `_26.pkg` publication; stable `v0.6.4_1.pkg` remains unchanged.

## GH-071 CI routing correction (same P4b scope)

The first P4b source candidate unintentionally queued **two unrelated historical S3 RUNNING/Voice VMs**: their `pull_request.paths` included `scripts/test-extra-resources-inventory-cache.py` even though the actual production inventory-cache implementation was unchanged. To keep genuine native coverage while eliminating this test-only fan-out, `stage5-native-cross-clean-running.yml` and `stage5-native-running-voice.yml` now trigger on the **actual installed** `src/opnsense/scripts/OPNsense/Zapret/extra_resources_inventory_cache.py` source instead, not on changes to its fast unit tests. The automatic S3 jobs remain available for true cache/runtime changes or intentional manual dispatch; GH-071 budget regression asserts both path filters. This does not classify a skipped historical VM as native PASS. The relevant GUI P4b acceptance remains the bounded installed Chromium RU/EN check on the actual candidate.

## First exact-head CI diagnosis and corrective test update

The initial `c7569d96` source attempt did not qualify P4b. The fast project regression was blocked by a **stale synthetic JavaScript fixture** in `scripts/test-extra-resources-gui-contract.py`: its fake DOM only supported `.text()` and assumed `installed=false` returned immediately; with the correctly rendered file list it failed on `.appendTo()`. The old synthetic fragment is replaced with the repeatable test which actually evaluates the production renderer. The installed Chromium failed a 30-second `expect_response` predicate that incorrectly required `HTTP 200` **and exact-case URL matching**; its check now records real cache transport errors as `unavailable` and normalizes route casing, without inventing any response or declaring cached files present. When no request occurs, it still fails closed.

The two unrelated historical Stage 5 RUNNING/Voice workflows were accidentally triggered by a unit-test source path; they are no longer an acceptance gate for help-only P4b and their triggers are corrected to real installed cache production source. One historical run also reported an unrelated synthetic Lab timeout restoration failure (`RESTORE_FAILED` versus `TIMEOUT`), which is not evidence that this unchanged UI renderer caused a product lifecycle regression. The G03 classifier and unchanged runtime safety boundaries remain intact. Exact-head acceptance is pending renewed S0/S1/native browser evidence.

## Exact-head correction after first CI retry

The CI hygiene gate detected a release-note link relative to the wrong directory; it is now ../verification/P4_NATIVE_RESOURCE_HELP.md. Native Chromium also exposed a racy fixture: waiting on a newly emitted inventory HTTP response is unreliable after the native Help toggle has already loaded or reused a cache. The fixture now clicks the actual Full Help switch, makes one bounded authenticated cache-only API request through existing page jQuery, and checks the separately rendered real panel; it does not intercept traffic, synthesize a successful answer, mutate Config or assume a missing cache is empty. Its native PASS remains open until a completed exact-head run.

## Real native section-collapse check (Chromium run #43085166268)

The clean-installed Chromium test reached native Full Help but found its Lua/BIN panel hidden. The actual Help panel is nested inside the separately collapsible Service table, whereas the Full Help toggle is in Settings. The browser test now expands the Service table with its genuine header click when needed, without changing styles or synthesizing elements. If the panel remains hidden, the test fails quickly with non-sensitive evidence: native help icon on/off, panel display and Service table visibility. A product integration defect must still fail; native PASS is not claimed before the new exact-head execution.

## Native help switch normalization (after run #43086394142)

The exact Chromium refusal reported icon_on=False with the separate Service body already visible, so the prior double-toggle fixture was not a valid proof of a broken Help renderer. The fixture now opens a collapsed Service table with its real header, records whether the native OPNsense Full Help icon was already ON, clicks it only if it was OFF, checks the actual panel and cache-only API, and restores the icon only when the fixture itself changed it. A remaining hidden panel still fails with sanitized icon/visibility diagnostics. No forced DOM styling or product runtime modification.

## Fresh F5 isolation and native toggle evidence

An earlier exact-head Chromium run still found icon_on=False despite a visible Service section. To avoid diagnosing prior popup/Full Help toggles as a product resource catalog bug, the inventory probe now executes **after native F5** with verified unchanged saved field values. It checks again that opening resource Help does not mutate those fields. On a remaining invisible panel it records only native icon state before and immediately after the real click and the final native icon/Service/panel visibility, without dumping private page data or forcing CSS.
