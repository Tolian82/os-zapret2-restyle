# Strategy Lab BLOB loading / startup / RSS measurement

Status: **_3 ACCEPTED / _4 COMMON-SET MEASUREMENT IN SOURCE / PRODUCTION MODEL C UNCHANGED**

## Question

Does BLOB declaration/loading impose measurable warm-worker startup/readiness or RSS cost, and
does that cost grow when Model C eagerly declares a common external-resource set for several
compatible candidates?

This remains an evidence question. Neither `_3` nor `_4` changes the accepted
`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`
production chain.

## Production reason for measuring common-set cost

Model C renders one compatible bucket into one warm dvtws2 worker. External `--blob=`
declarations required by candidates in that bucket are deduplicated and emitted into the common
worker argument set before candidate-specific selector/action chains.

That is correctness-safe, but it means a candidate can cause a BLOB to be loaded even while a
different chain is the one selected for the current probe. The remaining performance question is
therefore not whether one small BLOB works, but whether the **eager common declaration set** has a
measurable startup/readiness or RSS price at the current bounded candidate width.

## `_3` controlled three-variant measurement — accepted

Policy: `blob-startup-rss-v1`.

The common Lua/runtime shape was held constant:

- `zapret-lib.lua`;
- `zapret-antidpi.lua`;
- `zapret-auto.lua`;
- `strategy_lab_model_c.lua`;
- TLS/IPv4/TCP/443 filter;
- `--in-range=x`, `--out-range=-d8`, `--payload=tls_client_hello`;
- `multisplit:pos=2,midsld-2:seqovl=1` action structure.

Variants:

1. BLOB-free;
2. built-in `fake_default_tls`;
3. one external `fake_tls_7.bin` declaration used by the action.

The owner-installed `_3` run completed 9 trials per variant, 27 starts total, with all adapter,
sample-count, cleanup and lifecycle-restoration checks passing and
`conclusion=measurement_accepted`.

Median stable readiness:

- BLOB-free `63.061 ms`;
- built-in `62.652 ms`;
- external `62.566 ms`.

Median ready and settled RSS was `4360 KiB` for all variants. Built-in and external median
readiness differed from BLOB-free by only `-0.409 ms` (`-0.649%`) and `-0.495 ms` (`-0.785%`).
Those differences were smaller than the observed within-variant jitter/tails and did not establish
a BLOB startup penalty.

Initial/final normal Zapret2 evidence matched exactly and remained RUNNING. `_3` used
`cache_policy=natural-cache-no-drop`; it is not a cold-cache claim.

Evidence:
`docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`.

## `_4` common-set scaling measurement

Policy: `blob-common-set-scaling-v1`, report schema `2`.

`_4` addresses the coverage still required by the adaptive-search experiment authority:
small-inline plus several semantically compatible external resources. It also removes worker/port
identity as a comparison variable.

### Fixed worker identity

Every variant uses:

- adapter worker: `external`;
- divert port: `9992`;
- the same common Lua/filter/action shape.

The active `dvtws.args` is rewritten immediately before each launch. No four different worker
identities or ports are compared.

### Controlled variants

1. **blob-free**
   - no external declaration;
   - no pattern.

2. **inline-small**
   - no external declaration;
   - active `seqovl_pattern=0x1603`;
   - two inline bytes.

3. **external-single**
   - declare canonical `fake_tls_7` from ResourceInventory;
   - use `fake_tls_7` in the active action.

4. **external-common-3**
   - declare canonical `fake_tls_7`;
   - declare canonical `tls_clienthello_rutracker_org_kyber`;
   - declare canonical `tls_clienthello_vk_com_kyber`;
   - use only `fake_tls_7` in the active action;
   - retain the other two as intentionally unused eager declarations that stand in for resources
     belonging to other compatible candidates in the same common worker.

The three external files are TLS ClientHello resources. They are not unrelated protocol files
added merely to increase count.

The set size equals the current maximum production candidate width of three and is explicitly a
**bounded synthetic production-width common-set upper bound**. It does not claim that the current
search graph always produces those exact three resources in one bucket.

The report records canonical resource paths, declaration count and total declared bytes from the
same immutable ResourceInventory contract used by Strategy Lab.

### Trial design

Default: 12 trials per variant, 48 worker starts total.

Accepted trial counts are 4, 8, 12 or 16. This guarantees complete four-order rotations rather
than accepting a partially balanced run.

The measurement intentionally does not drop OS caches and reports
`cache_policy=natural-cache-no-drop`.

For every launch:

1. write that variant's arguments into the same worker slot;
2. launch the same worker/port identity;
3. poll approximately every 25 ms for at most 4 s;
4. require two consecutive snapshots with exact process identity, divert socket readiness, clean
   log and positive RSS;
5. record first-ready and stable-ready latency;
6. wait 200 ms and record settled RSS;
7. stop the worker before the next variant.

Per variant the report retains min/mean/median/stdev/p90/max for stable readiness, ready RSS and
settled RSS.

Primary comparison:

- `external-common-3` vs `external-single`.

Supporting comparisons:

- `inline-small` vs `blob-free`;
- `external-single` vs `blob-free`;
- `external-common-3` vs `blob-free`.

## Isolation / lifecycle ownership

The experiment retains the lifecycle-locked `_3` wrapper and the audited narrow Model-B adapter.
It MUST NOT:

- call `route-add` or install experiment traffic routes;
- stop/start/reconfigure normal Zapret2;
- change normal firewall rules;
- mutate Traffic Strategy, target lists or resource files;
- change production Model C/B/A behavior;
- leave temporary worker/rule/socket state.

The wrapper owns `/var/run/zapret2-lifecycle.lock`. Initial and final semantic service evidence is
collected with `zapret_service.sh strategy-lab-evidence`; acceptance requires identical service
state, child/supervisor booleans, runtime-args hash, effective-config hash and normal-firewall hash.

## Decision boundary

`production_change_recommended=false` is hard-coded for `_4`.

A valid `_4` run is measurement evidence, not production-change authorization.

- If `external-common-3` shows a material readiness/RSS cost above measured jitter relative to
  `external-single`, reproduce that effect before considering a separate production patch.
- If no material cost appears for the current width-three common-set upper bound, close the
  BLOB-loading optimization as a negative result for the present architecture instead of adding
  lazy-loading complexity without evidence.

Any future production BLOB-loading change remains a separate packaged patch and may not alter
CandidateSpec resource identity, source-port attribution, deadlines, cleanup or restoration
semantics.
