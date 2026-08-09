# Strategy Lab architecture and delivery plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How will Diagnostics Blockcheck be replaced with the approved asynchronous Strategy Lab?

Purpose:
Record the complete approved product, runtime, lifecycle, reporting, timeout, testing,
and patch-delivery contract before implementation begins.

Updated when:
An approved Strategy Lab behavior, implementation boundary, patch boundary, message,
timeout, verification gate, or delivery order changes.

Read after:
`docs/ARCHITECTURE.md`.

Do not store here:
Unrelated plugin architecture, release history, or implementation results that belong
in the development log.

==================================================
STATUS AND AUTHORITY
==================================================

Status:
Initial architecture approved on 2026-08-04 and implemented. Search-policy portions were
amended on 2026-08-08 by
`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`.

This document remains the base product/lifecycle/stage authority. The current Python
ownership is defined by `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`; the approved
adaptive-search target, partially implemented through `_29`, is defined by
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`.

The synchronous Blockcheck path has already been replaced. Historical initial-delivery
sections below are retained as engineering history and do not override current
`docs/GITHUB_PUBLICATION.md`, `docs/ROADMAP.md`, or the later dated decisions.

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
- finishes the standard automated search within a bounded time budget;
- supports extended TLS 1.2, HTTP and configured UDP while keeping QUIC limited to the
  fixed IPv4 UDP/443 capability/precheck and circular validation separate from discovery.

==================================================
NON-GOALS
==================================================

The work package does not:

- use classic zapret/nfqws1 strategy syntax as a search source or translation input;
- assume that simultaneous different-strategy probes are useful before the dedicated
  OPNsense experiment proves isolation and value;
- run multiple permanent dvtws2 instances;
- replace the permanent Traffic Strategy automatically;
- merge a recommended profile into saved settings automatically;
- infer arbitrary service endpoints without an explicit contract;
- treat a global success percentage as sufficient when a required endpoint fails;
- perform owner-dependent manual OPNsense verification before all implementation
  patches have been published and processed by GitHub.

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
execute isolated candidate probes under the selected verified runtime model
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
`docs/GITHUB_PUBLICATION.md` and
`docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`.

The historical rule that required every prior patch to finish all post-merge GitHub
processing before any independent next-patch preparation is superseded. One logical
scope still uses one Ready PR and required latest-head checks; same-scope repairs remain
in that PR; `main` receives one squash commit. Independent analysis/documentation may
continue while unrelated GitHub processing runs, but unrelated source is never added to
the checked branch.

==================================================
MANUAL VERIFICATION POLICY FOR THIS SERIES
==================================================

The original implementation series used deferred consolidated owner verification. That
series is complete. Current live verification is governed by
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`; experimental warm/search
mechanisms are governed separately by
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Each source patch still requires:

- focused automated contract tests;
- syntax and static validation;
- standard pull-request CI;
- the standard FreeBSD package build performed by CI when applicable;
- documentation synchronized in the same logical commit.

Owner-assisted evidence is requested only when the behavior being selected cannot be
proved faithfully in repository CI, such as FreeBSD/IPFW routing, real provider results,
warm-worker state isolation or timing on the supported appliance.

==================================================
JOB MODEL
==================================================

The GUI uses an asynchronous job contract:

- start: validate input, create one job, return `job_id` immediately;
- status: read the current job state without mutating runtime;
- events: return or expose ordered progress records;
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
- determine whether usable IPv6 routing and connectivity exist;
- perform the fixed QUIC/IPv4 precheck;
- record IPv6 and QUIC capability evidence; the adaptive target does not open a QUIC
  strategy-search branch.

40 — Clean target baseline

- resolve required target addresses;
- test the target without Zapret2;
- determine whether direct TLS 1.3 already works;
- record results for every required endpoint.

50 — Low-cost TLS 1.3 reconnaissance

- run inexpensive native-Zapret2 seed candidates;
- record pass/fail evidence and technique/family tags;
- use the evidence for Stage-60 ordering, never as a hard branch allowlist.

60 — Adaptive TLS 1.3 candidate search

