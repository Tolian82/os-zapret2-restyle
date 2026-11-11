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
