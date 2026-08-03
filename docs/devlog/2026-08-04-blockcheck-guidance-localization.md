# 2026-08-04 — Blockcheck guidance localization

Logical change:
Localize the initial explanatory text in the Diagnostics Blockcheck section according
to the language selected in OPNsense.

Implementation:

- retained the existing project convention that reads `document.documentElement.lang`;
- uses the approved Russian copy only when the language starts with `ru`;
- uses the approved English copy otherwise and as the static fallback;
- renders each paragraph with jQuery `.text()`;
- removes the obsolete English-only gettext-wrapped sentence;
- adds focused CI coverage for language detection, both text variants, safe rendering,
  and removal of the old copy;
- advances the package candidate to `0.3.2_3` without changing `VERSION`.

Validation performed before publication:

- reconstructed the current Diagnostics template and verified its blob SHA against
  `main` before editing;
- ran the focused localization contract test successfully;
- ran `sh -n` on the new test script;
- parsed the modified CI workflow as YAML;
- verified exact English and Russian text presence and obsolete-text absence;
- verified the modified documentation baselines against their current Git blob SHAs.

Delivery boundary:
This is one ordinary package patch. No project release, tag, release asset, or public
pkg-repository publication is authorized.
