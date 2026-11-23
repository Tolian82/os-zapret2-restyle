# TZ6v5 S05a — public read-only JSON Status, compatible plain Status

**23.11.2026.** Candidate `v0.6.5_155` based on merged `main _154 67133c88`, [S04 five-state native GO](ZAPRET2_TZ6V5_S04_NATIVE_INVENTORY_GO.md). Not an operator package. S05a is a bounded *subset* of S05: native diagnostic producers and GUI presentation are not yet accepted.

## Exact physical boundary

`zapret_service.sh status` **retains its original shell case and existing original FD9/exit-code/plain-text contract**. `status --json` is strictly allowlisted (`status --force`, duplicates or extra flags return rc64 **before** lifecycle dispatch). The new route calls the existing qualified Python runtime, imports S04 `component_inventory_opnsense.collect()`, and passes only S04's enum-only output through a pure `status_projection.project()`. It does **not** take FD9, modify Config, write a new journal, run an engine, compile, enumerate an independent PID identity, mutate IPFW, or start/stop/reload anything. It prevents `__pycache__` via `PYTHONDONTWRITEBYTECODE` and `sys.dont_write_bytecode` before imports.

The public envelope includes `schema,timestamp,runtime_state,status_exit_code,verification,components,code,message,stage,operation_id,generation,exit_status,stderr_excerpt,log_ref,requested,effective,authorization,physical_transition_allowed`. Physical runtime maps RUNNING→0, STOPPED→1, all INCOMPLETE/FOREIGN/UNKNOWN→2. A malformed original report never grants owner authority; the JSON fallback reports `STATUS_UNAVAILABLE`, runtime UNKNOWN, rc2 and **never** claims stopped or running.

**Important:** `code` is the honest current S04 **component classification**. `stage,operation_id,generation,exit_status,stderr_excerpt,log_ref,requested,effective` remain `null` until a verified existing original lifecycle diagnostic producer is wired. Null is not a claim of no errors. No raw native `dvtws2` stderr, Config XML, domains, IPs, full argv or any user secrets may enter Status. No fake producer, no second error database, no duplicate FD9/Config writer.

## RED→GREEN acceptance

Source tests: strict shape/authorization, seven runtime cases, no fabricated error/owner, unqualified fail-closed behavior, invalid options before FD9, no direct new write/process/IPFW owner. **Native acceptance still required** on a disposable OPNsense of the exact installed path across fresh/plugin-only/engine-only/RUNNING/invalid saved Config/foreign IPFW, before/after no-write of Config/pkgdb/owner journal/PID/epoch/IPFW trees plus old plain status equivalence. The producer/consumer diagnostic work (actual `engine-start/stop/setup/configd/P2/Apply/Lab` latest event, bounded sanitization and RU/EN GUI) belongs to S05b/c before **full S05 GO**. Release and operator hardware remain untouched.
