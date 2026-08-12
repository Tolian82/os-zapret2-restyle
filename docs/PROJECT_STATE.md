# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered: Where is the project now?

Read after `AGENTS.md` and `docs/INDEX.md`. Historical implementation detail belongs in
`docs/patches/`, `docs/devlog/` and `docs/verification/evidence/` and must not override a
later current patch/live record.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=25`
Current source candidate: `os-zapret2-restyle-0.4.0_25.pkg`
Latest published testing prerelease: `v0.4.0_25`
Latest owner-tested testing candidate: `v0.4.0_25` — source-port lease corrective owner-live PASS
Required package ABI: `FreeBSD:15:amd64`

Published `_25` runtime commit:
`a5ecfbfd57820e30e5f2be450e510b96c00267e3`.

Published `_25` asset:
`os-zapret2-restyle-0.4.0_25.pkg`, `178783` bytes,
`sha256:1355b5000c0a9acc7e6717ddc7bd78248626abd21d826dd82cb8f15fcc4fdf91`.

Publication evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_25-publication.md`.

Owner-live acceptance evidence:
`docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`.

Active Strategy Lab ownership authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Current `_25` change authority:
`docs/patches/v0.4.0_25.md`,
`docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md`,
`docs/verification/evidence/2026-08-11-v0.4.0_25-publication.md`, and
`docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`.

Model-C architecture authority:
`docs/architecture/STRATEGY_LAB_MODEL_C.md` and
`docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md`.

Current Stage-60 preferred model: `C-warm-bucket-source-port-dispatch`.
Immediate fallback/reference: `B-warm-worker-parallel-batched`.
Final fail-closed fallback: cold Model A.
Candidate width remains at most 3; pinned endpoints inside one candidate remain sequential;
there is no CPU-count gate.

==================================================
LATEST OWNER-LIVE EVIDENCE
==================================================

`v0.4.0_25` has completed its selected source-port corrective owner-live gate. Durable record:
`docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`.

Extended `telegram.org`, `job.5yGde5`:

- Stage 60 genuinely used `C-warm-bucket-source-port-dispatch`;
- `stopped_reason=graph_exhausted`;
- 16/16 candidates completed, zero winners;
- `.parallel.fallbacks=[]` — no Model-B or cold-Model-A fallback;
- Stage 60 duration `34198 ms`;
- total job duration `114759 ms`;
- final outcome `NO_CANDIDATE`;
- all six batches persisted `_25` lease evidence with
  `policy=preferred-free-else-alternate` and `foreign_port_action=skip-only`;
- this run encountered no occupied preferred port, so `collisions=[]` and
  `replacement_count=0` in every batch;
- Stage 90 restoration succeeded;
- post-job Zapret2 remained RUNNING;
- rules `19128-19130` left no residue.

This closes the visible `_23` failure path where Extended `telegram.org` shared one occupied
`42004` between Model C and Model B, fell to cold Model A and timed out after 13 candidates.
The `_25` owner-live run does not claim a real alternate-port replacement because no foreign
collision occurred during that run; alternate selection under collision remains covered by
the focused automated lease contract.

Retained comparison evidence:

- `_23` Model-C live HOLD / source-port collision:
  `docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md`;
- accepted `_22` Model-B baseline:
  `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

Historical `_7`/`_8` timeout containment remains closed; current 16/16 search behavior is
not the old fixed-parent-timeout defect.

==================================================
CURRENT `_25` STATUS
==================================================

`v0.4.0_25` is **published and owner-live accepted for the selected source-port corrective**.

`_25` changes only the concrete controlled-source-port ownership boundary for warm Stage 60.
The deterministic `42000+` map remains the preferred identity plan, but each admitted warm
batch leases its actual exact ports:

- free preferred ports are retained;
- an occupied foreign port is skipped, never killed, closed or reused destructively;
- a unique free alternate above the deterministic plan is selected through the audited
  `source-port-free` adapter;
- Model-C renderer, Lua selector, IPFW route and curl probe all use the exact leased port;
- the endpoint-level source-port availability check remains as race protection;
- if Model C falls back, Model B performs a fresh independent lease rather than inheriting
  Model C's failed concrete port;
- bounded lease exhaustion fails closed into the existing fallback chain.

Successful probes retain strict connected-socket endpoint/local-port identity. Failed probes
retain the `_21` exact command source-port + pinned `--resolve` + exact rule counter growth +
successful cleanup attribution contract. Stage 70/80/85 and Stage-90 restoration ownership
are unchanged.

No Strategy Lab timeout was increased by `_25`.

==================================================
NEXT ACTION: ADAPTIVE BUDGET
==================================================

The next Strategy Lab timing design must use an **adaptive budget calculated from the actual
eligible work matrix**:

`number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode`.

When IPv6, QUIC or Generic UDP are available/selected, Strategy Lab should automatically
receive a finite reasonable additional budget proportional to the work it can actually
perform. Do **not** solve this by guessing one oversized static timeout. Admission,
stage/overall deadlines, cancellation and telemetry must remain explicit and finite.

The accepted `_25` Telegram run gives a clean no-fallback timing baseline for this work:
Stage 60 `34198 ms`, total Extended job `114759 ms`, with IPv4 available while IPv6 and QUIC
were excluded and Generic UDP was not active.

Broader IPv6/QUIC/Generic-UDP timing work should now build from this clean Model-C baseline,
not from accidental Model-C -> Model-B -> cold-Model-A fallback cost.
