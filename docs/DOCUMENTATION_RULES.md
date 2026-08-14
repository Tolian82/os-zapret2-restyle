# os-zapret2-restyle — Documentation rules

Status: **CANONICAL / MANDATORY LEVEL 1**
Updated: 2026-08-14

This file is the single primary authority for **how project documentation is structured, updated,
archived and read**. General project principles remain in [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md);
GitHub delivery mechanics remain in [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md). Where an older
active document conflicts with these rules, the newer owner canon and this file win and the active
document must be reconciled.

## Numbered documentation rules

1. **Documentation is part of the project architecture.** It is not optional commentary and must move
   with the code, workflows and project decisions it describes.

2. **Every published GitHub project state must be recoverable with zero chat/model memory.** A future
   assistant must be able to determine what the project is, what recently changed, what is true now,
   what the current patch is meant to achieve, what comes next and where the full history is stored.

3. **The owner's newest unambiguous statement is current canon.** If current documentation disagrees
   with it, the documentation is stale and must be brought into agreement; old documentation does not
   override the owner.

4. **The owner-canon “Суслик” rule is permanent.** Never keep a known contradiction hidden in another
   active document. A current statement is either reconciled everywhere it can matter or explicitly
   historical/superseded.

5. **`Зафиксируй` / `запиши это` / `record this` has a strict meaning.** At the first GitHub change
   after that instruction, record the owner's words in the correct canonical/current home and perform
   a complete active-documentation sweep so no current text or CI contract can still contradict them.

6. **A stale documentation test is stale documentation.** Tests and CI rules must be updated when they
   encode superseded documentation canon; current architecture or owner intent must never be distorted
   merely to satisfy an old textual assertion.

7. **Source code and documentation answer different questions.** Source is authoritative for what the
   implementation currently does; documentation is authoritative for approved intent, current state,
   current task and future plan. A temporary difference between implementation and approved direction
   must be stated explicitly until it is removed.

8. **Owner-facing communication is normal understandable Russian by default.** Internal English terms
   are used in chat only when technically necessary and are immediately explained in Russian. Phrases
   such as “evidence/history”, “latest head” or “governance” must not be used as unexplained owner-facing
   shorthand.

9. **Use precise version terminology.** Say “second numeric component”, “third numeric component” and
   “package revision suffix” rather than relying on the ambiguous standalone word `minor`.

10. **The version hierarchy has three documentation meanings.** In `v0.4.2_14`: the second numeric
    component is `4`, the third numeric component is `2`, and the package revision suffix is `_14`.

11. **The second numeric component defines the long-lived project-state line.** Examples are `v0.4.x`,
    `v0.5.x`, `v0.6.x`. `PROJECT_STATE.md` belongs to that line and remains the current factual state
    file while the second numeric component stays unchanged.

12. **Changing the second numeric component is owner-controlled.** The assistant must never initiate
    `v0.4.x -> v0.5.x` by inference. It requires an explicit owner version/transition instruction or
    separate owner approval of a proposal.

13. **Changing the second numeric component always means a full project release.** Once the transition
    itself is authorized, its archive/release steps need no redundant second confirmation.

14. **A full release does not imply a change of the second numeric component.** The owner may publish a
    full release while remaining inside the same `v0.4.x`/`v0.5.x` line.

15. **The third numeric component identifies the current development stage/current relevance inside
    one second-component line.** For example `v0.4.1 -> v0.4.2` means the project has moved to a new
    current task/stage while still belonging to the `v0.4.x` project-state line.

16. **A third-component transition is not a full release by itself.** It may coincide with a full
    release only when the owner explicitly requests that release.

17. **A third-component transition is made only for a real change of current development stage/task.**
    Do not increment it merely because another small patch was created.

18. **When the third numeric component changes, the package revision suffix resets to `_1`.** Thus a
    normal new-stage transition is, for example, `v0.4.1_14 -> v0.4.2_1`.

