# Stage 5 — installed OPNsense WAN Exclude IPSet A/B acceptance protocol

**Status (29 October 2026): design only; owner-live execution NOT AUTHORIZED or performed.** Candidate is the *existing installed* testing-only `os-zapret2-restyle-0.6.1_12`. No new package or installed mutation is implied by this document. The real native `dvtws2 v1.0.6` Exclude IPv4/IPv6 loopback A/B [passed isolated FreeBSD15.1 CI](evidence/2026-10-29-v0.6.1_12-native-engine-exclude-loopback.md). The installed WAN, FD9, native IPv6, Voice call/media and on-wire Exclude acceptance remain **OPEN**.

## 1. Aim and separate proof levels

- **A07 (Strategies):** For *one identical remote destination IP*, SNI/Host and request, obtain independently attributable evidence that a currently eligible, enabled DPI Strategy changes a relevant outgoing packet without the global Exclude match, and that **the same flow class** passes without that modification when the remote IP is excluded. Use a first/middle/last strategy only when a live eligible candidate really exists; previously qualified VM profile positions do not substitute for installed WAN proof.
- **A08 (Voice):** Separate acceptance for each actually configured Voice profile and applicable IPv4/IPv6 destination in the five managed Voice IPSETs. Telegram STUN presence is not Telegram media/call success. Do not enable an unconfigured service merely to obtain an A08 tick.
- **Stage 5 IPv6:** Prove IPv6 WAN eligibility, actual family and captured transmission/reinjection with packet-level observations. A routing-table lookup, IPFW counter increment, `curl` HTTP status, or the absence of errors **does not** prove IPv6 or exclusion. A WAN without IPv6 remains a supported `UNAVAILABLE` family, not a failed IPv4 acceptance.
- **FD9 / rollback:** Existing shared Apply/config persistence and a clean restoration to previous owner are separate checks. Never inject a firewall or transaction failure on the owner's live gateway. Real fault injection remains in isolated FreeBSD CI.

Any result other than fully correlated and cleanly restored packet evidence is recorded as `INCONCLUSIVE`, `UNAVAILABLE` or `BLOCKED`, **not** inferred `PASS`.

## 2. Existing observed facts — do not re-request them

- Owner-installed `v0.6.1_12` service ran successfully; global `196.216.2.24/29` Exclude was normalized and persisted; all **8/8** executable profiles had exactly one native `--ipset-exclude`.
- `pay.afrinic.net` pinned to `196.216.2.28` was reachable (HTTP 302) and covered by existing Exclude **but matched neither active HOSTLIST**. It is therefore **not** an adequate A07 Strategies control.
- `yt3.ggpht.com` pinned to `142.251.127.198` matched both existing HOSTLISTs, did **not** match existing global Exclude or any of the five Voice IPSETs, and reached HTTP 400. This is a **candidate** for a controlled IPv4 Strategies control, not an established live Lua-modification witness; IP ownership/routing/hostlist contents must be freshly attested at execution time.
- Telegram `t.me` pinned to `149.154.167.99` is inside managed Telegram IPSET `149.154.160.0/20`; do **not** use it as an isolated Strategies control.
- Previous shared TCP IPFW counter increments were not flow-attributed; they are neither evidence of Lua modification nor evidence of exclusion.

See the [owner read-only report](evidence/2026-10-29-v0.6.1_12-installed-one-shot-exclude.md) and [native engine proof](evidence/2026-10-29-v0.6.1_12-native-engine-exclude-loopback.md).

## 3. Safety and start gate (read-only only)

**Owner approval is required separately before even a reversible live GUI Exclude edit.** A normal PR/CI does not authorize production/appliance Config changes. No attempt may replace managed files, edit `/conf/config.xml`, add/delete/flush IPFW rules, attach a second process to the active divert port, stop the service, inject an IPFW error, or modify network routing.

Before a live A/B, the implementation must have a **single bounded owner-run script** whose source and focused tests have been reviewed and merged. Required dry preflight:

