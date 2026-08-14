# os-zapret2-restyle — Project development rules

Status: **CANONICAL / MANDATORY LEVEL 1**
Updated: 2026-08-14

This file is the single normative home for owner-approved rules, principles, and assertions that govern **how the project itself is designed, changed, verified, versioned, and released as a product**.

Other rule domains:

- [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — documentation governance (`DOC-*`);
- [`CHAT_RULES.md`](CHAT_RULES.md) — owner/assistant communication semantics (`CHAT-*`);
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — GitHub operations and publication (`GH-*`).

Current product facts belong in `PROJECT_STATE.md`; concrete technical contracts belong in requirements/architecture. This file contains durable cross-task development rules.

## A. Owner canon and engineering authority

DEV-001. **The owner's newest unambiguous project instruction, fact, or approved decision is current project canon.** It supersedes conflicting older active plans, assumptions, or normative text.

DEV-002. **Accepted owner canon remains locked until the owner explicitly changes it or fresh direct reproducible evidence disproves the factual premise.** Loss of conversational memory, an old document, or a stale test is not counter-evidence.

DEV-003. **The “Суслик” principle is permanent.** If implementation, active documentation, tests, or plans contradict the newest unambiguous owner canon, reconcile the project to that canon; do not reinterpret the owner's words merely to preserve stale project material.

DEV-004. **Settled findings stay settled.** Do not reopen a completed investigation or design choice solely because a later session starts with less context. Reopen it only for a new owner decision, a changed requirement, or new direct evidence material to the conclusion.

DEV-005. **Source and approved intent have different authority.** Committed source is authoritative for what is currently implemented; owner-approved requirements/architecture/current-state documentation is authoritative for intended direction. A mismatch is explicit transition debt, not an excuse to silently choose one narrative.

DEV-006. **A project decision must have an evidentiary or owner-authority basis.** Do not turn a guess, convenience, benchmark projection, or tooling limitation into architecture canon.

## B. Engineering quality and change discipline

DEV-007. **Correctness and sufficiency outrank speed.** Prefer the smallest change that fully solves the confirmed problem and preserves required behavior over speculative breadth.

DEV-008. **Preserve working behavior before optimizing it.** Optimization is justified only when the relevant cost or defect is measured or otherwise demonstrated and the required semantics are preserved.

DEV-009. **Do not hide behavior behind silent magic.** Important defaults, fallback, state mutation, lossy normalization, recovery, or failure handling must be explicit enough to reason about and verify.

DEV-010. **Failure classes must remain truthful.** Infrastructure/internal/restoration/validation failures must not be reported as network candidate failure, normal completion, or success merely to simplify control flow.

DEV-011. **Never claim an unexecuted verification as PASS.** A test, live row, package build, restoration check, benchmark, or release gate is PASS only when corresponding evidence actually exists.

DEV-012. **Diagnose from exact evidence before changing code.** Read the concrete failure/log/state first; do not patch a plausible cause and then retrofit the explanation.

DEV-013. **A stale test never outranks current owner canon or current architecture.** Update the stale assertion/fixture/contract rather than bending valid implementation back toward obsolete behavior.

DEV-014. **External infrastructure failures do not justify speculative product changes.** Runner, network, service, action, or dependency outages are retried or diagnosed as infrastructure unless source evidence establishes a product defect.

DEV-015. **Unknown platform behavior is verified, not guessed.** Material OPNsense, FreeBSD, configd, package, shell, firewall, process, PHP, JavaScript, or upstream Zapret2 behavior must be checked against current source/runtime evidence when correctness depends on it.

DEV-016. **Audits and refactors are scope/risk based.** Inspect enough surrounding behavior to prove the change safe; do not repeat broad audits mechanically when existing evidence remains applicable.

DEV-017. **One logical engineering scope should remain one logical change.** Same-root-cause repairs, tests, and documentation belong together; unrelated improvements wait for their own scope.

DEV-018. **Do not change approved architecture merely to make an old test or old implementation path convenient.** First determine whether the contract or the implementation is stale.

DEV-019. **Requirements or architecture changes require explicit rationale.** A change to approved user-visible behavior, safety semantics, ownership, or public contract is not smuggled in as an implementation cleanup.

## C. Runtime and product-safety invariants

DEV-020. **Runtime/lifecycle changes fail closed.** Preserve bounded actions, transactional mutation, explicit ownership, cleanup on success/failure/cancel, and verifiable restoration.

DEV-021. **Semantic restoration is stronger than command success.** When work temporarily changes runtime state, success requires the required final semantic state/evidence, not merely a zero exit code or a new process ID.

DEV-022. **A restoration failure outranks a useful intermediate result.** Never hide `RESTORE_FAILED` or equivalent unsafe residue behind a successful search, setup, Apply, package, or diagnostic result.

DEV-023. **A subsystem has one authoritative owner for each piece of mutable state or policy.** Compatibility layers may adapt inputs/outputs but must not recreate a competing source of truth.

DEV-024. **Preserve native Zapret2 semantics.** Candidate syntax, Lua/BLOB identity, filters/ranges, and upstream behavior are not approximated or normalized into a different strategy unless a specific approved design intentionally changes them.

DEV-025. **Project source shell is POSIX `/bin/sh` unless a documented boundary explicitly requires something else.** FreeBSD-specific commands are allowed; shell-language assumptions must remain deliberate and testable.

DEV-026. **Repository/package identity remains independent.** The project is `Tolian82/os-zapret2-restyle`, package `os-zapret2-restyle`, and internal service key `zapret`; inherited upstream/fork identity must not leak back into product ownership. Changing the service key or product identity requires explicit owner approval.

## D. Version semantics

DEV-027. **`VERSION` is the single project-version source.** Its value has exactly three numeric components `A.B.C`.

DEV-028. **`PLUGIN_REVISION` is the package revision suffix `_N`.** It identifies the concrete installable patch/iteration inside the current `VERSION`.

DEV-029. **The second numeric component defines the long-lived project-state/release line.** In `v0.4.2_14`, `4` defines line `v0.4.x` and the scope of `PROJECT_STATE.md`.

DEV-030. **The third numeric component defines the current development stage/task.** In `v0.4.2_14`, `2` identifies the genuine current development stage inside `v0.4.x`.

DEV-031. **The `_N` suffix defines the concrete patch/iteration.** In `v0.4.2_14`, `_14` is the exact package candidate and handoff boundary.

DEV-032. **An ordinary packaged source/behavior change inside the same development stage increments only `PLUGIN_REVISION`.** It does not change `VERSION` merely because a new package is built.

DEV-033. **Documentation/governance/CI-only changes change neither `VERSION` nor `PLUGIN_REVISION`.** They may advance `main` while the packaged candidate identity stays unchanged.

DEV-034. **A genuine new development stage changes the third numeric component and starts at package revision `_1`.** Do not change the third component merely because many patches accumulated; it marks a real change of development stage.

DEV-035. **A third-component transition is not a full release by itself.** `v0.4.1_N -> v0.4.2_1` may be an internal development-stage transition with no stable/Web/pkg publication.

DEV-036. **A second-component transition is owner-controlled.** The assistant must never infer or initiate `v0.4.x -> v0.5.x` from apparent readiness, technical scope, roadmap progress, or accumulated changes. It requires the owner's explicit version/transition instruction or explicit agreement to a proposed transition.

DEV-037. **A second-component transition always includes a full release and documentation-line rollover.** Therefore `second-component transition => full release`; the inverse is not true.

DEV-038. **A full release may occur without changing the second component and may use the exact current `_N` candidate.** Publication alone does not reset `PLUGIN_REVISION`; `_1` is caused by a new third-component stage or new second-component line.

DEV-039. **A full release means a complete installation-ready OPNsense delivery.** It is not merely a tag or uploaded file: the exact package must be published through the project package repository and be installable/upgradable through the OPNsense Web interface, with the associated release identity/assets verified.

DEV-040. **A testing package is not a full release.** It may be persistently published for owner testing without promoting the stable project package repository or claiming stable release status.

## E. Verification and release readiness

DEV-041. **Live release gates are selected from current risk and evidence, not from a blanket checklist.** A live-only defect fixed by the candidate, materially changed appliance-only behavior, or affected lifecycle/restoration safety requires applicable replacement live evidence.

DEV-042. **CI, FreeBSD package qualification, and live OPNsense evidence are complementary.** None may fabricate or substitute for evidence that only another layer can establish.

DEV-043. **Known critical defects block a full release.** `RESTORE_FAILED`, unverified restoration, unexplained temporary runtime/firewall residue, or another known critical defect remains a blocker until resolved and evidenced.

DEV-044. **Only explicitly selected mandatory live rows block a given release for being pending.** Unrelated regression rows remain valuable coverage but are not silently promoted to mandatory gates; an unrun row is never rewritten as PASS.

DEV-045. **Optimization decisions are measurement-driven.** If measured data does not show a meaningful benefit or reveals semantic cost, retain the simpler/accepted production architecture and close the optimization question until new evidence appears.

## Authority boundary

Current facts (for example the selected production model, current DNS status, exact next patch, or latest package) belong in `PROJECT_STATE.md` / `START_HERE.md`, not in this permanent rule book. Documentation mechanics belong to `DOC-*`; communication semantics belong to `CHAT-*`; GitHub mechanics belong to `GH-*`.

When a durable project-development rule changes, update this file using the next stable `DEV-*` ID or explicitly supersede the affected rule, then apply `DOC-008` to reconcile dependent active documents and checks.
