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

## Owner-confirmed one-phase offline result (30 October 2026)

**Owner-executed Stage 5 retrospective evidence (30 October 2026, installed OPNsense 26.7.7 / FreeBSD 15.1, package `0.6.1_12`):** The separately qualified one-phase, no-network offline reviewer processed the **previously retained** `/tmp/zapret2-wan-one-4uv588kt/baseline.pcap` and original generated plan, returning `BASELINE_OFFLINE_REVIEW_ONLY` / `CORRELATED_TCP_PAYLOAD_OBSERVED_ONLY`. Exact bounded report: `ipv4` `192.168.80.251:54111 -> 142.251.127.198:443`, **18 outgoing / 14 incoming TCP packets**, **6 outgoing payload packets / 6 unique segments**, **1,766 observed outbound payload bytes**, 0 duplicate payload packets, 0 same-sequence conflicts, 0 unrelated packets, outgoing flags SYN=1, FIN=1, RST=0. Capture SHA-256 `0e8187f524259d36db99a472a0f25969431468cadbf173b0616339108200bc21`; sequence-ordered unique payload fingerprint `d67fc57e934408a9c177f1d09fbb557515ec49d5651ac12b95aee98e22de9019`. **This verifies only correlated observed TCP-flow contents in the supplied PCAP, not original SNI, independently verified WAN origin, dvtws2/Lua packet alteration, Exclude effect, IPv6 or Voice media**. `installed_a07=OPEN`, `installed_a08=OPEN` unchanged. Raw capture retained locally; no new WAN packet or active appliance change was performed by the offline test. One-HTTPS-trial permission remains consumed.

The next **read-only** question is whether any of the 32 retained IPv4/TCP packet *headers* contain an explainable anomaly. An already present system `tcpdump` can print time, TTL, IP identifier, TCP flags, sequence/acknowledgment numbers, TCP options and payload **lengths** from the original PCAP with `-nn -tt -v -r`. Do not use `-A`, `-X`, `-XX` or live interface `-i`; never export raw packet bytes. Any checksum anomaly may be due to NIC offloading; an unusual TTL/IP ID/sequence alone cannot attribute modification to a particular Lua strategy. Do not infer SNI or successful HTTPS solely from TCP headers. No new network permission exists.

## Retrospective absolute-number result and owner stop gate (30 October 2026)

**Owner-confirmed final retrospective TCP sequence witness (30 October 2026):** The owner ran the consent-free, offline absolute-number `tcpdump -S -v -r` over the **same previously SHA-256 verified PCAP** `0e8187f524259d36db99a472a0f25969431468cadbf173b0616339108200bc21`. The client's initial SYN sequence number was **3827693904**, the server's first reply after client payload carried cumulative **ACK 3827694067** and SACK **[3827693904, 3827693905)**. The SACK range contains exactly **one TCP sequence-space position coinciding with the initial SYN sequence number**. Under [RFC 2883](https://www.rfc-editor.org/rfc/rfc2883), a first SACK block below the ACK is consistent with a D-SACK-like duplicate indication; under [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293), SYN itself consumes one sequence number. Therefore **do not label the SACK as an observed duplicate byte of TLS data, injected fake SYN, dvtws2/Lua strategy modification or Exclude success**. This single PCAP does not establish downstream origin or independent WAN provenance, and further reprinting of the same headers cannot close A07/A08. **Owner requests no more piecemeal console tests:** retrospective PCAP/header investigation is complete for now; A07/A08 remain OPEN. The next possible *live* gate is one fully engineered, independently approved, controlled same-endpoint A/B for A07 (with existing native state and restoration safeguards); Voice/IPv6 acceptance remains separately unproven. No further live network request, service, Config, GUI Apply or IPFW operation is authorized. Continue source/CI engineering independently, especially existing `v0.6.1_13` installed Python runtime task [#732](https://github.com/Tolian82/os-zapret2-restyle/issues/732); do not relabel the standalone/docs-only change as a new package.

## Owner-confirmed header-only TCP sequence and D-SACK lead (30 October 2026)

**Owner-confirmed header-only retrospective (30 October 2026):** `/usr/sbin/tcpdump -nn -tt -v -r` examined **the same previously SHA-256-verified** 14,941-byte classic Ethernet PCAP (`0e8187f524259d36db99a472a0f25969431468cadbf173b0616339108200bc21`), **not** a second connection. All 32 reported packets belong to the IPv4 flow `192.168.80.251:54111 ↔ 142.251.127.198:443`; 18 outbound, 14 inbound. The outbound data segments are consecutive `seq 0:163`, `163:1371`, `1371:1562`, `1562:1642`, `1642:1742`, `1742:1766` (lengths 163, 1208, 191, 80, 100, 24; **1,766 bytes**). The remote TCP data spans `seq 1:10500` (**10,499 bytes**). Normal SYN/SYN-ACK/ACK establishment and both FIN directions are visible; no RST, obvious seq overlap/retransmission, TTL-divergent outbound packet or bad checksum in the displayed headers. Outbound TTL is 64; inbound TTL 118, outbound IP IDs 0 (most headers), 1, 2 in the two later initial segments; the server uses ID 0 for SYN/ACK then 52317–52329 in later packets. These headers **do not identify** a particular Lua strategy, prove unmodified TLS ClientHello, prove genuine WAN peer/origin, or justify Exclude IPSet Apply.

**Specific lead, NOT a demonstrated dvtws2 modification:** The server's first cumulative `ack 163` includes `sack 1 {0:1}`. In relative-number display that SACK block is **below the cumulative ACK**, consistent with the *D-SACK* duplicate-data signal defined by [RFC 2883](https://www.rfc-editor.org/rfc/rfc2883). The one-packet apparent duplicate indication is not contradicted by the lack of repeated **outbound data segments in this single capture**: capture visibility, downstream processing, and TCP display interpretation are distinct. Do **not** infer packet injection, a fake 1-byte payload, a particular strategy, SNI verification, or global Exclude effect from this alone. The next safe discriminator is a read-only `tcpdump -S` **absolute TCP sequence/SACK** inspection of the **existing same-hash PCAP**, followed by analysis of the actual eligible installed strategy where independently available; no capture, DNS/HTTPS, GUI Apply, service restart or IPFW/Config edits have been authorized. Stage 5 A07/A08 remain `OPEN`.

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
