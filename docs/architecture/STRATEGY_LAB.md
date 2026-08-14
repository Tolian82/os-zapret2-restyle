# Strategy Lab architecture and delivery plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How does the approved asynchronous Strategy Lab behave, and which product/lifecycle/stage contracts remain active?

Purpose:
Record the complete approved product, runtime, lifecycle, reporting, timeout, testing,
and delivery contract. Historical implementation sections are retained only as history
and never override current owner canon or current specialist architecture.

Updated when:
An approved Strategy Lab behavior, implementation boundary, patch boundary, message,
timeout, verification gate, or delivery order changes.

Read after:
`docs/ARCHITECTURE.md`.

Do not store here:
Unrelated plugin architecture or release history.

==================================================
STATUS AND AUTHORITY
==================================================

Status:
Initial architecture approved on 2026-08-04 and implemented. Search-policy portions were
amended on 2026-08-08 and subsequently implemented/evolved through the current Python,
adaptive-search and Model-C architecture.

This document remains the base product/lifecycle/stage authority. Current specialist
authorities are:

- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — current Stage-50/60 search semantics;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` — current parent-budget ownership;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — current Stage-60 runtime execution;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — implementation ownership/migration history.

**Model C is selected as the normal production Stage-60 direction. A/B/C production
model selection is closed.** Packaged source through `v0.4.1_12` still contains legacy
B/A automatic fallback, but that is implementation transition debt scheduled for
removal by `v0.4.1_13`, not an unresolved architecture choice.

The synchronous Blockcheck path has already been replaced. Historical initial-delivery
sections below are retained as engineering history and do not override current
`docs/PROJECT_PRINCIPLES.md`, `docs/START_HERE.md`, `docs/PROJECT_STATE.md`,
`docs/ROADMAP.md`, or current specialist architecture.

==================================================
OBJECTIVE
==================================================

Provide an asynchronous Strategy Lab that:

- tests a domain or IP target without interference from the user's active Zapret2
  service;
- reports online progress by numbered stages;
- isolates candidate effects and preserves deterministic candidate ownership;
- searches native Zapret2 candidates adaptively instead of making family acceptance a
  hard reachability gate;
- confirms stability before recommending a strategy;
- can be interrupted without losing completed results;
- always cleans temporary runtime state;
- restores the exact initial Zapret2 service state;
- reports concise English or Russian results according to the OPNsense language;
- finishes within bounded operation/stage/job budgets;
- supports extended TLS 1.2, HTTP and configured UDP while keeping QUIC limited to the
  fixed IPv4 UDP/443 capability/precheck and circular validation separate from discovery.

==================================================
NON-GOALS
==================================================

The work package does not:

- use classic zapret/nfqws1 strategy syntax as a search source or translation input;
- allow unqualified/unattributed simultaneous different-candidate traffic;
- run multiple permanent dvtws2 instances;
- replace the permanent Traffic Strategy automatically;
- merge a recommended profile into saved settings automatically;
- infer arbitrary service endpoints without an explicit contract;
- treat a global success percentage as sufficient when a required endpoint fails;
- reopen A/B/C model selection because historical experiment text remains in the repository.

==================================================
HIGH-LEVEL FLOW
==================================================

Diagnostics GUI
        ↓
start asynchronous Strategy Lab job
        ↓
return job_id immediately
        ↓
GUI polls read-only status and events
        ↓
acquire the shared lifecycle boundary
        ↓
record the exact initial Zapret2 state
        ↓
stop the normal Zapret2 runtime when it was running
        ↓
run capability and clean-baseline tests
        ↓
execute candidate probes under the selected Model-C runtime contract
        ↓
confirm stable candidates and form a shortlist
        ↓
clean every temporary process and rule
        ↓
restore the exact initial Zapret2 state
        ↓
publish complete or partial results

==================================================
DELIVERY AUTHORITY
==================================================

Strategy Lab changes follow the current repository-wide authority in
`docs/GITHUB_PUBLICATION.md` and the canonical principles in
`docs/PROJECT_PRINCIPLES.md`.

One logical scope uses one Ready PR and required latest-head checks; same-scope repairs
remain in that PR; `main` receives one squash commit. Independent analysis/documentation
may continue while unrelated GitHub processing runs, but unrelated source is never added
to the checked branch.

A stale test/documentation contract never overrides newer owner canon. When a contract
asserts a superseded decision, correct the stale contract rather than bending current
architecture back toward it.

==================================================
MANUAL VERIFICATION POLICY
==================================================

Current live verification is governed by
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`. Historical A/B/C and adaptive
search experiment plans are retained as evidence/history; they do not reopen current
Model-C selection.

