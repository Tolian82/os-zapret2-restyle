# Owner evidence: false SUCCESS in top-level domain HTTPS shortcut

**Date:** 22 October 2026. Four owner GUI screenshots and CLI output; the screenshots do not identify the service listening at 192.168.1.2 and do not independently establish proxy/interception mechanism.

**Observed:** Facebook DNS 157.240.205.35, HTTPS HTTP200, remote 192.168.1.2, TLS verify 20, Result SUCCESS. Meta DNS 157.240.205.1, HTTP200, remote 192.168.1.2, TLS verify 20, SUCCESS. Telegram DNS 149.154.167.99, HTTP200, remote 192.168.1.2, TLS verify 19, SUCCESS. Instagram DNS 157.240.205.174, HTTP200, remote 192.168.1.2, TLS verify 20, SUCCESS.

**Independent owner shell:** direct curl to meta.com/telegram.org was interrupted after hanging. Instagram curl -v attempted IPv6 (no route) then public IPv4 157.240.205.174 and hung before completion. These CLI invocations and GUI tests are not identical commands and are supporting observations, not proof of matching routes.

**Source-backed root cause:** legacy `src/opnsense/scripts/OPNsense/Zapret/test_domain.sh` used plain `curl -4 -sk` and assigned `=== Result: SUCCESS ===` on curl exit 0; `-k` skipped certificate verification and neither remote IP nor certificate result was checked. `192.168.1.2` is the user's OPNsense LAN address, **not the public DNS address**. TLS Verify 19/20 is nonzero and not a validated CA chain. Which local service supplied 200 is not proven.

**Source candidate `_12`:** pin DNS A answer with `--resolve`, use private Chrome profile and system-trusted CA with no proxy, verify exit 0, actual remote IP matching selected DNS IP, nonzero TLS handshake, certificate result 0 and genuine HTTP 2xx-5xx final response. No fallback to insecure curl. API transport status `ok` is report delivery only. Stage50 PASS in Strategy Lab is screening-stage completion; no TLS families found is a legitimate negative. Runtime and Stage90 unchanged.

**Status:** owner root-cause evidence proven; `_12` code change requires CI and owner installation before calling fixed installed output PASS. No installable `_12` package yet.