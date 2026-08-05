# Strategy Lab profile output contract

## Purpose

Define the user-ready Traffic Strategy profile emitted by Strategy Lab and the proof required before it may appear in the final shortlist.

## User-ready profile

A shortlist item contains both:

- `strategy`: the catalog fragment retained as internal engineering evidence and for current circular-test compatibility;
- `profile`: the complete self-contained configuration intended for copying into the Traffic Strategy field.

Protocol-specific headers are:

- TLS 1.3 and TLS 1.2: `--filter-tcp=443` and `--filter-l7=tls`;
- HTTP: `--filter-tcp=80` and `--filter-l7=http`;
- QUIC: `--filter-udp=443` and `--filter-l7=quic`;
- generic configured UDP: `--filter-udp=<port>` without an L7 filter.

Every profile also contains one static target selector, `--out-range=-d10`, and the exact tested catalog desynchronization lines.

Static selectors are:

- domain TLS/HTTP/QUIC: `--hostlist-domains=<domain>`;
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
- catalog attempts to replace the generated protocol filters or output range.

## Exact replay

The displayed profile is the replay source. The replay adapter may translate the approved domain selector to the temporary Strategy Lab hostlist required by the isolated runtime. Generic UDP keeps its static IP set. Every other profile line is passed unchanged.

Each source candidate is replayed three times using:

- a fresh temporary protocol-specific candidate runtime;
- sequential endpoint probes;
- the endpoint-binding and IPFW interception evidence contract;
- the exact profile text stored in the shortlist item.

A candidate is publishable only when all three attempts report `all_pass=true`, `profile_exact=true`, and successful endpoint/interception evidence.

The shortlist item records target, target type, protocol, transport, port, optional L7 selector, resolved addresses, complete profile, attempt results, pass count, and `profile_replay.verified`.