Each source patch still requires:

- focused automated contract tests;
- syntax/static validation;
- standard pull-request CI;
- standard FreeBSD package qualification when applicable;
- synchronized documentation in the same logical change.

Owner-assisted evidence is requested only when behavior cannot be proved faithfully in
repository CI, such as FreeBSD/IPFW routing, real-provider results or timing on the
supported appliance.

==================================================
JOB MODEL
==================================================

The GUI uses an asynchronous job contract:

- start: validate input, create one job, return `job_id` immediately;
- status: read the current job state without mutating runtime;
- events: return/expose ordered progress records;
- cancel: request controlled interruption of the active job;
- result: return complete or partial stage results after mandatory cleanup.

Only one Strategy Lab job may be active. A second start request reports busy and does
not alter the active job.

The job continues if the Diagnostics page is refreshed or closed. Reopening the page
must discover the active job and resume status polling.

Recommended persistent runtime locations:

- `/var/run/zapret2-restyle/strategy-lab/` for active job state and control;
- `/var/log/zapret2/strategy-lab/` for detailed per-job logs;
- `status.json` for an atomically replaced current snapshot;
- `events.ndjson` for append-only ordered progress events.

State files never replace the lifecycle lock. They describe the job; they do not
serialize firewall or process mutation.

==================================================
LIFECYCLE OWNERSHIP
==================================================

The user's active Zapret2 service must not influence Strategy Lab results.

Before baseline or candidate testing, Strategy Lab must:

1. Enter the same exclusive lifecycle boundary used by normal Zapret2 mutations.
2. Classify the initial service state as exactly RUNNING or STOPPED.
3. Reject incomplete or unknown initial state before test runtime mutation.
4. Record the active dvtws2 identity, supervisor identity, plugin-owned firewall state,
   and active runtime identity needed for restoration verification.
5. When initially RUNNING, stop the normal service through its approved service path.
6. Verify that normal dvtws2, supervisor processes, and plugin-owned rules are absent.
7. When initially STOPPED, verify that no normal runtime remains active.

Every exit path performs cleanup and restoration:

- normal completion;
- no strategy found;
- operation timeout;
- stage timeout;
- overall timeout;
- user cancel;
- worker TERM or HUP;
- candidate start failure;
- probe failure;
- internal error.

Final-state contract:

- initial RUNNING becomes fully RUNNING again;
- initial STOPPED remains fully STOPPED;
- temporary dvtws2 processes and temporary rules are absent;
- restoration failure produces `RESTORE_FAILED` and is never reported as a normal
  completed or canceled result.

The cleanup and restoration stage cannot be canceled by the user.

==================================================
CANCEL CONTRACT
==================================================

The GUI provides a separate `Stop test` / `Прервать тест` control.

Cancel behavior:

1. Record a cancel request for the active `job_id`.
2. Stop or terminate the currently running probe within its bounded operation timeout.
3. Stop the temporary candidate dvtws2 when one exists.
4. Remove temporary candidate firewall rules and runtime files.
5. Preserve every result from stages completed before cancellation.
6. Mark the interrupted and all remaining unexecuted user-visible stages as skipped due
   to cancellation.
7. Execute the full cleanup and restoration stage.
8. Produce a partial report rather than an error.

Approved user-visible skipped messages:

Russian:
`SKIPPED — отменено`

English:
`SKIPPED — canseled`

The exact approved English spelling above is retained as the current product text.
Internal state keys may use conventional machine-readable spelling, but the displayed
message follows the approved text until the owner changes it.

==================================================
NUMBERED STAGES
==================================================

00 — Target initialization

- validate domain or IP input;
- normalize the target;
- register required endpoints;
- select standard or extended mode;
- create the job and initial stage table.

10 — Lifecycle lock and snapshot

- enter the shared lifecycle boundary;
- classify initial Zapret2 state;
- record runtime, process, supervisor, and firewall evidence required for restoration.

20 — Stop normal Zapret2

- stop the service when initially running;
- verify absence of normal dvtws2, supervisor, and plugin-owned rules;
- leave an initially stopped service stopped.

30 — Network capability precheck

- verify IPv4 control connectivity;
- determine whether usable IPv6 routing/connectivity exist;
- perform the fixed QUIC/IPv4 precheck;
- record IPv6/QUIC capability evidence; the adaptive target does not open a QUIC
  strategy-search branch.