- explore compatible native-Zapret2 neighbors/stronger branches according to current
  evidence, cost and remaining budget;
- permit stronger variants after a simple representative failed;
- stop expansion when enough strong candidates exist or the stage budget is exhausted;
- preserve all results already obtained.

70 — Stability confirmation

- run sequential fresh-connection checks for the best candidates;
- require each required endpoint to pass 3 of 3 attempts;
- fail fast after the first attempt that makes 3/3 impossible;
- reject unstable candidates.

80 — Extended protocol testing

- TLS 1.2;
- plain HTTP;
- arbitrary UDP when a non-web UDP target is explicitly configured;
- additional approved URIs or endpoints.

The fixed IPv4 UDP/443 QUIC precheck remains Stage-30 diagnostic evidence only.

85 — Shortlist and recommendation

- normally select the best two to three stable candidates when available;
- rank by required-endpoint coverage, stability, simplicity, and minimal traffic
  modification;
- recommend candidate number 1.

90 — Cleanup and exact restoration

- stop temporary probes and temporary dvtws2;
- remove temporary rules and runtime state;
- restore RUNNING to RUNNING or STOPPED to STOPPED;
- verify processes, supervisor, and firewall state.

99 — Final report

- construct a complete or partial report only from recorded stage results;
- report the restoration result explicitly;
- never discard completed data because a later stage was canceled or timed out.

==================================================
STAGE AND JOB STATUSES
==================================================

User-visible stage statuses:

- `PASS` — the stage completed and produced a valid result;
- `FAIL` — the stage completed and the tested network condition or strategy failed;
- `TIMEOUT` — the stage started but exhausted its stage budget;
- `SKIPPED` — the stage was not applicable or was skipped because the test was canceled;
- `ERROR` — an internal implementation failure prevented a valid stage result.

A negative network result is `FAIL`, not `ERROR`.

Internal job outcomes may distinguish:

- `COMPLETED`;
- `PARTIAL`;
- `TIMEOUT`;
- `NO_STRATEGY`;
- `TARGET_ACCESSIBLE`;
- `RESTORE_FAILED`;
- `ERROR`.

Cancellation produces a partial normal result after restoration. The skipped stage rows
use the approved bilingual cancellation messages.

==================================================
ONLINE PROGRESS OUTPUT
==================================================

The GUI polls job state approximately once per second and shows useful current progress,
not only a spinner.

The current snapshot may include:

- current stage number and name;
- current stage status;
- current operation;
- active candidate and descriptive technique/family tags;
- candidate index and candidate count;
- endpoint currently being checked;
- completed endpoint results;
- Stage-50 reconnaissance evidence and number of working candidates;
- cancel requested state;
- cleanup and restoration state.

Detailed timing may be stored for diagnostics and timeout enforcement. The approved
short report does not display elapsed time.

==================================================
TARGET AND ENDPOINT MODEL
==================================================

Supported target types:

- domain;
- IP address for a protocol with an explicitly known port and probe contract.

A domain job contains:

- one primary target;
- one or more explicitly defined required endpoints;
- no more than two different endpoints tested concurrently during screening;
- one selected candidate identity shared by those concurrent endpoint requests.

The system does not guess unrelated `www`, CDN, API, or application hosts. Additional
endpoints are explicit inputs or approved built-in service definitions.

A candidate passes only when every required endpoint passes. Optional endpoints may add
information but cannot compensate for a failed required endpoint.

For a specific destination IP that represents a TLS service, hostname and SNI must
remain explicit. A raw IP URL must not silently replace the service hostname.

==================================================
PROBE AND VALIDATION CONTRACT
==================================================

All web probes use explicit settings:

- explicit IPv4 or IPv6 selection;
- exact TLS minimum and maximum version;
- HTTP/1.1 for the primary search unless a separate approved HTTP/2 check is added;
- bounded redirects;
- retry disabled;
- bounded connect timeout;
- bounded request timeout;
- `Connection: close` or an equivalent fresh-connection guarantee;
- bounded response download;
- recorded exit status, remote address, HTTP version, response status, and downloaded
  size where supported.

No `-k` certificate bypass is used for the Strategy Lab validation contract.

