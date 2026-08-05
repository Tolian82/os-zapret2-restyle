# 2026-08-05 — Strategy Lab endpoint and interception evidence

Patch candidate: `v0.3.2_33`.

Each candidate endpoint now receives one deterministic IPv4 binding. The same address is used to install the temporary IPFW rule and to perform the TCP, TLS 1.3, TLS 1.2, HTTP, QUIC, or configured UDP request. Domain requests preserve the original hostname for SNI, Host, and certificate verification while connecting to the selected address.

Candidate probes run sequentially so a shared deduplicated rule has an isolated counter interval. Every endpoint result records the selected address, observed remote address, assigned rule number, packet and byte counters before and after the request, endpoint-match state, and interception state. PASS requires request success, exact endpoint match, and packet-counter growth. Bound HTTP requests do not follow redirects.

Verification is supplied by `scripts/test-strategy-lab-interception-evidence.sh` and is wired into the mandatory domain-diagnostics suite. Patch `_34` remains blocked until GitHub validation and the FreeBSD package build for `_33` complete successfully.