40 — Clean target baseline

- resolve/pin required target addresses;
- test the target without Zapret2;
- determine whether direct TLS 1.3 already works;
- record results for every required endpoint.

50 — Low-cost TLS 1.3 reconnaissance

- run inexpensive native-Zapret2 seed candidates;
- record pass/fail evidence and technique/family tags;
- use evidence for Stage-60 ordering, never as a hard branch allowlist.

60 — Adaptive TLS 1.3 candidate search

- explore compatible native-Zapret2 neighbors/stronger branches according to current
  evidence, cost and remaining budget;
- permit stronger variants after a simple representative failed;
- stop expansion when enough strong candidates exist or the stage budget is exhausted;
- preserve all results already obtained;
- execute normal production candidate work under the selected Model-C runtime contract.

70 — Stability confirmation

- run sequential fresh-connection checks for the best candidates;
- require each required endpoint to pass 3 of 3 attempts;
- fail fast after the first attempt that makes 3/3 impossible;
- reject unstable candidates.

80 — Extended protocol testing

- TLS 1.2;
- plain HTTP;
- arbitrary UDP when a non-web UDP target is explicitly configured;
- additional approved URIs/endpoints.

The fixed IPv4 UDP/443 QUIC precheck remains Stage-30 diagnostic evidence only.

85 — Shortlist and recommendation

- normally select the best two to three stable candidates when available;
- rank by required-endpoint coverage, stability, simplicity and minimal traffic modification;
- recommend candidate number 1.

90 — Cleanup and exact restoration

- stop temporary probes/dvtws2;
- remove temporary rules/runtime state;
- restore RUNNING to RUNNING or STOPPED to STOPPED;
- verify processes, supervisor and firewall state.

99 — Final report

- construct complete/partial report only from recorded stage results;
- report restoration explicitly;
- never discard completed data because a later stage was canceled/timed out.

==================================================
STAGE AND JOB STATUSES
==================================================

User-visible stage statuses:

- `PASS` — stage completed and produced a valid result;
- `FAIL` — tested network condition/strategy failed;
- `TIMEOUT` — stage exhausted its budget;
- `SKIPPED` — not applicable/canceled before execution;
- `ERROR` — internal/infrastructure failure prevented a valid stage result.

A negative network result is `FAIL`, not `ERROR`. Model-C infrastructure/readiness/
attribution/rendering failure is not silently rewritten as candidate network FAIL.

Internal job outcomes may distinguish:

- `COMPLETED`;
- `PARTIAL`;
- `TIMEOUT`;
- `NO_STRATEGY`;
- `TARGET_ACCESSIBLE`;
- `RESTORE_FAILED`;
- `ERROR`.

Cancellation produces a partial normal result after restoration.

==================================================
ONLINE PROGRESS OUTPUT
==================================================

The GUI polls job state approximately once per second and shows useful current progress,
not only a spinner.

The snapshot may include:

- current stage number/name/status;
- current operation;
- active candidate and technique/family tags;
- candidate index/count;
- endpoint being checked;
- completed endpoint results;
- Stage-50 evidence / working candidate count;
- cancel requested state;
- cleanup/restoration state.

Detailed timing may be stored for diagnostics/timeout enforcement. The approved short
report does not display elapsed time.

==================================================
TARGET AND ENDPOINT MODEL
==================================================

Supported target types:

- domain;
- IP address for a protocol with explicit port/probe contract.

A domain job contains:

- one primary target;
- one or more explicitly defined required endpoints;
- no more than two different endpoints tested concurrently during screening;
- one selected candidate identity shared by those endpoint requests.

The system does not guess unrelated `www`, CDN, API or application hosts. Additional
endpoints are explicit inputs/approved built-in service definitions.

A candidate passes only when every required endpoint passes. Optional endpoints may add
information but cannot compensate for a failed required endpoint.

For a destination IP representing a TLS service, hostname/SNI remain explicit. A raw IP
URL must not silently replace service hostname identity.

==================================================
PROBE AND VALIDATION CONTRACT
==================================================

Web probes use explicit settings:

- explicit IPv4/IPv6 selection;
- exact TLS min/max version where relevant;
- HTTP/1.1 for primary search unless separately approved;
- bounded redirects;
- retry disabled;
- bounded connect/request timeout;
- fresh-connection guarantee;
- bounded response download;
- recorded exit status/remote address/protocol/status/size where supported.

No `-k` certificate bypass is used for Strategy Lab validation.

