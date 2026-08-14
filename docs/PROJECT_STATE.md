# os-zapret2-restyle — Current state

Status: **CURRENT**
Updated: 2026-08-14

This file answers: **Where is the project now?**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Exact continuation: `docs/START_HERE.md`.
Future work: `docs/ROADMAP.md`.

## Repository / package identity

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- semantic version: `0.4.1`;
- current packaged source revision: `12`;
- package candidate: `os-zapret2-restyle-0.4.1_12.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- testing tag: `v0.4.1_12`;
- package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`.

Documentation-only `main` may be newer than the packaged source merge. Resolve actual `main` SHA
before every mutation.

## Locked governance / owner facts

- one unambiguous owner instruction/fact/confirmed decision becomes current canon immediately;
- once accepted, it is not repeatedly reconfirmed merely because an old doc/test disagrees;
- reopen a settled factual claim only when the owner changes it or fresh direct reproducible evidence
  contradicts it;
- `зафиксируй` / equivalent requires a full reconciliation of all active authority docs that could
  contradict the new canon;
- a stale test/CI contract is corrected instead of forcing current documentation back to old intent;
- every new durable principle is added to `docs/PROJECT_PRINCIPLES.md` in the first synchronized docs
  change;
- owner-facing project status is written in clear Russian by default, with technical English/internal
  labels translated/explained when shown;
- routine temporary branch/repository cleanup is part of normal completion and is normally silent;
- every substantive GitHub delivery remains a zero-memory recovery checkpoint.

Decision:
`docs/decisions/DEC-2026-08-14-owner-canon-lock-and-repository-hygiene.md`.

## DNS state — closed fact

**DNS is fixed/currently working.**

Historical local/container DNS behavior was slow and unreliable, but the owner fixed it. Do not
classify DNS as broken again from historical evidence, an old timeout, old documentation or memory
loss. A new DNS problem requires fresh direct reproducible evidence.

## Model-C state — selection closed

**Model C is the selected normal production Stage-60 direction. A/B/C model selection is closed.**

Actual packaged `_12` source still contains legacy transition fallback:

`Model C -> Model B -> Model A cold`.

That chain describes current implementation debt only; it is not the approved long-term architecture
and cannot be used to reopen Model B as a production choice.

Roles:

- Model C — selected normal production runtime;
- Model B — reference/warm implementation plus `_12` transition fallback only;
- Model A — cold correctness/reference implementation.

Next packaged source patch `_13` removes automatic B/A production replay.

## Active architecture reconciliation

A full active-document audit after the previous continuity patch found stale current authority in:

- `docs/ARCHITECTURE.md` — old `_31` runtime state and “A/B/C not selected” text;
- `docs/architecture/STRATEGY_LAB.md` — old implementation/experiment ownership text.

Both are corrected in the current docs/governance change and now describe current Model-C architecture.
Historical experiment records remain history only.

## Model-C behavior already accepted and preserved

- native adaptive graph/planner and immutable CandidateSpec;
- job-scoped ResourceInventory;
- logical candidate width at most three;
- exact source-port-qualified attribution;
- pinned endpoints sequential inside one candidate;
- `preferred-free-else-alternate` source-port leasing;
- profile-compatible physical segmentation preserving logical batch identity;
- readiness: process identity + socket + clean log + two consecutive qualified snapshots;
- 25 ms readiness polling, bounded by 4 s;
- bounded GET-4K production discovery;
- finite `eligible-work-v1` adaptive budgets;
- cleanup/cancellation containment and Stage-90 semantic restoration;
- downstream Stage 70/80/85/result ownership.

## Accepted live evidence

Latest `_12` lifecycle/readiness evidence:

- 5/5 completed;
- 5/5 `model_c_only=true`;
- no fallback observed in the retained live replay;
- lifecycle/RSS evidence complete;
- cleanup/restoration PASS;
- physical-segment startup median `82.5 ms`;
- median aggregate RSS `4366 KiB`.

Evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Closed measurement questions

Do not reopen these merely because a new chat starts or an old plan mentions them:

- Lua initialization (`_2`): no production change justified;
- BLOB startup/RSS/common set (`_3/_4`): no material current-width penalty; no lazy-BLOB production
  change justified;
- discovery (`_5/_6`): retain bounded GET-4K;
- lifecycle (`_7` through `_12`): `_11/_12` corrected real issues; further cross-batch keep-warm/reuse
  is not justified for current architecture.

Reopen only by newer owner direction, current roadmap selection, material architecture change or fresh
direct reproducible evidence.

## Most recent docs/governance corrective

Current docs-only work is the canon-lock and active-documentation reconciliation:

- `docs/patches/v0.4.1_12-owner-canon-lock-doc-audit.md`;
- `docs/devlog/2026-08-14-owner-canon-lock-doc-audit.md`;
- `docs/decisions/DEC-2026-08-14-owner-canon-lock-and-repository-hygiene.md`.

No runtime/source/package metadata change is part of this corrective.

## Exact next packaged source change — `v0.4.1_13`

Make Model C the **only normal production Stage-60 runtime**:

- remove automatic production replay through Model B/cold Model A;
- keep Model-C infrastructure failures explicit and bounded;
- preserve leasing, attribution, segmentation, readiness, budgets, discovery, cleanup and restoration;
- retain B/A only where useful outside the normal production path.

Exact work surfaces and acceptance are in `docs/START_HERE.md`.
