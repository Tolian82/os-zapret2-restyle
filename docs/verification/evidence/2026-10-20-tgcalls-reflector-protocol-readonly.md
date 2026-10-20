# 2026-10-20 — pinned Telegram reflector protocol and responder discovery (read-only source audit)

**Proof level:** inspected repository source at **`TelegramMessenger/tgcalls@efd330ca04f74706024a5abdfb5b41f4e4dd1065`**, which the project's TNAS testbench records as the pinned tgcalls engine. This is source verification only, **not** a new OPNsense/live network experiment.

## Pinned source facts

- [`tools/cli/main.cpp`](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tools/cli/main.cpp): CLI accepts `--reflector HOST:PORT` and `--reflector-list IP1,IP2,...`; the list mode picks one address randomly and, if no port is encoded, a random port 596–599. `makeReflectorServer` configures `login="reflector"`, `isTurn=true`, `isTcp=false`, and a hex-encoded 16-byte peer tag. Caller and Callee receive separate first-byte role markers 0 and 1.
- [`tgcalls/v2/ReflectorPort.cpp`](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tgcalls/v2/ReflectorPort.cpp): `SendReflectorHello()` sends a **40-byte non-STUN** UDP message: 16-byte tag, 12 × FF, FE + 3 × FF, and 64-bit integer 123. While connecting it resends after 500 ms.
- `ReflectorPort::HandleIncomingPacket()`: packet must originate from the exact configured `server_address_.address` (`IP:port`), be at least 16 bytes, and match the first **12** bytes of the port's peer tag. On a matching packet, it changes state to `STATE_READY` and adds a relay candidate; media establishment is separate. Incorrect source, too-short payload, tag mismatch, or disconnected state is rejected. The source does not by itself prove any current server will reply.
- [`tools/cli/run-test.sh`](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tools/cli/run-test.sh): its routine production test path fetches `https://core.telegram.org/getReflectorList`, strips per-line ports to a unique IP list and passes those IPs through `--reflector-list` for random selection, with port 596–599 selected by the CLI.

## Current endpoint decision

- Our previous lab is **fixed** at historical `91.108.13.10:596`, so no current official-list membership or reply eligibility was proven merely by the historical CLI input or WAN capture.
- This assistant environment could not fetch the Telegram endpoint (web source unavailable, direct container DNS unavailable). **No current list contents are claimed.** Even list membership would not alone prove the UDP server is responsive through OPNsense or that DPI caused a loss.
- Previously observed `120 fake TTL7 + 60 real TTL63` and zero return packets remain valid [wire evidence](2026-10-20-telegram-ttl7-wan-owner-live.md); do not reinterpret `NO_REPLY` as proof of DPI placement or TTL efficacy.

## One next authorized observation (no network-media experiment)

At the owner's OPNsense root shell, fetch the published reflector-list resource once over HTTPS to a temporary file with a bounded timeout, validate it contains parsable IPv4 entries, and report count, membership of `91.108.13.10`, and a small set of sample addresses/ports. This changes no Zapret2 config, routing or firewall rule and sends **no UDP/596 test traffic**. If HTTPS fetch fails or format is invalid, report the exact error instead of guessing or opening a new TTL/fragment sweep.

After interpreting the real list, choose **one** specific newly qualified control/endpoint and acceptance observations before any further packet generation; native Voice STUN profile stays unchanged.
