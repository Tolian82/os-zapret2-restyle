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
