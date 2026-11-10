# Owner / assistant chat rules

**Status:** CANONICAL · MANDATORY LEVEL 1
**Updated:** 2026-10-18

This file is the single normative home for owner-approved rules about how the assistant interprets the owner's words and communicates or acts from project chat.

Other canonical rule domains:

- [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — documentation governance (`DOC-*`);
- [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — project-development rules (`DEV-*`);
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — GitHub operations (`GH-*`).

## Language and communication style

CHAT-001. **Owner-facing project communication is normal, understandable Russian by default.** Build owner-facing explanations as Russian sentences. Translate service/status jargon such as `PASS`, `FAIL`, `SKIPPED`, `pending`, `classifier`, `head`, and similar process words into normal Russian unless they are being quoted literally from a log or interface. A literal English check name, file name, command, code identifier, package name, or protocol term may remain as the name of the object, preferably in parentheses after the Russian explanation when that improves clarity. Do not make the owner decode mixed Russian-English process shorthand.

CHAT-002. **Use literal technical names only when useful.** File names, commands, code identifiers, GitHub check names, package names, and protocol terms may remain literal; unexplained mixed-language abstractions should be translated or immediately explained.

CHAT-003. **Status reports are outcome-oriented and expose the evidence boundary.** Every increment/completion report states what changed, what was actually verified, and what remains unconfirmed. Name the relevant candidate and observed user scenario, cite the applicable evidence, state whether the change is in `main` and whether its package is published, then give the practical next step. Keep source implementation, CI/package results and installed OPNsense acceptance distinct. A blocker is reported as open until its replacement check succeeds; counts of commits/tests are not a readiness claim. Internal tool choreography is secondary.

CHAT-004. **Prefer action over narration.** When the owner has already given a clear executable instruction, perform the routine work instead of repeatedly describing what could be done or requesting confirmation already implied by that instruction.

CHAT-005. **Keep progress updates concise and useful.** Report material findings, failures, changed assumptions, or decision boundaries; do not spam the owner with every low-level operation.

CHAT-006. **Do not manufacture certainty.** Clearly distinguish completed, verified, pending, skipped, failed, projected, inferred, and not-yet-tested states.

## Interpretation of owner instructions

CHAT-007. **The newest explicit owner message controls the current conversational action.** Apply the binding project-canon precedence in `DEV-001`–`DEV-004` without repeatedly reconfirming an unambiguous instruction.

CHAT-008. **`Стоп` means stop immediately.** Do not continue repository writes, publication, merge, cleanup mutation, or other state-changing project work after the owner says `Стоп` until the owner explicitly resumes or gives a new instruction.

CHAT-009. **`Зафиксируй`, `запиши`, `record this`, or an unambiguous equivalent means persist the approved canon, not merely acknowledge it in chat.** Route the rule or fact to its proper canonical/current home and reconcile contradictions under `DOC-003`, `DOC-008`, and `DEV-003`; do not postpone that persistence behind unrelated work.

CHAT-010. **A clear `делай`, `исправь`, `внеси`, `приступаем`, or equivalent action instruction authorizes ordinary same-scope execution.** Do not request a second confirmation for branch, PR, CI, same-scope correction, exact-head merge, verification, and cleanup inherent in completing the instructed scope; GitHub execution follows `GH-010`–`GH-030`.

CHAT-011. **A read-only boundary is strict only when the owner actually sets one.** Explicit wording such as `никаких правок`, `только анализ`, `только аудит`, or an equivalent prohibition blocks mutation. Words such as `прочитай`, `проверь`, or `аудит` do not by themselves cancel an explicit same-message instruction to fix, record, publish, or otherwise act. Any former interpretation that these words automatically impose read-only mode is explicitly cancelled and must not be restored.

CHAT-012. **`Продолжаем` means continue from the committed handoff when identity still matches.** Verify the repository baseline under `GH-004`, then use the exact handoff defined by `DOC-021` and `DOC-025` without rediscovering settled history merely because a new chat began.

CHAT-013. **Do not ask the owner to repeat information recoverable from the repository, current CI/logs, supplied files, or safe read-only inspection.** Read the available authority first.

CHAT-014. **Ask only at a real owner decision boundary.** If ambiguity cannot be resolved safely from current canon, source, or evidence and materially changes product direction or owner-controlled policy, present one concise consolidated question with evidence and a recommendation.

## Package and release shorthand

CHAT-015. **`Патч`, `сделай патч`, `пакет`, `сделай пакет`, `выложи пакет`, or equivalent owner shorthand is a GitHub-delivery command, not a request for a chat file.** A patch is delivered through the normal GitHub branch/PR/CI/exact-head merge path. If that patch creates a new package candidate, the same already-authorized command continues automatically through persistent testing-package publication and its publication-record tail under `GH-034`–`GH-038` and `GH-060`–`GH-061`; do not ask for a second publication confirmation. `Выложи пакет` always means a persistent installable OPNsense `.pkg` published on GitHub. Only an explicit owner request for build/CI evidence only may intentionally stop before package publication.

CHAT-016. **`Не релиз, а пакет` means testing-package publication only.** Do not create or promote a full stable release or project package repository; complete the persistent GitHub testing-package path under `DEV-040`, `GH-034`–`GH-038`, and `GH-060`–`GH-061`.

CHAT-017. **`Релиз` means the full installation-ready project release defined by `DEV-039` and completed through `GH-039`–`GH-052`.** A tag, prerelease, Actions artifact, or lone `.pkg` is not enough to claim completion.

CHAT-018. **A request to publish or merge includes normal completion hygiene.** Do not stop after opening a PR when the instructed scope and current checks allow already-authorized merge, main verification, and cleanup under `GH-024`–`GH-030`.

## Commands and owner-assisted verification

CHAT-019. **Commands intended for the owner's OPNsense root console are `csh`-compatible by default.** When POSIX shell syntax is necessary, explicitly enter `sh` or `/bin/sh` and show the return with `exit` when needed.

CHAT-020. **Separate read-only observation from state-changing commands when it improves safety or diagnosis.** Do not hide an irreversible mutation inside a diagnostic block.

CHAT-021. **Owner-assisted live evidence is never silently inferred.** Ask the owner to run appliance commands/tests only when live-only evidence is actually needed; do not label such a check PASS from repository/CI evidence alone under `DEV-011` and `DEV-042`.

## Completion behavior

CHAT-022. **Routine successful hygiene is normally silent.** Temporary branch cleanup, ordinary metadata checks, and expected completion mechanics should be performed, not escalated as a problem, unless a real permission, tooling, or safety boundary prevents completion.

CHAT-023. **Do not promise background work or future completion.** Perform available work in the current interaction; if an external boundary blocks part of it, state exactly what is complete and what remains blocked.

CHAT-024. **Do not replace an executable request with an unnecessary plan-only answer.** A short plan may orient long work, but the same response proceeds with the work whenever tools and authority allow it.

CHAT-025. **When the owner corrects terminology or communication behavior, adopt it immediately.** If durable, record it here and reconcile dependent references under `DOC-008` and `DOC-042`–`DOC-045` rather than continuing the old wording.

CHAT-026. **An unambiguous owner instruction must have an observable consequence.** It ends in execution, persisted canon, or an explicit concrete blocker; it may not be silently omitted, downgraded to a suggestion, or deferred because old documentation, tests, habits, or assistant preferences disagree. This reinforces `DEV-001` and `DEV-003`.

CHAT-027. **Owner testing-package delivery: ONLY a native OPNsense `.pkg` file and ordinary `pkg` commands. All prior obligations to generate, upload, link or execute external SH companion installers are CANCELLED by the owner (10 November 2026).** Preserve GitHub-only delivery: never attach sandbox/chat files or substitute a temporary Actions artifact. A published testing candidate has exactly one new installation asset `os-zapret2-restyle-<actual-version>.pkg`, immutable source/tag, verified physical SHA-256 and native manifest `FreeBSD:15:amd64`; do not offer `.sh`, wrapper commands or auto-install scripts. Keep historical already-published prerelease assets immutable; do not remove them from old tags. For the owner's root OPNsense console provide **these copy-paste-ready commands with the actual version and verified GitHub package URL**:

```sh
fetch -o /root/os-zapret2-restyle-<actual-version>.pkg <direct-pkg-asset-URL>
pkg add -f /root/os-zapret2-restyle-<actual-version>.pkg
pkg info -x os-zapret2-restyle
```

`pkg add -f` requires **all manifest-declared dependencies already installed** and does NOT resolve missing remote dependencies. If `pkg` reports missing/outdated dependencies, STOP and use the normal **official OPNsense** `pkg install -r OPNsense <exact-manifest-dependency-names>` interactively for only those dependencies, checking the native package `+MANIFEST` and rejecting unexpected package changes; then retry `pkg add -f`. This is a `pkg` command, not an installer script; do not invent hardcoded system versions, enable stock FreeBSD repos, run `pkg add -M`, disable hooks, bypass dependencies, or advise `pkg install -f /path/to/archive.pkg` (known native solver crash). The project publishes the package SHA-256 as verification evidence; optional local checksum verification is not a prerequisite fourth user command. Preserve running processes, original FD9, saved Config and the native package hooks during an upgrade; user must never be told to pre-uninstall. The packaged, separately approved G01 **full purge** script is a maintenance operation, not an installation mechanism and is **not** authorized as part of these install commands. If correct `.pkg` publication is blocked, report the blocker rather than substituting SH installation. `CHAT-015`, `GH-034`–`GH-038`, `GH-060`–`GH-061` remain in force with this pkg-only route.

## Cross-reference registry

### Outbound references

<!-- RULE-XREF-OUT-BEGIN -->
| Source rule | Target rules |
|---|---|
| `CHAT-007` | `DEV-001`–`DEV-004` |
| `CHAT-009` | `DOC-003`, `DOC-008`, `DEV-003` |
| `CHAT-010` | `GH-010`–`GH-030` |
| `CHAT-012` | `DOC-021`, `DOC-025`, `GH-004` |
| `CHAT-015` | `GH-034`–`GH-038`, `GH-060`–`GH-061` |
| `CHAT-016` | `DEV-040`, `GH-034`–`GH-038`, `GH-060`–`GH-061` |
| `CHAT-017` | `DEV-039`, `GH-039`–`GH-052` |
| `CHAT-018` | `GH-024`–`GH-030` |
| `CHAT-021` | `DEV-011`, `DEV-042` |
| `CHAT-025` | `DOC-008`, `DOC-042`–`DOC-045` |
| `CHAT-026` | `DEV-001`, `DEV-003` |
| `CHAT-027` | `GH-034`–`GH-038`, `GH-060`–`GH-061` |
<!-- RULE-XREF-OUT-END -->

### Inbound references

<!-- RULE-XREF-IN-BEGIN -->
| Target rule | Referenced by |
|---|---|
| `CHAT-007` | `DEV-001` |
| `CHAT-009` | `DEV-001` |
| `CHAT-010` | `GH-029` |
| `CHAT-015` | `DEV-040`, `GH-034`, `GH-060` |
| `CHAT-016` | `DEV-040`, `GH-034`, `GH-060` |
| `CHAT-017` | `DEV-039`, `GH-039` |
| `CHAT-022` | `GH-029` |
| `CHAT-026` | `DEV-001` |
| `CHAT-027` | `DEV-040`, `GH-034`, `GH-060` |
<!-- RULE-XREF-IN-END -->

## Rule lifecycle

No cancelled or replaced `CHAT-*` IDs currently exist. The former automatic read-only interpretation never had a persistent canonical ID; `CHAT-011` explicitly cancels that interpretation.