1. Confirm installed `0.6.1_12`, existing native owner `ready`, service and engine `running`, and intact managed config/IPFW ownership via the **production** `voice_live_inspect.py` (not duplicate ownership logic). Reuse the CI-qualified [read-only one-shot](STAGE5_INSTALLED_OPNSENSE_READONLY.md) for IPv6 Voice route eligibility.
2. Select **one** domain already matched by a real enabled Strategy and **one** pinned IPv4 or IPv6 address. Confirm target family/route/WAN, TLS SNI/Host identity, absence of Voice IPSET overlap for A07, and exact global Exclude membership. For IPv6, an actual global IPv6 route through the correct WAN is mandatory.
3. Require reliable packet source attribution, e.g. a uniquely reserved TCP local source port or controlled five-tuple and bounded packet capture on the **actual egress WAN**. Check that no other current traffic collides with this five-tuple. Capture both phase transcripts with identical endpoint, protocol, SNI and request body. Do not assume `tcpdump` sees exactly what the downstream peer receives.
4. Bound packet count/duration, snap length and evidence sizes. Keep raw PCAP locally; export only **sanitized and flow-correlated** headers, per-phase counters, hashes/lengths and evidence classification. Never upload raw Config, complete HOSTLIST/IPSET, TLS secrets, full captures or credentials. An incomplete capture is `INCONCLUSIVE`.
5. Take immutable **read-only** before witnesses of Config digest, owner, managed Exclude content digest, active release, engine process identity, plugin IPFW rules/tables, and appropriate route. Capture independent service health. No diagnostic script may silently switch the Exclude setting.

If these requirements cannot be met, stop as `BLOCKED` before any state change.

## 4. Controlled same-endpoint A/B — proposed, NOT executable yet

| Phase | Exclude for the one pinned IP | Action | Required evidence |
|---|---|---|---|
| A — baseline | IP **absent** | One fixed, uniquely identified controlled request through the normal service and existing WAN | Attributable proof that the **active strategy actually selected and modified/emitted** the intended flow; HTTP success alone is insufficient |
| B — excluded | IP **present** | Repeat identical request to the same pinned endpoint, family, Host/SNI and chosen local source port (sequentially; never concurrent collisions) | Matching native global Exclude reference, unaltered outgoing flow in the bounded capture, no strategy-generated modification for the same eligible packet |
| R — restoration | Return to **exact owner-approved original Exclude** | Normal supported GUI Apply only, followed by independent health/ownership attestations | Same saved Config semantics and managed Exclude, healthy current owner and IPFW ownership; restoration not assumed from a successful GUI toast |

For the existing `196.216.2.24/29` Exclude, a Strategies control IP is added **temporarily** only after explicit approval. If there is no live phase-A strategy modification to observe, **do not** change Config for phase B: record `NO_BASELINE_MODIFICATION / INCONCLUSIVE` and choose a new target in offline engineering. Never force a global Voice UDP `0.0.0.0/0` or `::/0` or broaden existing IPFW capture.

The eventual owner workflow should be **one reviewed scripted collection** with clearly labelled, explicitly acknowledged GUI Apply boundaries, rather than repeated unstructured shell requests. The script itself stays read-only; every GUI Apply is an intentional owner action. Do not automatically toggle settings via an API or rewrite active files as a shortcut. Where even temporary application risks connectivity, stop at preflight and keep Stage 5 OPEN.

## 5. Classification and stop conditions

**PASS is narrowly scoped to a specific protocol/IP family/target/strategy only when** baseline mutation is directly attributable, Exclude suppresses that same mutation, both phases have stable pinned endpoint and host identity, and restoration and service health are independently attested. Aggregate IPFW counters may be logged for context, but never substituted for payload or strategy evidence. IPv4 PASS cannot count as IPv6 PASS; Strategies PASS cannot count as Voice A08; native loopback CI PASS cannot count as WAN PASS.

`UNAVAILABLE`: family has no actual usable route, no eligible same-family service target, or no compatible capture. `INCONCLUSIVE`: baseline already unchanged, differing endpoint/strategy, offload obscures comparison, capture incomplete, packet ambiguity or only HTTP/IPFW counters observed. `BLOCKED`: mismatched version, ownership, untrusted files, unexpected rule, unsafe Apply, unproven restoration or affected connectivity.

