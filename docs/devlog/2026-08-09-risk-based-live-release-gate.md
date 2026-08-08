# 2026-08-09 — Risk-based live release gate

The owner completed the `_27` post-migration Standard live retest on `rutracker.org`.
Stages 40 and 50 passed, search continued through Stages 60/70, `NO_CANDIDATE` was
reported truthfully and Stage 90 reported clean restoration of the initially running
Zapret2 service.

The live matrix was then corrected as governance: its 18 rows remain a regression
inventory, while stable-release blocking is selected from release-specific risk, known
critical defects and live-only evidence needs. Pending unrelated rows no longer block a
release solely because they have not been manually executed.

For `v0.4.0`, Scenario 1 is the selected mandatory post-migration live row and is PASS on
`v0.3.3_27`. Rows 2–18 remain pending regression coverage; no PASS is claimed for them.

Decision:
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

Evidence:
`docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md`.

No runtime code or package metadata changed in this governance patch.

