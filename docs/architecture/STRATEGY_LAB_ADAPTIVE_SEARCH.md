# Strategy Lab adaptive native-Zapret2 search architecture

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What is the approved target architecture for Strategy Lab candidate representation,
resource discovery, adaptive native-Zapret2 search, validation and future runtime
acceleration?

Purpose:
Define the post-migration search architecture in enough detail for the `_28`–`_33`
implementation series without promoting unmeasured warm-worker ideas to production
requirements.

Updated when:
Candidate representation, search graph, resource inventory, protocol priority, validation,
runtime execution model or timeout architecture changes.

Read after:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` and
`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`.

Verification companion:
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Do not store here:
Chronological implementation logs, package publication state or raw OPNsense test logs.

==================================================
STATUS AND IMPLEMENTATION BOUNDARY
==================================================

Status:
Approved target architecture; `_28` through `_30` implement the representation,
reachability and native-graph slices while `_31`–`_33` remain pending.

The current `0.4.0_4` source removes the Stage-50 family hard gate, establishes the
candidate/resource boundary and makes the native graph executable while deliberately
keeping later adaptive ordering/telemetry/validation behavior unchanged.
In particular:

- `strategy_lab_py/search_graph.py` validates a deterministic DAG with seven Stage-50
  reconnaissance seeds and sixteen Stage-60 nodes; accepted families affect priority but
  never graph membership;
- both agreed golden strategies are exact graph nodes and remain reachable after empty or
  unrelated Stage-50 evidence;
- `strategy_lab_py/resources.py` records one immutable job-scoped snapshot of every
  installed `*.lua` and fake `*.bin`, the supported built-ins and inline capability;
- `strategy_lab_py/candidate_spec.py` normalizes stable identity, ordered Lua actions,
  filters/ranges/resources/dependencies/provenance/cost and exact runtime rendering;
- static candidates declare only functional `zapret-lib.lua` and `zapret-antidpi.lua`
  startup dependencies; unrelated installed Lua remains inventory evidence rather than
  an automatically loaded candidate dependency;
- active candidate/profile shell adapters receive exact Python-rendered arguments and no
  longer select Lua files, BLOB resources or a fixed range;
- graph planning schedules BLOB-free, built-in and inline nodes independently and skips
  only the external golden node when `fake_tls_7.bin` is unavailable; unrelated installed
  resources do not generate Cartesian candidates;
- each graph node's serialized `CandidateSpec` is verified by the candidate runtime and
  preserved through stability; jobs persist `family-search-graph.json` and
  `search-graph.json` planning evidence;
- graph ranges include `-d8`, `-d10` and absence; `strategy_lab_py/result.py` preserves
  zero or one candidate-defined input/output range without injecting a default;
- compatibility and non-graph extended catalogs carry their unchanged `-d10` choice
  explicitly;
- Stage 80 still contains a capability-gated QUIC candidate branch;
- candidate execution is cold and serial: prepare/start/ready/probe/stop/cleanup for
  each candidate.

This document records the destination. Source behavior changes only when its dedicated
patch, focused regression and normal CI gate are complete.

==================================================
AUTHORITATIVE TECHNICAL BOUNDARY
==================================================

Strategy Lab searches only native `bol-van/zapret2` mechanisms.

Authoritative upstream references include:

- Zapret2 manual: `https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md`;
- Zapret2 `blockcheck2` only as a search-method reference, not as code to import;
- the actual installed Zapret2 Lua and fake-file resources captured for the job.

Classic zapret/nfqws1/dvtws/winws command lines are outside the search-space contract.
They are neither candidates nor translation input. If a concept is useful, it must
already exist as a native Zapret2 mechanism and be represented directly from Zapret2
semantics.

The implementation boundary remains:

```text
Python planner / CandidateSpec / ResourceInventory / evidence
        -> narrow candidate system adapter
        -> FreeBSD IPFW/divert + dvtws2
        -> bounded probe
        -> Python classification / next decision
