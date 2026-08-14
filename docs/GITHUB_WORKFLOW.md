# os-zapret2-restyle — GitHub workflow

Official repository: `Tolian82/os-zapret2-restyle`
Primary branch: `main`
Authoritative procedure: `docs/GITHUB_PUBLICATION.md`

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Operational handoff: `docs/START_HERE.md`.
Current state: `docs/PROJECT_STATE.md`.

## Before work

Mandatory context order is controlled by root `AGENTS.md`:

`AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> task specialists`.

For GitHub mutation, then read `docs/GITHUB_PUBLICATION.md` completely.

## Scope-first preflight

Always verify:

- current `main` SHA;
- `VERSION` / `PLUGIN_REVISION`;
- current documented task/plan;
- same-scope open PR state;
- GitHub-plugin availability.

Expand inventory only when the operation needs it: CI runs/logs, release/artifact state, complete
branch inventory, protection settings or recursive tree.

## Documentation gate

Before publication confirm project docs record:

1. what changes and why;
2. expected result and acceptance;
3. complete immediate + long-term plan.

Immediately before publication reconcile the plan against implementation/testing and update changed
priorities first.

## Ordinary change

1. record exact base and scope;
2. create one task branch;
3. implement code + synchronized docs;
4. run focused validation and review complete diff;
5. reconcile current/future plan;
6. open one Ready PR;
7. keep same-scope repairs in the PR;
8. require successful latest-head checks;
9. squash merge exact expected head with versioned subject;
10. verify `main` and branch cleanup.

Draft is optional for intentional WIP only.

Every PR title/branch commit/squash subject starts with exact candidate prefix
`v<VERSION>_<PLUGIN_REVISION>:`.

## CI failure

Read exact failed-job evidence before source/workflow/runner changes.

- same-scope defect -> repair same PR;
- external infrastructure -> no source change, at most one unchanged rerun after recovery;
- second unchanged infrastructure failure -> stop for diagnosis;
- plugin unavailable -> stop GitHub work.

## Testing package

Owner package/testing/install request means persistent GitHub `.pkg` unless explicitly requesting
build/CI evidence only.

- Actions artifacts/local files are not final delivery;
- `не релиз, а пакет` still publishes a testing `.pkg`, but no semantic release/Pages/pkg repo;
- package request itself authorizes deterministic testing-package publication;
- verify exact source/tag/asset/digest/direct URL;
- use generic `publish-prerelease.yml` only when build-and-publish automation is needed;
- remove temporary publication branch after success.

## Full release

Requires explicit semantic VERSION authority, revision reset to `1`, versioned preparation title,
verified merge/tag and the full release/package/Pages/pkg-repository pipeline.

Never rewrite published `main`/tags/assets/history.

## OPNsense

Owner console is root `csh`; POSIX-only commands must explicitly enter `sh` and return with `exit`.
