# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED HISTORICAL INPUT; `v0.4.1_15` SOURCE/PACKAGE ACCEPTED AND PUBLISHED, OWNER-LIVE CORRECTIVE VERIFICATION PENDING.**

Only FreeBSD 15 amd64 packages are valid. Source tests/CI do not replace selected owner-live evidence.

## Current package/source boundary

- current published testing package/tag: `os-zapret2-restyle-0.4.1_15.pkg` / `v0.4.1_15`;
- `_15` source merge/tag target: `a219161c901c663b56cac6757364d3bbd32766c7`;
- `_15` package SHA-256: `e25c47519844623f6e1fcfe4d45a517960d06d0939f5cf004112a02186a5701f`;
- publication workflow run: `31879283227`;
- stable Pages/pkg repository promoted: no;
- owner installation/live verification of `_15`: pending.

Machine publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_15.md`.

Normal Stage 60 remains Model C only; automatic Model B/A production fallback is disabled from `_13`.

## Accepted `_13` baseline

### Normal Model-C-only paths

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

- `telegram.org` `job.6RhNa1`: `NO_CANDIDATE`, Stage 60 `16/16`, `graph_exhausted`, no automatic fallback, verified RUNNING restoration.
- `rutracker.org` `job.PEEjoY`: `SUCCESS`, Stage 60 `16/16`, three stable shortlist entries, no automatic fallback, verified RUNNING restoration.
- `www.youtube.com` `job.7Kz5ro`: `SUCCESS`, early Stage-60 stop at `7/16` / `enough_candidates`, three stable shortlist entries, verified RUNNING restoration.

### Initial permanent service STOPPED

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`.

`rutracker.org` Standard `job.5b97u9` completed `SUCCESS` with three stable strategies and left the permanent Zapret2 service STOPPED; the immediate post-job normal `dvtws2|zapret.*supervisor` query was empty. The owner accepted this observable row as sufficient and declined redundant deeper replay.

### Extended TLS 1.2 / HTTP and historical QUIC behavior

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md`.

`rutracker.org` Extended `job.TJlWoY`:

- terminal `SUCCESS`, Stage 80 PASS, Stage 90 PASS;
- TLS 1.2 and HTTP branches executed with truthful negative endpoint evidence;
- `_13` Stage 30 classified QUIC/IPv4 closed and Stage 80 capability-skipped QUIC;
- UDP was skipped because no valid payload was supplied.

That `_13` QUIC skip is historical evidence only and is superseded as product behavior.

## `_14` owner-live observations that selected `_15`

The owner installed `_14` and supplied Extended screenshots for `telegram.org` and `rutracker.org` with **Enable QUIC checked**.

Both showed:

- ordinary QUIC control probe blocked/closed;
- Stage 80 `QUIC=not_found, UDP=skipped`, not a capability skip;
- Stage 90 restoration PASS.

`telegram.org` ended `NO_CANDIDATE`; `rutracker.org` ended `SUCCESS` with one stable TLS 1.3 candidate.

These runs proved the old capability skip no longer appeared at the normal GUI boundary, but `_14` ordinary output did not expose the actual QUIC `tested` set. Therefore `not_found` alone was not final live proof of real candidate attempts.

The same cycle exposed:

- raw/internal Stage-30/Stage-80 wording in the Russian UI;
- English-only Enable QUIC help text;
- owner-reported false rejection of a nominal 140-byte Generic UDP payload;
- no ordinary direct selected-port/payload UDP control observation.

The owner selected these findings as one corrective package scope: `_15`.

## `_15` implemented and automated-accepted behavior

### A. QUIC execution observability

`_15` preserves `_14` execution semantics and adds owner-visible proof:

- Stage 30 presents measured `QUIC открыт` / `QUIC закрыт` (or English equivalent) separately from the job-local QUIC-search enabled/disabled choice;
- Enable QUIC ON still runs candidates regardless of blocked control result;
- Stage 80 reads the actual structured `tested` array and presents attempted count + candidate IDs;
- current catalog remains `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`;
- working candidate ID or natural no-working-strategy text is presented in RU/EN;
- raw `working/not_found/skipped/disabled` remain structured evidence rather than primary normal UI text.

### B. QUIC help localization

The Enable QUIC explanatory text is bound through deterministic RU/EN UI language selection. Both language strings and displayed-control binding are covered by automated source acceptance.

### C. Exact Generic UDP input

Browser source uses:

`readAsArrayBuffer -> Uint8Array.byteLength 1..4096 -> binary Base64 -> strict API/backend decode`.

Browser `File.size` and Data-URL parsing are no longer authoritative validation owners. An exact 140-byte payload is covered through Base64 transport/job-local decode metadata.

### D. Selected-port UDP control observation

Configured Generic UDP performs a bounded direct observation for each fixed search-epoch selected IP using:

- the selected destination port;
- the exact job-local payload.

Evidence records selected endpoint/IP, port, payload bytes, reply observed/not observed, timeout/return state and duration.

No-reply semantics remain deliberately limited: **no reply does not mean the port is closed and does not gate the bypass candidate loop.** Stage 80 then presents actual UDP candidate count/IDs plus winner/no-winner meaning in RU/EN.

## `_15` source/publication acceptance — PASS

All required pre-live gates completed:

1. exact 140-byte payload regression PASS;
2. browser ArrayBuffer/exact-byte/Base64 contract PASS;
3. direct selected-IP/port/exact-payload UDP observation regression PASS;
4. non-gating UDP-silence semantics PASS;
5. blocked-control Enable QUIC candidate-execution regression PASS;
6. Stage-30 and Stage-80 RU/EN protocol presentation regression PASS;
7. complete Strategy Lab corrective matrix PASS;
8. FreeBSD-15 package build/inspection qualification PASS;
9. exact verified source head `ecf3d5269574988e56707c68b6eb9696d936b1ca` squash-merged as `a219161c901c663b56cac6757364d3bbd32766c7`;
10. `v0.4.1_15` testing package persistently published and verified with SHA-256 `e25c47519844623f6e1fcfe4d45a517960d06d0939f5cf004112a02186a5701f`.

The publication-record documentation tail is PR `#242`; its machine evidence was generated by the publisher before the repository setting blocked GitHub Actions from creating the Draft PR automatically.

