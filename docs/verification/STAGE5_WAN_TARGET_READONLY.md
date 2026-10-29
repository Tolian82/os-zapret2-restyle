# Stage 5 — one-shot read-only WAN target-selection preflight (v0.6.1_12)

**Status (29 October 2026): source candidate; CI and installed-owner acceptance separately tracked.** This is an intermediary for the [same-destination A/B WAN evidence protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md), not A07/A08/IPv6 acceptance. The previously installed `os-zapret2-restyle-0.6.1_12` package and stable v0.6.0 do not change.

## What this actually establishes

[`scripts/stage5-wan-target-preflight.py`](../../scripts/stage5-wan-target-preflight.py) performs one bounded read-only collection:

1. Delegates package-version, current committed owner, process and real IPFW health to the **existing production** native inspector via `stage5-installed-evidence.py`; rejects a missing/unready owner or installed package other than `0.6.1_12`.
2. Parses the **actual active** `runtime-v2/dvtws.args` using production `global_exclusions.segments/templates_and_imports/inherited` and verifies exactly one final global Exclude per executable profile. It does not synthesize or change a strategy. Only possible ordinary TLS/443 HOSTLIST profiles are considered; explicit IPSET/Voice and incompatible L3-family filters cannot silently qualify.
3. Checks exact/parent domain membership in managed `hostlist-user.txt` / `hostlist-youtube.txt`, with bounded regular-file reads (no symlinks/hardlinks) and safely rejects malformed or whole-family IPSETs. It will never select an address already covered by the actual managed global Exclude or any of five Voice IPSETs.
4. Considers **at most three fixed controls** previously observed in the owner's hostlists: `yt3.ggpht.com`, `play.google.ru`, `zyro.com`. Makes bounded DNS **lookup queries only** (up to 8 seconds per eligible domain) and read-only FreeBSD FIB queries `route [-6] -n get`; it sends **no HTTP, TLS, UDP/STUN or target-connection probes**. Keeps at most two IPv4 and two IPv6 candidate addresses per domain and a total of four candidates.
5. Requires an actual route and, when a configured Voice service attests a WAN, refuses route interfaces inconsistent with those attested WANs. Prints a single small JSON object: pinned domain/IP/family, potential profile ordinals, proposed TCP/443/SNI/Host and selected route interface. Source address/port and five-tuple attribution remain `null`/`false`; a real matching Lua modification remains `false`.

For every report, `status=READ_ONLY_CANDIDATE_PREFLIGHT`, `qualification=POTENTIAL_ONLY`, `a07_installed_acceptance=OPEN`, `a08_installed_acceptance=OPEN`, `ipv6_packet_proven=false`, `exclude_packet_proven=false`, `baseline_modification_proven=false`. No candidate is `NO_ELIGIBLE_CONTROL_FOUND`, **not** a failed IPv4/IPv6 service.

The report contains only a maximum of four selected external domains/IPs and minimal routing/profile identifiers; no raw HOSTLIST/IPSET, Config XML, credentials, packet bytes, process argv, Lua functions, or PCAP is exported. DNS lookup traffic is the only intentional network traffic.

## Future single-command collection — owner permission required to request execution

This is prepared for the owner's test stand, **not executed** by the assistant and not automatically requested simply because CI passed. In root OPNsense `csh`, the command launches a POSIX `sh` process, stages exactly two read-only scripts under `/tmp`, and stores one JSON file:

```sh
/bin/sh -c '/usr/bin/fetch -q -o /tmp/stage5-installed-evidence.py https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/main/scripts/stage5-installed-evidence.py && /usr/bin/fetch -q -o /tmp/stage5-wan-target-preflight.py https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/main/scripts/stage5-wan-target-preflight.py && /usr/local/bin/python3.13 /tmp/stage5-wan-target-preflight.py > /tmp/stage5-wan-target.json'
```

The owner then attaches only `/tmp/stage5-wan-target.json`. A failure is `WAN_TARGET_PREFLIGHT=UNVERIFIED` with the exact cause; it must not trigger restart, GUI Apply, IPFW adjustment, manual Config rewrites or broad hostlist investigation. Because `/tmp` does not establish an installable package, this is documentation/CI-only tooling; it does not change the immutable published `_12` package.

## What remains OPEN

This tool **does not** observe packets, verify WAN source-port/five-tuple attribution, establish baseline Lua modifications, prove Exclude suppression, test actual IPv6/Voice media, or confirm GUI Apply/FD9 restoration. The full [A07/A08 on-WAN acceptance procedure](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md) requires a separately reviewed, externally attributable packet capture with a pinned request and explicit owner-approved Config changes/restoration. Before owner testing, verify source/CI and operational safety against actual installed device context. Isolated real FreeBSD engine IPv4/IPv6 loopback A/B [already passed](evidence/2026-10-29-v0.6.1_12-native-engine-exclude-loopback.md); it cannot replace installed WAN evidence.
