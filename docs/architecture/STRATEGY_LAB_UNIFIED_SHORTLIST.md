# Strategy Lab unified shortlist contract

## Scope

Stage 85 is the single final publication gate for verified Strategy Lab profiles.

Standard mode considers only stable TLS 1.3 candidates. Extended mode additionally considers the confirmed working candidate, when present, from TLS 1.2, HTTP, QUIC, and configured generic UDP results produced by Stage 80.

## Deterministic selection

All source candidates receive these ranks:

1. TLS 1.3;
2. TLS 1.2;
3. HTTP;
4. QUIC;
5. configured UDP.

Within a protocol, candidates are ordered by profile line count, character count, and stable candidate ID. Duplicate protocol/port/strategy combinations are removed.

After exact replay verification:

- standard mode publishes up to five TLS 1.3 profiles;
- extended mode publishes the best verified profile for each available protocol, up to five items;
- the first item is the recommendation, so a verified TLS 1.3 result remains preferred when available.

## Circular boundary

Circular validation is not generalized by this patch. The shortlist stores a separate `circular_items` array and `circular_count` containing only the best three-to-five replay-verified TLS 1.3 candidates. Legacy shortlist files without these fields remain readable as TLS 1.3-only historical results.

Extended TLS 1.2, HTTP, QUIC, and UDP profiles are never injected into the current TLS circular runtime.

## UDP boundary

A generic UDP domain profile has no domain-layer selector. Its user-ready profile therefore uses the exact selected IPv4 addresses recorded by the successful candidate as `--ipset-ip=`. A fresh replay must still hit and intercept those same addresses.

This patch consumes configured UDP evidence when it already exists. Supplying UDP port and payload through the supported GUI/API request is a separate following change.
