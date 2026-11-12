# User-journey-first testing: measured value instead of long green matrices

**Approved by owner 12 November 2026. Canon:** `DEV-061`–`DEV-062`, `GH-062`, `GH-069`–`GH-072`. **Source-only CI/process change**; it is not proof of working User Domains on any package.

## Why the old method failed

- `v0.6.4_42`: Python domain normalizer accepted `!` and `^` in isolation, while OPNsense Model Regex rejected them on the actual Apply route. A parser-only PASS was falsely taken as feature readiness.
- `v0.6.4_44`: fixed YouTube modifier Apply works on the owner's appliance, but *any* User Domains edit hits `SharedApplyEnvelope`'s 65,536-byte encoded argument limit. `test-shared-apply-envelope.php` proves that oversized arguments are refused safely; **it does not prove oversized user lists can be saved**.
- An owner read-only probe returned `PASS_READONLY_PRECONDITIONS` on installed `0.6.4_44`: static Model masks, native types, bridges and synthetic modifier parsing passed. It never sent a modified User Domains field, saved Config, rebuilt HOSTLIST or tested a browser click.
- Blanket Validate Project (~100 checks) + Validate Voice (~60) ran for small UI edits. Many checks were genuine for their own scope but irrelevant to these user-visible failures.

## Mandatory decision card before coding or testing

For each logical PR, record in its body:

1. **Observable user outcome:** e.g. type `^t.me` into User Domains with a realistically *large* preexisting list, press Apply, read saved Config and generated managed HOSTLIST; include the case with two changed lists.
2. **Actual path and authority:** browser POST → OPNsense Model → Python policy bridge → `SharedApplyEnvelope` / configd transport → original FD9 → authoritative Config writer → generated runtime files → GUI feedback. Name the changed code and security invariants.
3. **Pre-fix reproducer:** smallest test using production modules that truly FAILS for the reported bug on old code (including length/format/context), plus valid/invalid examples. Do not mark a test `PASS` merely because it detects the known fault and returns success.
4. **Minimum evidence:** the same test must PASS after repair. Add exactly the native installed/Chromium or owner test that portable code cannot establish; retain explicit proof of no Config/IPFW/process mutation on failure when the change touches Apply.
5. **Stop rule and cost:** list needed S0/S1/S2/S3 checks, the decision each changes, a short budget and prior valid evidence being reused. Record elapsed CI minutes and failures caught before native work. Once mandatory checks pass, STOP and deliver the properly qualified testing `.pkg` for owner acceptance.

### Fast failure-first examples for #936

| Owner journey | Test that should have caught it cheaply | Real acceptance |
| --- | --- | --- |
| `!youtube.com` / `^youtube.com` in YouTube Domains | Original OPNsense Model validation + Python normalization + real changed-field candidate | One actual GUI Apply, Config read-back and generated HOSTLIST |
| `^t.me` in User Domains, large existing content | Submit an explicit synthetic User Domains edit whose **encoded** whole changed-field value exceeds 65,536 bytes, plus combined YouTube + User Domains; demonstrate broken pre-fix behavior, then a corrected *safe* transport with bounded request admission and genuine original-FD9 apply semantics | Owner GUI Apply with real existing list; Config and managed HOSTLIST match, unrelated fields unchanged |
| Invalid or stale input | Bad modifier, invalid IP/CIDR and stale Telegram baseline must refuse without state mutation | Browser shows actionable error; snapshot before/after confirms unchanged active Config/rules |
| Lab Help and typography | Real browser: page-level top-right native-looking switch; OFF hides only four guidance paragraphs, ON reveals them; 13px consistent Voice/Strategies/Lab | Owner visual confirmation RU/EN, Lab's working controls remain visible |

**Do not** implement a fake huge-list PASS by raising the configd argv limit or only unit-testing `encode()`. A corrected design may need a safely owned bounded transport/staging mechanism; its exact implementation and security must be tested as changed scope, not dictated by a misleading old test.

## Executable CI path policy

`scripts/ci_owner_journey_scope.py` supplies `owner_flow`, `full_matrix`, `voice_scope` from **actual changed paths**. The routing is deliberately fail-closed.

- **Docs/CI-policy only**, including the noninstalled `docs/verification/owner-p6-readonly-probe.py`: version/title/docs/source-rule checks, no production matrices or package VM.
- **Pure GUI/help/domain/IPSET policy edits** in a small *explicit* allowlist: short `journey` first (real PHP Model-to-Python and bounded shared Apply contract plus UI checks), relevant native browser when the separate scoped workflow requires it, and actual native package qualification if installed sources changed. The two historical full matrices are skipped.
- **Original FD9/Config/SharedApply/model or any new/unknown production path:** `journey` first; then existing critical full matrix and applicable native scope. Never downgrade risk based only on a familiar filename's current intent; if a GUI-view edit materially changes Apply/lifecycle safety, explicitly elevate its gate.
- **Manual whole-project/full-release:** use `workflow_dispatch` / S3 with intentional recorded rationale; do not start every historic matrix for each patch.
- Real package changes still require physical byte identity and ABI qualification, and published testing packages follow `CHAT-027`, `GH-060`, `GH-061`.

**Important boundary:** Fast CI checks for User Domains currently test canonical Python/Model and the *safe refusal* of an oversized envelope. The actual known large-User-Domains persistence case is **NOT PASSED** until the bug-fix PR adds its deliberate red→green production-path reproducer and one real owner Apply/Config/HOSTLIST witness.

## Accountability and effectiveness

Track per PR: direct owner failure covered (yes/no), number of user journeys tested, number of full-matrix/native runs, observed CI runtime, number of defects detected *before* launching native jobs, and exact package/owner acceptance status. More green checks without a changed user outcome count as **zero** new feature acceptance. A failed or missing mandatory gate is not waived by elapsed time. No duplicate VM jobs for the same change; no unbounded reruns after external infrastructure failure.

**First recorded on-device probe (12 November 2026):** owner reported all required booleans true, `package_identity=os-zapret2-restyle-0.6.4_44`, `status=PASS_READONLY_PRECONDITIONS`, with Config/service/IPFW untouched. User Domains Apply remains FAIL/BLOCKED.
