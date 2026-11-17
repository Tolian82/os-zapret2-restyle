# os-zapret2-restyle — master plan

## Current priority

**Protected upgrade — exact qualified predecessor milestone:** PR [#1178](https://github.com/Tolian82/os-zapret2-restyle/pull/1178) merged into `main` at `1affc6f`. A disposable OPNsense 26.7 really installed the immutable published `_79.pkg`, verified original Auto RUNNING, retired it under original FD9, replaced the package only from independently verified STOPPED, and started the `_85` successor with a new committed Auto epoch and unchanged Config. [Native PASS #44053453048](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44053453048) and [evidence](verification/evidence/2026-11-17-v0.6.5_85-published79-native-bootstrap.md). This is **not** unrestricted direct `pkg add -f` from RUNNING and not a `_85.pkg` publication. The owner's `_79` stays installed and its earlier original-FD9 reviewed recovery is distinct.

**Current `_86` milestone (source-only PR #1179):** isolated [OPNsense native #44059909766](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44059909766) PASS for the actual `pkg` SIGKILL *inside native POST_INSTALL* after extraction, while original FD9 protected STOPPED/retired Auto and `prepared` record survived with Config unchanged and denied Start/Apply/repeat/finish. First-head identity/docs checks failed, final corrective single-commit head needs its own exact CI; this is not a release or mid-extraction/power-loss acceptance. [Evidence](verification/evidence/2026-11-17-v0.6.5_86-native-pkg-postinstall-kill.md).

**Next safety gate:** design and execute a genuinely observable interruption *during extraction* and reboot/resume classification without fabricating a completed package, preserving the old package's `_79` one-time stopped-bootstrap limitation. Do not infer a reliable fail-closed interrupted `pkg` transaction merely from a hook SIGKILL. Then assess the outstanding Voice, client forwarding, retained settings/ordinary uninstall/reinstall/purge and GUI acceptance under [ТЗ_6v2](architecture/TZ_6v2.md) and [STEP0–10](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). No production installation or testing-package publication without its appropriate physical-byte/native gate.

**Previously qualified native mechanism:** merged `_84` first-party protected updater uses original FD9 prepare/stop, ordinary native `pkg` outside FD9, durable failure record and exact POST_INSTALL attestation, then original FD9 restore; [real same-archive native PASS #44045130181](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44045130181) covers STOPPED, RUNNING LIST/AUTO, between-phase omission and explicitly reviewed finish. Stock shell, Lua and developer-mode pre-install refusal attempts were proven **not** to abort FreeBSD `pkg`. No SH installer, SQLite witness, second FD9, external pkg interceptor or foreign PF/IPFW takeover.

| Stage | Bounded result | Status |
|---|---|---|
| P0 | Nonactivating native observer feasibility and generation attribution | Completed within recorded scope |
| P1 | One domain policy, strict IDNA and offline ICANN+PRIVATE PSL | Completed |
| P2 | Original FD9 queue, native Config/P1/ACK, minute raw/debug maintenance, safe four-generation retention and lifecycle handoff | Integrated; exact-head portable/native and finite installed HTTP/RST/Stop/Boot PASS; prolonged owner forwarding/reboot/failure OPEN |
| P3 | Protected auto-owned known/unknown lists, explicit-only Auto HOSTLIST, no legacy migration | Integrated; native installed Config/P1/Hostlist and independent `configd` CAS tests PASS; owner native hot-reload and exclusion acceptance OPEN |
| P4 | [ТЗ_6v2](architecture/TZ_6v2.md): five manual/auto editors, one standard bottom Apply/restart, three-way merge, native Advanced-only schedule select | Old `_70` separate Save/Reload GUI integrated/tested only for former behavior; new P4 needs REWORK/NEW work via [STEP 4–8](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). Owner acceptance OPEN |
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

- [Future #1167 — Strategy Lab comparative checks](https://github.com/Tolian82/os-zapret2-restyle/issues/1167): owner-approved deferred comparison of verified TLS/HTTP/QUIC strategies, one finite warm session and restored normal service; **IPFW rule numbers `19140–19200` reserved in README only**, not used by the current plugin. No implementation or current delivery priority authorized.

Voice UDP ports, an additional shared IPv6 checkbox and P2P remain in the **long-term plan**, as the owner clarified on 13 November. The [retained future design](architecture/VOICE_PORTS_IPV6_P2P_FUTURE.md) preserves the accepted concept, proposed implementation refinements and unresolved verification questions. This does not add them to the current #1052 delivery.

Porting to pfSense remains a separately scoped future target. It has no current compatibility or release claim and does not authorize a speculative parallel implementation. Follow the established platform/dependency rules when that work receives its own specification and qualification.

Voice UDP ports, an additional shared IPv6 checkbox and P2P remain **deferred long-term work**, as explicitly retained by the owner on 13 November 2026. The [future Voice design](architecture/VOICE_PORTS_IPV6_P2P_FUTURE.md) keeps the detailed port/capture/overlap requirements and unresolved P2P proposals outside the archive. This does not advance their priority, implement them or establish call success.

## Closed and excluded directions

External pkg approval/SQLite witnesses/grants, new IPFW/PF management and the completed Telegram direct-provider media research campaign are closed. Historical outcomes from that campaign remain distinct from the deferred future Voice extension. [Owner clarification](decisions/DEC-2026-11-13-documentation-review-owner-clarifications.md).

Old plans and their old next steps remain reachable through the [stage archive](history/README.md). Their presence does not create new implementation or live-testing gates. Published artifacts remain immutable; package publication and stable release follow the existing authorization rules.
