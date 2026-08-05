# Strategy Lab profile output contract

## Purpose

Define the user-ready Traffic Strategy profile emitted by Strategy Lab and the proof required before it may appear in the final shortlist.

## User-ready profile

A shortlist item contains both:

- `strategy`: the catalog fragment retained as internal engineering evidence and for current circular-test compatibility;
- `profile`: the complete self-contained configuration intended for copying into the Traffic Strategy field.

For the current TLS 1.3 candidate family, the complete profile contains:

- `--filter-tcp=443`;
- `--filter-l7=tls`;
- one static target selector;
- `--out-range=-d10`;
- the exact tested catalog desynchronization lines.

Static selectors are:

- domain: `--hostlist-domains=<domain>`;
- IPv4 address: `--ipset-ip=<address>`.

The profile must contain exactly one static selector.

## Excluded arguments

Process and runtime-global arguments are not part of Traffic Strategy output. At minimum the profile rejects:

- `--port`;
- `--lua-init`;
- daemon, PID, socket, user, UID, and GID arguments;
- dynamic runtime `--hostlist` and `--ipset` paths;
- project placeholders such as `<HOSTLIST:name>` and `<IPSET:name>`;
- nested `--new` separators.

## Exact replay

The displayed profile is the replay source. The replay adapter may resolve the approved static selector to the temporary Strategy Lab hostlist required by the isolated candidate runtime, but every other profile line is passed unchanged.

Each shortlist candidate is replayed three times using:

- a fresh temporary candidate runtime;
- sequential endpoint probes;
- the endpoint-binding and IPFW interception evidence contract;
- the exact profile text stored in the shortlist item.

A candidate is publishable only when all three attempts report:

- `all_pass=true`;
- `profile_exact=true`;
- successful endpoint and interception evidence.

The shortlist item records target, target type, protocol, port, resolved addresses, complete profile, attempt results, pass count, and the final `profile_replay.verified` decision.