19. **The package revision suffix `_N` identifies the concrete patch/iteration inside the current third-
    component stage.** `START_HERE.md` is oriented primarily to this exact current revision boundary.

20. **Before every package-revision increment, reconcile the plan and documentation.** Compare the
    proposed patch with the current plan, update `START_HERE.md` for the new revision and update
    `PROJECT_STATE.md` whenever the patch changes facts that are true for the current second-component
    line.

21. **Every GitHub delivery includes synchronized documentation even when package metadata does not
    change.** Documentation-only and CI-only changes still update the current handoff/state/plan when
    their facts or rules changed.

22. **`START_HERE.md` is the live revision-level handoff, not a historical journal.** It tells a zero-
    memory session what the current exact revision is doing and how to continue from it.

23. **The first links in `START_HERE.md` are mandatory orientation links.** The first one is
    `PROJECT_STATE.md`; it is followed by this documentation-rules file, `PROJECT_PRINCIPLES.md`, the
    GitHub publication rules, the master development plan and `INDEX.md`.

24. **`START_HERE.md` must state the current revision identity, what was just done in the current
    revision, why it was done, the intended effect/acceptance, the exact immediate next action and the
    relevant future-plan direction.** It remains concise and links to detail instead of copying it.

25. **Completed tasks flow from `START_HERE.md` into `PROJECT_STATE.md` as durable current facts.** The
    handoff then moves to the next task/revision. Detailed execution chronology flows to the current
    ledger/devlog/evidence stores rather than bloating either Level-1 file.

26. **`PROJECT_STATE.md` is scoped to the current second numeric component.** For example, throughout
    `v0.4.x` it contains the current facts accumulated and still true for that line, regardless of
    whether the third component is `0`, `1`, `2` or later.

27. **`PROJECT_STATE.md` contains current facts, not patch-by-patch history and not the exact next-task
    specification.** The exact next patch belongs in `START_HERE.md`; chronology belongs in the current
    line ledger and deep records.

28. **When the second numeric component changes, the final old `PROJECT_STATE.md` content flows into
    that line's archive before the new state is initialized.** For `v0.4.x -> v0.5.x`, the final
    `v0.4.x` state is preserved in `history/archive/v0.4.x.md`, then `PROJECT_STATE.md` is rewritten as
    the current `v0.5.x` state.

29. **Every current `PROJECT_STATE.md` ends with direct links to every completed version-line archive.**
    The list grows when new second-component lines are archived.

30. **Do not retroactively rewrite `v0.4.0` or older history into this new model.** Existing older
    archive maps remain historically valid. The state-snapshot rule applies to the current `v0.4.x`
    line when it eventually closes and to all later lines.

31. **`ROADMAP.md` is the master development plan and must always be easy to find.** It contains a
    compact ordered list of the project's major completed, current and future intentions.

32. **The master plan records every known future intention at least once.** A future task may be only a
    short line of a few words; sub-items are allowed when one line would be ambiguous.

33. **The master plan also preserves the major completed path.** Entries such as Model A testing,
    Model B testing/integration and Model C testing/integration stay visible as short checked items so
    a zero-memory reader can understand the overall development trajectory without reading a devlog.

34. **The master plan is concise by design.** Detailed implementation notes, timings and evidence do
    not belong there; link to the current ledger or deep records when needed.

35. **Documentation uses three memory levels.** Level 1 is the bounded always-read recovery set;
    Level 2 is current version-line and task-selected detail; Level 3 is archives and deep history.

36. **Level 1 consists of `AGENTS.md`, `PROJECT_PRINCIPLES.md`, this file, `START_HERE.md`,
    `PROJECT_STATE.md`, then only the current-task specialist documents named by the handoff.** Keep
    these files compact enough for frequent cold starts.

37. **The current `history/current/vX.Y.x.md` ledger is Level 2.** It stores richer chronology for the
    current second-component line and is read only when the current task needs more context than Level 1.

