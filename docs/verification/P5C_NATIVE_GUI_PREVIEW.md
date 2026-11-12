# P5c — authenticated unsaved Strategies GUI preview

**Feature:** #936 / approved P5. **Source candidate:** v0.6.4_42. **State:** source implementation and fast mock route tests; exact installed native P5c / authenticated RU+EN Chromium **NOT TESTED** until a separate same-source receipt. Owner A11/A16 and P6 remain open.

## Product path and guarantees

The new `Validate and Preview` / `Проверить и показать` button on the existing Strategies page posts **unsaved** form values and the existing Telegram-IPSET concurrency baseline to `SettingsController::previewAction`, separate from `applyAction`. Only the canonical domain/IPSET Python bridge normalizes edited fields in memory, never into the browser input. The existing `SharedApplyEnvelope` bounds exactly the changed, form-owned fields; the root worker freshly reads Config, rechecks the baseline and model, and uses `SettingsApply::renderCandidateXml` on a detached XML string. There is no `Config::save()`, `serializeToConfig()`, shared-work materialization, PREPARED journal, new Apply owner or service activation.

The route `configd zapret strategy_preview` inherits the **original** locked FD9 through `zapret_service.sh`. `strategy_preview_route.py` launches `strategy_preview_candidate.php` with exactly that FD9 inherited, collects candidate XML through a private subprocess pipe (not configd argv, a log or persistent file), uses the existing P5a canonical profile-policy structural summary, then passes this XML to the **unchanged P5b2b original detached** renderer, orchestrator, mapped validator and actual installed `dvtws2 --dry-run`. The temporary candidate is private and self-cleaning, with native pre/post narrow assertions. The P5b2b *full* installed semantic no-mutation witness has independently passed on the previous exact source head; it is not magically inherited as proof of this new GUI endpoint.

The response makes the result explicit: native mapped and engine dry-run `passed` / `failed` / `unavailable` / `not_run`, effective profile ordering and requested ports/L7/selectors, Lua action sequence and warnings. All display uses escaped text, with a 32-profile/20k-character browser cap. Error responses are fixed safe codes; native failures never mean successful bypass. WAN-first remains mandatory for Start/Apply but a read-only preview may present incomplete WAN/runtime findings. The button does not reload the page, overwrite other profiles or activate the candidate. All new human-facing text has RU+EN forms from the selected OPNsense profile locale.

## Evidence and next gate

- **S0:** `php -l strategy_preview_candidate.php`; Python compilation and focused route mock cases for native-refusal, successful mapped/engine state, failed build, invalid request and structural metadata; source-only tests do not attest actual FD9, Config lock, original builder or browser.
- **S1:** current-head product/GUI/CI-policy source gates, native .pkg build classification when applicable.
- **S2 required before claiming P5c acceptance:** one **real installed disposable OPNsense** native/configd + authenticated browser RU/EN test on same source, with both STOPPED and RUNNING and semantic before/after Config/FD9/IPFW/Voice/resources/process snapshots. Include unsaved edit, invalid baseline, missing-runtime case and a real dry-run receipt; no separate P0–P4 or unrelated Strategy Lab/HTTP/TLS/QUIC packet matrices.
- **P6 / owner:** one physically identified testing `.pkg` after applicable qualification, owner GUI/browser verification, upgrade preservation and the remaining A01–A19 checklist. Neither source preview nor its installed dry-run proves ISP bypass or owner appliance readiness.

**Stable package:** published `v0.6.4_1.pkg` unchanged; `v0.6.4_42.pkg` is only a prospective identity, not a file available for download.
