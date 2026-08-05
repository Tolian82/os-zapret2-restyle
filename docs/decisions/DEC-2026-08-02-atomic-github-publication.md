# DEC-2026-08-02 — Atomic GitHub publication, branch ownership, and release gates

Status: Superseded on 2026-08-05

This decision solved a real branch-clutter problem, but its implementation was too rigid.
It required preparation through unreferenced Git objects, exactly one work commit and one
check set, and replacement of a valid PR after ordinary failures. In practice those rules
increased waiting, duplicated GitHub work, obscured the difference between PR history and
permanent `main` history, and were not consistently followed.

The useful safety outcomes remain active:

- one logical scope per pull request;
- no reflexive sibling branches such as `-clean`, `-final`, `-atomic`, `-fixed`,
  `-retry`, or `-publish`;
- no force-update of `main` or published tags;
- explicit patch/release separation;
- temporary branch cleanup;
- exact head/base verification before merge.

The delivery mechanics are replaced by:

- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Those authorities allow multiple same-scope commits inside one PR branch, repair in the
same PR, Ready-by-default publication, CI gating of the latest mergeable state, and
independent analysis or preparation while checks run. Squash merge still creates one
logical permanent commit in `main`.

Historical reason for this decision:
Early v0.3.2 publication attempts created multiple remote branches before the final scope
was stable. The branch-clutter lesson remains valid; the former low-level API and
one-check-set prescription does not.