38. **Completed `history/archive/vX.Y.x.md` files are Level 3 archive maps/state snapshots.** Archiving
    never deletes, rewrites or folds away original detailed devlogs, patches, verification evidence,
    decisions, audits, release records or Git history.

39. **`INDEX.md` is the integrity/navigation map.** It must directly route to all Level-1 authorities,
    the current line ledger, every completed line archive and every deep-record store. It is not a
    current-state narrative.

40. **One fact has one primary current home.** `PROJECT_STATE` owns current line facts; `START_HERE`
    owns the exact revision handoff; `ROADMAP` owns the master plan; the current ledger owns richer line
    chronology; deep records own detailed execution/proof/rationale; `INDEX` owns navigation.

41. **Duplication is not preservation.** Preserve information through primary homes and durable links;
    do not copy the same long narrative into `START_HERE`, `PROJECT_STATE`, `ROADMAP`, ledger, patch and
    devlog simultaneously.

42. **Detailed action logging remains durable and discoverable.** Recent execution/proof lives in the
    existing devlog/patch/verification/decision stores and is reached through `INDEX.md` or the current
    ledger when the current task needs it.

43. **Every development stage begins and ends with documentation reconciliation.** Before work state
    objective/plan/expected result; during work record decisions that affect later work; after work
    record actual result, verification, current facts, plan progress and exact continuation.

44. **A full release always includes a complete human-facing `README.md` review.** The README must
    present the actual current product clearly, attractively and concisely and distinguish the full
    Web/pkg release from later testing candidates.

45. **A full release is a complete OPNsense delivery.** It includes the exact current candidate package,
    semantic tag, GitHub Release assets/checksum and matching Pages/pkg repository so installation or
    update is available through the OPNsense Web GUI.

46. **A testing package is not a full release.** It may be a persistent GitHub prerelease `.pkg` for
    live verification and does not promote the Pages/pkg repository.

47. **Full-release publication is independent of the package revision suffix.** A full release may use
    the current `_N` candidate; the suffix resets to `_1` because of a new third-component/second-
    component stage transition, not merely because a release is being published.

48. **The release workflow must enforce the version meanings.** A second-component change cannot pass
    without a full-release preparation; a third-component-only change may pass without a release but
    must reset the suffix to `_1`; an ordinary `_N -> _(N+1)` patch does not change `VERSION`.

49. **Repository structure and documentation must remain mutually consistent.** Keep referenced files,
    branch state, workflow contracts and documentation paths current so future work does not begin with
    avoidable rediscovery or repository cleanup.

50. **Repository hygiene is continuous.** Temporary task/publication branches are removed after their
    useful work is merged or preserved; obsolete generated/transport artifacts are not left tracked.

51. **Selected mandatory documents are read completely through EOF before mutation.** Historical
    documents are loaded only for a concrete dependency, investigation, proof or rationale question.

52. **Changes to documentation policy are made here first.** Any new or changed documentation rule must
    receive the next sequential number in this file and all affected active documents/tests must be
    reconciled in the same logical GitHub change.

## File responsibility map

The numbered rules above are authoritative. This map is descriptive and contains no additional rules.

- `AGENTS.md` — repository entrypoint and mandatory read order.
- `PROJECT_PRINCIPLES.md` — general permanent project/development principles.
- `DOCUMENTATION_RULES.md` — this file; all numbered documentation-governance rules.
- `PROJECT_STATE.md` — current facts for the active second-component line.
- `START_HERE.md` — exact current package-revision handoff.
- `ROADMAP.md` — concise master development plan.
- `history/current/vX.Y.x.md` — richer current-line chronology.
- `history/archive/vX.Y.x.md` — completed-line archive map plus, from `v0.4.x` onward, final state snapshot.
- `GITHUB_PUBLICATION.md` — GitHub/package/release procedure.
- `INDEX.md` — navigation/integrity map.
- `devlog/`, `patches/`, `verification/`, `decisions/`, `audit/`, `releases/` — deep durable records.
