# Strategy Lab BLOB loading / startup / RSS measurement

Status: **_3 ACCEPTED / _4 ACCEPTED / BLOB-LOADING OPTIMIZATION CLOSED / PRODUCTION MODEL C UNCHANGED**

## Question

Does BLOB declaration/loading impose measurable warm-worker startup/readiness or RSS cost, and
does that cost grow when Model C eagerly declares a common external-resource set for several
compatible candidates?

For the current candidate-width-three architecture, this evidence question is now closed. Neither
`_3` nor `_4` changes the accepted
`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`
production chain.

## Production reason for measuring common-set cost

Model C renders one compatible bucket into one warm dvtws2 worker. External `--blob=`
declarations required by candidates in that bucket are deduplicated and emitted into the common
worker argument set before candidate-specific selector/action chains.

That is correctness-safe, but it means a candidate can cause a BLOB to be loaded even while a
different chain is the one selected for the current probe. The remaining performance question was
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

## `_4` common-set scaling measurement — accepted

Policy: `blob-common-set-scaling-v1`, report schema `2`.

`_4` addressed the remaining coverage required by the adaptive-search experiment authority:
small-inline plus several semantically compatible external resources. It also removed worker/port
identity as a comparison variable.

Testing prerelease `v0.4.1_4` was published from exact source merge
`461fe2d045b131f3400f285a9cb59808b5f33ce2`. The owner-live measurement is accepted. Publication
evidence is recorded in
`docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-publication.md`; owner-live evidence
is recorded in
`docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`.

### Fixed worker identity

Every variant used:

- adapter worker: `external`;
- divert port: `9992`;
- the same common Lua/filter/action shape.

The active `dvtws.args` was rewritten immediately before each launch. No four different worker
identities or ports were compared.

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
   - use `fake_tls_7` in the active action;
   - `226` declared bytes.

4. **external-common-3**
   - declare canonical `fake_tls_7`;
   - declare canonical `tls_clienthello_rutracker_org_kyber`;
   - declare canonical `tls_clienthello_vk_com_kyber`;
   - use only `fake_tls_7` in the active action;
   - retain the other two as intentionally unused eager declarations that stand in for resources
     belonging to other compatible candidates in the same common worker;
   - `3825` declared bytes total.

The three external files are TLS ClientHello resources. They are not unrelated protocol files
added merely to increase count.

The set size equals the current maximum production candidate width of three and is explicitly a
**bounded synthetic production-width common-set upper bound**. It does not claim that the current
search graph always produces those exact three resources in one bucket.

### Accepted owner-live result

The final report completed `48` starts, `12` per variant, with all acceptance checks true and
`conclusion=measurement_accepted`.

Stable-readiness summary:

| Variant | mean ms | median ms | stdev ms | p90 ms |
|---|---:|---:|---:|---:|
| BLOB-free | 63.494 | 62.478 | 1.903 | 66.100 |
| inline-small | 62.674 | 62.398 | 1.286 | 64.520 |
| external-single | 65.055 | 62.332 | 5.502 | 72.535 |
| external-common-3 | 63.610 | 62.566 | 2.276 | 66.033 |

Primary `external-common-3` versus `external-single` median readiness delta was only
`+0.234 ms` / `+0.375%`. That delta is far below the observed stdev in either external variant.
The common-set mean and p90 were lower, not higher, so the distribution does not show a consistent
startup penalty.

Median ready and settled RSS was `4360 KiB` for `external-single` and `4362 KiB` for
`external-common-3`: `+2 KiB` / `+0.046%`. The difference is below observed RSS spread. Common-3
versus BLOB-free was only `+4 KiB` / `+0.092%`.

Initial and final normal-service state matched exactly and remained RUNNING. Cleanup passed and no
temporary worker state remained.

### Trial design

The accepted owner run used 12 trials per variant, 48 worker starts total, with the complete
four-order balance and `cache_policy=natural-cache-no-drop`.

For every launch the measurement:

1. wrote that variant's arguments into the same worker slot;
2. launched the same worker/port identity;
3. polled approximately every 25 ms for at most 4 s;
4. required two consecutive snapshots with exact process identity, divert socket readiness, clean
   log and positive RSS;
5. recorded first-ready and stable-ready latency;
6. waited 200 ms and recorded settled RSS;
7. stopped the worker before the next variant.

Per variant the report retained min/mean/median/stdev/p90/max for stable readiness, ready RSS and
settled RSS.

## Isolation / lifecycle ownership

The experiment retained the lifecycle-locked `_3` wrapper and the audited narrow Model-B adapter.
It did not:

- call `route-add` or install experiment traffic routes;
- stop/start/reconfigure normal Zapret2;
- change normal firewall rules;
- mutate Traffic Strategy, target lists or resource files;
- change production Model C/B/A behavior;
- leave temporary worker/rule/socket state.

The wrapper owned `/var/run/zapret2-lifecycle.lock`. Initial and final semantic service evidence
collected with `zapret_service.sh strategy-lab-evidence` matched exactly for service state,
child/supervisor booleans, runtime-args hash, effective-config hash and normal-firewall hash.

## Decision — closed negative optimization result

`production_change_recommended=false` remains correct.

The accepted `_3` and `_4` owner measurements together provide no evidence of a material BLOB
startup/readiness or RSS penalty for the present architecture: neither one representative external
BLOB nor the bounded eager common set at candidate width three produced an effect above normal
jitter.

Therefore:

- production Model C BLOB loading remains unchanged;
- lazy BLOB loading is not added;
- no package revision is created solely for this optimization;
- the BLOB-loading startup/RSS optimization is closed as a negative result for current width three.

This closure is intentionally bounded. A future architecture that materially increases candidate
width, BLOB count, or resource size must collect new evidence instead of extrapolating this result.
