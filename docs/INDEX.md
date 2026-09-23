# os-zapret2-restyle — Engineering memory index

**Status:** NAVIGATION / INTEGRITY MAP · NOT A CURRENT-STATE NARRATIVE
**Updated:** 2026-09-23

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
- **[`Telegram voice / UDP DPI-bypass research`](research/TELEGRAM_VOICE_UDP.md)** — protocol changes and source links, rebuild motivation, Phase A/B interpretation and current Phase C experiments.
- **[`Telegram Voice emulation/oracle architecture`](architecture/TELEGRAM_VOICE_EMULATION_LAB.md)** — rebuilt media oracle, retired control route, corrected post-NAT wire path, current call-success goal and result taxonomy.
- **[`TOS Telegram Voice companion recipe`](../tools/telegram-voice-lab/compose.tos.yml)** — digest-pinned host-network build/runtime source; endpoint routing through OPNsense is measured per epoch.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) / [`architecture/`](architecture/) — current technical architecture.
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md) — Strategy Lab architecture entry point.
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md) — accepted production execution model.
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md) — persisted Enable QUIC contract.
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md) — Generic UDP input contract.
- [`REQUIREMENTS.md`](REQUIREMENTS.md) — product requirements.
- [`USER_GUIDE_STRATEGY_LAB.md`](USER_GUIDE_STRATEGY_LAB.md) — user-facing Strategy Lab guide.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor entry points.
- [`SECURITY.md`](SECURITY.md) — security reporting/reference.
- [`2026-09-20 current laboratory qualification`](verification/evidence/2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md) — rebuilt binary and local P2P gate.
- [`2026-09-21 post-NAT fragmentation tests`](verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md) — local defects, corrected wire output, failed media call, restoration and archive identities.
- [`2026-09-22 reverse run and successful-call observation`](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md) — owner identified the fixed-reflector CLI; the first empty archive does not attribute the reported success.
- [`2026-09-22 post-reboot reverse repeat`](verification/evidence/2026-09-22-telegram-voice-reverse8-postreboot.md) — 60 valid reverse position-8 pairs, no replies/media, exact restoration.
- [`2026-09-23 reverse position-32 result`](verification/evidence/2026-09-23-telegram-voice-reverse32.md) — 60 valid reverse pairs, no replies/media and exact restoration.
- [`2026-09-23 reverse position-16 result`](verification/evidence/2026-09-23-telegram-voice-reverse16.md) — 60 valid reverse pairs, no replies/media and exact restoration; guarded reverse position 24 is prepared next.

## Level 3 — completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- **[`v0.4.x archive`](history/archive/v0.4.x.md)** — completed Strategy Lab / Model C / IPv4-Host-SNI feature line.

Archive mechanics are owned by `DOC-026`–`DOC-030`; version authority is owned by `DEV-029`–`DEV-038`.

## Level 3 — deep history, decisions, audits, and proof

- [`2026-09-05 fixed-reflector control`](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md) — historical `MEDIA_PASS`; route `192.168.1.140` is no longer working and is retired from the active plan.

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