Mass discovery and finalist validation are different evidence levels. Discovery uses a
cheap bounded probe selected by measured agreement with final validation. It may avoid a
full response-body GET when the experiment proves that the cheaper signal is reliable
enough for ranking.

For stability confirmation, probes are sequential, use fresh connections and require
3/3 with fail-fast rejection.

The best two to three finalists receive a real bounded GET with a response target of at
least 16 KiB when the selected resource can supply it. A resource that completes normally
before 16 KiB makes the 16-KiB depth criterion `inconclusive`; it is never rewritten as a
16-KiB PASS. Connectivity/stability evidence remains separately classified.

Candidate runtime coexistence and simultaneous candidate probes are governed by the A/B/C
experiment plan. Even if several warm workers coexist, a probe must have exactly one
deterministically attributed candidate.

==================================================
FIXED QUIC PRECHECK
==================================================

The QUIC precheck is fixed and is not configurable:

- control host: `yandex.ru`;
- port: `443`;
- IP family: IPv4;
- protocol: QUIC;
- ALPN: `h3`;
- timeout: 2 seconds;
- success is determined only from the command exit status.

The runtime algorithm does not:

- inspect output to override the exit status;
- test whether OpenSSL supports `-quic` before running the precheck;
- search local PF/IPFW rules for UDP/443 blocking;
- repeat the control against another provider-selected host.

The result is recorded as the fixed IPv4 UDP/443 QUIC capability signal. PASS or FAIL does
not open an adaptive QUIC strategy-search branch. QUIC search is outside the approved
post-migration Strategy Lab search space.

==================================================
IPV6 POLICY
==================================================

AAAA DNS records alone do not prove IPv6 availability.

IPv6 testing requires usable IPv6 routing and a successful control connection. When
IPv6 is unavailable:

- IPv6 target probes are skipped;
- IPv6 candidate strategies are skipped;
- IPv4 testing continues normally.

The plugin does not attempt to create IPv6 service where the provider or OPNsense WAN
configuration supplies no usable IPv6 route.

==================================================
TIMEOUT POLICY
==================================================

The current source enforces bounded operations, stages and overall job budgets. The
adaptive redesign makes candidate cost an explicit containment level and reviews every
constant from telemetry:

1. Individual operation timeout.
2. Candidate envelope, including required cleanup.
3. Numbered stage timeout.
4. Overall standard or extended job budget.

Required hierarchy:

`operation deadline <= candidate deadline <= stage deadline <= job deadline`.

Current operation limits. The Stage-40 DNS limit was widened by corrective `_27` after
owner evidence showed valid local-Unbound answers taking 8–10 seconds:

- DNS query: 15 seconds;
- IPv6 route/capability inspection: 1 second;
- QUIC precheck: 2 seconds;
- TCP connect: 2 seconds;
- one TLS/HTTP probe: 3 seconds;
- temporary dvtws2 start: 3 seconds;
- temporary dvtws2 stop: 3 seconds;
- one complete candidate run including cleanup: 5 seconds;
- normal Zapret2 stop stage: 10 seconds;
- normal Zapret2 restore action: 45 seconds under the later corrective restoration
  contract.

Current stage budgets:

- 00: 2 seconds;
- 10: 3 seconds;
- 20: 10 seconds;
- 30: 6 seconds;
- 40: 20 seconds;
- 50: 45 seconds;
- 60: 60 seconds;
- 70: 60 seconds;
- 80: 120 seconds;
- 85: 3 seconds;
- 90: restoration is outside an exhausted search budget and uses its own bounded
  corrective lifecycle contract;
- 99: 2 seconds.

Overall budgets:

- standard automated test: 150 seconds;
- extended protocol test: an additional 120 seconds;
- circular live validation: separate user-controlled session with its own Stop control.

A new candidate must not start when the remaining stage or overall budget is
insufficient for its complete start, probes, stop, and cleanup sequence.

A stage timeout preserves completed results. Mandatory cleanup and restoration still
run after any timeout.

The numeric values above are implementation baselines, not permanent optimization
postulates. `_31` records per-phase timing and `_32` replaces inconsistent or inefficient
limits only after the measurement review defined in
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

