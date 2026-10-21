# Owner Extended mask-h2 report — verified HTTP80 only

**Date:** 22 October 2026. **Source:** owner screenshot, Strategy Lab job `job.4YSRMq`. Package revision was not printed; it must not be inferred. This is separate from the earlier owner's read-only `quic.json` evidence for the same host.

- Target `mask-h2.icloud.com`, Extended mode, QUIC enabled; generic UDP port 443 with 114-byte payload.
- Job completed, overall SUCCESS, and Stage90 explicitly reported restored original Zapret2 service and rules.
- Stage80 QUIC: **four tested** (`quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`), **no working strategy**.
- Stage80 generic UDP/443: a **direct control reply was observed**, then **three strategy candidates tested** (`udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`), **no working strategy**. The direct response is not a desynchronization profile, and packet tests are not a verified bypass strategy.
- Stage85: **one** final verified profile, `protocol=http`, TCP port **80**, family `multisplit`, destination `17.250.83.196`, `1/1` replay and copyable `--filter-tcp=80` + `--filter-l7=http` + `--hostlist-domains=mask-h2.icloud.com` + `--out-range=-d10` + `--payload=http_req` + `--lua-desync=multisplit:pos=host`.
- No verified TLS/TCP443, QUIC/UDP443 or generic UDP443 bypass profile was displayed. Apple documents this specific hostname as the TCP443 fallback for iCloud Private Relay ([official endpoint table](https://support.apple.com/en-ie/101555)). The HTTP/TCP80 result **does not demonstrate access to the actual Private Relay service on TCP443**.
- The UI's `SUCCESS` refers to having at least one protocol-specific verified profile and successful job completion/restoration, **not** proof of whole-service availability. That is correct shortlist filtering, but previously insufficiently explicit GUI wording.

**Change scope:** v0.5.6_11 proposes an informational RU/EN scope sentence beneath the final summary, counting only verified shortlisted profiles. Backend candidacy, final replay, packet filter, and restoration are unchanged; no failed candidate is promoted into a profile. Owner-live verification of the new GUI has not yet occurred.
