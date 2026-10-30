# Stage 5 — real upstream TLS fake packet/Exclude native attribution

**Scope (30 October 2026):** new source/CI-only experiment using pinned upstream Zapret2 `v1.0.6`, disposable **FreeBSD 15.1** VM, authentic OpenSSL TLS 1.2 ClientHello, `lo0` and test-owned IPFW divert. This is **NOT** the installed gateway's actual fake/split strategy, an approved WAN capture, A07/A08 PASS, or a published `v0.6.1_18` package. Only run from the existing guarded VM CI. All packets are local.

## Observable test

The [native test](../../scripts/test-freebsd15-native-tls-fake.py) uses the real production `global_exclusions.compose()/audit()` and six-list IPSET semantic compiler, the original native FreeBSD guest-only gate, and existing strict DLT_NULL/DLT_LOOP TCP PCAP parser. It uses a real upstream profile `--filter-l7=tls --payload=tls_client_hello --lua-desync=fake:blob=stage5_wire_fake:badsum` with a unique fixed hexadecimal blob and an unrelated out-of-profile control. The fake uses bad TCP checksum; its bytes must be seen in a bounded **native** outgoing PCAP and must *not* alter the independently received original TLS ClientHello.

For each family (`127.0.0.1` and `::1`), the same test captures exactly attributed TCP flows for one un-diverted baseline, one divert-owned active stream and one bypass-port control. A native source-port/target-port+payload witness attributes the unique fake only to the intended active flow; no fake may appear on the baseline or bypass. Real IPFW rule owner, native process, rule counter, BPF capture readiness, bounded cleanup and default-allow restoration are mandatory.

| Phase | Global Exclude | Native captured fake on active flow |
|---|---|---|
| A | Empty | Must appear |
| N | Nonmatching `192.0.2.1/32` and `2001:db8::1/128` | Must still appear |
| B | Matching `127.0.0.1/32` and `::1/128` | Must not appear |

A forged blob observed on an unrelated TCP source port, an absent fake when allowed, a fake during the matched Exclude phase, missing genuine ClientHello, incomplete PCAP, changed native IPFW ownership or unclean cleanup are **failures**, not partial success.

## Evidence and acceptance boundary

**Local preflight:** Python syntax plus negative/positive packet-attribution assertions can be tested off-target; synthetic PCAP frames never prove native behavior. Native qualification requires the **exact** `NATIVE_TLS_FAKE_PACKET=PASS` marker from a successfully completed FreeBSD15.1 job on the exact PR head. A failed/skipped native run is not success; retain and investigate its logs before any correction.

The technique proves only the selected **test fake strategy** can inject an independently recognizable outgoing packet and that global Exclude suppresses it on this isolated VM. It does not prove the user's actual current fake/split Lua configuration, production WAN packet origin or installed A07/A08. The next useful gate is to identify the user's actual effective configured profile using approved read-only evidence, and only then design a bounded owner-reviewed installed Phase A. No user shell requests, WAN captures or GUI Apply are authorized here. Python interpreter unification remains cancelled for the current TЗ.
