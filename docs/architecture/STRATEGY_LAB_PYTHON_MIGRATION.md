# Strategy Lab — Python and native-adapter ownership

**Status:** CURRENT OWNERSHIP CONTRACT. The historical filename is retained for existing references; the migration execution series is completed and archived. The current browser and dual-stack contracts supersede older IPv4/client assumptions below.

## Current component flow

```text
Diagnostics GUI / JavaScript
        ↓  validates persisted job snapshots; retries transient reads
OPNsense PHP MVC/API
        ↓  request validation + transient transport classification
configd action
        ↓
strategy_lab_launcher.sh / short launcher lock
        ↓  background daemon closes launcher FD 9
zapret_service.sh / shared lifecycle lock
        ↓
strategy_lab_worker.sh
        ↓
Python strategy_lab_py/orchestrator.py
        ├─ state.py
        ├─ request.py / probe.py
        ├─ candidate.py / candidate_spec.py / resources.py / family.py
        ├─ search.py / extended.py
        └─ result.py
             ↓
        narrow shell system adapters
             ↓
FreeBSD/OPNsense: dvtws2, ipfw, process/file observations, service lifecycle
```

PHP remains responsible for HTTP/API validation and bounded configd invocation. JavaScript
owns presentation only. Neither layer may derive automated backend truth independently of
the persisted Python-owned job snapshot.

## Python runtime contract

Migration Patch 1 established:

- OPNsense 26.7 / FreeBSD 15 target;
- Python exactly 3.13;
- plugin dependency `python313` mapped to `lang/python313`;
- OPNsense-owned `/usr/local/bin/python3` production interpreter boundary;
- standard-library-only migration code;
- packaged `.py` sources under `src/opnsense/`.

FreeBSD CI invokes `/usr/local/bin/python3.13` explicitly.

## Authoritative automated ownership

Patch 2 — `strategy_lab_py/state.py`

- sole automated `status.json` / `events.ndjson` mutation owner;
- schema/revision/progress/stage/result/lifecycle/circular-eligibility persistence;
- atomic revisioned writes and stale reconciliation.

Private circular-session `state.json` remains deliberately shell-owned.

Patch 3 — `strategy_lab_py/orchestrator.py`

- stage order `00,10,20,30,40,50,60,70,80,85,90,99`;
- Standard/Extended wall-clock budgets;
- cancellation/signals/adapter process-group termination;
- mandatory Stage 90 restoration and Stage 99 convergence;
- terminal state/outcome/report policy;
- restoration-failure override.

Patch 4 — `strategy_lab_py/request.py` and `probe.py`

- finite DNS/TLS/HTTP/TCP/QUIC-control request execution;
- distinct stdout/stderr/return-code/timeout/termination evidence;
- DNS ANSWER-section-aware A/AAAA parsing;
- Stage 30/40 network/baseline execution and public result compatibility.

Patch 5 — `strategy_lab_py/candidate.py` and `family.py`

- endpoint binding through the shared DNS parser;
- candidate runtime/readiness/fatal-log/interception policy;
- exact remote-IP and IPFW counter-growth evidence;
- ordered Stage-50 TLS 1.3 family screening and per-candidate timeout/cancellation.

Adaptive-search `_29` extends this owner with `strategy_lab_py/candidate_spec.py` and
`resources.py`: immutable normalized candidate evidence, one job-scoped installed
resource snapshot, exact candidate-minimal Lua/BLOB/range rendering and persisted
resource/spec identity. It does not change the fixed catalog or search graph.

Adaptive-search `_30` adds `strategy_lab_py/search_graph.py`: a validated seven-seed/
sixteen-node native Zapret2 DAG, semantic resource eligibility, exact golden candidates,
candidate-defined ranges and persisted planning/node evidence. Active Stage 50/60 no
longer obtains policy from flat TSV catalogs.

Patch 6 — `strategy_lab_py/search.py` and `extended.py`

- current `_31` Stage-60 graph exploration chooses one reachable node after every live
  PASS/FAIL while Stage-50 evidence remains priority rather than a reachability gate;
- every candidate and extended path verifies the fixed Stage-40 search-epoch identity;
- Stage-70 source de-duplication/ranking/three-attempt stability replay;
- Stage-80 TLS 1.2/HTTP/QUIC/generic-UDP orchestration;
- one generalized candidate lifecycle across supported protocols;
- exact-endpoint QUIC and generic-UDP request execution through the request owner.

The accepted-family gate was part of the completed migration baseline and is superseded
by `_28`. The current QUIC candidate-search branch remains pre-redesign behavior; the
later adaptive target keeps only the fixed IPv4 UDP/443 QUIC precheck and concentrates
search on native Zapret2 TCP/TLS plus the approved non-QUIC extended branches.

Patch 7 — `strategy_lab_py/result.py`

- complete user-ready profile construction and validation;
- deterministic final source collection/ranking;
- exact three-attempt replay of the complete published profile;
- Standard and Extended unified shortlist selection;
- recommendation and TLS 1.3 circular subset publication;
- automated-job circular eligibility after verified restoration.

Final replay reuses `candidate.py`; there is no second candidate state machine.

## Remaining shell responsibilities

Shell remains authoritative only for deliberate boundaries such as:

- public service lifecycle entry points and shared lifecycle lock ownership;
- audited FreeBSD dvtws2/IPFW/process/file mutations and observations behind explicit
  adapters;
- short compatibility launch wrappers;
- private circular-session ownership/state and immutable-parent consumption.

The replay-specific `strategy_lab_profile_candidate_adapter.sh` is a system adapter, not a
result/search owner. Python replaces the validated static selector with the temporary
runtime hostlist and writes the exact argument file; the profile adapter only delegates
system actions to the canonical candidate adapter.