Current mass discovery uses bounded GET-4K, selected by the `_5/_6` measurement cycle.
HEAD/GET-1 did not justify a production change. Historical long-GET finalist proposals
are not automatic current requirements unless a current specialist contract selects them.

Stability confirmation remains sequential/fresh and fail-fast under its current contract.

Model C may execute multiple logical candidates through compatible physical segments,
but every probe must remain deterministically attributable to exactly one candidate.
See `docs/architecture/STRATEGY_LAB_MODEL_C.md`.

==================================================
FIXED QUIC PRECHECK
==================================================

The QUIC precheck is fixed and not configurable:

- control host: `yandex.ru`;
- port: `443`;
- IP family: IPv4;
- protocol: QUIC;
- ALPN: `h3`;
- timeout: 2 seconds;
- success determined only from command exit status.

The runtime does not:

- inspect output to override exit status;
- test OpenSSL `-quic` support before the precheck;
- search local PF/IPFW rules for UDP/443 blocking;
- repeat against another provider-selected host.

PASS/FAIL is capability evidence only and does not open an adaptive QUIC candidate-search branch.

==================================================
IPV6 POLICY
==================================================

AAAA records alone do not prove IPv6 availability.

IPv6 testing requires usable IPv6 routing and successful control connectivity. When unavailable:

- IPv6 target probes are skipped;
- IPv6 candidate strategies are skipped;
- IPv4 testing continues.

==================================================
DNS FACT BOUNDARY
==================================================

The historical local/container DNS problem is **closed**. DNS used to be slow/unreliable,
but the owner fixed it. Treat DNS as currently working.

Existing bounded DNS operation handling remains an implementation containment mechanism;
it is not evidence that DNS is currently broken. Reopen a DNS diagnosis only on fresh
direct reproducible evidence, not an old log, old timeout, historical document or new-chat
memory gap.

==================================================
TIMEOUT / BUDGET POLICY
==================================================

All operations remain bounded and preserve this containment hierarchy:

`operation/candidate work <= stage parent <= finite job parent`.

Current Stage-60/job parent-budget ownership is the implemented `eligible-work-v1` policy
documented in `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`. Admission uses remaining
absolute budget and cleanup/restoration remain bounded/mandatory.

Historical fixed numeric stage/job values and the `_31/_32` measurement plan are retained
in prior patch/decision/evidence records as implementation history; they do not override
the current adaptive-budget contract.

A previously observed admission concern involved the legacy `C -> B` fallback transition.
Do not optimize that transition instead of completing `_13`. After Model-C-only production
finalization, any Model-C-only timeout/deadline defect is a separate evidence-based task.

==================================================
LIVE MEASUREMENT HISTORY
==================================================

Historical owner-supplied OPNsense measurements established initial implementation bounds
and later measurement cycles refined Lua/BLOB/discovery/lifecycle behavior. Current accepted
conclusions are summarized in `docs/PROJECT_STATE.md` and specialist architecture.

The old DNS timing observations are historical only because DNS has since been fixed by the owner.

==================================================
STRATEGY SEARCH MODEL
==================================================

The search space uses native Zapret2 mechanisms. Technique/family tags may include:

- multisplit;
- multidisorder;
- seqovl;
- fake;
- fake plus split;
- syndata;
- hostfakesplit.

Stage 50 may test inexpensive representatives, but PASS/FAIL is only evidence. Stage 60
must not use accepted-family set as a reachability gate.

Adaptive exploration may cover:

- split positions;
- seqovl values;
- semantically compatible BLOB-free, built-in, inline and installed external resources;
- repeats;
- out-range;
- other native Zapret2 parameters represented by `CandidateSpec`.

Classic zapret/nfqws1/dvtws/winws examples are not used as candidate/translation input.
Community presets are ordering evidence, not proof for the current provider/target/path.
Known native/owner-proven strategies form a golden corpus for CandidateSpec/resource/graph
representability; historical success changes priority only, never removes graph reachability.

==================================================
CANDIDATE RUNTIME ISOLATION — MODEL C SELECTED
==================================================

Candidate effect must always be isolated and attributable.

A/B/C selection is closed:

- Model A — cold correctness/reference implementation;
- Model B — warm/reference implementation and legacy `_12` automatic fallback only;
- Model C — selected normal production Stage-60 runtime.

Current `_12` source still has `Model C -> Model B -> Model A cold` automatic replay. That
is transition debt, not architecture authority. `_13` removes B/A from the normal
production fallback chain.

