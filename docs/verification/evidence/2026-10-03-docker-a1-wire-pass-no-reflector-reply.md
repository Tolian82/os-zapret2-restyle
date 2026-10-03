# 2026-10-03 — first real Docker A1 experiment: 120 bad-checksum fakes precede 60 valid Reflector Hellos, no response

**Status:** OWNER-LIVE FIXED-ORACLE RUN · **A1 `WIRE_OK / NO_REPLY_UNKNOWN`** · **`MEDIA_PASS` NOT REACHED**. **First actual**, as opposed to the three earlier **preflight-only** attempts. No new real human Telegram call.

## Archive identity, fixed epoch and tested state

Owner uploaded private `a1-20261003T082936Z-2UPyka.tgz` (downloaded file may carry `(1)` suffix); **8,044 bytes**, SHA-256 **`d0a56ee85442986a8155cd033fb14118ead68caa60ed7efd55dc9ed647f474cf`**. The one-command OPNsense runner identified itself as `a1-one-command-v3-linux-from-route-compatible`. Exact UTC acquisition: runner **08:29:36**, CLI **08:29:39–08:29:54**; the LAN and WAN full-snaplen Ethernet PCAPs each cover a ~14.51-second packet window. These are private packet captures and traffic config, not for public GitHub. Public documentation preserves only measured summaries and immutable SHA-256 evidence identities.

The **complete preflight passed**: saved ordinary GUI model and all candidate-specific A1 markers YES; effective *one-block* A1 present along with existing separate Telegram STUN-helper profile; Telegram managed IPSET includes pinned destination; Voice `requested/effective=on`, `service=running`, `active_profile=on`, table present with 14 entries; ordinary outgoing IPFW UDP capture includes 596–599. **Crucial rule precedence:** Voice destination-scoped IPFW **19000** increased from **0 packets / 0 bytes** to **60 packets / 4080 IP bytes**. Ordinary port rule **19002** stayed at **0/0** because rule19000 already captured these same Telegram-destination UDP packets; **rule19002 zero is NOT a missing A1 or unprocessed UDP**. TCP rule19001 remained unchanged during this bounded run. Current PFIL IPv4 outbound retained the earlier measured IPFW→PF ordering.

The **original operator-approved** route guard returned `OK` for both TNAS `91.108.13.10/32` and `149.154.167.99/32` via OPNsense `192.168.1.2`. Updated v3 redundant preflight independently received Linux `from 192.168.1.100 via 192.168.1.2 dev ovs_eth1` for both targets; Docker `tgvoice-lab` was **already running**, `network=host`, left running (not started/stopped by runner). Exact pinned `/results/tgcalls_cli` SHA-256 **`7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`**, calling/called engines **13.0.0**.

### Exact tested candidate A1

```text
--filter-l3=ipv4
--filter-udp=596-599
<IPSET:telegram>
--payload=unknown
--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:badsum:repeats=2

--new
```

The pinned Docker `--mode reflector --reflector 91.108.13.10:596 --duration 15` started **both** peers in fresh process and produced its complete call summary:

```text
Duration:          15s
Mode:              reflector (91.108.13.10:596)
Caller state:      Reconnecting
Callee state:      Reconnecting
Call established:  no
BWE non-zero:      no
Errors:            none
tgcalls_exit=1
```

The generic **runner** reported `ACQUIRED_MEDIA_UNVERIFIED`, `script_exit=0` because its **data collection** succeeded; the **actual oracle returned 1**. Do not confuse runner exit success with media success.

## Full LAN versus post-NAT WAN wire analysis

| Property | LAN `vtnet0` | WAN `vtnet1` |
|---|---:|---:|
| Ethernet IPv4 frames captured, pinned-target only | **60** | **180** |
| Genuine unfragmented 40-byte Reflector Hello (IPv4 total 68) | **60** | **60** |
| Additional all-zero **16-byte** fake UDP payloads (IPv4 total 44) | **0** | **120** |
| Inbound UDP from pinned reflector target | **0** | **0** |
| Valid recorded IPv4 header checksums, relevant outbound UDP | **60/60** | **180/180** |
| Valid recorded UDP checksums of *original* 40-byte datagrams | **60/60** | **60/60** |
| Deliberately **invalid** UDP checksums of A1 fakes | — | **120/120** |
| Noninitial IP fragments or MF on captured target traffic | **0** | **0** |

