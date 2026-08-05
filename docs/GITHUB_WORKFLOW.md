# os-zapret2-restyle — GitHub workflow

Official repository: `Tolian82/os-zapret2-restyle`
Primary branch: `main`
Authoritative delivery procedure: `docs/GITHUB_PUBLICATION.md`
Active delivery decision: `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`
Active title decision: `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`

Normal delivery:

1. establish the exact current `main` SHA and requested scope;
2. derive the exact package-candidate prefix from `VERSION` and `PLUGIN_REVISION`;
3. prepare one logical change with affected documentation;
4. validate and review the complete diff;
5. publish one task branch and open one Ready PR;
6. keep any repairs in the same PR when they remain in scope;
7. require the exact package-candidate prefix in the PR title and every branch commit
   subject;
8. require successful checks for the latest mergeable PR state;
9. squash merge using the expected head SHA and the same exact versioned prefix;
10. verify the resulting `main` commit subject and clean the temporary branch.

CI is a merge gate, not a ban on independent analysis or separate preparation. A PR may
contain multiple same-scope work commits; `main` receives one logical squash commit.

Every GitHub-delivered title begins with the exact current working candidate, for example:

`v0.3.2_24: Restore universal versioned GitHub titles`

This applies equally to code, documentation, governance, CI, maintenance, and release
preparation. Non-packaged changes keep package metadata unchanged and reuse the current
prefix.

Current versions, package candidates, active PRs, and next work belong in
`docs/PROJECT_STATE.md`, not in this stable workflow document.
