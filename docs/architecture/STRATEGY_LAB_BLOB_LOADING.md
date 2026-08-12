# Strategy Lab BLOB loading / startup / RSS measurement

Status: **MEASUREMENT-ONLY / PRODUCTION MODEL C UNCHANGED**

## Question

Does declaring/loading a built-in fake or an external fake-file BLOB add measurable warm-worker
startup/readiness or RSS cost relative to an otherwise equivalent BLOB-free Model-C profile?

This is an evidence question. `_3` does not optimize production BLOB loading and does not alter
the accepted Model-C / Model-B / Model-A execution chain.

## Controlled variants

The measurement holds the common Lua/runtime shape constant:

- `zapret-lib.lua`;
- `zapret-antidpi.lua`;
- `zapret-auto.lua`;
- `strategy_lab_model_c.lua`;
- TLS/IPv4/TCP/443 filter;
- `--in-range=x`, `--out-range=-d8`, `--payload=tls_client_hello`;
- `multisplit:pos=2,midsld-2:seqovl=1` action structure.

Only the fake resource changes:

1. **blob-free** — no BLOB declaration or pattern;
2. **builtin** — `seqovl_pattern=fake_default_tls`, relying on Zapret2 built-in fake identity;
3. **external** — `--blob=fake_tls_7:@<canonical installed file>` and
   `seqovl_pattern=fake_tls_7`.

The external path comes from the same immutable `ResourceInventory` contract used by
production Strategy Lab. `_3` also centralizes canonical resource roots so the previous `_2`
measurement-only path mismatch cannot recur.

## Isolation / lifecycle ownership

The experiment reuses the already-audited narrow FreeBSD Model-B adapter only for temporary
worker launch/snapshot/stop on dedicated divert ports `9990`, `9991`, `9992`.

It MUST NOT:

- call `route-add` or install experiment traffic routes;
- stop/start/reconfigure normal Zapret2;
- change normal firewall rules;
- mutate Traffic Strategy, target lists or resource files;
- run different normal Strategy Lab jobs in parallel.

A dedicated wrapper acquires `/var/run/zapret2-lifecycle.lock`. Initial and final semantic
service evidence is collected with `zapret_service.sh strategy-lab-evidence`; acceptance
requires identical state, child/supervisor booleans, runtime args hash, effective config hash
and normal firewall hash. Adapter cleanup must also leave all dedicated worker ports/rules
clean.

## Measurement protocol

Policy identifier: `blob-startup-rss-v1`.

Default: 9 trials per variant, 27 worker startups total. Allowed trial count: 3..15.
Trial order is balanced/interleaved over three rotations to reduce simple order bias.

The measurement intentionally does **not** drop OS caches. It records
`cache_policy=natural-cache-no-drop`; no sample is described as a cold-cache measurement.

For each worker launch:

1. poll the adapter approximately every 25 ms for at most 4 s;
2. require two consecutive snapshots with exact process identity, divert socket ready,
   clean log and positive RSS;
3. record first-ready and stable-ready latency;
4. wait 200 ms and record settled RSS;
5. stop the owned worker and verify cleanup before continuing.

Per variant the report retains raw samples and min/median/p90/max for:

- stable readiness ms;
- ready RSS KiB;
- settled RSS KiB.

It also reports median delta and percentage for:

- builtin vs BLOB-free;
- external vs BLOB-free;
- external vs builtin.

## Decision boundary

One valid run is measurement evidence, not automatic production authorization.
`production_change_recommended` remains `false` in `_3`.

If lifecycle/cleanup and sample integrity pass, the report conclusion is
`measurement_accepted` and next step is
`evaluate_reproducibility_before_any_production_blob_change`.

A production BLOB-loading change requires reproducible evidence and a separate packaged patch.
No optimization may alter CandidateSpec resource identity, source-port attribution, deadline,
cleanup, or restoration guarantees.