==================================================
LIVE MEASUREMENT BASELINE
==================================================

Owner-supplied OPNsense measurements on 2026-08-04 established the initial timeout
basis:

- normal Zapret2 stop completed in approximately 2.06 seconds;
- normal Zapret2 start and full restoration completed in approximately 6.51 seconds;
- DNS A and AAAA lookups completed well below one second;
- direct TLS 1.3 to `yandex.ru` passed;
- direct TLS 1.3 to `telegram.org` and `web.telegram.org` reached the 2-second connect
  timeout;
- fixed QUIC/IPv4 precheck returned status 124 after the 2-second timeout;
- no IPv6 default route was present;
- IPv6 HTTPS control failed immediately;
- stopping Zapret2 removed dvtws2, supervisor, and plugin-owned IPFW rules;
- restarting Zapret2 restored the service and rule 19000.

These values define starting implementation limits. They are not a provider-wide
hardcoded blacklist. Runtime prechecks decide which branches apply on each system.

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
must not use the accepted-family set as a reachability gate.

Adaptive exploration may cover:

- split positions;
- seqovl values;
- semantically compatible BLOB-free, built-in, inline and installed external resources;
- repeats;
- out-range;
- other native Zapret2 parameters represented by `CandidateSpec`.

The search space contains Zapret2 semantics only. Classic zapret/nfqws1/dvtws/winws
examples are not used as candidate or translation input. Upstream Zapret2 `blockcheck2`
may inform search methodology without importing its POSIX-shell implementation.

Community presets are ordering evidence, not proof that a strategy works for the
current provider, target, Zapret2 version, or WAN path.

Known native/owner-proven Zapret2 strategies form a golden corpus that proves
`CandidateSpec` expressiveness, resource binding and graph reachability. Historical
success changes candidate priority only; it never removes a branch from the graph.

==================================================
CANDIDATE RUNTIME ISOLATION
==================================================

Candidate **effect** must always be isolated and attributable even if a future runtime
optimization keeps processes warm.

Model A remains the cold reference: build candidate runtime, start one dvtws2, install
target rules, probe, stop, clean and prove teardown before the next candidate.

Models B and C are experimental only:

- B — multiple isolated warm dvtws2 workers with distinct ownership;
- C — one compatible warm candidate bucket with deterministic dispatcher.

Warm coexistence does not imply simultaneous candidate probes. Before either model can
replace A for discovery it must match cold candidate results, prove exact traffic routing,
show no cross-candidate Lua/conntrack state leakage, and retain bounded cancellation/
cleanup/restoration. Finalists remain cold-reference verifiable.

Full experiment contract:
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

==================================================
SCREENING, EXPANSION, AND STABILITY
==================================================

Reconnaissance:

- inexpensive native seeds produce candidate-local evidence;
- technique/family labels remain diagnostic metadata;
- a rejected representative does not reject stronger related candidates.

Adaptive expansion:

- schedule graph neighbors according to cost and current evidence;
- simple success prioritizes nearby stable/simple variants;
- simple failure may open stronger compatible combinations;
- stop when enough strong candidates exist or budget is exhausted;
- preserve candidates found before budget exhaustion or cancellation.

Stability confirmation:

- sequential fresh connections;
- three attempts per required endpoint;
- every required endpoint must pass 3 of 3;
- stop further attempts after any failure makes 3/3 impossible;
- a combined percentage never hides a failed required endpoint.

==================================================
SHORTLIST AND RANKING
==================================================

The normal adaptive-search target is two to three strong stable strategies when enough
candidates are available. A truthful smaller shortlist is allowed when fewer candidates
survive the evidence/budget gates.

Ranking order:

1. Every required endpoint passes.
2. Stability across repeated fresh connections.
3. No detected control-endpoint or collateral regression.
4. Simpler strategy structure.
5. Minimal traffic modification.
6. Lower fake and repeat requirements.
7. TTL or AutoTTL techniques only when simpler strategies do not work.
8. Complex multi-step chains only when required.

Strategy number 1 is the recommended candidate.

The report returns exact candidate text for review. It does not overwrite or merge the
saved Traffic Strategy.

