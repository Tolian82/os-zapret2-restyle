# Strategy Lab profile output contract

## Purpose

Define the user-ready Traffic Strategy profile emitted by Strategy Lab and the proof required before it may appear in the final shortlist.

Search policy follows [adaptive search](STRATEGY_LAB_ADAPTIVE_SEARCH.md); browser/QUIC and address-family behavior follow their current accepted contracts. Per-revision `_31` transition notes remain historical.

## User-ready profile

A shortlist item contains both:

- `strategy`: the catalog fragment retained as internal engineering evidence and for current circular-test compatibility;
- `profile`: the complete self-contained configuration intended for copying into the Traffic Strategy field.

Protocol-specific headers are:

- TLS 1.3 and TLS 1.2: `--filter-tcp=443` and `--filter-l7=tls`;
- HTTP: `--filter-tcp=80` and `--filter-l7=http`;
- generic configured UDP: `--filter-udp=<port>` without an L7 filter.

Explicitly enabled QUIC candidate/replay behavior follows the [QUIC control](STRATEGY_LAB_QUIC_CONTROL.md) and [browser probe](STRATEGY_LAB_BROWSER_HTTP.md) contracts. Do not infer a candidate or call result from a diagnostic precheck.

Every profile also contains one static target selector and the exact tested native
Zapret2 candidate lines. `--out-range` is emitted only when the tested `CandidateSpec`
contains it and must preserve that exact value; `-d10` has no privileged status.

External-BLOB declarations are emitted only when the candidate requires the installed
resource. BLOB-free, built-in and inline-pattern candidates do not acquire a synthetic
external BLOB declaration merely for output uniformity.

Static selectors are:

- domain TLS/HTTP: `--hostlist-domains=<domain>`;
- literal IP target: `--ipset-ip=<address>` under current family eligibility;
- generic UDP domain target: `--ipset-ip=<comma-separated replay-verified selected IP addresses under current family eligibility>`.

The profile must contain exactly one static selector.

## Excluded arguments

Process and runtime-global arguments are not part of Traffic Strategy output. At minimum the profile rejects:

- `--port`;
- `--lua-init`;
- daemon, PID, socket, user, UID, and GID arguments;
- dynamic runtime `--hostlist` and `--ipset` paths;
- project placeholders such as `<HOSTLIST:name>` and `<IPSET:name>`;
- nested `--new` separators;
- candidate attempts to replace the generated protocol filters.

## Exact replay

The displayed profile is the replay source. Python translates the approved domain
selector to the temporary Strategy Lab hostlist required by the isolated runtime and
renders every other profile line unchanged. Generic UDP keeps its static IP set. The
shell replay adapter receives the resulting exact arguments and performs only system
actions.

Each source candidate selected for stability is replayed up to three times using:

- a fresh temporary protocol-specific candidate runtime;
- sequential endpoint probes;
- the endpoint-binding and IPFW interception evidence contract;
- the exact profile text stored in the shortlist item.

A candidate satisfies the strict stability gate only when all three attempts report
`all_pass=true`, `profile_exact=true`, and successful endpoint/interception evidence. The
replay is fail-fast: after a failed attempt, 3/3 is impossible and remaining stability
attempts are not spent on that candidate.

Finalists receive the applicable exact-profile bounded replay. Body-byte/depth observations are diagnostic under BH-08; a valid shorter response does not introduce a separate reachability failure gate. The [browser contract](STRATEGY_LAB_BROWSER_HTTP.md) owns current transport-specific evidence.

The shortlist item records target, target type, protocol, transport, port, optional L7
selector, pinned search-epoch addresses, normalized candidate/resource identity, complete
profile, attempt results, pass count, deep-validation evidence for finalists, and
`profile_replay.verified`.

## Source history

The [full original page](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md) preserves earlier source versions, investigation notes and acceptance claims at their actual dates. [PROJECT_STATE](../PROJECT_STATE.md) owns current evidence; this page owns its bounded technical contract.
