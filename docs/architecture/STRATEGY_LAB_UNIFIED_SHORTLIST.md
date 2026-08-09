# Strategy Lab unified shortlist contract

## Scope

Stage 85 is the single final publication gate for verified Strategy Lab profiles.
Migration Patch 7 makes `strategy_lab_py/result.py` the authoritative automated Stage-85
publisher.

The 2026-08-08 adaptive-search decision amends search selection without changing Python
ownership. The current `_29` source still contains the original QUIC/five-item-compatible
logic; `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` defines the approved target.

Standard mode considers stable TLS 1.3 candidates. Extended mode additionally considers
confirmed working candidates, when present, from TLS 1.2, HTTP and configured generic UDP
results produced by Stage 80. QUIC remains only the fixed IPv4 UDP/443 precheck in the
adaptive target and does not publish a bypass profile.

## Deterministic selection

All source candidates receive these ranks:

1. TLS 1.3;
2. TLS 1.2;
3. HTTP;
4. configured UDP.

Within a protocol, candidates are ordered by profile line count, character count, and
stable candidate ID. Duplicate protocol/port/strategy combinations are removed.

After exact replay verification:

- Standard adaptive search normally stops after two to three strong TLS 1.3 profiles;
- Extended mode may add the best verified requested non-QUIC protocol profiles without
  forcing the primary search to fill an arbitrary five-item quota;
- the first item is the recommendation, so a verified TLS 1.3 result remains preferred when available.

Every source is replayed exactly three times using the complete user-ready profile through
the same Python candidate lifecycle/readiness/interception owner used by search stages.
Only 3/3 exact-profile PASS results are publishable.

## Circular boundary

Circular validation is not generalized by Patch 7. The Python-published shortlist stores a
separate `circular_items` array and `circular_count` containing only the best three-to-five
replay-verified TLS 1.3 candidates. Legacy shortlist files without these fields remain
readable as TLS 1.3-only historical results.

Extended TLS 1.2, HTTP, and UDP profiles are never injected into the current TLS
circular runtime. Private circular session state remains shell-owned and must not mutate
the parent automated shortlist.

The current circular eligibility/count contract is deliberately separate from the new
two-to-three primary-search early-stop rule. Circular must not cause adaptive discovery to
manufacture extra winners merely to satisfy its existing three-to-five input shape.

## UDP boundary

A generic UDP domain profile has no domain-layer selector. Its user-ready profile therefore
uses replay evidence selected IPv4 addresses as `--ipset-ip=` and the validated configured
UDP port. Generic UDP input is already supplied by the approved GUI/API job-local
port/payload contract; Patch 7 consumes that persisted evidence but does not change the
input surface.

A fresh final replay must still send the configured payload to the selected endpoint and
prove exact endpoint identity plus IPFW interception before the UDP profile can enter the
shortlist.
