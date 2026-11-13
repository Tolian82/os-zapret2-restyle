# Strategy Lab — unified shortlist contract

**Status:** CURRENT. The accepted browser reachability and dual-stack specifications supersede former client/family assumptions. Current results carry only the evidence actually measured.

## Production ownership

Stage 85 is the publication gate. The packaged Python entrypoint installs IPv4/Host-SNI and truthful-result behavior, then dispatches result operations through:

`compat._run_result -> adaptive_result_compat.run_result -> adaptive_validation.run_result/build_shortlist`.

`result.py` supplies protocol contracts, source collection and full-profile construction. Its older standalone three-replay implementation is not the normal adaptive publication path.

## Source selection and ordering

Standard considers stable primary `tls13` candidates in the current source. Extended also collects working Stage-80 `tls12`, `http`, `quic` and configured `udp` sources. QUIC already can contribute a bypass profile; the former statement that it is only a precheck and never published was stale.

Current protocol ranks are:

1. `tls13`;
2. `tls12`;
3. `http`;
4. `quic`;
5. `udp`.

Within a protocol, sorting uses line count, character count and stable candidate ID; duplicate protocol/port/strategy combinations are removed. The normal configured limit is three. Standard selects up to that limit; Extended selects the best source per protocol and applies the same overall limit. Thus a lower-ranked protocol may remain in its stage result without entering the top three. The first verified selected item is the recommendation.

The legacy `tls13` identifier is not proof of the negotiated TLS version. The current private-Chrome primary branch uses natural negotiation and reports the measured protocol.

## Stability and exact replay

Primary candidates already passed fail-fast 3/3 stability in Stage 70. The production adaptive Stage-85 path performs **one cold deep replay** per admitted finalist using the complete user-ready profile, pinned endpoint epoch and existing candidate lifecycle. It records `attempt_count=1` and a separate deep-validation outcome. It does not rerun three deep transfers for every finalist.

A source/replay from another epoch, a changed profile, failed endpoint or missing required interception cannot produce a verified recommendation. Web body/depth observations are diagnostic under BH-08. They do not add a mandatory size gate to otherwise valid reachability evidence. The installed `truthful_result_support` preserves authenticated/intercepted HTTP 4xx/5xx semantics.

**QUIC evidence boundary:** Use the current [private-Chrome/QUIC contract](STRATEGY_LAB_BROWSER_HTTP.md) and its requested transport, identity, attempts and replay evidence. An old saved handshake/candidate result is not retroactively a measured HTTP/3 response or a new 3/3 sequence. Historical pre-migration limitations remain in the [source snapshot](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md).

## Circular boundary

Published recommendations and private circular candidates are separate arrays. The adaptive publisher first places deeply verified primary candidates in `circular_items`; `adaptive_result_compat._backfill_circular` may add stable primary candidates up to the configured limit with `finalist_validation=stability_only_pending_circular`.

That private pending-circular marker is not a deeply verified public recommendation. Existing circular eligibility, lifecycle lock, stop and restoration remain authoritative; the browser migration must preserve that distinction. Extended TLS1.2, HTTP, QUIC and generic UDP are not added to the primary circular runtime by this work.

## Generic UDP and fixed-address profiles

Generic UDP retains its configured destination port and exact payload. For domain input it uses recorded selected IPv4 addresses as `--ipset-ip=` because this transport has no domain-layer selector. Fixed-IPv4 recommendations retain the entered destination selector. Exact profile replay remains tied to the original endpoint epoch and verified interception.

References: [adaptive search](STRATEGY_LAB_ADAPTIVE_SEARCH.md), [Model C](STRATEGY_LAB_MODEL_C.md), [target/result requirements](../REQUIREMENTS.md), [current entrypoint](../../src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_result_compat.py), [adaptive publisher](../../src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/adaptive_validation.py).