==================================================
EXTENDED MODE
==================================================

Extended testing is separate from the standard TLS 1.3 search and uses its own 120
second budget.

Approved branches:

- TLS 1.2;
- plain HTTP;
- additional approved URI paths;
- arbitrary UDP for a target with an explicit port and probe contract.

TLS 1.1 is outside the normal interface and may only be introduced later as a hidden
legacy diagnostic with a separate decision.

The fixed IPv4 UDP/443 QUIC precheck remains diagnostic capability evidence only. A
generic UDP result must not be reported as a QUIC result.

==================================================
CIRCULAR LIVE VALIDATION
==================================================

Circular validation is a later second-stage feature, not the primary automated search.

It:

- receives a shortlist of three to five stable strategies;
- builds a temporary target-scoped circular profile;
- allows browser or application testing against the real client flow;
- provides its own Stop control;
- does not modify permanent Traffic Strategy settings;
- cleans temporary runtime and restores the initial normal service state.

The existing circular three-to-five eligibility contract is separate from the adaptive
search early-stop target and must not force discovery to manufacture five winners. Any
future circular eligibility change requires its own decision.

Automatic permanent profile merge is outside this work package unless approved in a
later decision.

==================================================
BILINGUAL SHORT REPORT CONTRACT
==================================================

Language selection follows the active OPNsense document language:

- English is the default for every language other than `ru*` and for fallback;
- Russian is used when the document language begins with `ru`;
- the plugin adds no language selector.

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

The following 13-patch plan is retained only to explain how the original asynchronous
Strategy Lab was delivered. It is complete and is **not** the current implementation
roadmap. Its family-first, QUIC-search, serial-delivery and one-cold-candidate assumptions
do not override the 2026-08-08 adaptive-search decision or current GitHub delivery
authority. Current next source work is `_30`–`_33` in `docs/ROADMAP.md`.

Patch 1 — Documentation and approved architecture

- documentation only;
- no source, package, VERSION, or PLUGIN_REVISION change;
- add this specialist architecture document;
- add the Strategy Lab decision, audit, and planning devlog records;
- update current project state and roadmap;
- record the serial GitHub processing gate and deferred manual verification policy.

Patch 2 — Asynchronous job and GUI shell

Planned files:

- `strategy_lab_launcher.sh`;
- `strategy_lab_worker.sh`;
- `strategy_lab/common.sh`;
- `strategy_lab/state.sh`;
- Diagnostics API start/status/cancel actions;
- Diagnostics GUI polling, progress area, and Stop test button;
- focused job-contract and bilingual-output tests.

No real network or Zapret2 runtime mutation is introduced in this patch.

Patch 3 — Lifecycle stop, cleanup, and restoration

Planned files:

- `strategy_lab_transaction.sh`;
- `strategy_lab/lifecycle.sh`;
- shared lifecycle helpers when extraction is required;
- focused RUNNING, STOPPED, cancel, signal, and restore contract tests.

Implements stages 10, 20, and 90.

Patch 4 — Targets, capability precheck, and clean baseline

Planned files:

- `strategy_lab/target.sh`;
- `strategy_lab/probe.sh`;
- `strategy_lab/request.sh`;
- `strategy_lab/result.sh`;
- focused precheck and baseline tests.

Implements stages 00, 30, and 40.

Patch 5 — One isolated temporary candidate runtime

Planned files:

- `strategy_lab/runtime.sh`;
- `strategy_lab/firewall.sh`;
- `strategy_lab/candidate.sh`;
- focused candidate runtime and teardown tests.

Runs one fixture candidate only and establishes process/firewall isolation.

Patch 6 — TLS 1.3 family screening

Planned files:

- `strategy_lab/catalog/tls13-families.conf`;
- `strategy_lab/catalog/tls13-screening.conf`;
- `strategy_lab/screening.sh`;
- focused family-screening tests.

Implements stage 50.

Patch 7 — Accepted-family parameter expansion

Planned files:

- `strategy_lab/catalog/tls13-candidates.conf`;
- `strategy_lab/expansion.sh`;
- focused expansion, budget, and early-stop tests.

