# Decision: Canon lock, stale-contract handling, Russian owner communication and repository hygiene

Date: 2026-08-14
Status: **ACCEPTED / ACTIVE**

## Context

The previous continuity corrective correctly recorded that DNS had been fixed and that Model C was
the selected production direction, but the active/current-looking documentation reconciliation was
incomplete.

A broad review found three places capable of reviving obsolete model-selection state:

- `docs/ARCHITECTURE.md` still described the old `_31` state and said cold A, warm B and dispatcher C
  were experimental choices with no model yet selected;
- `docs/architecture/STRATEGY_LAB.md` still delegated runtime coexistence to the old A/B/C experiment
  plan;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` still marked itself current and
  described Model B as selected production while Model C remained future.

Those statements directly contradicted newer owner canon and could have caused a future cold-start
session to reopen an already-settled decision.

The same class of failure can appear in CI contracts: a test may encode a historical decision even
though tests must not become a competing source of product truth.

The owner also requires routine GitHub status to be understandable without decoding English/internal
GitHub terminology, and routine temporary-branch cleanup to be completed as part of the task rather
than escalated as an owner problem.

## Decision

### 1. Canon lock after one unambiguous owner statement

An unambiguous owner instruction, explicit project fact or explicitly confirmed decision becomes
current canon immediately.

Once accepted:

- do not repeatedly reconfirm it;
- do not phrase later work as if the decision is uncertain;
- do not reopen it because an old doc/test/roadmap says otherwise;
- reopen only if the owner explicitly changes it or fresh direct reproducible evidence contradicts a
  factual assertion.

Current locked examples:

- DNS is fixed. Historical DNS slowness/failures are closed unless fresh direct evidence shows a new
  DNS problem;
- Model C is selected as the normal production Stage-60 direction. A/B/C model selection is closed.

### 2. `Зафиксируй` means full active-authority reconciliation

When the owner says `зафиксируй`, `запиши это`, `record this` or equivalent, the first GitHub docs
change must:

1. write the new canon into the canonical principles/current handoff as applicable;
2. inspect all active/current/current-looking authority documents capable of contradicting it;
3. correct every active contradiction in the same logical change;
4. leave old statements only in clearly historical/superseded records that cannot be mistaken for
   current authority.

A narrow update to only one current-state file is insufficient when architecture/procedure/current
specialist or current-marked verification/experiment docs can still state the opposite.

### 3. Tests/CI do not override current canon

If a test or CI contract asserts a superseded decision, the contract is stale.

The correct response is to update the stale test/contract and synchronize current docs as needed.
Current architecture/documentation must never be bent back toward obsolete intent merely to satisfy a
stale assertion.

A still-valid test that protects the **new** direction remains valid even if its wording originated
before the current docs sweep. Example: the contract that says not to spend the next patch improving
`C -> B` remains aligned with the Model-C-only transition, so it is preserved rather than deleted.

### 4. Owner-facing status is clear Russian

Routine project status and completion reports to the owner are written in understandable Russian.
Internal English/GitHub/CI labels are secondary evidence, not the primary explanation.

When a technical term is materially useful, translate/explain it immediately and state the practical
meaning: what succeeded/failed and what happens next.

### 5. Repository hygiene is continuous and normally silent

Temporary task/publication branches are implementation machinery, not owner-maintained state.

After a logical task is merged/completed:

1. verify whether the temporary branch contains useful unique work not present in `main`;
2. if useful unique work exists, preserve it in the appropriate working/history path first;
3. otherwise remove the temporary branch;
4. verify normal branch state afterward.

Routine cleanup is performed without asking the owner or reporting ordinary cleanup as a problem.
Only a real permission/tooling boundary that prevents safe cleanup is owner-relevant.

## Active/current-looking documentation correction performed with this decision

The broad review corrects/reclassifies:

- `docs/ARCHITECTURE.md` — rewritten as current Model-C architecture;
- `docs/architecture/STRATEGY_LAB.md` — rewritten as current base Strategy Lab contract while
  preserving useful lifecycle/stage/interface/probe/report behavior;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` — converted from a misleading
  `CURRENT` Model-B-era plan into **HISTORICAL / COMPLETED** experiment/evidence history. The complete
  pre-archive text remains available in Git history at commit
  `938d01bca0617d4dad6e4715e637ebd2a3cb11f4`.

The current handoff/state/roadmap/procedure/principles/index and patch/devlog records are synchronized
with the same rule set.

## Consequences

- a future session must not ask again whether DNS is fixed or whether Model C was selected merely
  because old material exists;
- old active/current-looking architecture or experiment plans cannot coexist as competing authority
  with newer owner canon;
- a canon-recording request automatically expands documentation scope to all conflicting active/
  current-looking authority files;
- stale tests are corrected rather than allowed to dictate obsolete architecture;
- useful historical evidence is preserved but clearly separated from current authority;
- owner reports become Russian and outcome-oriented;
- repository branch hygiene is a normal completion obligation.

## Supersession boundary

This decision strengthens, and does not weaken:

- `DEC-2026-08-14-owner-canon-and-zero-memory-recovery.md`;
- `DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`;
- evidence-first debugging and source-code authority for actual currently implemented behavior.

Source may temporarily contain transition debt, but that debt does not reopen an already-selected
product direction.
