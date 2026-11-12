# P5a — Canonical read-only structural advisory (NOT full P5)

Feature: issue #936, approved plan docs/architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md, source candidate v0.6.4_36. Exact-head CI and native installed/owner acceptance are pending; stable v0.6.4_1.pkg is unchanged.

## One canonical parser, without mutation

P5a adds backend/strategy_preview.py as a private source-only structural inspector. It calls the **existing canonical** profile_policy.split_profiles() and profile_policy.expand_profiles() on an in-memory JSON candidate. The helper has no filesystem writes, persistent workspace, Config operations, IPFW commands, process ownership, FD9 lock, service start, or network requests. It is not yet exposed via the Strategies GUI or an API.

CLI: python3 strategy_preview.py inspect-stdin. Request is one bounded UTF-8 JSON object up to 65536 bytes, with exactly required strategy and target_mode (all/list/auto), optional extra_arguments and boolean exclude_domains_configured / exclude_ipset_configured. Duplicate keys, malformed types, control characters, unsupported mode, malformed canonical profile/placeholder, excessive profiles (more than 128) and oversize request fail with fixed error codes that do not echo raw user strategy.

The report gives an **advisory observation** only: canonical source and expanded profile counts/order, requested port/L7 filter tokens, textual HOSTLIST/IPSET selector annotations, ordered payload/range/Lua snapshots, possible first-match overlap, repeated textual references, and explicit warning when Extra Arguments or default targets require later native resolution. Values that cannot be safely abbreviated are truncated for display, without rewriting input.

Every report MUST retain these negative proof labels:
- state = advisory_not_native_validated
- engine_native_dry_run = not_run
- effective_ipfw_port_coverage = not_computed
- actual_resources = not_checked
- actual_voice_merge = not_checked
- real_network_bypass = not_tested
- config_process_fd9_ipfw_mutation = not_performed

This is not evidence of valid native syntax, actual IPFW port coverage, real Lua/BIN availability, final resolved list files, Voice merge, WAN readiness, completed TCP/QUIC handshake or provider DPI bypass. The current generator, ports.sh, mapped validator and native dvtws2 --dry-run remain authoritative; no second full native grammar is introduced.

## Focused source verification

scripts/test-strategy-preview-shape.py checks empty config, HTTP/TLS/QUIC annotations, canonical multi-target expansion, preserved Lua action ordering/ranges, possible-overlap warnings, conservative default targets, invalid --new, malformed placeholder, oversized JSON, duplicate keys, invalid types, NUL, no temporary writes on success/error, and no imports from privileged or mutating modules. All checks run as quick S0/S1 source tests only. The main CI invokes this exact test.

## Next P5 increments — still OPEN

1. Expose separate RU/EN Validate and Preview button on Strategies that can inspect the **unsaved** candidate and distinguish saved model baseline, without invoking Apply.
2. Reuse the existing detached Config/native template + generator + mapped validator and real installed dvtws2 --dry-run under the original native lifecycle owner. Only private temporary artifacts with guaranteed cleanup; never write Config, IPFW, Voice, resources, shared operation record or runtime.
3. Verify before/after semantic fingerprints for RUNNING, STOPPED, missing runtime, invalid strategy and cancellation/error paths (Config and history, FD9, PID/process, IPFW rules/tables, Voice, resource state).
4. Expose truthful RU/EN statuses for syntax/native unavailable/native failed/network not tested, per-profile effective summaries and actionable field/profile errors.
5. Installed disposable OPNsense witness and separate owner A11/A16; full P5 and P6 publication not accepted by P5a.

No new .pkg is built or published by this documentation record.
