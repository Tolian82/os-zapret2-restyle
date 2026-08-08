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
Approved for implementation by the project owner on 2026-08-04.

This document is the specialist authority for the Strategy Lab work package. The first
patch records the full design only. Later patches must implement this contract in the
order recorded here and in `docs/ROADMAP.md`.

The existing synchronous Blockcheck implementation remains active until the replacement
has passed all implementation patches. It is removed only in the final replacement
patch after every new caller and runtime path exists.

==================================================
OBJECTIVE
==================================================

Replace the current synchronous Blockcheck wrapper with an asynchronous Strategy Lab
that:

- tests a domain or IP target without interference from the user's active Zapret2
  service;
- reports online progress by numbered stages;
- runs only one candidate strategy at a time;
- searches Zapret2 strategy families before expanding parameters;
- confirms stability before recommending a strategy;
- can be interrupted without losing completed results;
- always cleans temporary runtime state;
- restores the exact initial Zapret2 service state;
- reports concise English or Russian results according to the OPNsense language;
- finishes the standard automated search within a bounded time budget;
- supports later extended TLS 1.2, HTTP, QUIC, UDP, and circular validation.

==================================================
NON-GOALS
==================================================

The work package does not:

- mix classic zapret syntax with Zapret2 syntax;
- run several different strategies concurrently;
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
run one temporary candidate strategy at a time
        ↓
confirm stable candidates and form a shortlist
        ↓
clean every temporary process and rule
        ↓
restore the exact initial Zapret2 state
        ↓
publish complete or partial results

==================================================
SERIAL PATCH DELIVERY GATE
==================================================

The Strategy Lab series is strictly sequential.

The next patch must not be prepared, published, or partially staged until the previous
patch has completed every GitHub operation and has been verified as correctly
published.

The gate for patch N is complete only when all of the following are true:

1. The final atomic commit for patch N is published through exactly one task branch.
2. The ready pull request contains only the approved logical scope.
3. Every pull-request check has completed successfully.
4. The pull request has been squash merged once.
5. The resulting `main` commit has been verified.
6. Every workflow triggered by the new `main` commit has completed successfully.
7. Automatic task-branch cleanup has completed.
8. The exact task branch has been verified absent.
9. No unresolved GitHub processing or failed required check remains for patch N.

Only after all nine conditions are satisfied may preparation of patch N+1 begin.

A failed delivery cycle is handled under `docs/GITHUB_PUBLICATION.md`: close the PR,
delete and verify absence of the task branch, reconcile against current `main`, and
begin one clean replacement cycle. Never prepare a later Strategy Lab patch on top of
an incomplete or failed earlier patch.

==================================================
MANUAL VERIFICATION POLICY FOR THIS SERIES
==================================================

All manual checks that require project-owner participation are deferred until every
Strategy Lab implementation patch has been published, merged, cleaned up, and fully
processed by GitHub.

Each individual patch still requires:

- focused automated contract tests;
- syntax and static validation;
- standard pull-request CI;
- the standard FreeBSD package build performed by CI when applicable;
- post-merge `main` workflow completion;
- documentation synchronized in the same logical commit.

After the final replacement patch, one consolidated owner-assisted OPNsense verification
matrix validates the complete end-to-end feature. No intermediate patch may request
manual commands or live evidence from the project owner unless a newly discovered
safety blocker makes further implementation impossible without that evidence.

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
- enable or exclude IPv6 and QUIC test branches.

40 — Clean target baseline

- resolve required target addresses;
- test the target without Zapret2;
- determine whether direct TLS 1.3 already works;
- record results for every required endpoint.

50 — Strategy-family screening

- run one representative candidate from each approved TLS 1.3 family;
- run different families strictly sequentially;
- accept or reject each family using all required endpoints.

60 — Accepted-family parameter expansion

- expand parameters only inside accepted families;
- stop expansion when enough useful candidates exist or the stage budget is exhausted;
- preserve all results already obtained.

70 — Stability confirmation

- run sequential fresh-connection checks for the best candidates;
- require each required endpoint to pass 3 of 3 attempts;
- reject unstable candidates.

80 — Extended protocol testing

- TLS 1.2;
- plain HTTP;
- QUIC when the fixed QUIC precheck passed;
- arbitrary UDP when a non-web UDP target is explicitly configured;
- additional approved URIs or endpoints.

85 — Shortlist and recommendation

- select three to five stable candidates when available;
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
- active strategy family;
- candidate index and candidate count;
- endpoint currently being checked;
- completed endpoint results;
- number of accepted and rejected families;
- number of working candidates;
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
- one active candidate strategy shared by those concurrent endpoint requests.

The system does not guess unrelated `www`, CDN, API, or application hosts. Additional
endpoints are explicit inputs or approved built-in service definitions.

A candidate passes only when every required endpoint passes. Optional endpoints may add
information but cannot compensate for a failed required endpoint.

For a specific destination IP that represents a TLS service, hostname and SNI must
remain explicit. A raw IP URL must not silently replace the service hostname.

==================================================
PROBE CONTRACT
==================================================