Implements stage 60.

Patch 8 — Stability, shortlist, and report

Planned files:

- `strategy_lab/verify.sh`;
- `strategy_lab/score.sh`;
- `strategy_lab/report.sh`;
- focused 3/3 stability, ranking, partial result, and bilingual report tests.

Implements stages 70, 85, and 99.

Patch 9 — Extended TLS 1.2 and HTTP

Planned files:

- `strategy_lab/catalog/tls12-candidates.conf`;
- `strategy_lab/catalog/http-candidates.conf`;
- `strategy_lab/extended_web.sh`;
- focused extended web tests.

Implements the TLS 1.2 and HTTP branches of stage 80.

Patch 10 — QUIC strategy branch

Planned files:

- `strategy_lab/catalog/quic-candidates.conf`;
- `strategy_lab/quic.sh`;
- focused precheck gate and QUIC candidate tests.

Runs only after a successful fixed QUIC precheck.

Patch 11 — Arbitrary UDP strategy branch

Planned files:

- `strategy_lab/catalog/udp-candidates.conf`;
- `strategy_lab/udp.sh`;
- focused UDP target and report tests.

Keeps arbitrary UDP separate from QUIC.

Patch 12 — Temporary circular live validation

Planned files:

- `strategy_lab/circular.sh`;
- GUI circular start/status/stop controls;
- focused temporary profile, scope, cleanup, and restoration tests.

Does not modify permanent Traffic Strategy.

Patch 13 — Final replacement of synchronous Blockcheck

Planned scope:

- remove the long synchronous configd action;
- remove PHP and browser long-request timeouts;
- remove the old textual SUMMARY parser;
- remove old direct PF/IPFW manipulation from `blockcheck.sh`;
- remove `blockcheck.sh` or retain only a minimal asynchronous CLI adapter;
- route every GUI caller through start/status/cancel/result;
- update and close DIAG-001 only after automated implementation completion;
- prepare the consolidated owner-assisted OPNsense verification matrix.

==================================================
HISTORICAL POST-PATCH-13 VERIFICATION PLAN
==================================================

This list records the original consolidated test plan. Current owner-assisted verification
is governed by `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`; adaptive-search
runtime theories use `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

After every patch has passed the serial GitHub gate, one consolidated live test covers:

- standard domain test while normal Zapret2 is initially running;
- standard domain test while normal Zapret2 is initially stopped;
- active online progress and page refresh recovery;
- user cancellation during baseline, family screening, expansion, and stability;
- exact skipped cancellation output in English and Russian;
- operation, stage, and overall timeout paths;
- IPv4-only and usable-IPv6 systems when available;
- fixed QUIC precheck pass and fail paths when environments are available;
- one and two required endpoints;
- accepted and rejected strategy families;
- parameter expansion early stop;
- 3/3 stability filtering;
- shortlist ranking and exact strategy output;
- extended TLS 1.2 and HTTP;
- QUIC branch where available;
- arbitrary UDP target;
- circular start and stop;
- cleanup after normal completion, failure, timeout, cancel, and signal;
- exact RUNNING-to-RUNNING and STOPPED-to-STOPPED restoration;
- explicit `RESTORE_FAILED` injection test;
- absence of temporary processes, rules, files, and locks after every job;
- final removal of the old synchronous caller chain.

==================================================
HISTORICAL INITIAL WORK-PACKAGE ACCEPTANCE
==================================================

These were the original replacement-series criteria and are retained as historical
delivery evidence. They are not active search-policy postulates after the later Python
migration and adaptive-search decisions.

The original criteria were:

- all 13 patches have individually passed the serial GitHub delivery gate;
- every approved stage and message contract is implemented;
- one active strategy at a time is guaranteed;
- cancellation returns partial results with skipped remaining stages;
- standard testing remains within the approved overall budget;
- cleanup and exact service-state restoration are verified;
- all automated tests and CI builds pass;
- the consolidated owner-assisted verification passes;
- the old synchronous Blockcheck execution path is absent or reduced to an approved
  asynchronous compatibility adapter;
- documentation, audit state, development history, and user guidance are synchronized.
