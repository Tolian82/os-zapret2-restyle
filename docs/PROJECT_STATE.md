# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_11.pkg`

Strategy Lab:

- Patches 1–8: complete and merged.
- Patch 8 merged as `50b4ca23197367ca3cc583d6016d99d2f9620d67`; task branch removed.
- Patch 9: extended TLS 1.2 and plain HTTP in delivery.
- Patches 10–13: blocked by the serial gate.

Patch 9 adds protocol-specific TCP/443 TLS 1.2 and TCP/80 HTTP testing in extended mode. Standard mode and the legacy synchronous Blockcheck remain unchanged. `VERSION=0.3.2`; `PLUGIN_REVISION=11`; no release publication is authorized.

Next action: completely process Patch 9 before Patch 10.
