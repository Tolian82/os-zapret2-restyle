# Owner QUIC job — mask-h2.icloud.com (TCP fallback, invalid QUIC target)

**Date evidence received:** 22 October 2026 (owner read-only `quic.json` extract from the Strategy Lab OPNsense job). **Exact installed package revision:** not included in this extract; do not infer from the repository or previous package publication. **Testing application:** `mask-h2.icloud.com`, pinned epoch address `17.250.80.226`, Extended mode with QUIC enabled. Stage90 successful restoration is reported separately by the owner's prior screenshot. No package, network, service or running firewall configuration was changed to obtain these diagnostics.

## Owner-provided exact execution observations

| Execution | Return code | Error | Positive QUIC handshake / final HTTP3 | Rule 19100 counter increase |
|---|---:|---|---|---|
| Direct target | `7` | Failed to connect after 57 ms | No; observed remote IP empty, `time_appconnect=0` | Not a candidate |
| `quic-fake-1` | `7` | Failed to connect after 230 ms | No | 3 packets, 3684 bytes |
| `quic-fake-2` | `7` | Failed to connect after 235 ms | No | 3 packets, 3684 bytes |
| `quic-ipfrag-8` | `28` | Timed out after 2006 ms | No | 4 packets, 4912 bytes |
| `quic-ipfrag-16` | `28` | Timed out after 2028 ms | No | 4 packets, 4912 bytes |

All four candidates reported `intercepted=true`, `packets_before=0`; none passed the first attempt (`pass_count=0`, `attempts_executed=1`, `stable=false`). Top-level `status=not_found`, `reason=null`. All evidence objects show `quic_verified=false`, `http3_response=false`, `http_version=null`, `http_status=null`, `remote_ip=""`, `ssl_verify_result=1` and `time_appconnect=0`. A nonzero `ssl_verify_result` **without an established TLS/QUIC handshake** is not, by itself, a demonstrated invalid server certificate. Code 7 means failure to establish connection; code 28 means elapsed connection timeout. Both are distinct from unsupported-client curl exit 4 addressed by source `v0.5.6_10` and from the independently proven HTTP/3 client capability in prior owner Stage1 testing.

IPFW packet/byte increments prove that the outgoing test packets reached the local divert rule. They do **not** prove that the remote endpoint responded, that QUIC TLS completed, or that censorship/DPI blocked a valid QUIC service.

## Independent target protocol verification

Apple's official [Use Apple products on enterprise networks](https://support.apple.com/en-ie/101555) table lists:
- `mask.icloud.com` — **UDP/443**, iCloud Private Relay.
- `mask-h2.icloud.com` — **TCP/443**, iCloud Private Relay TCP fallback.
- `mask-api.icloud.com` — **TCP/443**.

This distinction is independently explained in [APNIC's investigation of Apple Private Relay](https://blog.apnic.net/2023/01/25/an-investigation-into-apples-new-relay-network/) (QUIC primary host vs TLS-over-TCP fallback host). The selected target `mask-h2.icloud.com` is not a documented QUIC service target; one must **not** infer QUIC bypass failure or provider UDP blocking from its inability to complete an HTTP/3-only probe. Nor can the log establish a missing-HTTP/3 binary error: neither exit 4 nor the unsupported-option stderr was present.

The owner's prior GUI confirmed successful selection/replay of an **HTTP/TCP80** candidate and Stage90 service restoration; that is a Strategy Lab application-response observation, **not** proof that the full Apple Private Relay protocol works using that candidate.

## Conclusion and next acceptance gate

**Classification:** `not_found` on the QUIC branch is consistent with probing the wrong hostname for UDP/443. The current evidence does **not** justify a new desynchronization family, another fake/fragmentation variant, modifications to IPFW, or a forced version bump. Preserve the unchanged source identity `v0.5.6_10` (CI PASS; unpublished); published testing package `v0.5.6_9` remains available.

If owner-live QUIC verification is still needed, use the correct Apple UDP target **`mask.icloud.com`**, with DNS-resolved/pinned epoch address for that distinct hostname, or a separately known real HTTP/3 host. Do not reuse `17.250.80.226` from the TCP fallback for this test without independently validating its new DNS target. Apply the approved target QUIC-only CA/remote-IP evidence, direct baseline, IPFW UDP/443 attribution, 3/3 stability, exact Stage85 replay and Stage90 restoration. The Apple Private Relay service might impose additional application-level requirements beyond a generic HTTP/3 GET; do not claim the service itself works based only on a QUIC handshake.