Model C must preserve:

- exact candidate results/identity;
- deterministic source-port-qualified routing/attribution;
- no cross-candidate state leakage;
- logical planner batch identity even when physical profile-compatible segmentation is required;
- bounded cancellation/cleanup/restoration;
- current readiness proof.

Historical A/B/C experiment documentation is retained as evidence for how Model C was selected.
It cannot reopen the selection question.

==================================================
SCREENING, EXPANSION, AND STABILITY
==================================================

Reconnaissance:

- inexpensive native seeds produce candidate-local evidence;
- technique/family labels remain diagnostic metadata;
- rejected representative does not reject stronger related candidates.

Adaptive expansion:

- schedule graph neighbors according to cost/current evidence;
- simple success prioritizes nearby stable/simple variants;
- simple failure may open stronger compatible combinations;
- stop when enough strong candidates exist or budget is exhausted;
- preserve candidates found before budget exhaustion/cancellation.

Stability confirmation:

- sequential fresh connections;
- three attempts per required endpoint under the current stability contract;
- every required endpoint must pass required attempts;
- stop further attempts when required success becomes impossible;
- combined percentage never hides a failed required endpoint.

==================================================
SHORTLIST AND RANKING
==================================================

The normal target is up to three strong stable strategies when enough candidates exist.
A truthful smaller shortlist is valid.

Ranking order:

1. every required endpoint passes;
2. stability across repeated fresh connections;
3. no detected control/collateral regression;
4. simpler strategy structure;
5. minimal traffic modification;
6. lower fake/repeat requirements;
7. TTL/AutoTTL only when simpler strategies do not work;
8. complex multi-step chains only when required.

Strategy number 1 is the recommendation. Strategy Lab never overwrites/merges saved Traffic Strategy.

==================================================
EXTENDED MODE
==================================================

Extended branches may include:

- TLS 1.2;
- plain HTTP;
- approved URI paths;
- arbitrary UDP with explicit port/probe contract.

TLS 1.1 is outside normal interface unless separately approved. The fixed IPv4 UDP/443
QUIC precheck remains diagnostic evidence only. Generic UDP is never reported as QUIC.

==================================================
CIRCULAR LIVE VALIDATION
==================================================

Circular validation is a separate second-stage bounded lifecycle transaction.

It:

- receives eligible stable shortlist results;
- builds a temporary target-scoped profile;
- allows browser/application validation;
- provides its own Stop control;
- never modifies permanent Traffic Strategy;
- cleans temporary runtime and restores initial service state.

Circular validation and automated Strategy Lab jobs cannot run concurrently because they
share the lifecycle lock. Its eligibility/TTL behavior is controlled by the current
circular contract; historical discovery winner targets do not force Strategy Lab to
manufacture extra winners.

==================================================
BILINGUAL SHORT REPORT CONTRACT
==================================================

Language selection follows active OPNsense document language:

- English default/fallback for non-`ru*`;
- Russian when language begins with `ru`;
- no plugin-specific language selector.

Messages use stable keys with variable substitution. Approved examples follow.

Target:

EN:
`PASS — Target: telegram.org; type: domain; endpoints: telegram.org, web.telegram.org; mode: standard.`

RU:
`PASS — Цель: telegram.org; тип: домен; endpoints: telegram.org, web.telegram.org; режим: основной.`

Normal service stopped:

EN:
`PASS — The Zapret2 service has been stopped.`

RU:
`PASS — Служба Zapret2 остановлена.`

Network capability, restricted:

EN:
`PASS — IPv4 is available; IPv6 is unavailable; QUIC/IPv4 is blocked; IPv6 and QUIC tests have been excluded.`

RU:
`PASS — IPv4 доступен; IPv6 недоступен; QUIC/IPv4 закрыт; проверки IPv6 и QUIC исключены.`

Network capability, full:

EN:
`PASS — IPv4, IPv6, and QUIC/IPv4 are available.`

RU:
`PASS — IPv4, IPv6 и QUIC/IPv4 доступны.`

Clean baseline:

EN:
`PASS — DNS: OK; direct TLS 1.3 connection failed.`

RU:
`PASS — DNS: OK; прямое TLS 1.3-соединение не установлено.`

Rejected families:

EN:
`PASS — multisplit, multidisorder, and fake were rejected.`

RU:
`PASS — multisplit, multidisorder и fake были отклонены.`

Accepted families:

EN:
`PASS — multisplit, multidisorder, and fake were accepted.`