On unexpected state change or uncertain rollback, immediately stop the experiment, preserve evidence locally, and use only the **existing native supported** repair/GUI controls after diagnosing the actual failure. Do not issue `ipfw flush`, ad hoc kernel module toggles, blind service restart, or force-write a previous Config merely to make the test green.

**Additional isolated native negative control qualified (30 October 2026):** Alongside the earlier two-phase loopback dvtws2 test, the disposable FreeBSD 15.1 VM now executes a **third control with nonmatching Exclude IPv4 and IPv6 CIDRs**; real [native CI #41062883392](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41062883392) PASS. The real engine must still apply the three test-only `VERDICT_DROP` profiles to local `127.0.0.1` and `::1` despite the `--ipset-exclude` option being present. The matching-Exclude phase must pass the same payloads. This closes the risk of a blanket bypass whenever the option exists; it does **not** prove installed WAN, original TLS strategy alteration, Voice media, or an owner-approved A07/A08. This native VM control passed on the source head used in CI #41062883392; future changes must preserve the same exact-head native gate. No live request, appliance mutation or new Python requirement is included.

**Offline A07 A/B/restoration readiness increment (30 October 2026):** The new [non-executing retrospective reviewer](STAGE5_WAN_AB_READINESS.md) binds the trusted plan/PCAP and production-native owner snapshot parsers. It validates absent→present→restored Exclude membership for one pinned IPv4/IPv6 endpoint, two captured flow identities, changed/returned Config digest, restored IPFW/Voice scope and exact original managed Exclude bytes. All outputs remain `REVIEW_ONLY` with `phase_b_permitted=false`; installed A07/A08 remain `OPEN`. Captures and snapshots cannot independently prove Lua packet modification, WAN origin, process continuity, real SNI or owner consent. The reviewer never sends traffic or invokes GUI Apply. The prior single baseline permits only baseline-only offline review; new live actions still require separate approval.

## 6. Next engineering work, no owner action yet\n\n- The [installed TLS Phase-A identity and packet-provenance design](STAGE5_INSTALLED_TLS_PHASE_A_PLAN.md) requires four separate witnesses, including actual effective production TLS profile and independent engine-action/packet attribution. It is non-executing and does not authorize a fresh WAN capture, phase B or GUI Apply.\n

- The [bounded read-only A07 target-selector](STAGE5_WAN_TARGET_READONLY.md) and 19 focused tests passed [PR #721 Project/Voice/FreeBSD15 CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40902179064). It only nominates candidates: actual five-tuple attribution, baseline Lua modification, excluded WAN packet evidence and owner-live acceptance all remain OPEN.
- Qualify exact packet comparison semantics on a disposable FreeBSD 15.1 WAN-like path/CI fixture before asking for installed packet evidence; the existing loopback `dvtws2` test is the lower proof level.
- A [consent-gated baseline-only lifecycle controller](STAGE5_WAN_SINGLE_BASELINE_CAPTURE.md) is a source/CI candidate, not owner-live acceptance: native owner/route/port/DLT checks and bounded process cleanup still require native FreeBSD qualification, then separate owner permission. It cannot toggle Exclude or start a second A/B phase; actual Lua baseline modification and GUI restoration proof remain independent.
- The [bounded non-executing WAN capture-plan helper](STAGE5_WAN_ACQUISITION_PLAN.md) proposes identical source/target five-tuples, bounded tcpdump filters and one pinned HTTPS request per phase with exact existing offline-analyzer manifest. This is **not** capture, live-flow ownership or owner authorization. A separate bounded lifecycle controller and explicit GUI consent remain required before live execution.
- The new [offline TCP PCAP attribution helper](STAGE5_WAN_OFFLINE_PCAP_ATTRIBUTION.md) analyzes only **already-collected** bounded Ethernet captures and deliberately does not attest actual WAN origin, SNI or DPI mutation. Next design needs a safe acquisition/controlled source-port witness on the owner's WAN; never assume packet fingerprints alone close A07/A08.
- Draft/validate one bounded owner-run command and small sanitized report format. Explicitly gate all GUI Apply work on owner approval. Do not publish a new package solely for the evidence tool.
- Stage 6 Strategy Lab IPv6 checkbox and 150/200 / 270/350-second budgets remain a separate workstream; **not** accidentally implemented or declared accepted here.
