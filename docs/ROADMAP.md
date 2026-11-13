# os-zapret2-restyle — master plan

## Current priority

Complete owner-approved [#1052 Auto-detect / Target Mode / HOSTLIST / Auto Restart](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) through the [P0–P5 plan](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). P0/P1 are complete; P2 is partial; P3–P5 are open. [PROJECT_STATE](PROJECT_STATE.md) owns facts and [START_HERE](START_HERE.md) owns the exact next action. Per-revision measurements and CI receipts belong to the [v0.6.x ledger](history/current/v0.6.x.md).

| Stage | Bounded result | Status |
|---|---|---|
| P0 | Nonactivating native observer feasibility and generation attribution | Completed within recorded scope |
| P1 | One domain policy, strict IDNA and offline ICANN+PRIVATE PSL | Completed |
| P2 | Durable queue and native cron/configd worker with real owner, FD drain and generation proof | Partial: P2a–P2e source/proof; offline native builder qualified; observer/schema-2/owned writes remain |
| P3 | Auto-owned destination lists, obsolete-path retired in `_30`, and native reload | Partial: obsolete path code retired; active worker/destination provenance and reload open |
| P4 | Editable Auto Hostlist and independent scheduled restart in native Advanced Mode | Open |
| P5 | Proportionate source/native checks, exact testing package and owner acceptance | Open |

## Completed lifetime path

| Milestone | Result / retained record |
|---|---|
| v0.1.x–v0.2.x | Independent plugin identity, model/targets, transactional service and native package/setup boundaries; [archives](history/README.md) |
| v0.3.x | Asynchronous Strategy Lab and corrective lifecycle/state/result contracts; [v0.3.x archive](history/archive/v0.3.x.md) |
| v0.4.x | Python ownership, native adaptive search and Model-C-only production; measurement questions closed; [v0.4.x archive](history/archive/v0.4.x.md) |
| v0.5.x | Shared Voice/Strategies backend, Chrome reachability, Additional Resources Install/Remove and cache-backed help; [v0.5.x final state](history/archive/v0.5.x.md) |
| v0.6.2 | Dual-stack IP lists, global Exclude IPSet and opt-in Laboratory IPv6; bounded acceptance and explicit live limits; [release](releases/v0.6.2.md) |
| v0.6.3–v0.6.4 | Native OPNsense packaging and G01–G11 clean-install/update/uninstall/purge/WAN/empty-Strategy lifecycle; owner accepted; [lifecycle contract](architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md) |
| v0.6.5 stable | #936 HOSTLIST/modifiers/profile policy/RU-EN/read-only preview and #1084 appearance accepted; final `_1.pkg` installed via owner GUI; [release](releases/v0.6.5.md) |
| Documentation review, 13 November | Current authority separated from historical plans/diaries; no information discarded; [findings](audit/DOCS-2026-11-13.md) |

## Accepted future direction

Voice UDP ports, an additional shared IPv6 checkbox and P2P remain in the **long-term plan**, as the owner clarified on 13 November. The [retained future design](architecture/VOICE_PORTS_IPV6_P2P_FUTURE.md) preserves the accepted concept, proposed implementation refinements and unresolved verification questions. This does not add them to the current #1052 delivery.

Porting to pfSense remains a separately scoped future target. It has no current compatibility or release claim and does not authorize a speculative parallel implementation. Follow the established platform/dependency rules when that work receives its own specification and qualification.

Voice UDP ports, an additional shared IPv6 checkbox and P2P remain **deferred long-term work**, as explicitly retained by the owner on 13 November 2026. The [future Voice design](architecture/VOICE_PORTS_IPV6_P2P_FUTURE.md) keeps the detailed port/capture/overlap requirements and unresolved P2P proposals outside the archive. This does not advance their priority, implement them or establish call success.

## Closed and excluded directions

External pkg approval/SQLite witnesses/grants, new IPFW/PF management and the completed Telegram direct-provider media research campaign are closed. Historical outcomes from that campaign remain distinct from the deferred future Voice extension. [Owner clarification](decisions/DEC-2026-11-13-documentation-review-owner-clarifications.md).

Old plans and their old next steps remain reachable through the [stage archive](history/README.md). Their presence does not create new implementation or live-testing gates. Published artifacts remain immutable; package publication and stable release follow the existing authorization rules.
