# 2026-10-19 — A3a native Voice STUN outbound packet proof

**Proof status:** OWNER-LIVE, installed `os-zapret2-restyle-0.5.5_1`. **STUN_MATCH / FAKE_TX / ORIGINAL_TX passed for one generated packet. STUN_RX, MEDIA_PASS and CALL_PASS not established.**

## Controlled isolation of native profile 1

Earlier A2 isolated ordinary Strategy profile 4: UDP `596–599`, non-STUN `unknown`, zero16 fake twice. The installed merged configuration also has the **native Voice** profile 1: IPv4, Telegram managed IPSET, UDP all, `--filter-l7=stun --payload=stun`, `fake:blob=0x00000000000000000000000000000000:repeats=2`.

The A3a single-packet trial deliberately chose destination `91.108.13.10:3478`, in the Telegram Voice IPSET and outside the ordinary Strategy profile 4 UDP `596–599` capture selector. This address/port was **not known to offer a STUN responder**. TNAS `tgvoice-lab` with host networking bound the UDP socket explicitly to `192.168.1.100:54299` and sent one RFC 8489-valid 20-byte Binding Request (type `0x0001`, body length 0, magic cookie `0x2112A442`, random 12-byte transaction ID). The exact owner-console request was `000100002112a4424c1eca057a24a74c8b0e0894`.

One passive OPNsense WAN `vtnet1` capture was saved locally at `/tmp/tgvoice-a3a.f9EsiU/wan.pcap`. The owner-provided `tcpdump -nn -tttt -vv -XX` output at local 2026-10-19 16:50:03 shows **exactly three outbound datagrams**, source translated to `192.168.80.251:2911`, destination `91.108.13.10:3478`, in order:

| Order | UDP data bytes | Hex and WAN properties |
|---|---:|---|
| 1 | 16 | All zero, `udp sum ok`, IPv4 TTL 63 |
| 2 | 16 | All zero, `udp sum ok`, IPv4 TTL 63 |
| 3 | 20 | Exact STUN request bytes preserved, `udp sum ok`, IPv4 TTL 63 |

Host UDP socket received **no reply within two seconds**; the WAN capture output showed no inbound packet. `SSH_EXIT=0` confirmed only successful completion of the remote script.

The single candidate profile matching both STUN and destination/port is native Voice profile 1, not ordinary profile 4; combined with two expected zero16 fake packets this is **specific evidence of active native outbound STUN desynchronization**. No profile, source or network settings were edited.

## Interpretation and next action

A3a closes **native Voice STUN outgoing transmission and its two fake packets** for the controlled request. Lack of reply from a **non-validated STUN responder** is not a failure of that output and does not locate loss beyond the WAN.

The real Telegram reflector `91.108.13.10:596` uses a non-STUN 40-byte Hello covered by **ordinary Strategy profile 4**, not Voice STUN profile 1; A2 showed its unchanged 40-byte originals and 120 zero16 fakes on WAN, with zero remote answers. Therefore no additional native plugin source change is presently supported by packet evidence.

**One next productive operation:** a bounded read-only ICMP hop-limit traceroute through the same OPNsense WAN toward the actual reflector address to inform the already documented **untested** limited-fake-TTL hypothesis for ordinary Strategy profile 4. Such a trace does **not** identify DPI position; any selected test TTL is explicitly speculative until wire-qualified. After recording an exact profile snapshot and revert path, test **one** fake-TTL value in a fresh controlled reflector run while keeping the original 40-byte datagram TTL unchanged. Do not run the deprecated PoC runner or repeat completed A0/A1/A2/A3a gates. A known valid STUN responder is needed separately to qualify STUN_RX; do not infer one from Telegram IP `91.108.13.10:3478`.
