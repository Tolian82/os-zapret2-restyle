# os-zapret2-restyle — GitHub workflow

Official repository: `Tolian82/os-zapret2-restyle`
Primary branch: `main`
Authoritative delivery procedure: `docs/GITHUB_PUBLICATION.md`
Active decision: `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`

Normal delivery:

1. establish the exact current `main` SHA and requested scope;
2. prepare one logical change with affected documentation;
3. validate and review the complete diff;
4. publish one task branch and open one Ready PR;
5. keep any repairs in the same PR when they remain in scope;
6. require successful checks for the latest mergeable PR state;
7. squash merge using the expected head SHA;
8. verify `main` and clean the temporary branch.

CI is a merge gate, not a ban on independent analysis or separate preparation. A PR may
contain multiple same-scope work commits; `main` receives one logical squash commit.

Current versions, package candidates, active PRs, and next work belong in
`docs/PROJECT_STATE.md`, not in this stable workflow document.
