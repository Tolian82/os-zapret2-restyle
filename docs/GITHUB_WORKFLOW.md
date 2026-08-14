# os-zapret2-restyle — GitHub workflow

Official repository: `Tolian82/os-zapret2-restyle`
Primary branch: `main`
Authoritative procedure: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
Documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)

## Before work

Mandatory context order is controlled by root `AGENTS.md`:

`AGENTS -> PROJECT_PRINCIPLES -> DOCUMENTATION_RULES -> START_HERE -> PROJECT_STATE -> task specialists`.

`START_HERE` links the master plan and index at its top. Before GitHub mutation read
`GITHUB_PUBLICATION.md` completely.

## Scope-first preflight

Verify current `main`, `VERSION`, `PLUGIN_REVISION`, current revision handoff, current second-component
state, master plan, same-scope PR state and GitHub-plugin availability.

## Documentation gate

Every delivery must leave a zero-memory checkpoint. Reconcile:

- `START_HERE` — exact `_N` revision work/effect/next step;
- `PROJECT_STATE` — durable current facts for the second-component line;
- `ROADMAP` — complete concise completed/current/future plan;
- `INDEX` — navigation integrity;
- current line ledger/deep records — only when distinct chronology/proof is useful.

Owner `зафиксируй` invokes the complete active-document “Суслик” reconciliation from
`DOCUMENTATION_RULES.md`.

## Version flow

- same development stage: keep third component, increment `_N` for packaged source change;
- new development stage: change third numeric component and reset `_N` to `_1`;
- third-component-only transition: no automatic full release;
- second-component transition: owner-authorized only, reset `_N` to `_1`, archive state/line and full release;
- full release inside same second-component line: allowed at the current exact `_N` candidate when
  explicitly requested; release itself does not reset `_N`.

## Ordinary change

1. exact base/scope;
2. one task branch;
3. implementation + synchronized documentation;
4. focused validation + complete diff review;
5. handoff/state/master-plan reconciliation;
6. one Ready PR;
7. same-scope repairs stay in that PR;
8. latest-head required checks pass;
9. exact-head squash merge with current candidate prefix;
10. verify `main` and clean temporary branch.

## CI failure

Read exact failed evidence before changing code or workflows. Repair same-scope defects in the same PR;
update stale assertions; do not make speculative source changes for external infrastructure failures.

## Testing package

Persistent GitHub `.pkg` for testing; no full release and no Pages/pkg-repository promotion.

## Full release

Explicit owner authority; exact current candidate; full README review; merge subject
`v<VERSION>_<PLUGIN_REVISION>: Prepare release v<VERSION>`; immutable semantic tag; normal GitHub
Release assets/checksum; matching Pages/pkg repository ready for OPNsense Web installation.

A change to the second numeric component always requires this full-release path. A full release does
not itself require such a change.

## OPNsense / communication

Owner console is root `csh`; POSIX-only commands explicitly enter `sh` and return with `exit`.
Owner-facing project communication is normal understandable Russian; explain internal English terms.