Two distinct host-network source UDP streams are present in the LAN PCAP: **30 originals per peer** over 15 seconds to target UDP/596. On WAN NAT, those source ports become **two different translated ports**, maintaining exactly 30 original packets per peer. **All 60 genuine post-NAT payloads match the complete 60 LAN genuine payloads byte for byte**, with valid WAN UDP checksums; no genuine loss or corruption on the observed OPNsense WAN.

**Exact 60/60 ordering invariant:** each LAN 40-byte Hello produces **on WAN** three consecutive unfragmented IPv4 UDP datagrams on the matching NATed five-tuple: first **16-byte zero fake** with deliberately invalid UDP checksum, second **identical 16-byte zero fake** with deliberately invalid UDP checksum, third **the original genuine valid-checksum 40-byte Hello**. For every triplet all three have **valid recorded IPv4 header checksums** and the same observed IPv4 ID; the capture places fake #1 before the genuine by at most **179.1 microseconds**. These checks were computed from raw Ethernet/IPv4/UDP frames, including post-NAT pseudoheaders. Reusing an IP ID across **unfragmented** datagrams is an observed fact, **not proof of a loss mechanism**; no fragmentation is present.

**No UDP reply from `91.108.13.10` appears on either LAN or WAN** during the fully overlapping, short capture windows. Both tcpdump capture logs show **zero kernel drops** (LAN 60 packets captured; WAN 180). This proves the intended **local WAN transmission pattern** was produced; it does **not** prove which malformed fake packets a remote DPI/parser noticed, that Telegram received them or the genuine packets, or why the remote reflector never replied. The existing owner-established ISP Telegram DPI restriction remains the project's premise; this PCAP cannot uniquely isolate packet discard location or upstream device behavior.

**Private exact artifact subhashes**, for owner-side source matching:

| Private artifact in TGZ | SHA-256 |
|---|---|
| `lan.pcap` | `87c7d4c8c04638c516097c6a778b47644aea5d1570950eed9df4d5381af2afb5` |
| `wan.pcap` | `98ea18717c605d5c7da4f9180e9446b68bfa375084f4d36a8f08b0b3628c7e03` |
| `tgcalls-cli.log` | `00ac5e6b135d08ff4285d2c27c999c3aea941aa2e31ab1a33d5f287fba6e219d` |

## Interpretation and next experiment: change **one variable**, not routes or real callers

A1 conclusively **matched unknown 40-byte reflector traffic**, generated two per-original **bad-UDP-checksum** zero16 fakes, and preserved the real datagram after NAT. Therefore **A1 is not a matching, rule, checksum-correction or local-wire failure**. Its specific fake waveform has **no observed reflector response and no media**, so do **not** repeat unchanged A1 hoping for a different status, increase repeat count without rationale, or go back to already-closed reverse fragment-position sweeps.

**Bounded next candidate for documentation/review, A2 hypothesis only:** keep **all** active matching, original forwarding, fixed Docker target/binary, two-zero16-fake repeats, Voice helper and route/measurement conditions identical, but **omit only `:badsum` from the A1 `fake` expression**, producing an expected checksum-valid zero16 fake (verify on WAN; it is **not yet measured**). This isolates whether the upstream DPI processes/discards *bad-checksum* UDP fakes before the original, while limiting the possibility of interpretation mixing. Note possible endpoint-side consequences if the **valid** short zero16 packets reach Telegram; the experiment is permitted only as a **bounded Docker lab candidate**, not an assertion it should work.

A2 tentative snippet, **not currently applied**:

```text
--filter-l3=ipv4
--filter-udp=596-599
<IPSET:telegram>
--payload=unknown
--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2

--new
```

**Automation dependency:** the existing runner deliberately verifies **exact A1** and would reject A2. **Do not ask the owner to paste A2 yet**. First separately document/implement/CI-qualify a *candidate-aware* single-command runner that preserves all route/SSH/host-network/container safeguards, detects the requested A1/A2 config and records expected fake checksum validity, with no loose “any GUI profile” bypass or separate hidden active dvtws2. Only then, after a confirmed docs-first decision, can the owner switch A1→A2 as **one GUI change** and run **one** automated lab test with one archive. The current A1 archived result remains immutable.

Other possible follow-up families such as calibrated TTL-sensitive fakes require independent source and route measurements; **no TTL value, successful Telegram media result or new server endpoint is inferred from this failed test**. Independent current fixed-target working-path control would help attribution but does not justify asking for human Telegram calls per candidate.

**Current gates:** A1 `CONFIG_PASS` ✓; A1 `WIRE_OK` ✓; A1 `REFLECTOR_READY` **NO observed reply**; `MEDIA_PASS` **OPEN**; real `CALL_PASS` **OPEN**. All code/product integration remains unapproved.
