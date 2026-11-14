# #1052 P2k8q3a — original shared-FD9 pretraffic and terminal epoch call path

**Candidate:** `v0.6.5_49`, 14 November 2026. Source-only: active native schema-2 producer, genuine installed FreeBSD first-packet test, old-generation writer-FD attestation, bounded 512-step/4 MiB rollover, worker/ACK, cron and package remain **UNQUALIFIED / DISABLED**.

## Observable safety defect and exact repair

Before this increment P2k8q2's real `EpochReceipts.seal_pretraffic` and `finish_running` existed as isolated source methods, but the actual original FD9 launcher never called them. The original `apply_runtime_original_launcher_once` captured/restored native inodes but could neither durably establish an empty cursor before launch nor safely complete the epoch after the common owner was committed. Calling `finish_running` directly after the engine start is **wrong**: `attest_running_generation` requires a terminal original journal, a real supervisor and exact current installed+sealed candidate argv/map.

The **only** current launcher retains old five-argument ordinary behavior. For an actual (not P2h) native auto observer it now additionally requires a 32-hex original shared generation plus the independently attested 64-hex native PHP candidate digest, both passed by the original `shared_apply_execute_service` through `apply_runtime_activate`. Original `auto_detect_post_drop.py`, already restricted to genuine inherited FD9 and root FreeBSD, adds two bounded commands; no new subprocess owner or lock:

1. `capture` keeps P2k8q1's P2a original empty raw/debug inode proof.
2. `seal-epoch <generation> <candidate-digest>` uses the **same** original P2a queue flock, immutable original shared-work `verify_seal` and active P2c schema-2 map, and fsyncs root-only `pretraffic.json` **before** one `launcher_start_once`.
3. `restore` verifies real launched PID/birth and original raw/debug inode reownership after native `--user=nobody` and **before** any new IPFW diversion.
4. Original Config::save, installed Config proof, IPFW commit, supervisor and terminal `committed` journal finish under original FD9; **only then** `finish-epoch <generation>` requires genuine P2c reattestation of original current generation and exact original P2a queue identities, preserving raw/debug first-packet append and cursor zero.

No invented after-launch empty check, fallback old `begin()`, external witness, new daemon, Config writer, kernel rule, or separate queue. An older active observer without an independently supplied generation/candidate refuses before launching. If epoch completion fails after final native commit, the shared Apply returns a critical error rather than claiming success or deleting evidence.

## Physical vs simulated evidence and hard stop

The modified `scripts/test-auto-detect-fd9-launch.sh` exercises real original shell `apply_runtime_activate` → single launcher order with stubbed native FD9 Python commands, plus missing-ID refusal and injected seal failure before engine/IPFW. The existing `scripts/test-auto-detect-pretraffic-epoch.py` retains 18 real-file source tests of immutable seals, debug/raw inode snapshots and first-packet cursor-zero completion; it injects the native P2c owner. The existing P2h builder regression also now distinguishes **absence of an active map in the builder** from a new postterminal-only epoch hook: the old blanket no-map-string assertion was superseded. CI must run these on the exact PR head. Shell mock **does not** establish FreeBSD original FD9, native process/FD, product first-match or a working worker.

**Deliberate fail-closed boundary:** `apply_runtime_observer_preflight` still invokes the non-existent `authorize` command and refuses every actual active `--hostlist-auto`. The original builder still emits only the inert P2h preview. Hence this code **does not activate** auto discovery, write actual new raw events, schedule configd minute, or change the installed OPNsense. Integration requires the actual original released schema-2 producer **together with** native worker/ACK and historical FD/512-slot/4MiB lossless rollover qualification before replacing the authorization refusal. A new observer may not be enabled merely because this source call graph exists.

[Plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [Prior physical epoch tests](P2K8Q2_TWO_PHASE_PRETRAFFIC_EPOCH.md) · [Original FD9 zero](P2K8Q1_ORIGINAL_FD9_PRETRAFFIC_ZERO.md).
