# DEC-2026-08-05 — Serial commit delivery

Status: Superseded
Superseded by:

- `DEC-2026-08-05-efficient-github-delivery.md`;
- `DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/GITHUB_PUBLICATION.md`.

## Historical context

This decision recorded the temporary execution discipline used while the Strategy Lab
hardening series was being repaired commit by commit. It required each published source
commit to finish all checks before preparation of the next patch.

That discipline helped isolate early failures, but it was later found to be too strict as
a permanent repository-wide delivery rule. It also conflicted with the approved outcome-
based GitHub workflow, where one logical PR may contain multiple same-scope work or repair
commits and independent analysis may continue while CI runs.

## Current authority

This file is retained only as historical evidence. It does not govern current work.

Active GitHub delivery rules are:

1. one logical scope per PR;
2. all PR titles, branch commit subjects, and final squash subjects begin with the exact
   current package-candidate prefix;
3. same-scope repairs may remain in the same PR;
4. the latest mergeable PR head must pass required checks;
5. `main` receives one logical squash commit;
6. unrelated work is not added to an active checked PR.

No statement in this historical decision may be used to require exactly one branch
commit, exactly one workflow run, mandatory idle waiting during CI, or automatic closure
of a valid PR after an ordinary same-scope failure.
