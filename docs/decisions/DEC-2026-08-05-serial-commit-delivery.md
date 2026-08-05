# DEC-2026-08-05 — Serial commit delivery

Status: Active

## Decision

Repository work is performed strictly one published commit at a time.

For every logical patch, the mandatory sequence is:

1. prepare and validate one logical change;
2. create and publish exactly one commit;
3. wait until every required GitHub check for that commit reaches a terminal state;
4. repair same-scope failures before starting any later logical patch;
5. verify the remote commit and its completed checks;
6. only then begin preparation of the next commit.

No later patch may be prepared, committed, or published while the current commit has queued or running checks. Several unverified commits must never be stacked on the working branch.

A pull-request metadata correction, such as fixing the required package-candidate title, may be made while validating the current commit because it does not change the source tree. Its resulting check must also finish successfully before the next source commit begins.

## Reason

GitHub checks and package validation belong to the exact source commit that triggered them. Stacking later commits before the previous commit is complete obscures the failing scope, invalidates the intended one-patch/one-verification cycle, and makes recovery slower and less reliable.

## Consequences

- One logical change remains one atomic commit.
- One commit is fully published and verified before the next change starts.
- A failed check is handled within the current patch scope.
- The branch always has at most one source commit awaiting verification.
- The complete corrective programme is delivered as an ordered sequence rather than as a batch of unverified commits.
- This decision supersedes any earlier wording that allowed preparation or publication of a later patch before the preceding commit completed its required checks.

## Affected documents

- docs/decisions/DEC-2026-08-05-serial-commit-delivery.md
- docs/WORKING_CONVENTIONS.md
- docs/DEVELOPMENT_GUIDE.md
- docs/DECISIONS.md
- docs/GITHUB_WORKFLOW.md

The specialist documents must be synchronized in subsequent governance patches using this serial rule; this decision file is the immediate authoritative record requested by the project owner.
