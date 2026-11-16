# os-zapret2-restyle — master plan

## Current priority

The owner-approved [#1052 Auto-detect / Target Mode / HOSTLIST / Auto Restart](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) is now integrated as source `v0.6.5_70` (merged PR #1161), and the immutable `v0.6.5_70.pkg` testing prerelease is published. The latest documentation-only `_72` revision records owner-observed `_70` **P0 startup/Auto-detect/recovery failures and P1 GUI regressions**; no `_72.pkg` exists. The current owner P5 acceptance is **BLOCKED** until [OWN70-01…06](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md#9-owner-acceptance-defects-on-installed-v065_70pkg--16-november-2026) are fixed and retested. **Next outcome:** owner installs the actual `.pkg` and verifies GUI, continuous live traffic, retention, scheduled opt-in restart, preservation on update/uninstall/reinstall, and purge. Preserve fail-closed FD9/Config/IPFW/Voice and do not create an unrelated Strategy Lab workstream.

| Stage | Bounded result | Status |
|---|---|---|
| P0 | Nonactivating native observer feasibility and generation attribution | Completed within recorded scope |
| P1 | One domain policy, strict IDNA and offline ICANN+PRIVATE PSL | Completed |
| P2 | Original FD9 queue, native Config/P1/ACK, minute raw/debug maintenance, safe four-generation retention and lifecycle handoff | Integrated; exact-head portable/native and finite installed HTTP/RST/Stop/Boot PASS; prolonged owner forwarding/reboot/failure OPEN |
| P3 | Protected auto-owned known/unknown lists, explicit-only Auto HOSTLIST, no legacy migration | Integrated; native installed Config/P1/Hostlist and independent `configd` CAS tests PASS; owner native hot-reload and exclusion acceptance OPEN |
| P4 | Editable RU/EN Auto Hostlist and independent Advanced-only Auto Restart | Real two-tab Chromium Save/conflict/F5 PASS; five choices/default Off GUI PASS; real opt-in scheduled RUNNING/STOPPED behavior OPEN |
| P5 | Proportionate native checks, exact standalone testing package and owner acceptance | Source/ABI and `v0.6.5_70.pkg` publication PASS; owner installed, upgrade, preservation, purge, long-run and rollback acceptance OPEN |

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