RU:
`PASS — multisplit, multidisorder и fake были приняты.`

Candidate expansion:

EN:
`PASS — Tested 18 variants across three working families; found 6 candidates that opened both endpoints.`

RU:
`PASS — Проверено 18 вариантов в трёх рабочих семействах; найдено 6 кандидатов, открывающих оба endpoints.`

Early expansion stop:

EN:
`PASS — Enough working candidates were found; further parameter testing was stopped.`

RU:
`PASS — Получено достаточно рабочих кандидатов; дальнейший перебор параметров остановлен.`

Stability passed:

EN:
`PASS — Three candidates passed stability testing: each endpoint was opened successfully 3 out of 3 times.`

RU:
`PASS — Три кандидата прошли проверку устойчивости: каждый endpoint успешно открыт 3 из 3 раз.`

Stability filtered:

EN:
`PASS — Three of 6 candidates confirmed stability; the remaining candidates produced unstable results.`

RU:
`PASS — Из 6 кандидатов три подтвердили устойчивость; остальные дали нестабильные результаты.`

Extended mode not requested:

EN:
`SKIPPED — Extended testing was not requested.`

RU:
`SKIPPED — Расширенное тестирование не запрашивалось.`

Extended web results:

EN:
`PASS — TLS 1.2 and HTTP were tested; 2 additional profiles were found. QUIC and IPv6 were skipped because they are unavailable.`

RU:
`PASS — TLS 1.2 и HTTP проверены; найдено 2 дополнительных профиля. QUIC и IPv6 пропущены как недоступные.`

UDP result:

EN:
`PASS — One working profile was found for the UDP target; QUIC profiles were not tested.`

RU:
`PASS — Для UDP-цели найден один рабочий профиль; QUIC-профили не проверялись.`

Shortlist:

EN:
`PASS — Three strategies were selected; strategy No. 1 is recommended because of its 3/3 stability and minimal traffic modification.`

RU:
`PASS — Выбраны 3 стратегии; №1 рекомендована из-за устойчивости 3/3 и минимального количества модификаций трафика.`

Restore running:

EN:
`PASS — Temporary processes and rules were removed; the original Zapret2 service was restarted and is fully operational.`

RU:
`PASS — Временные процессы и правила удалены; исходная служба Zapret2 снова запущена и полностью исправна.`

Restore stopped:

EN:
`PASS — Temporary processes and rules were removed; Zapret2 was left in its original stopped state.`

RU:
`PASS — Временные процессы и правила удалены; Zapret2 оставлен в исходном остановленном состоянии.`

Final result:

EN:
`COMPLETED — The target is blocked without bypass. Three stable strategies were found that open all required endpoints. Strategy No. 1 is recommended. The original Zapret2 state was restored.`

RU:
`COMPLETED — Цель заблокирована без обхода. Найдены 3 устойчивые стратегии, открывающие все обязательные endpoints. Рекомендована стратегия №1. Исходное состояние Zapret2 восстановлено.`

Cancellation skip:

EN:
`SKIPPED — canseled`

RU:
`SKIPPED — отменено`

Recommended message keys:

- `target_initialized`;
- `service_stopped`;
- `network_ipv4_only`;
- `network_full`;
- `baseline_tls_failed`;
- `families_rejected`;
- `families_accepted`;
- `candidates_found`;
- `candidate_limit_reached`;
- `stability_passed`;
- `stability_filtered`;
- `extended_skipped`;
- `extended_web_passed`;
- `udp_profile_found`;
- `shortlist_ready`;
- `service_restored_running`;
- `service_restored_stopped`;
- `test_completed`;
- `stage_canceled`.

==================================================
HISTORICAL INITIAL IMPLEMENTATION PATCH SERIES
==================================================

The original 13-patch implementation plan is retained in Git history and the prior
version of this document, plus patch/devlog records. It is complete and is **not** the
current roadmap. Its family-first, QUIC-search, serial-delivery and cold-candidate
assumptions do not override current Python/adaptive/Model-C architecture.

Current next source work is `v0.4.1_13` Model-C-only production finalization as defined in
`docs/START_HERE.md` and `docs/ROADMAP.md`.

==================================================
HISTORICAL VERIFICATION / ACCEPTANCE
==================================================

Historical implementation-series verification and acceptance are preserved in
`docs/verification/`, `docs/patches/`, `docs/devlog/`, decisions and Git history.

Current verification authority is the current live matrix, specialist architecture and
exact current patch acceptance in `docs/START_HERE.md`.
