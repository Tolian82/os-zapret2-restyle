# Stage 5 — single owner-reviewed baseline WAN checkpoint (review only)

**29 October 2026. Status: REVIEW PREPARED, NOT AUTHORIZED, NOT EXECUTED.** This is the next narrow operator-facing gate after [PR #725](https://github.com/Tolian82/os-zapret2-restyle/pull/725) merged and the isolated FreeBSD 15.1 native `tcpdump` lifecycle test passed. It does **not** establish an installed OPNsense Ethernet-WAN trial, actual DPI modification, global Exclude IPSet suppression, A07/A08 or native IPv6 acceptance. Stable `v0.6.0`, published/installed testing `v0.6.1_12`, `VERSION=0.6.1` and `PLUGIN_REVISION=12` stay unchanged.

## Review objective

Obtain at most **one** later, explicitly owner-approved baseline-only HTTPS request, with a real Ethernet-linktype PCAP from the installed OPNsense WAN and an unchanged verified native common owner. No automatic second/excluded phase, no Exclude edit, GUI Apply, Config/FD9/IPFW change, service restart or firewall recovery. The exact existing [single-phase capture controller](STAGE5_WAN_SINGLE_BASELINE_CAPTURE.md), not copied shell command arrays, owns subprocesses, deadlines and cleanup.

**This document is not consent.** The owner's general instruction to continue project development does not authorize traffic capture or an appliance test. The capture command and its live opt-in must not be issued until the owner has reviewed the exact proposed destination and independently approved **one** live baseline request.

## Pinned review inputs — no implicit fallback

| Field | Review requirement |
| --- | --- |
| Appliance/package | Installed OPNsense, root, exact testing package `os-zapret2-restyle-0.6.1_12`; healthy common owner, supervisor and owned IPFW attested by the existing production inspector |
| Tools | The exact reviewed GitHub `main` source at `3dd108412ba1a984e8b52456f05cb0ef15aa373d`, not moving `main`: `stage5-wan-acquisition-plan.py`, `stage5-wan-baseline-capture.py`, `stage5-installed-evidence.py` and `stage5-wan-pcap-attribution.py` staged adjacently; source/pinning verified before use |
| Candidate | One freshly checked domain and pinned public remote address outside active global Exclude and all Voice IPSETs, demonstrably eligible for one current ordinary TLS/443 HOSTLIST profile |
| Flow | One concrete WAN interface, a presently assigned same-family source address, and one reviewable unused local TCP source port; no hardcoded historical WAN source assumption |
| Network | The remote route resolves to the declared WAN; `tcpdump -L` offers Ethernet `EN10MB` there; IPv6 is eligible only with a real same-family source and route |
| Probe | One direct proxy-disabled HTTPS HEAD with the exact pinned remote IP, Host/SNI, source IP and port from the trusted generated plan; max 12 seconds, overall capture/probe deadline 18 seconds |
| Evidence | One bounded classic Ethernet PCAP stored locally with restrictive permissions, a compact redacted JSON and an unchanged-before/after native-owner comparison; no raw packet bytes or private configuration in GitHub/chat |

Historical `yt3.ggpht.com / 142.251.127.198` is a **potential** IPv4 control, not a live-pinned endpoint or a proven modified DPI payload. The previously excluded AFRINIC target is not in HOSTLIST, and Telegram `t.me` overlaps Voice; neither can be silently substituted as an A07 Strategies control. The [read-only target selector](STAGE5_WAN_TARGET_READONLY.md) can nominate candidates, but only current owner/native/WAN checks can qualify the chosen flow.

## Single checkpoint procedure — only after separate owner authorization

1. **Review and freeze inputs.** Use the existing read-only target selector and existing owner/native inspector to select one actual eligible endpoint; confirm WAN address, family, source port, installed package and reviewed source commit. Any missing or ambiguous field is `BLOCKED`, not guessed.
2. **Validate offline.** Produce one JSON with the trusted [plan generator](STAGE5_WAN_ACQUISITION_PLAN.md) from exactly those fields. Run the already available capture controller in `--check --plan <file>` mode. `PLAN_VALIDATED_ONLY` means *no native inspection and no packets*; it must never be presented as a WAN or owner proof.
3. **Get independent explicit consent.** Present the exact hostname, pinned IP, address family, WAN interface, source address/port, single HTTPS HEAD, 18-second bound and local PCAP retention. The owner must explicitly authorize only this baseline trial; general project continuation, old approvals and an offline `--check` result are insufficient. No executable live command is supplied by this document before that decision.
4. **Run one owner-gated baseline, if approved.** Only the existing `--execute --plan <file>` controller with its separate exact opt-in performs the trial. It must first check installed native ownership, read-only `ifconfig`/FIB/`tcpdump -L` and local-port availability, then observe real `tcpdump` readiness, start one pinned curl, terminate its own processes and compare the unchanged native owner. No direct manual `tcpdump`/curl command-array execution or repeated retries.
5. **Review the sanitized result.** Keep any raw `baseline.pcap` only on the appliance. Share only the redacted JSON result and narrowly required process/route/DLT evidence, never raw PCAP, credentials, full Config, hostlists or live process arguments. If it succeeds, classify `BASELINE_CAPTURE_OBSERVED_ONLY`; independently proving real selected Lua modification is still a separate gate. Do not proceed to an Exclude phase or GUI mutation without its own specific approval and restoration design.

## Stop conditions and classification

Refuse or stop on mismatched package, changing/unknown native owner, unverified source/route, non-Ethernet DLT, unavailable/busy source port, unsupported family, stale pinned target, missing readiness, failed HTTPS, timeout, ambiguous/empty PCAP, changed owner, failed cleanup or any attempted unapproved Config/IPFW/GUI action. The controller must fail closed and remove its partial artifacts; do not force IPFW, restart services or improvise a route to “fix” the gate. Treat an uncertain owner or cleanup result as **unsafe/inconclusive**, never as capture success.

Even if the single baseline succeeds, `engine_strategy_modification_proven=false`, `exclude_effect_proven=false`, `wan_origin_proven=false` in the current controller's output are deliberate limits. `installed_a07=OPEN`, `installed_a08=OPEN`, real installed IPv6 transmission/reinjection, FD9 rollback, Telegram media/call and Strategy Lab IPv6 remain separate unpassed acceptance conditions. One PCAP, HTTP status, aggregate IPFW counter or payload fingerprint alone cannot prove A07/A08. See the [full A/B protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md) and [offline attribution limits](STAGE5_WAN_OFFLINE_PCAP_ATTRIBUTION.md).

## Completion gate for this documentation increment

Completed now: the **review and consent boundary**, exact input/output contract, fail-closed stop conditions and the one-request scope are explicit, grounded in existing source and isolated-VM CI. **Not completed:** owner authorization, any staged/running tool on installed OPNsense, real Ethernet WAN linktype/capture, genuine DPI Lua-modification proof, Exclude A/B and native IPv6/Voice acceptance. The next permitted transition is an independently authorized **single** baseline checkpoint, not a new package or an unapproved on-appliance experiment.
