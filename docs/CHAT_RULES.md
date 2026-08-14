# Owner / assistant chat rules

Status: **CANONICAL / MANDATORY LEVEL 1**
Updated: 2026-08-14

This file is the single normative home for owner-approved rules about **how the assistant interprets the owner's words and communicates/workflows with the owner in project chat**.

Other rule domains:

- [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — documentation governance (`DOC-*`);
- [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — project-development rules (`DEV-*`);
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — GitHub operations and publication (`GH-*`).

These rules describe communication semantics. They do not duplicate the engineering or GitHub procedure that executes the resulting instruction.

## A. Language and communication style

CHAT-001. **Owner-facing project communication is normal, understandable Russian by default.** Do not make the owner decode English process jargon when a clear Russian explanation exists.

CHAT-002. **Use literal technical names only when they are useful.** File names, commands, code identifiers, GitHub check names, package names, and protocol terms may remain literal; unexplained mixed-language abstractions such as `evidence/history` should be replaced with natural Russian or immediately explained.

CHAT-003. **Status reports are outcome-oriented.** State what was found, what changed, what passed/failed, whether the change is already in `main`, and what the practical next step is. Internal tool choreography is secondary.

CHAT-004. **Prefer action over narration.** When the owner has already given a clear executable instruction, perform the routine work instead of repeatedly describing what could be done or asking for confirmation already implied by the instruction.

CHAT-005. **Keep progress updates concise and useful.** Report material findings, failures, changed assumptions, or decision boundaries; do not spam the owner with every low-level tool call or ordinary housekeeping step.

CHAT-006. **Do not manufacture certainty.** Clearly distinguish completed, verified, pending, skipped, failed, projected, inferred, and not-yet-tested states.

## B. Interpretation of owner instructions

CHAT-007. **The newest explicit owner message controls the current conversational action.** Apply the project-canon precedence defined by `DEV-001`–`DEV-004` without repeatedly reconfirming an already unambiguous instruction.

CHAT-008. **`Стоп` means stop immediately.** Do not continue repository writes, publication, merge, cleanup mutation, or other state-changing project work after the owner says `Стоп` until the owner explicitly resumes or gives a new instruction.

CHAT-009. **`Зафиксируй`, `запиши`, `record this`, or an unambiguous equivalent means persist the approved canon, not merely acknowledge it in chat.** Route the rule/fact to its correct canonical/current document and apply the reconciliation required by `DOC-003`, `DOC-008`, and `DEV-003`.

CHAT-010. **A clear `делай`, `исправь`, `внеси`, `приступаем`, or equivalent action instruction authorizes ordinary same-scope execution.** Do not request a second confirmation for routine branch/PR/CI/squash-merge/cleanup steps already inherent in completing that instructed scope; GitHub execution follows `GH-*`.

CHAT-011. **A read-only boundary is strict.** If the owner says `аудит`, `проверь`, `прочитай`, `никаких правок`, `только анализ`, or otherwise explicitly limits work to read-only inspection, do not mutate the repository until the owner later authorizes changes.

CHAT-012. **`Продолжаем` means continue from committed handoff when identity still matches.** Verify current repository/handoff identity, then continue the exact documented next task without rediscovering settled history merely because a new chat/session began.

CHAT-013. **Do not ask the owner to repeat information that can be recovered from the repository, current CI/logs, supplied files, or safe read-only inspection.** Read the available source first.

CHAT-014. **Ask only at a real owner decision boundary.** If ambiguity cannot be resolved safely from current canon/source/evidence and materially changes product direction or owner-controlled policy, present one concise consolidated question with the relevant evidence and a recommendation.

## C. Package and release shorthand

CHAT-015. **`Пакет`, `патч`, `сделай пакет`, `выложи пакет`, or equivalent owner shorthand means a persistent installable OPNsense `.pkg` on GitHub unless the owner explicitly asks only for build/CI evidence.** Publication mechanics follow `GH-*`.

CHAT-016. **`Не релиз, а пакет` means testing-package publication only.** Do not create/promote a full stable release or project package repository; still provide a persistent GitHub testing package according to `GH-*`.

CHAT-017. **`Релиз` means the full installation-ready project release defined by `DEV-039` and the full-release `GH-*` procedure.** A tag, prerelease, Actions artifact, or lone `.pkg` is not enough to claim that instruction completed.

CHAT-018. **A request to publish/merge includes normal completion hygiene.** Do not stop after opening a PR when the instructed scope and current checks allow the already-authorized merge and cleanup to be completed.

## D. Commands and owner-assisted verification

CHAT-019. **Commands intended for the owner's OPNsense root console must be `csh`-compatible by default.** When POSIX shell syntax is necessary, explicitly enter `sh` or `/bin/sh` and show the return with `exit` when the command sequence needs it.

CHAT-020. **Separate read-only observation from state-changing commands when it improves safety or diagnosis.** Do not mix an irreversible mutation into a diagnostic block without making the boundary clear.

CHAT-021. **Owner-assisted live evidence is never silently inferred.** Ask the owner to run appliance commands/tests only when the project actually needs live-only evidence; do not label a live check PASS from CI or repository inspection alone (`DEV-011`, `DEV-042`).

## E. Completion behavior

CHAT-022. **Routine successful hygiene is normally silent.** Temporary branch cleanup, ordinary metadata checks, and other expected completion mechanics should be performed, not escalated as a problem, unless a real permission/tooling/safety boundary prevents completion.

CHAT-023. **Do not promise background work or future completion.** Perform the available work in the current interaction; if a real external boundary blocks part of it, state exactly what is complete and what boundary remains.

CHAT-024. **Do not replace an executable request with an unnecessary plan-only answer.** A short plan/update may orient long work, but the same response should proceed with the work whenever tools and authority allow it.

CHAT-025. **When the owner corrects terminology or communication behavior, adopt the correction immediately.** If it is durable, record it here using the next `CHAT-*` rule and reconcile active references under `DOC-008` rather than continuing the old wording.
