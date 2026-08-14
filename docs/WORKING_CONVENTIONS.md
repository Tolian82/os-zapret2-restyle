# os-zapret2-restyle — Working conventions quick reference

Status: **NONCANONICAL QUICK REFERENCE**
Updated: 2026-08-14

This file contains stable identifiers and day-to-day technical pointers. It is **not** a fifth rule book.

Canonical rules:

- documentation: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) (`DOC-*`)
- project development: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) (`DEV-*`)
- owner/assistant chat: [`CHAT_RULES.md`](CHAT_RULES.md) (`CHAT-*`)
- GitHub: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) (`GH-*`)

## Stable project identifiers

- project/repository/package: `os-zapret2-restyle`;
- Makefile `PLUGIN_NAME`: `zapret2-restyle`;
- MVC namespace: `OPNsense\Zapret`;
- internal service/configd namespace: `zapret`;
- project version source: `VERSION`;
- package revision suffix: `PLUGIN_REVISION`;
- supported owner console: root `csh`;
- packaged source shell baseline: POSIX `/bin/sh`.

Project identity and shell-development rules are `DEV-025`–`DEV-026`; owner command presentation is `CHAT-019`–`CHAT-020`.

## Day-to-day routing

- Current task and exact package boundary: `START_HERE.md`.
- Current facts: `PROJECT_STATE.md`.
- Complete concise plan: `ROADMAP.md`.
- Current-line chronology: `history/current/v0.4.x.md`.
- Architecture: `ARCHITECTURE.md` and `architecture/`.
- Product requirements: `REQUIREMENTS.md`.
- GitHub execution: `GH-*`.
- Historical rationale/proof: `decisions/`, `devlog/`, `patches/`, `verification/`, `releases/` through `INDEX.md`.

## Finding versus architecture debt

Use these terms when classifying engineering work:

- **Finding** — confirmed implementation defect, inconsistency, obsolete behavior, or concrete operational risk.
- **Architecture debt** — unresolved design question for which intended behavior has not yet been approved.

A typical finding lifecycle is:

`Open -> Discussion -> Decision -> Implementation -> Verification -> Documentation -> Closed`

The governing development rules are `DEV-004`, `DEV-012`–`DEV-019`.

## Current BLOB shorthand contract

Current strategy shorthand:

- `--blob=<name>` resolves to `files/fake/<name>.bin`;
- strategy shorthand omits `.bin`;
- there is no implicit alias table;
- native upstream `--blob=name:value` declarations containing `:` remain native declarations;
- missing referenced files are errors rather than silent substitutions.

This is a technical product contract, not a general rule. Its implementation/architecture owners remain the applicable strategy/runtime documents and source.

## Current GUI maintenance backend

`/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` is the current backend used for GUI management of bol-van/zapret2 releases, including discovery, installed version, update indication, release selection, and install/update/reinstall.

The separately discussed additional BLOB repository remains a roadmap item awaiting an owner-supplied/approved technical contract. It must not acquire invented URL/manifest/layout/version/integrity/update semantics (`DEV-006`, `DEV-019`).