## Owner-live `_15` matrix after publication

### A. Enable QUIC preference

- default OFF on new unset preference;
- checked/unchecked state persists across Diagnostics reload;
- saving preference does not restart/apply the permanent Zapret2 service.

### B. Enable QUIC OFF

Extended mode, checkbox OFF:

- no QUIC candidates;
- structured state may remain `skipped/disabled`;
- ordinary Stage-80 text says strategy search is disabled naturally in selected RU/EN language.

### C. Enable QUIC ON with blocked ordinary QUIC

Required:

- Stage 30 says QUIC blocked/closed **and** QUIC strategy search enabled;
- Stage 80 shows actual tested count greater than zero and attempted IDs;
- result truthfully shows a working candidate or no working candidate;
- no capability skip;
- restoration PASS.

### D. Valid configured Generic UDP / 140-byte regression

Required:

- exact/small payload including 140-byte sample starts normally;
- displayed payload byte count matches actual decoded size;
- selected destination port and endpoint/IP are shown;
- direct control observation says reply/no reply truthfully;
- no-reply text explicitly avoids claiming the port is closed;
- actual UDP candidate count/IDs are visible and non-zero;
- winner/no-winner result is human-readable;
- terminal payload cleanup and Zapret2 restoration PASS.

### E. Oversized Generic UDP

Required:

- >4096 decoded bytes shows visible `1–4096` error;
- no new job starts;
- previous completed result is not cleared solely by invalid Run.

### F. RU/EN presentation

Required in both selected UI languages:

- Enable QUIC help;
- Stage-30 measured QUIC state + independent search choice;
- Stage-80 QUIC candidate evidence;
- Stage-80 Generic UDP control/candidate evidence;
- no primary raw internal status fragments.

One Extended job may cover C and D simultaneously when Enable QUIC is ON and valid Generic UDP is configured.

## Scenario matrix

| # | Scenario | Result |
|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | **PASS ON `_13`** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | **PASS ON `_13` — OWNER ACCEPTED** |
| 3 | Extended TLS 1.2 | **PASS ON `_13`** |
| 4 | Extended HTTP | **PASS ON `_13`** |
| 5 | Historical closed-QUIC capability skip | **OBSERVED/PASS FOR `_13`; SUPERSEDED** |
| 6 | `_14` Enable QUIC ON, blocked control path, no capability skip | **PARTIAL LIVE PASS; selected `_15` observability** |
| 7 | `_15` QUIC tested count/IDs ordinary output | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 8 | `_15` Stage-30/80 RU/EN protocol presentation | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 9 | `_15` Enable QUIC RU/EN help | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 10 | `_14` nominal 140-byte Generic UDP input | **FAIL OWNER — FALSE SIZE REJECTION REPORTED** |
| 11 | `_15` exact 140-byte binary input | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 12 | `_15` selected-port/payload direct UDP observation | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 13 | `_15` no-reply does not mean closed / does not gate candidates | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 14 | Enable QUIC OFF/default/persistence owner-live | PENDING |
| 15 | Oversized Generic UDP owner-live | PENDING |
| 16 | Target already accessible | PENDING REGRESSION |
| 17 | User cancellation after service stop | PENDING REGRESSION |
| 18 | Controlled internal failure / timeout containment | PENDING REGRESSION |
| 19 | Circular start/stop/stale recovery | PENDING REGRESSION |
| 20 | Settings Apply guards during Strategy Lab/circular | PENDING REGRESSION |
| 21 | Diagnostics persistence/reload | PENDING REGRESSION |
| 22 | General RU/EN presentation review | PENDING REGRESSION |
| 23 | Retention/reboot residue | PENDING REGRESSION |

## Failure policy for `_15`

`_15` fails owner-live acceptance if any of the following occur:

- enabled QUIC is suppressed because Stage 30 says QUIC blocked;
- disabled QUIC launches candidates;
- enabled QUIC ordinary output cannot prove actual attempted count/IDs;
- Stage-30 measured state is presented as the reason search is enabled/disabled;
- normal RU/EN UI leaks selected raw QUIC/UDP enums or English-only help;
- a valid `1..4096` decoded-byte UDP payload, including 140 bytes, is rejected by size handling;
- direct UDP observation uses a different port/payload/binding than the candidate job;
- UDP silence is asserted to mean a definitely closed port or suppresses candidate search;
- configured UDP is silently skipped as unconfigured;
- lifecycle restoration or temporary payload/runtime cleanup fails.