Patch 7 physically retired these competing automated owners:

- `strategy_lab_profile_replay_runner.sh`;
- `strategy_lab/worker_result.sh`;
- `strategy_lab/worker_stage_machine.sh`.

Some older helper modules may remain where compatibility/system/private-circular code still
sources them. Presence does not make them authoritative and no production path may delegate
Python-owned policy back to them.

## GUI / status ownership

The automated launcher serializes short launcher operations with a nonblocking lock on FD
9. Before `_25`, `start_job()` launched the long-lived background lifecycle process through
`daemon(8)` without closing that descriptor. The private circular launcher already closed
FD 9 correctly.

Patch 8 requires the automated daemon launch to close FD 9 before the worker starts. The
short start transaction remains serialized, but the background worker must not inherit the
launcher lock that status/result/cancel requests need.

Transport/read status is separate from job state:

- empty or invalid configd output is reported by PHP as `status:"error"` plus
  `transient:true`;
- AJAX/network failures use the same transient marker;
- a browser job snapshot is accepted only with a valid `job.*` ID and persisted state
  `queued`, `running`, `cancel_requested`, `completed`, or `error`;
- visible job state is derived only from `data.state`;
- `data.status` is transport/API metadata and must never be used as fallback job state;
- a transient read preserves the last valid rendered state/progress and schedules a retry;
- accepted start may render the known accepted job as queued Stage 00 until the first
  persisted snapshot arrives;
- persisted Python `progress.percent` is authoritative; the stage-to-percent map remains
  compatibility fallback only;
- initial Diagnostics discovery retries transient reads, resumes an actual active snapshot,
  and treats explicit `{status:"idle"}` as idle without resurrecting terminal history;
- private circular presentation also preserves its last valid state across transient/busy
  reads.

This reconciliation changes presentation/read semantics only. It does not create another
state writer or backend owner.

## Persistence / result compatibility

Evidence locations remain stable:

- `/var/run/zapret2-restyle/strategy-lab/`;
- `/var/log/zapret2/strategy-lab/`;
- per-job `status.json`;
- `events.ndjson`;
- stage/candidate/search/final evidence files required by public contracts.

Patch 7 preserves the unified shortlist contract while making Python its publisher:

- `count` and `items` for the public shortlist;
- deterministic `recommendation`;
- `circular_count` and `circular_items` as replay-verified TLS 1.3 subset;
- complete user-ready `profile` plus structured replay evidence.

Patch 8 does not alter these persistence or result schemas. It makes Diagnostics consume
them consistently.

## Profile / final replay contract

Supported final protocol profiles:

- TLS 1.3 — TCP/443, TLS L7;
- TLS 1.2 — TCP/443, TLS L7;
- HTTP — TCP/80, HTTP L7;
- QUIC — UDP/443, QUIC L7 in the current `_31` implementation only; the approved
  adaptive-search target removes QUIC candidate search and retains only the fixed precheck;
- generic UDP — validated configured port, no L7 filter, validated job-local payload.

In the current `_31` implementation each published profile contains one transport filter,
optional protocol L7 filter, one validated target selector, the candidate's optional
input/output range data, and the candidate desynchronization fragment. `-d8`, `-d10` and
absence are preserved exactly rather than inserted by shell. Runtime-only arguments,
nested selectors/filters,
placeholders and `--new` are rejected.

The adaptive-search target explicitly supersedes fixed `-d10`: `out-range` becomes
optional candidate data represented by `CandidateSpec`, and final profile replay must
preserve the exact range (or absence of range) that was actually tested.

Each final source is replayed exactly three times. A shortlist entry is accepted only when
all three attempts pass and each replay proves the exact complete published profile was
used.

## Stage / budget / cancellation contract

Production stage order remains:

`00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99`.

Python owns the Standard 150-second budget, Extended +120-second budget, stage/operation
ceilings, Stage-80 shared deadline, typed timeout handling and cancellation process-group
termination.

Terminal mapping remains:

- `ERROR`, `TIMEOUT`, `RESTORE_FAILED` => state `error`, report FAIL;
- `SUCCESS`, `NO_CANDIDATE`, `TARGET_ACCESSIBLE`, `PARTIAL` => state `completed`, report PASS;
- restoration failure overrides the prior outcome.

Automated circular eligibility is evaluated only after Stage 90 restoration evidence and
before the terminal snapshot is published.

## Lifecycle safety

Mandatory invariants:

1. Snapshot exact initial Zapret2 state before mutation.
2. Use the shared lifecycle ownership boundary.
3. Stop normal runtime only through approved lifecycle paths.
4. Keep candidate identity, traffic effects and evidence deterministically isolated.
5. Keep temporary firewall/divert ownership isolated.
6. The cold reference cleans candidate runtime between candidates. Current Model-C
   production reuses a job-owned worker only within the selected compatible physical
   segment, preserving deterministic attribution, bounded cleanup and no state leakage;
   the closed A/B/C experiment is not a new implementation gate.
7. Execute Stage 90 on normal completion, timeout, cancel, signal or internal error.
8. Restore initial RUNNING to healthy RUNNING and initial STOPPED to STOPPED.
9. Never hide restoration failure behind a successful result.
10. Saved Traffic Strategy remains immutable.
11. Final profile replay uses the same unified candidate readiness/interception/cleanup owner.
12. Private circular sessions cannot mutate the parent automated result.
13. Long-lived automated or circular workers must not inherit short launcher serialization locks.


## Completed migration and proof

The serial migration/cutover/backlog/qualification sequence is historical. Current callers retain one Python automated owner and narrow native system adapters; [PROJECT_STATE](../PROJECT_STATE.md) owns current progress. The [full former migration document](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md) retains the implementation sequence and old live boundaries.
