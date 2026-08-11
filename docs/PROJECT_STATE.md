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
Latest owner-tested testing candidate: `v0.4.0_23` (Model C proven live, source-port corrective required)
Required package ABI: `FreeBSD:15:amd64`

Published `_25` runtime commit:
`a5ecfbfd57820e30e5f2be450e510b96c00267e3`.

Published `_25` asset:
`os-zapret2-restyle-0.4.0_25.pkg`, `178783` bytes,
`sha256:1355b5000c0a9acc7e6717ddc7bd78248626abd21d826dd82cb8f15fcc4fdf91`.

Publication evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_25-publication.md`.

Active Strategy Lab ownership authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Current `_25` change authority:
`docs/patches/v0.4.0_25.md`,
`docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md`, and
`docs/verification/evidence/2026-08-11-v0.4.0_25-publication.md`.

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

`v0.4.0_23` has now been owner-live exercised. The durable record is:
`docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md`.

Extended `rutracker.org`, `job.FaLtIk`:

- Stage 60 genuinely used `C-warm-bucket-source-port-dispatch`;
- one physical warm bucket served concurrent candidate routes;
- all 16 candidates completed with winners `seqovl-host` and `seqovl-midsld`;
- no fallback occurred;
- Stage 70/80/85 and semantic restoration succeeded.

Extended `telegram.org`, `job.G0wC5l`:

- IPv4 available; IPv6 unavailable; QUIC/IPv4 closed;
- the first warm batch hit `controlled source port is already in use: 42004`;
- Model C and Model B both received the same static concrete source-port plan and both
  failed on `42004`;
- Stage 60 fell through to `A-cold-fallback`, completed 13 candidates, then stopped with
  `insufficient_stage_budget` / `TIMEOUT`;
- semantic restoration was exact RUNNING -> RUNNING with identical runtime/config/firewall
  hashes and `temporary_runtime_clean=true`.

Therefore `_23` proves Model C itself works, but also confirms a source-port ownership defect
in the shared static plan. It does **not** show a lifecycle/restoration regression.

The accepted `_22` Model-B baseline remains useful comparison evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.
Historical `_7`/`_8` timeout containment remains closed; current 16/16 search behavior is
not the old fixed-parent-timeout defect.

==================================================
CURRENT `_25` CORRECTIVE
==================================================

`_25` changes only the concrete controlled-source-port ownership boundary for warm Stage 60.
The deterministic `42000+` map remains the preferred identity plan, but each admitted warm
batch now leases its actual exact ports:

- free preferred ports are retained;
- an occupied foreign port is skipped, never killed, closed or reused destructively;
- a unique free alternate above the deterministic plan is selected through the audited
  `source-port-free` adapter;
- Model-C renderer, Lua selector, IPFW route and curl probe all use the exact leased port;
- the existing endpoint-level source-port availability check remains as race protection;
- if Model C falls back, Model B performs a **fresh independent lease** rather than inheriting
  Model C's failed concrete port;
- bounded lease exhaustion fails closed into the existing fallback chain.

Successful probes retain strict connected-socket endpoint/local-port identity. Failed probes
retain the `_21` exact command source-port + pinned `--resolve` + exact rule counter growth +
successful cleanup attribution contract. Stage 70/80/85 and Stage-90 restoration ownership
are unchanged.

No Strategy Lab timeout is increased by `_25`.

`v0.4.0_25` is now published as a testing prerelease from exact runtime commit
`a5ecfbfd57820e30e5f2be450e510b96c00267e3`. Publication workflow `31534534435` passed
FreeBSD 15 build, manifest verification, release publication, published-contract verification
and temporary publication-branch cleanup.

==================================================
FOLLOW-UP: ADAPTIVE BUDGET
==================================================

After `_25` removes accidental cold-fallback inflation, the next timing design must use an
**adaptive budget calculated from the actual eligible work matrix**:

`number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode`.

When IPv6, QUIC or Generic UDP are available/selected, Strategy Lab should automatically
receive a finite reasonable additional budget proportional to the work it can actually
perform. Do **not** solve this by guessing one oversized static timeout. Admission,
stage/overall deadlines, cancellation and telemetry must remain explicit and finite.

This requirement is documented now but intentionally not implemented in `_25`.

==================================================
VERIFICATION / NEXT ACTION
==================================================

Source/CI qualification for `_25` passed the complete Strategy Lab corrective matrix, focused
source-port lease contract and FreeBSD 15 package build/inspection. Testing prerelease
`v0.4.0_25` is published; owner-live verification is now the active gate.

First owner-live recheck: Extended `telegram.org`. Expected boundary: Model C should skip an
occupied preferred `420xx` port by leasing an alternate instead of forcing Model C and Model B
through the same collision into cold Model A. Evidence must show actual selector lease ports
and clean Stage-90 restoration/no `19128-19130` residue.

Broader IPv6/QUIC/Generic-UDP timing work follows only after this collision corrective is
measured, so adaptive-budget design is based on real workload rather than accidental
fallback cost.
