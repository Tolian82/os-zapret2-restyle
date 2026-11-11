# P3 — native OPNsense 26.7 form localization boundary

**Version:** `v0.6.4_16`, source-only candidate. **Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936). This records the *observable rendering contract*, not physical owner GUI A12–A16 acceptance.

## Upstream template and locale evidence

Read directly from [OPNsense core `stable/26.7` `base_form.volt`](https://github.com/opnsense/core/blob/stable/26.7/src/opnsense/mvc/app/views/layout_partials/base_form.volt) and [`form_input_tr.volt`](https://github.com/opnsense/core/blob/stable/26.7/src/opnsense/mvc/app/views/layout_partials/form_input_tr.volt):

- Section heading: `<thead><tr><th><div><b>{{section['label']}}</b></div></th></tr></thead>` per section table; find by an *existing stable field ID* inside that table, not English title or section index.
- Input caption: `<div class="control-label" id="control_label_{{ id }}">...<b>{{label}}</b>...</div>`; there is **no HTML `<label>` element**. Prior `_14`/ `_15` scripts searched `label`, so source-only tests did not establish visible RU field captions.
- Static `info` field: `<span id="{{ id }}"></span>` inside input cell; the XML `<text>` is **not** rendered by this template. Prior XML `<span id="...">` nested in `<text>` did not establish an actual DOM anchor. Use a true `<id>` element for each form's info field and fill it from bounded JS locale strings. Native fields and values stay untouched.

Language authority: [`ControllerRoot::setLang()`](https://github.com/opnsense/core/blob/stable/26.7/src/opnsense/mvc/app/controllers/OPNsense/Base/ControllerRoot.php) resolves system language with logged-in user's per-profile override. [`default.volt`](https://github.com/opnsense/core/blob/stable/26.7/src/opnsense/mvc/app/views/layouts/default.volt) renders `<html lang="{{ langcode|safe }}">`. Therefore existing `document.documentElement.lang` on OPNsense-rendered pages derives from the **server-selected user profile**, not browser language/geolocation. No second locale authority is required.

## `_16` source fix and acceptance boundary

- Both `forms/general.xml` and `forms/voice.xml` now assign real IDs to their static `info` fields. The original English XML narrative remains available as source/documentation, while `general.volt` fills a bounded EN/RU HTML string and `voice.volt` fills its existing bilingual plain-text description.
- Strategies: three section titles and 10 field captions use native `thead th b` / `div.control-label > b`; Exclude IPSet keeps its dedicated inline-only F5 help and gains the actual caption selector. Voice: two section titles, 15 field captions and its information label use the same native DOM wiring. ARIA captions are synchronized without altering any input value.
- Native popup/Full Help help sources and the ordinary shared Apply/Voice/FD9/WAN/IPFW/backend/API are unchanged. The original GNU gettext/native XML label path remains available for EN and non-RU locale fallback.
- Expanded source checks in `scripts/test-strategies-i18n.py` and `scripts/test-voice-gui-contract.py` enforce the actual OPNsense 26.7 DOM selectors, real info IDs and section anchoring. This is a **source/CI assertion**, not evidence from a logged-in RU or EN owner browser.
- Still OPEN: actual OPNsense GUI RU/EN profile switching, F5, Full Help/popups, preservation of typed values; complete A12–A16 API errors and remaining help; P2 installed native rejection/rollback and final product acceptance. No `_16.pkg` published; stable `v0.6.4_1.pkg` remains unchanged.

## `_24` — installed disposable OPNsense RU/EN user-profile browser gate

This extends the existing `stage5-native-browser-wan.yml` disposable OPNsense 26.7 guest. It is **not** a simulated locale toggle: the test-only `scripts/p3-native-profile-locale.php` sets the *logged-in root user's* `system.user.language` to `en_US` and then `ru_RU` through the OPNsense native `Config::save()` API, with strict GitHub Actions/disposable-VM guards, a user identity allowlist and before/after Zapret subtree hash equality. It restores `en_US` afterward. This fixture is **not shipped in the plugin package**, and must never run on an owner appliance.

The authenticated `scripts/p3-browser-i18n.py` opens the **installed** Strategies and Voice pages through the same loopback-only SSH tunnel as the existing native WAN/Apply/F5 Chromium test. It asserts the server-rendered `html lang`, native labels/section headings, all Target Mode option identities, popup-help source and real Full Help toggles, five Voice IPSET selector names, non-mutating typed-value help cycles, F5 reload preserving saved values, and exact persisted-value equality across EN/RU user profiles. One invalid IPSET passes through the existing **read-only** Voice Validate endpoint to the real user-facing field error. No Save Draft, Apply, Start or Stop is sent by this locale test. Receipts contain only locale, booleans and a digest, not passwords, user values or Config XML.

**Evidence boundary:** a passing CI run establishes these precise interactions in the disposable installed guest, not on the owner's production OPNsense. The user-profile GUI A12–A16 owner acceptance and physical P2 rollback remain independently OPEN. The stable public `v0.6.4_1.pkg` is immutable.

## `_24` P3 CI resource budget correction

The earlier P3 browser workflow reused the unrelated historical **RUNNING old-package upgrade** fixture and explicitly disabled the OPNsense VM cache. That incurred a fresh VM dependency download, historical-package fetch, engine setup, process/IPFW verification and full replacement before checking any P3 label. A single native action step consumed more than 40 minutes without reaching Chromium; no RU/EN success can be inferred from that stalled run.

For P3, the job now builds and **clean-installs the actual current-source official native Mk `.pkg`** into a disposable OPNsense 26.7 guest using `stage2-opnsense-real-native-clean-install.py`. It does not fabricate a DOM or use the older stable package as a substitute for current source. Dependencies are installed in the action's bounded `prepare` stage and cached using `cache-after-prepare`; `pkg update` and `pkg install` have separate timeout/error gates. The whole job is limited to 20 minutes, and the real lower-WAN Apply response is capped at 90 seconds. The authenticated Chromium EN/RU tests, real profile language changes, unsaved edits, help/F5, saved-value digests, read-only Voice validation and redacted receipts remain mandatory.

**Evidence distinction:** This native P3 GUI job now establishes current-package *clean-install browser rendering*, not an old-package `RUNNING→RUNNING` upgrade. The independent historical/native upgrade and service/lifecycle qualification remains in its own S2/S3 matrix; this refactor does not waive it when a runtime/package change actually requires it. Physical owner A12–A16 and rollback acceptance remain OPEN. A failed/cancelled/timed-out VM is never accepted as RU/EN success.
