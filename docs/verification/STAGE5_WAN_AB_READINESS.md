# Stage 5 — A07 offline A/B and exact-restoration readiness review

**Scope:** source-only, **non-executing** Stage 5 engineering gate for the existing testing `v0.6.1_12`. This is **not** authorization to change Exclude IPSet, send HTTPS/IPv6/Voice packets, run a capture, or Apply on OPNsense. Installed A07/A08 and real IPv6 WAN/media acceptance remain **OPEN**.

## What the reviewer does

The [A07 offline reviewer](../../scripts/stage5-wan-ab-readiness.py) consumes **existing local artifacts only** and calls the previously qualified [plan controller](../../scripts/stage5-wan-baseline-capture.py) for strict generated-plan verification, the [Ethernet TCP PCAP parser](../../scripts/stage5-wan-pcap-attribution.py) for source-port/five-tuple attribution, and the [native installed-owner evidence parser](../../scripts/stage5-installed-evidence.py) for genuine `voice_live_inspect.py` snapshot validation. It does **not** invoke any of their live entrypoints, and never imports a network/process execution module itself.

1. **Plan review**: validate the exact trusted `stage5-wan-acquisition-plan.py` plan; require baseline/excluded have the identical pinned domain, remote IP, WAN declaration, local address and port. Return `A07_PLAN_REVIEW_ONLY`, `phase_b_permitted=false`.
2. **Retained baseline review**: with `--baseline`, parse the **already-existing** bounded classic Ethernet PCAP; report only correlated TCP counts/sha256. Incomplete, conflicting or uncorrelated traffic stops progress. Even a correlated and apparently successful TLS request is **not independent dvtws2/Lua modification evidence**. Return `A07_BASELINE_CAPTURE_REVIEW_ONLY`, never permission for GUI phase B.
3. **Retrospective complete three-phase review**, **only if artifacts already exist from separately authorized owner actions**: validate an excluded Ethernet PCAP against the same manifest and inspect **three production-native snapshots** (original, excluded, restored) plus **three saved managed Exclude files** (original, excluded, restored). Require the native Config digest to differ in B and return exactly in R; require restored native IPFW rule/table counts and Voice scope to match A. Require the pinned endpoint **absent** from the original mixed-family Exclude, **present** in B, and require R's managed Exclude bytes to match A byte for byte. Reject malformed or unbounded CIDRs and mismatched/partial evidence.
4. **Output**: a small sanitized JSON containing only source/target identity, phase observation counters, capture/list SHA-256, boolean restoration observations and the next evidence gate. Never print the managed IPSET contents or packet payload. Even a complete matching retrospective bundle returns `A07_OFFLINE_AB_RESTORATION_REVIEW_ONLY`; `installed_a07=OPEN`, `installed_a08=OPEN`, `exclude_effect_proven=false` and `process_continuity_proven=false`.

**This is a fail-closed review of supplied artifacts, not their provenance.** The snapshots could have been collected incorrectly, and capture fingerprints cannot prove actual WAN origin, selected Strategy, original SNI, native packet mutation, owner consent, process start-time continuity or Voice media. A restoration report never rewinds an incorrectly changed gateway. **Only the original supported GUI/Apply and native owner** may alter the live configuration. No tool may interpret this report as a phase-B permission or Stage 5 PASS.

## Developer-only commands (local files, no live activity)

Plan review:

```sh
python3 scripts/stage5-wan-ab-readiness.py --plan saved-plan.json
```

Inspect only an **already retained** baseline PCAP:

```sh
python3 scripts/stage5-wan-ab-readiness.py --plan saved-plan.json --baseline baseline.pcap
```

For a **previously and independently owner-authorized, completed** A/B/R record, provide all nine distinct input paths (`--plan`, `--baseline`, `--excluded`, `--original-owner`, `--excluded-owner`, `--restored-owner`, `--original-exclude`, `--excluded-exclude`, `--restored-exclude`). Owner snapshots must be the **real native inspector's** JSON records; the three Exclude files must be original managed text. The reviewer accepts no partial B/R record. Keep private snapshots and PCAP files locally, not in a PR, issue or chat.

## Acceptance and next authority

Focused no-network regression [`test-stage5-wan-ab-readiness.py`](../../scripts/test-stage5-wan-ab-readiness.py) covers both IP families, same pinned identity, absent/present/returned membership, exact restoration, changed/returned native Config digest, matching native owner scope, ambiguous captures, incomplete evidence and a permanent `OPEN` verdict. The project CI runs it independently of the installed appliance.

**Separate isolated native attribution candidate:** [real upstream HTTP Strategy TCP byte test](STAGE5_NATIVE_STRATEGY_ATTRIBUTION.md) compares emitted receiver bytes with exact original bytes, including negative and positive Exclude controls. Its isolated HTTP result, even if FreeBSD CI PASS, cannot certify the installed TLS/SNI flow, real WAN origin or permission for live phase B.

**Still missing before any live phase B:** independent and reproducible identification of the active Strategy and actual modification of the baseline WAN flow, real WAN-interface/source provenance, a verified owner-reviewed bounded A/B/restore lifecycle, fresh and explicit owner permission for every GUI Apply and capture, and native process continuity/health evidence. The [binding installed A/B protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md) remains authoritative. No prior baseline consent is reusable. Python interpreter unification is **cancelled within the current technical specification**, not a prerequisite here.
