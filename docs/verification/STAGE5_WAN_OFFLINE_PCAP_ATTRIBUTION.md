# Stage 5 — offline WAN TCP PCAP attribution, without live changes

**Status (29 October 2026): source/CI-qualified in [PR #722 Project/Voice/FreeBSD15/package CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40908965260); installed OPNsense execution and on-WAN packet proof OPEN.** This is a read-only evidence-processing building block, not a live packet collector or automatic Exclude IPSet A/B implementation. Stable `v0.6.0`, published `v0.6.1_12` and existing service/Config/IPFW remain unchanged.

## User-visible scenario and proof scope

Given **two already-collected** bounded Ethernet PCAP files (one candidate-baseline and one excluded), plus a declarative manifest with the *same* remote TLS/443 destination and explicitly named source IP/port in each phase, [`scripts/stage5-wan-pcap-attribution.py`](../../scripts/stage5-wan-pcap-attribution.py) outputs a **single sanitized JSON report** identifying packets of that exact TCP five-tuple. It discards unrelated flows, counts reverse traffic, deduplicates repeated identical payload segments at the same TCP sequence number, and hashes outgoing payload bytes in sequence order **without the random initial sequence numbers**. It reports ambiguous same-sequence data conflicts as inconclusive.

The following are **not** established from two caller-supplied captures: actual capture interface and WAN egress, original TLS SNI/Host (the manifest's domain is merely a declared identity), correctness/completeness of TLS reassembly, baseline Lua modification, global Exclude match/suppression, installed IPv6 packet behavior, actual Voice/STUN media, FD9 Apply or Config restoration. Even matching or differing per-phase fingerprints **cannot** close installed A07/A08 acceptance. The report always uses `wan_capture_proven=false`, `tls_sni_proven=false`, `dpi_modification_proven=false`, `exclude_effect_proven=false` and `a07_installed_acceptance=a08_installed_acceptance=OPEN`. TCP source port and sequence count do not identify the running Zapret2 strategy on their own.

**Important:** This tool does **not** execute tcpdump, curl, DNS, send packets, run IPFW, call the OPNsense service, modify live or saved Config, or download/install anything. No captured packet bytes are exported; raw captures stay on the machine where they are examined. No owner console action is requested or authorized by this document.

## Bound input and error policy

- Inputs are three different existing regular files (one JSON manifest, two `pcap`), opened without following symbolic links and rejecting hardlinks. Manifest maximum **4096 bytes**; each PCAP maximum **8 MiB**, **2048 packets**, **256 matching outbound packets**. Invalid/truncated records, snaplen truncation, fragmented IPv4, unsupported IPv6 extension chains, ambiguous same-TCP-sequence payload or other uncertainties cannot yield installed acceptance.
- Only classic **Ethernet PCAP v2.4** with microsecond or nanosecond timestamp magic, little- or big-endian, is supported. Untagged and up to two VLAN tags; `pcapng`, FreeBSD `DLT_NULL`, `DLT_RAW` and captures without full packet bytes are **not supported**. A tool that receives one of those must fail closed, never silently interpret another format as Ethernet.
- The manifest is strict; no unexpected keys, no loopback/private remote target, invalid source-family mismatch, invalid TCP source port or arbitrary extra arguments. The normal candidate is TLS TCP/443; *no TLS payload parser/verification* is performed.
- TCP payload comparisons are **observations** only. Segmentation, retransmission, TLS ClientHello differences, different source ports or packet-capture offload may make otherwise comparable experiments have different fingerprints. Hash equality also cannot prove absence of DPI action.

## One-phase offline inspection of the owner-observed baseline (30 October 2026)

The real OPNsense 26.7.7 / FreeBSD 15.1 testing package `0.6.1_12` produced one previously authorized **`BASELINE_CAPTURE_OBSERVED_ONLY`** for `yt3.ggpht.com -> 142.251.127.198:443`, `192.168.80.251:54111`, declared `vtnet1`; 14,941-byte PCAP, 18 observed outbound TCP packets, 6 outbound payload packets, stable native owner. PCAP remains in `/tmp/zapret2-wan-one-4uv588kt/baseline.pcap`; its original, already-validated plan is `/tmp/zapret2-stage5-retry.otJS8S/plan.json`. These filenames are **this specific owner event**, not portable defaults.

The new `scripts/stage5-wan-baseline-offline-review.py` accepts the **existing** `--plan` and `--baseline` only and uses the **existing** exact-plan validator and strict read-only Ethernet PCAP parser from adjacent trusted tools. It does not need an excluded-phase capture. It emits a single sanitized `BASELINE_OFFLINE_REVIEW_ONLY` JSON report: exact five-tuple observed, outbound/reverse packet totals, TCP payload segment counts, same-sequence duplicate/conflict counts and a SHA-256 capture identifier. `CORRELATED_TCP_PAYLOAD_OBSERVED_ONLY` means only that the selected TCP flow contained outbound payload; conflicting data at one TCP sequence yields `AMBIGUOUS_SAME_SEQUENCE_TCP_PAYLOAD`, **not** DPI modification proof. All results retain `wan_origin_proven=false`, `tls_sni_proven=false`, `engine_strategy_modification_proven=false`, `exclude_effect_proven=false`, `installed_a07=installed_a08=OPEN`.

This helper performs **no live request, DNS, packet capture, service/native-owner read, IPFW, Config, GUI Apply or Exclude modification**. It checks bounded regular files, refuses symbolic/hard links, validates the original plan using the original generator and does not print packet bytes. Existing signed approval for one HTTPS request has been consumed; **do not generate another live capture without new owner authorization**. A read-only local offline review of the retained PCAP does not require a further traffic authorization.

A portable source-checkout example (offline files must already exist):

```sh
python3 scripts/stage5-wan-baseline-offline-review.py --plan existing-plan.json --baseline existing-baseline.pcap
```

## Offline invocation (not an OPNsense capture command)

The source is in the repository. A controlled, already-authorized offline workstation can run it against **existing** files:

```sh
python3 scripts/stage5-wan-pcap-attribution.py --manifest flow.json --baseline baseline.pcap --excluded excluded.pcap > flow-report.json
```

Example `flow.json` **for the synthetic IPv4 test fixture only**, not an attestation of your current live WAN:

```json
{
  "schema_version": 1,
  "domain": "yt3.ggpht.com",
  "remote_ip": "142.251.127.198",
  "wan_interface": "vtnet1",
  "baseline": {"source_ip": "192.0.2.10", "source_port": 54111},
  "excluded": {"source_ip": "192.0.2.10", "source_port": 54111}
}
```

To test IPv6, use an IPv6 remote and the *same-family* IPv6 source. The supplied interface name and domain are **declarations** (not verified provenance). Normal run outputs `OFFLINE_CAPTURE_ATTRIBUTION_ONLY`, not `PASS`. On errors the script stops with nonzero exit and `WAN_PCAP_ATTRIBUTION=UNVERIFIED`; it does not reinterpret a parser error as missing DPI bypass.

The planned [WAN acquisition argument generator](STAGE5_WAN_ACQUISITION_PLAN.md) can produce the precise two-phase manifest consumed here, but **does not capture packets or prove their provenance**. The independent owner-live controller and GUI approval remain separate open gates.

## Verification and what comes next

The included [focused no-network matrix](../../scripts/test-stage5-wan-pcap-attribution.py) uses synthetic IPv4/IPv6 Ethernet/TCP PCAPs; it covers VLAN, little/big endian, strict five-tuples, reverse/unrelated packet rejection, differing payload observations, changing initial TCP sequence number, duplicate retransmit/conflict handling, wrong family/schema, unsafe files, malformed PCAP/record truncation, IPv4 fragments and IPv6 extension refusal. **Local Python syntax and 13 focused tests executed successfully before PR, and [PR #722 exact-head Project/Voice/FreeBSD15/package CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40908965260) passed; no real WAN packets were observed.**

Next steps are to confirm a safe real packet-acquisition plan (bounded duration, known interface, controlled source IP/port, preservation of raw PCAP **locally only**), source attribution to an actually active strategy and a defensible baseline-Lua modification witness. Only **then**, after explicit owner permission and a proven restoration path, run one consolidated A/B GUI Apply trial under the [existing installed WAN protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md). If such proof cannot be obtained, Stage 5 installed and A07/A08 remain OPEN.
