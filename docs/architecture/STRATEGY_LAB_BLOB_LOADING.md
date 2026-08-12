# Strategy Lab BLOB loading / startup / RSS measurement

Status: **MEASUREMENT ACCEPTED / PRODUCTION MODEL C UNCHANGED**

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

## Accepted owner-live result

The owner-installed `_3` measurement completed 9 trials per variant, 27 worker starts total,
and reported:

- `adapter_preflight=true`;
- `all_samples_ready=true`;
- `expected_sample_count=true`;
- `temporary_workers_clean=true`;
- `cleanup_ok=true`;
- `lifecycle_restored=true`;
- `conclusion=measurement_accepted`.

Median stable readiness:

- BLOB-free: `63.061 ms`;
- built-in: `62.652 ms`;
- external: `62.566 ms`.

Median ready and settled RSS was `4360 KiB` for all three variants. Pairwise median RSS deltas
were exactly zero. Built-in and external median readiness differed from BLOB-free by only
`-0.409 ms` (`-0.649%`) and `-0.495 ms` (`-0.785%`) respectively. Those differences are
smaller than the within-variant spread/tails and do not establish a BLOB startup penalty.

Initial/final normal Zapret2 evidence matched exactly and remained RUNNING. The accepted run
used `cache_policy=natural-cache-no-drop`; it is not a cold-cache claim.

Evidence:
`docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`.

## Decision boundary

The accepted `_3` run is valid owner-live evidence, not production-change authorization.
`production_change_recommended` remains `false`.

Do not change production Model C BLOB loading from this result. The representative single
external `fake_tls_7.bin` case shows no material startup/readiness or RSS cost.

This three-variant result does not prove that arbitrary BLOB count/size has zero cost. The
broader experiment plan still requires small-inline and several semantically compatible
external-resource coverage. If that investigation continues, the next measurement should
address scaling/common eager-set cost rather than changing production first.

Any future production BLOB-loading change still requires reproducible evidence and a separate
packaged patch. No optimization may alter CandidateSpec resource identity, source-port
attribution, deadline, cleanup, or restoration guarantees.
