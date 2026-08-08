# Strategy Lab profile output contract

## Purpose

Define the user-ready Traffic Strategy profile emitted by Strategy Lab and the proof required before it may appear in the final shortlist.

Search-policy authority:
`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md` and
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`. The current `_27` implementation
still enforces fixed `-d10`/QUIC compatibility behavior until the planned source patches
replace it; the rules below define the approved target output contract.

## User-ready profile

A shortlist item contains both:

- `strategy`: the catalog fragment retained as internal engineering evidence and for current circular-test compatibility;
- `profile`: the complete self-contained configuration intended for copying into the Traffic Strategy field.

Protocol-specific headers are:

- TLS 1.3 and TLS 1.2: `--filter-tcp=443` and `--filter-l7=tls`;
- HTTP: `--filter-tcp=80` and `--filter-l7=http`;
- generic configured UDP: `--filter-udp=<port>` without an L7 filter.

QUIC candidate profiles are not part of the adaptive-search target. The fixed IPv4
UDP/443 QUIC precheck remains diagnostic evidence only.

Every profile also contains one static target selector and the exact tested native
Zapret2 candidate lines. `--out-range` is emitted only when the tested `CandidateSpec`
contains it and must preserve that exact value; `-d10` has no privileged status.

External-BLOB declarations are emitted only when the candidate requires the installed
resource. BLOB-free, built-in and inline-pattern candidates do not acquire a synthetic
external BLOB declaration merely for output uniformity.

Static selectors are:

- domain TLS/HTTP: `--hostlist-domains=<domain>`;
- IPv4 target: `--ipset-ip=<address>`;
- generic UDP domain target: `--ipset-ip=<comma-separated replay-verified selected IPv4 addresses>`.

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

The displayed profile is the replay source. The replay adapter may translate the approved domain selector to the temporary Strategy Lab hostlist required by the isolated runtime. Generic UDP keeps its static IP set. Every other profile line is passed unchanged.

Each source candidate selected for stability is replayed up to three times using:

- a fresh temporary protocol-specific candidate runtime;
- sequential endpoint probes;
- the endpoint-binding and IPFW interception evidence contract;
- the exact profile text stored in the shortlist item.

A candidate satisfies the strict stability gate only when all three attempts report
`all_pass=true`, `profile_exact=true`, and successful endpoint/interception evidence. The
replay is fail-fast: after a failed attempt, 3/3 is impossible and remaining stability
attempts are not spent on that candidate.

The normal best two to three finalists additionally receive cold isolated deep
validation with a real bounded GET. The deep record stores actual body bytes and whether
the 16-KiB target was reached. When the selected resource completes successfully but is
shorter than 16 KiB, the byte-depth criterion is `inconclusive`, not a fabricated PASS;
separate connectivity/stability evidence remains intact.

The shortlist item records target, target type, protocol, transport, port, optional L7
selector, pinned search-epoch addresses, normalized candidate/resource identity, complete
profile, attempt results, pass count, deep-validation evidence for finalists, and
`profile_replay.verified`.