```

Shell does not decide the next candidate, expand parameters, select BLOBs or silently add
strategy semantics.

==================================================
UPSTREAM FACTS USED BY THIS DESIGN
==================================================

The current Zapret2 manual establishes the following design-relevant behavior:

- `--lua-init` executes Lua code once at process startup;
- `--blob=<name>:...` loads a file or inline hex value into a named Lua BLOB at startup;
- Zapret2 provides built-in `fake_default_tls`, `fake_default_http` and
  `fake_default_quic` BLOBs;
- `multisplit` accepts an optional `seqovl_pattern`; its default is `0x00`;
- a profile can contain any number of ordered `--lua-desync` instances;
- profiles are scanned from first to last and the first matching profile is selected;
- `--new` starts a new profile but does not by itself provide an externally addressable
  candidate selector;
- Lua orchestrators can receive the execution plan for remaining instances and decide
  which of them to invoke.

Consequences:

- a valid bypass strategy can require no external `.bin` file;
- initializing resources once in a warm process can theoretically avoid repeated startup
  work;
- simply putting many otherwise identical candidates behind `--new` cannot select an
  arbitrary candidate for a probe;
- a laboratory dispatcher is technically plausible but still requires deterministic
  selection and OPNsense isolation evidence before production use.

==================================================
CANDIDATESPEC
==================================================

Python introduces one canonical immutable candidate description. The exact class layout
is an implementation detail, but the data contract must be able to express:

- stable `candidate_id`;
- optional family/technique tags used for diagnostics and ordering only;
- L3 capability requirement;
- transport and destination port;
- optional L7/payload filters;
- ordered Lua instance list and every instance argument;
- split/marker/position values;
- `seqovl`, repeat/fake and other native technique parameters;
- optional `in-range` / `out-range` values;
- required BLOB references and their resource class;
- required Lua/resource dependencies;
- target/endpoint binding requirements;
- search cost/complexity metadata;
- provenance, for example built-in seed, upstream example, owner golden case or adaptive
  neighbor;
- enough normalized data to render the exact tested user-ready strategy later.

`family` is not an authorization field. A candidate is reachable because the search graph
contains a valid path to it and budget remains, not because Stage 50 accepted a label.

`--out-range=-d10` is therefore no longer injected by contract. A candidate may carry
`-d8`, `-d10`, another valid native range, or no explicit output range when the strategy
does not require one.

==================================================
RESOURCEINVENTORY
==================================================

At job initialization Python snapshots the resources available from the installed
runtime:

- `/usr/local/etc/zapret2/lua/*.lua`;
- `/usr/local/etc/zapret2/files/fake/*.bin`;
- Zapret2 built-in BLOB names supported by the runtime contract;
- inline patterns that need no external file.

The inventory is job-scoped evidence. It records stable names and the information needed
to explain why a candidate was eligible or skipped. The search code must never assume that
the resources present in one Zapret2 release are identical in another release.

Owner-observed Lua baseline on 2026-08-08:

- `custom_diag.lua`;
- `custom_funcs.lua`;
- `init_vars.lua`;
- `zapret-16kb.lua`;
- `zapret-antidpi.lua`;
- `zapret-auto.lua`;
- `zapret-lib.lua`;
- `zapret-multishake.lua`;
- `zapret-obfs.lua`;
- `zapret-pcap.lua`;
- `zapret-tests.lua`;
- `zapret-wgobfs.lua`.

The owner also supplied a live fake-file listing. Explicit names retained from that
snapshot include `hello_www_onetrust_com.bin`,
`tls_serverhello_google_com_tls13.bin`, `wireguard_initiation.bin`,
`wireguard_response.bin`, `ya_ch.bin`, `zero_1024.bin`, `zero_256.bin`, and
`zero_512.bin`. That observed snapshot is evidence, not a permanent allowlist; the
implemented `ResourceInventory` must record the complete directory that actually exists
for each job rather than relying on this documentation copy.

Resource selection uses four classes:

1. BLOB-free;
2. built-in BLOB;
3. inline `0x...` BLOB/pattern;
4. external installed `.bin`.

External BLOB eligibility is semantic. TLS search does not multiply itself by unrelated
WireGuard, STUN, QUIC, NTP or other protocol payloads merely because those files exist.
Likewise, presence of a Lua file means it is available, not that every `CandidateSpec`
depends on it.

==================================================
LUA DEPENDENCY AND BYPASS BOUNDARY
==================================================

Zapret2 action logic is executed by ordered Lua instances. A Strategy Lab bypass
candidate therefore contains at least one `--lua-desync` action.

A profile with only C-side filters, resource initialization or selectors but no Lua
action is a pass-through/control case. It may be useful as baseline evidence but is not a
reported bypass strategy.

`CandidateSpec` records the functional Lua/resource dependencies even if a later warm
worker experiment chooses to preload a broader common bundle. This separation matters:

- dependency metadata makes the result reproducible;
- preload policy is only a runtime optimization;
- changing preload policy must not change candidate identity or search semantics.

==================================================
GOLDEN / REFERENCE CORPUS
==================================================

Known native-Zapret2 strategies become expressiveness regressions, not universal network
presets.

Every golden case must prove at least:

- `CandidateSpec` can represent the strategy without losing arguments or order;
- its required resources resolve correctly;
- rendering returns the intended user-ready strategy;
- the search graph contains a path capable of reaching the candidate;
- the candidate is not excluded by a family result unrelated to its own evidence.

The corpus includes several resource classes. Two agreed representative forms are:

Built-in BLOB case:

```text
--payload=tls_client_hello
--lua-desync=fake:blob=fake_default_tls
```

Owner working external-BLOB/range regression case:

```text
--out-range=-d8
--blob=fake_tls_7
--payload=tls_client_hello
--lua-desync=multisplit:pos=2,midsld-2:seqovl=1:seqovl_pattern=fake_tls_7
```

The second case specifically prevents a return of the hidden `-d10` assumption. Corpus
coverage is expanded from native Zapret2 examples and owner-proven results, but adding a
case does not cause it to be tried blindly for every protocol/target.

==================================================
SEARCH GRAPH
==================================================

Stage 50 becomes low-cost reconnaissance. It may retain simple representative seeds to
produce early evidence, but its result is not an allowlist for Stage 60.

Stage 60 becomes adaptive graph exploration.

Conceptually:

```text
simple native seed
        -> PASS: nearby simpler/stable variants get higher priority
        -> FAIL: stronger compatible modifiers become eligible
                 -> positions / markers
                 -> seqovl / pattern class
                 -> fake + split combinations
                 -> fakedsplit / syndata / other native branches
        -> exhausted: advance to another useful branch
```

Graph rules:

- cost and complexity generally increase as search goes deeper;
- an inexpensive success is useful evidence but does not prohibit alternatives;
- an inexpensive failure is useful evidence but does not prohibit stronger variants;
- protocol/resource compatibility removes meaningless branches before scheduling;
- historical success rates adjust priority only;
- current-job evidence has higher relevance than global historical ordering;
- the graph remains bounded by explicit stage/job budget and cancellation;
- the planner records why a node was scheduled, skipped, pruned or deferred.

The design intentionally avoids a full Cartesian product. Search quality is measured by
useful hit rate and time-to-stable-winner, not by the percentage of a theoretical catalog
enumerated.

==================================================
BASELINE AND ENDPOINT PINNING
==================================================

The clean baseline remains mandatory and precedes search.

If the target already works directly under the required baseline contract, Strategy Lab
returns `TARGET_ACCESSIBLE`; it does not spend budget searching for an unnecessary bypass.

For a search epoch:

- DNS resolution occurs once through the authoritative Python resolver/parser;
- the selected IP endpoint set is recorded;
- hostname/SNI remains the original validated target identity;
- candidate probes use the same endpoint selection so results are comparable;
- an explicit re-resolution starts a new recorded epoch rather than silently changing
  endpoints between candidates.

This is both an optimization and an experimental-control rule. It must preserve the
existing truthful DNS failure classification.

==================================================
PROTOCOL PRIORITY
==================================================

Primary search budget:

1. IPv4 + TCP + TLS;
2. IPv6 only when actual routing/connectivity capability exists and after primary IPv4
   work;
3. extended TLS 1.2 / HTTP / explicitly configured generic UDP according to mode.

QUIC is deliberately bounded to the existing fixed IPv4 UDP/443 capability/precheck.
There is no adaptive QUIC strategy search branch in the target design. A successful or
failed QUIC precheck remains diagnostic evidence only and does not consume a large
strategy-search budget.

==================================================
TWO-LEVEL VALIDATION
==================================================

Discovery and publication answer different questions and use different evidence levels.

Discovery:

- cheap bounded probe;
- fixed endpoint/hostname contract;
- enough structured evidence to rank a candidate;
- no retries that can hide the first result;
- exact lightweight method selected after timing/reliability measurement.

Stability:

- fresh connections;
- up to three attempts;
- requirement remains 3/3;
- fail fast as soon as one failure makes 3/3 impossible.

Finalist deep validation:

- only the best two to three candidates normally reach it;
- cold isolated replay remains the reference even if warm discovery is later selected;
- use a real bounded GET rather than treating response headers alone as content success;
- target at least 16 KiB of response body when the selected resource can provide it;
- record actual bytes, endpoint identity, protocol outcome and interception evidence;
- if the resource terminates before 16 KiB, record the 16-KiB criterion as
  `inconclusive`, not PASS;
- do not convert an `inconclusive` byte-length criterion into a false network failure;
  preserve the separate connectivity/stability evidence.

Early stop normally occurs after two to three candidates have stable evidence strong
enough for final ranking. A truthful one-candidate result remains valid when the budget or
network exposes no second winner.

==================================================
WARM RUNTIME OPTIONS
==================================================

The current cold candidate lifecycle remains the correctness reference:

- build runtime;
- initialize Lua/BLOB resources;
- start dvtws2;
- wait for readiness;
- probe;
- stop and prove cleanup.

The redesign does not assume that repeating this lifecycle is the best performance model.
Three execution models are evaluated:

- A — cold reference: one candidate -> one newly started dvtws2;
- B — warm process pool: compatible candidate/worker assignments use separate dvtws2
  processes and distinct divert ownership;
- C — warm bucket: one dvtws2 preloads a compatible set and a deterministic laboratory
  dispatcher selects exactly one candidate for the test flow.

Important distinction:

Model B may keep several workers alive while still probing candidates sequentially. That
can remove startup cost without introducing simultaneous strategy tests. True parallel
candidate probing is a separate experiment and receives no production status merely
because multiple processes can coexist.

For model C, plain `--new` cannot act as the selector because overlapping profiles use
first-match selection. A purpose-built dispatcher would have to choose exactly one
preloaded execution chain and bind that choice to the complete probe flow.

Controlled client source-port encoding is one possible selector hypothesis only. It is
not an approved implementation assumption until the experiment proves that the selector
is visible at the required Lua point, survives the OPNsense/NAT/IPFW path, is collision
safe and stays stable for the full connection.

Buckets, if model C survives testing, are grouped only by proven compatibility such as:

- IP family/transport/port/L7;
- process-global options;
- Lua initialization bundle;
- BLOB inventory;
- stateful/orchestrator requirements;
- interception/rule ownership requirements.

Buckets start lazily. A search branch that is never reached should not consume process
or memory cost.

Production selection of A, B, C or a hybrid is governed by
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

==================================================
TIMEOUT MODEL
==================================================

Current `_30` timeout values remain the executable source baseline until a later patch
changes them. They are not copied into the target design as unexplained constants.

The redesign first records timing for:

- DNS;
- candidate preparation;
- resource initialization;
- dvtws2 launch;
- readiness/stability wait;
- lightweight discovery probe;
- repeated stability probe;
- deep GET;
- dvtws2 stop;
- firewall/runtime cleanup;
- mandatory service restoration.

The future deadline model must satisfy containment:

`operation <= candidate <= stage <= job`.

The candidate envelope includes the operations it is expected to finish plus mandatory
candidate cleanup. A stage envelope cannot knowingly be shorter than a child operation it
authorizes. Job/stage budget admission checks use remaining measured cost before starting
new work.

Timeout tuning is data-driven. The objective is not merely larger numbers; it is to avoid
both premature parent termination and needless waiting after a result is already known.

==================================================
RESULT AND REPRODUCIBILITY CONTRACT
==================================================

Every reported candidate must be explainable from persisted evidence:

- normalized `CandidateSpec`;
- resource inventory identity;
- target/search epoch and pinned endpoints;
- exact rendered strategy/profile;
- discovery result;
- stability attempts;
- deep-validation result for finalists;
- runtime model used for discovery;
- cold-reference result when required;
- timing measurements;
- cleanup/interception evidence.

Runtime preload details are not silently embedded in user strategy output. Only resources
that the strategy itself requires become part of the reproducible profile contract.

==================================================
IMPLEMENTATION HANDOFF
==================================================

The architecture is intentionally split into the following source cycles:

- `_28`: **implemented in `0.4.0_2` source** — remove accepted-family hard gating while
  retaining Stage-50 evidence as accepted-first priority;
- `_29`: **implemented in `0.4.0_3` source** — immutable normalized `CandidateSpec`,
  job-scoped installed `ResourceInventory`, exact Python rendering and active-adapter
  policy cleanup;
- `_30`: **implemented in `0.4.0_4` source** — native search graph, semantic resource
  branches, golden corpus and variable range;
- `_31`: adaptive ordering, endpoint pinning, early stop, timing telemetry;
- `_32`: timeout hierarchy derived from telemetry;
- `_33`: lightweight discovery plus fail-fast 3/3 and finalist deep validation.

Each patch changes only its listed responsibility and updates this document when the
implemented result proves that the target design needs correction. Warm runtime selection
is not forced into this sequence before the A/B/C evidence is sufficient.
