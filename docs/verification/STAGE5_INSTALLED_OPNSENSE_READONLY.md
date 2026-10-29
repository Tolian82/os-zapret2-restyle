# Stage 5 — read-only installed OPNsense evidence and IPv6 WAN eligibility

**Current candidate:** published and owner-installed `v0.6.1_12` (FreeBSD 15, testing-only); stable `v0.6.0` remains unchanged. **Installed Stage 5 acceptance OPEN.** The one-shot helper was source/CI-qualified in [PR #719](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40891815771); an actual owner-installed one-shot result is not yet available. The previous `_5`–`_7` package/boot failure and recovery instructions in this runbook are historical; current status belongs to [START_HERE](../START_HERE.md) and [PROJECT_STATE](../PROJECT_STATE.md).

## Two separate evidence levels

The existing production `voice_live_inspect.py` is the authoritative read-only attestation for common Config owner, live supervisor/engine, owned IPFW rules/tables, and Voice services. [`scripts/stage5-installed-evidence.py`](../../scripts/stage5-installed-evidence.py) remains the thin exact-`0.6.1_12` bridge with `collect` and `compare`; both always keep Stage 5 acceptance OPEN. It never writes to Config, IPFW, FD9 or service lifecycle.

New [`scripts/stage5-installed-one-shot.py`](../../scripts/stage5-installed-one-shot.py) calls that **same** bridge once and inspects *only* the already-managed IPSET files for configured Voice services. For every configured Voice service it counts IPv4 and IPv6 networks; when a globally routable IPv6 target is present, it invokes read-only `route -6 -n get` to check whether the kernel would select the service's attested WAN interface. It does not send a packet, change a route, open a divert socket, touch Config or start/stop a service. Any invalid snapshot, unexpected managed IPSET, symlink, wrong package version or non-ready owner is a refusal, not PASS.

The one-shot JSON reports `READ_ONLY_PREFLIGHT`, `stage5_installed_acceptance: OPEN`, `ipv6_packet_proven: false` and `exclude_packet_proven: false` **unconditionally**. A matching WAN route proves only *eligibility for a future test*, never observed IPv6 transmission, STUN response, actual DPI exclusion, Voice media, native Apply or FD9 rollback. If no configured globally routable IPv6 Voice target exists, it reports `NO_GLOBAL_IPV6_TARGET` and performs no route lookup.

## One owner action when the finished plan is ready for a live preflight

Execute only on the owner's disposable OPNsense test stand with the installed `0.6.1_12` package and a normally running service. The code is checked in at `main` after its own PR has merged. The following is **one shell command**, compatible with the OPNsense root `csh` prompt. It downloads two **read-only scripts** to `/tmp` and writes one JSON report, without Apply or IPFW changes:

```sh
/bin/sh -c '/usr/bin/fetch -q -o /tmp/stage5-installed-evidence.py https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/main/scripts/stage5-installed-evidence.py && /usr/bin/fetch -q -o /tmp/stage5-installed-one-shot.py https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/main/scripts/stage5-installed-one-shot.py && /usr/local/bin/python3.13 /tmp/stage5-installed-one-shot.py > /tmp/stage5-one-shot.json'
```

The owner can attach only `/tmp/stage5-one-shot.json` if an installed check is **explicitly** needed. The report does not contain raw IP addresses, raw packet bytes, full IPSET lists, raw saved Config or long engine logs. Avoid repeatedly asking for a separate series of terminal commands.

If the command fails, do not interpret the missing or partial output as a failed IPv6 service: read the exact `STAGE5_ONESHOT=UNVERIFIED` reason and review offline. No blind restart/Apply, IPFW flush, package reinstall or generated live testing may follow automatically.

## Next controlled WAN experiment: design only

The approved next design is the [same-pinned-endpoint WAN Exclude A/B protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md). It is **not yet** an executable instruction or permission to change the installed GUI Exclude IPSet. The current one-shot remains read-only: it only determines IPv6 Voice route eligibility. A future full packet experiment must first be tested offline, reviewed, and explicitly authorized for the owner's test stand.

## Remaining installed acceptance

Actual IPv4/IPv6 native destination handling (including global Exclude IPSet), live WAN IPFW divert/reinjection, one committed Config and FD9 rollback, and meaningful Voice/STUN/media must be established independently via a **single reviewed, rollback-safe owner scenario**. Do not experiment by deleting/replacing active managed files, changing `ipfw` on the appliance, altering shared service rules, or forcing failures on WAN.

Already qualified **separately in an isolated disposable FreeBSD 15.1 VM**: mixed IPv4/IPv6 IPFW tables, IPv6 UDP divert/reinject, transactions/rollback ([PR #694](https://github.com/Tolian82/os-zapret2-restyle/pull/694)), and real upstream `dvtws2 v1.0.6` matching IPv4/IPv6 same-destination Exclude IPSet across three profiles ([PR #718](https://github.com/Tolian82/os-zapret2-restyle/pull/718); [evidence](evidence/2026-10-29-v0.6.1_12-native-engine-exclude-loopback.md)). These do **not** close installed WAN or five Voice profiles. Strategy Lab IPv6 checkbox (Stage 6) is not yet implemented.