The main web probe uses explicit settings:

- explicit IPv4 or IPv6 selection;
- exact TLS minimum and maximum version;
- HTTP/1.1 for the primary search unless a separate approved HTTP/2 check is added;
- GET rather than HEAD;
- bounded redirects;
- retry disabled;
- bounded connect timeout;
- bounded request timeout;
- `Connection: close` or an equivalent fresh-connection guarantee;
- bounded response download;
- recorded exit status, remote address, HTTP version, response status, and downloaded
  size where supported.

No `-k` certificate bypass is used for the Strategy Lab validation contract.

For screening, up to two different endpoints may be probed concurrently under the same
candidate. Different candidate strategies are never active concurrently.

For stability confirmation, probes are sequential and use fresh connections.

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

When the IPv4 QUIC precheck fails:

- QUIC/IPv4 is classified as closed;
- QUIC/IPv6 is skipped;
- every QUIC strategy test is skipped.

When the IPv4 QUIC precheck passes and usable IPv6 is available, QUIC/IPv6 may be tested
as an extended branch.

==================================================
IPV6 POLICY
==================================================

AAAA DNS records alone do not prove IPv6 availability.

IPv6 testing requires usable IPv6 routing and a successful control connection. When
IPv6 is unavailable:

- IPv6 target probes are skipped;
- IPv6 candidate strategies are skipped;
- IPv6 QUIC is skipped;
- IPv4 testing continues normally.

The plugin does not attempt to create IPv6 service where the provider or OPNsense WAN
configuration supplies no usable IPv6 route.

==================================================
TIMEOUT POLICY
==================================================

Timeouts are enforced at three levels:

1. Individual operation timeout.
2. Numbered stage timeout.
3. Overall standard or extended job budget.

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
- normal Zapret2 restore stage: 15 seconds.

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
- 90: 15 seconds;
- 99: 2 seconds.

Overall budgets:

- standard automated test: 150 seconds;
- extended protocol test: an additional 120 seconds;
- circular live validation: separate user-controlled session with its own Stop control.

A new candidate must not start when the remaining stage or overall budget is
insufficient for its complete start, probes, stop, and cleanup sequence.

A stage timeout preserves completed results. Mandatory cleanup and restoration still
run after any timeout.

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

The TLS 1.3 family tree begins with:

- multisplit;
- multidisorder;
- seqovl;
- fake;
- fake plus split;
- syndata;
- hostfakesplit.

Stage 50 tests one representative candidate from each family.

Stage 60 expands only families accepted by all required endpoints. Parameter expansion
may cover:

- split positions;
- seqovl values;
- approved BLOB resources;
- repeats;
- out-range;
- other family-specific Zapret2 parameters documented by the candidate catalog.

The catalog contains Zapret2 syntax only. Classic zapret/nfqws examples may inform
selection concepts but are never copied as Zapret2 candidates without translation and
validation.

Community presets are ordering evidence, not proof that a strategy works for the
current provider, target, Zapret2 version, or WAN path.

==================================================
CANDIDATE RUNTIME ISOLATION
==================================================

For each candidate:

1. Build a temporary candidate-specific runtime.
2. Start exactly one temporary dvtws2.
3. Install only the temporary candidate rules required for the target.
4. Run up to two required endpoints using that same active strategy.
5. Record all probe results.
6. Stop the temporary dvtws2.
7. Remove temporary rules and temporary runtime state.
8. Verify full teardown before starting the next candidate.

No candidate may reuse stale processes or rules from the preceding candidate.

Failure to clean one candidate stops further strategy testing and proceeds to mandatory
restoration.

==================================================
SCREENING, EXPANSION, AND STABILITY
==================================================

Family screening:

- one representative per approved family;
- families strictly sequential;
- all required endpoints must pass;
- accepted and rejected families are recorded explicitly.

Parameter expansion:

- accepted families only;
- stop when enough useful candidates have been found;
- initial useful-candidate target: approximately six before stability confirmation;
- preserve candidates found before budget exhaustion or cancellation.

Stability confirmation:

- sequential fresh connections;
- three attempts per required endpoint;
- every required endpoint must pass 3 of 3;
- optionally perform 5 of 5 for finalists only when the remaining budget permits;
- a combined percentage never hides a failed required endpoint.

==================================================
SHORTLIST AND RANKING
==================================================

The final shortlist contains three to five stable strategies when enough candidates are
available.

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
- QUIC/HTTP3 only after the fixed QUIC precheck passes;
- arbitrary UDP for a target with an explicit port and probe contract.

TLS 1.1 is outside the normal interface and may only be introduced later as a hidden
legacy diagnostic with a separate decision.

QUIC and arbitrary UDP are separate target types. A generic UDP result must not be
reported as a QUIC result.

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
IMPLEMENTATION PATCH SERIES
==================================================

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
FINAL OWNER-ASSISTED VERIFICATION AFTER PATCH 13
==================================================

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
ACCEPTANCE CRITERIA FOR THE COMPLETE WORK PACKAGE
==================================================

The Strategy Lab work package is complete only when:

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
