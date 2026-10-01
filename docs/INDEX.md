# os-zapret2-restyle — Engineering memory index

**Status:** NAVIGATION / INTEGRITY MAP · NOT A CURRENT-STATE NARRATIVE
**Updated:** 2026-10-01

## Level 1 — mandatory cold start

Read completely in this order (`DOC-016`):

1. [`../AGENTS.md`](../AGENTS.md)
2. [`START_HERE.md`](START_HERE.md)
3. [`PROJECT_STATE.md`](PROJECT_STATE.md)
4. [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
5. [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
6. [`CHAT_RULES.md`](CHAT_RULES.md)
7. [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
8. [`ROADMAP.md`](ROADMAP.md)
9. this `INDEX.md`
10. only current-task specialist documents selected by `START_HERE.md`

## Level 2 — current line and specialist detail

- **[`v0.5.x working ledger`](history/current/v0.5.x.md)** — current-line chronology and release handoff.
- **[`Telegram exact owner-live startup, SSH and manual TNAS route operations`](architecture/TELEGRAM_LAB_OPERATIONS.md)** — read first when continuing the live laboratory: Squid/sing-box GUI and file locations, Voice ON-but-lost-on-reboot warning, csh versus `/bin/sh`, verified SSH keys/port, full owner-tested manual TNAS route script and recovery checklist.
- **[`2026-10-01 owner-live lab inventory and sing-box GUI snapshot`](verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md)** — exact current status, hashes, full owner-provided sing-box JSON, startup and SSH/route proof; not post-reboot acceptance.
- **[`Telegram three-origin laboratory and reboot recovery`](architecture/TELEGRAM_TRAFFIC_POLICY.md)** — mandatory separate, reboot-persistent LAN/router-local/SOCKS5 testbed, experimental Squid/sing-box/PF/parent paths and TNAS routing; not approved plugin TCP/proxy scope.
- **[`September 23–October 1 evidence`](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md)** — fakefrag/tee/reverse8 results, verified TCP parent paths, failed and successful policy application, latest active-helper UDP failure.
- **[`Telegram voice / UDP DPI-bypass research`](research/TELEGRAM_VOICE_UDP.md)** — protocol changes and source links, rebuild motivation, Phase A/B and current Phase C experiments; approved product boundary is UDP-only.
- **[`Telegram Voice emulation/oracle architecture`](architecture/TELEGRAM_VOICE_EMULATION_LAB.md)** — current media oracle and sequential MEDIA_PASS/CALL_PASS gates before future native UDP-only plugin integration.
- **[`TOS Telegram Voice companion recipe`](../tools/telegram-voice-lab/compose.tos.yml)** — digest-pinned host-network build/runtime source; endpoint routing through OPNsense is measured per epoch.
- **[`REQUIREMENTS.md`](REQUIREMENTS.md)** — normative Telegram Voice UDP-only product scope and three approved stages; TCP/proxy remains experimental laboratory infrastructure.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) / [`architecture/`](architecture/) — current technical architecture.
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md) — Strategy Lab architecture entry point.
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md) — accepted production execution model.
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md) — persisted Enable QUIC contract.
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md) — Generic UDP input contract.
- [`USER_GUIDE_STRATEGY_LAB.md`](USER_GUIDE_STRATEGY_LAB.md) — user-facing Strategy Lab guide.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor entry points.
- [`SECURITY.md`](SECURITY.md) — security reporting/reference.
- [`2026-09-20 current laboratory qualification`](verification/evidence/2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md) — rebuilt binary and local P2P gate.
- [`2026-09-21 post-NAT fragmentation tests`](verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md) — local defects, corrected wire output, failed media call, restoration and archive identities.
- [`2026-09-22 reverse run and successful-call observation`](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md) — owner identified the fixed-reflector CLI; the first empty archive does not attribute the reported success.
- [`2026-09-22 post-reboot reverse repeat`](verification/evidence/2026-09-22-telegram-voice-reverse8-postreboot.md) — 60 valid reverse position-8 pairs, no replies/media, exact restoration.
- [`2026-09-23 reverse position-32 result`](verification/evidence/2026-09-23-telegram-voice-reverse32.md) — 60 valid reverse pairs, no replies/media and exact restoration.
- [`2026-09-23 reverse position-16 result`](verification/evidence/2026-09-23-telegram-voice-reverse16.md) — 60 valid reverse pairs, no replies/media and exact restoration.
- [`2026-09-23 reverse position-24 result`](verification/evidence/2026-09-23-telegram-voice-reverse24.md) — 60 valid equal-length reverse pairs, no replies/media and exact restoration; standalone fragment positions close; subsequent fakefrag results are in the October 1 evidence.

## Level 3 — completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- **[`v0.4.x archive`](history/archive/v0.4.x.md)** — completed Strategy Lab / Model C / IPv4-Host-SNI feature line.

Archive mechanics are owned by `DOC-026`–`DOC-030`; version authority is owned by `DEV-029`–`DEV-038`.

## Level 3 — deep history, decisions, audits, and proof

- [`2026-09-05 fixed-reflector control`](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md) — historical `MEDIA_PASS`; route `192.168.1.140` is no longer working and is retired from the active plan.
- [`2026-09-05 B/A/B archival measurements`](verification/evidence/2026-09-05-telegram-voice-phase-c-reflector-bab-path-isolation.md) — old gateway comparison salvaged from PR #286; no current independent control.
- [`2026-09-20 corrected client-source audit`](verification/evidence/2026-09-20-telegram-voice-win-android-source-audit.md) — corrected PR #287's historical source identities; no current client-parity claim.

- [`DECISIONS.md`](DECISIONS.md) / [`decisions/`](decisions/)
- [`AUDIT.md`](AUDIT.md) / [`audit/`](audit/)
- [`DEVLOG.md`](DEVLOG.md) / [`devlog/`](devlog/)
- [`patches/`](patches/)
- [`verification/`](verification/)
- [`verification/evidence/`](verification/evidence/)
- [`releases/`](releases/)
- [`CHANGELOG.md`](CHANGELOG.md)

Historical records preserve chronology/rationale/proof but do not override current Level-1 authority.

## User and repository front door

- [`README.md`](../README.md)
- [`LICENSE`](../LICENSE)
- [`NOTICE`](../NOTICE)

## Integrity contract

Current authorities, active specialist documents, completed archives and deep record stores must remain reachable through this map. Internal Markdown links and canonical rule references are validated by CI.
