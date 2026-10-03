# 2026-10-03 — A1 active, Docker test blocked by incorrect Linux route parser

**Status:** OWNER-LIVE A1 PERSISTED+EFFECTIVE+IPFW PREFLIGHT PASS · EXISTING SSH/TNAS ROUTES VERIFIED · **RUNNER BUG / NO DOCKER TRIAL / NO A1 MEDIA VERDICT**. The required next action is to update the existing one-command runner, **not** reconfigure A1, router proxies, TNAS routes or experimental desynchronization.

## Exact owner-supplied private archive and chronological stage

Owner uploaded `a1-20261003T054342Z-i1tW21.tgz`; the byte-identical private original supplied for inspection is **3,327 bytes**, SHA-256 **`7bc39f1fd86006ddbd041d50b6410fbec5799fccaf39a3cc5b48f2d4e09b88df`**. The one-shot runner `a1-one-command-v2-saved-gui-diagnostics` started **2026-10-03 05:43:42Z** and produced `result=PRECHECK_FAILED, script_exit=2`. The archive contains configuration snapshots and route diagnostics, but **no tgcalls_cli execution output or LAN/WAN PCAP**. These are **no network/strategy measurements**. Raw archive, effective full traffic config, private topology and SSH trust records remain off public GitHub; publish only the bounded results below.

### Distinct new positive configuration proof

The safely redacted saved GUI diagnostics have *all* `YES` markers:

```text
saved_gui_model=READ_OK
saved_gui_A1=YES
saved_gui_A1_port=YES
saved_gui_A1_payload=YES
saved_gui_A1_fake=YES
saved_gui_A1_ipset=YES
```

The runner independently accepted **one complete effective A1 profile** in `runtime-v2/traffic.conf`, the still-enabled STUN Voice helper, managed Telegram IPSET, Voice destination-scoped IPFW interception and the **now-present ordinary UDP capture on ports 596–599**. The preflight's observed IPFW rules included Voice **19000** `divert 989 udp ... table(zapret2_tgvoice) ... xmit vtnet1` and ordinary **19002** `divert 989 udp ... any 596-599 ... xmit vtnet1`. At this snapshot Voice was `requested=on`, `effective=on`, `service=running`, `active_profile=on`, **14 entries**; its counters were zero *before* testing, not evidence of failure. The previous [second preflight's saved-GUI-A1 absence](2026-10-02-docker-a1-second-preflight-saved-gui-absent.md) is **resolved** for the *current* active configuration epoch.

### Existing TNAS route guard was correct; the **runner's duplicate checker** was not

The already owner-qualified `/root/tgvoice-lab/ensure-tnas-routes.sh` invoked over the existing noninteractive SSH key completed successfully, reporting both specific routes already via **192.168.1.2**, without any manual TNAS login. The next new *read-only* SSH route preflight then obtained **this valid Linux response** for the fixed `91.108.13.10`:

```text
91.108.13.10 from 192.168.1.100 via 192.168.1.2 dev ovs_eth1 uid 0
    cache
```

The v2 runner incorrectly required the literal `src 192.168.1.100` in that `ip -4 route get "$target" from "$SRC"` response. Linux can echo the explicitly supplied source as **`from` instead of `src`**, so it emitted `ROUTE_INVALID` and stopped before checking the second route, Docker networking, binary SHA or running a call. The previous route guard also confirmed the second `149.154.167.99` route; its next duplicate check was never reached in this trial. The separate SSH post-quantum KEX warning did **not** indicate authentication or route failure.

**Root cause is a runner check's false negative on valid Linux route text, not broken TNAS routing and not a failed Telegram A1 strategy.** Do not alter TNAS routes to force a particular string format and do not infer a server/ISP UDP result.

## Approved narrow corrective and next experiment

Update the **same canonical independent** [GitHub one-command runner](../../../tools/telegram-voice-lab/run-a1-opnsense.sh): independently confirm that the expected **`192.168.1.100/...` IPv4 address is actually assigned to TNAS `ovs_eth1`**, then perform its explicitly sourced `ip -4 route get ... from 192.168.1.100` and require the correct **`via 192.168.1.2 dev ovs_eth1`** for each of the two pre-approved specific destinations; do **not** additionally require the kernel to repeat `src`. Retain the previously qualified owner's manual two-route guard, the exact SSH key/host trust, pinned host-network Docker binary/checksum, fixed endpoint/duration, active GUI/Voice/IPFW guards, both short LAN/WAN captures, cleanup, one private archive and fail-closed no-mutation behavior.

Add an offline regression that simulates **valid `from` output**, valid `src` output, *wrong gateway*, and *missing expected TNAS source address on expected interface*. All project CI and exact-head governance pass before merging, and verify main after. Then owner needs **one pinned-source replacement of only the OPNsense runner** (via already working Squid proxy `192.168.1.2:3128`) and runs that **same** one-command trial. Do not ask for a new A1 Apply, manual TNAS command, multiple tcpdump consoles, extra human Telegram call or new desynchronization candidate.

**Current acceptance gates:** A1 saved `YES`; A1 generated `YES`; A1 ordinary UDP capture `YES`; TNAS guard route `PASS`; second redundant runner route check `FALSE NEGATIVE`; remote binary and Docker A1 `NOT RUN`; `REFLECTOR_READY`, `MEDIA_PASS` and real-client `CALL_PASS` remain **OPEN**.
