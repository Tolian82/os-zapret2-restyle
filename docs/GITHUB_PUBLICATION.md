# GitHub publication and delivery discipline

Status: **AUTHORITATIVE PROCEDURE**

Permanent principles: `docs/PROJECT_PRINCIPLES.md`.
Current task: `docs/START_HERE.md`.

Read completely immediately before GitHub mutation.

## GitHub plugin boundary

Use the connected GitHub plugin first for every supported operation. A narrow fallback is allowed only
when the plugin is responding and one exact required function/permission is unavailable. Plugin
unavailability/non-response or inability to read required authoritative state is a stop condition.

## Scope-first preflight

Always verify:

1. exact current `main` SHA;
2. `VERSION` and `PLUGIN_REVISION`;
3. newest owner canon + current documented task/plan;
4. same-scope/relevant open PR state;
5. plugin availability.

Expand inventory only when needed: CI logs for CI diagnosis, release assets for package/release work,
branch inventory for cleanup, protection state for permission work, recursive tree for genuine broad
cross-cutting audits, and active-authority document sweep when the owner asks to record/reconcile canon.

## Owner canon / stale contract handling

A newer unambiguous owner instruction/fact/confirmed decision wins immediately over older docs, tests
and plans.

Do not ask again merely because an old authority disagrees. Reopen only on owner change or fresh
direct reproducible evidence for a factual claim.

When the owner says `зафиксируй`, `запиши это`, `record this` or equivalent, the first GitHub docs
change must review and correct **all active/current authority files capable of contradicting the new
canon**.

If CI/test code encodes superseded canon, update the stale contract. Never edit current architecture
back toward obsolete intent simply to satisfy such a test.

## Zero-memory documentation gate

Before the first substantive changed branch state is published, and again before final merge, the
logical change must make the repository self-contained for a future zero-memory restart:

- most recent completed logical work/recovery boundary;
- what changes and why;
- intended effect + acceptance;
- exact immediate next step;
- complete near-term/long-term/deferred plan;
- all new durable principles in `PROJECT_PRINCIPLES.md`;
- detailed patch/devlog/evidence pointer;
- full reconciliation against newest owner canon.

## Candidate identity / titles

Derive from proposed head:

- semantic version from `VERSION`;
- package revision from `PLUGIN_REVISION`;
- prefix `v<VERSION>_<PLUGIN_REVISION>:`.

Every PR title, branch commit subject and final squash subject uses the exact candidate prefix.
Docs/governance/CI-only changes do not alter package metadata.

## Ordinary development flow

1. resolve owner scope + newest canon;
2. complete mandatory startup/task reading;
3. scope-first preflight;
4. create one task branch from exact base;
5. implement one logical scope + synchronized documentation;
6. validate and review complete diff;
7. reconcile zero-memory handoff/current plan;
8. open one Ready PR (Draft only for intentional WIP);
9. keep same-scope repairs in same PR;
10. require successful checks for latest mergeable head;
11. re-reconcile canon/plan and verify exact head;
12. squash merge once with exact versioned subject;
13. verify resulting `main`;
14. perform repository/temporary-branch cleanup.

## CI failure handling

Read exact failed-job evidence before changing anything.

- same-scope source/docs/test defect -> repair same PR;
- stale test/CI assertion conflicting with newer owner canon -> update stale contract, not current canon;
- external GitHub/runner/network/action outage -> no speculative source change;
- metadata defect -> correct metadata;
- materially wrong base/scope/history -> replace only with evidence;
- missing protected authority/credentials/plugin -> stop at boundary.

Do not create retry/final sibling branches or replacement workflows without evidence.

## Repository / branch hygiene

Repository hygiene is part of normal completion and normally requires no owner interaction.

After merge/completion:

1. inspect the temporary branch against `main`/merged work;
2. if it contains useful unique work, preserve that work first in the correct branch/history path;
3. otherwise remove the temporary branch;
4. verify no obsolete task/publication branch remains;
5. keep `main` as normal steady-state branch authority (plus intentionally retained documented
   recovery references).

Do not tell the owner to clean ordinary temporary branches. Do not report routine cleanup as a problem
unless an actual tool/permission boundary prevents safe completion.

## Owner-facing status presentation

GitHub execution details may be technical internally, but owner reports are clear Russian by default.

Prefer practical wording such as:

- `Проверки прошли успешно` rather than requiring the owner to decode raw check names;
- `изменение слито в main` rather than unexplained `exact-head squash merge`;
- `пакет не собирался, потому что менялась только документация` rather than raw skipped-job jargon.

If an internal English term/check name is important evidence, show it secondarily and explain it in
Russian in the same sentence.

## Testing package delivery

Any owner request for installable package/patch bytes means a persistent GitHub `.pkg`, unless the
owner explicitly asks only for build/CI evidence.

Actions artifacts/local files are build evidence only.

`не релиз, а пакет` means:

- no semantic VERSION promotion;
- no stable/full project release;
- no Pages/pkg-repository promotion;
- yes: deterministic testing `.pkg` persisted on GitHub.

The package request itself authorizes deterministic testing-package publication; no second routine
confirmation is required.

When verified bytes exist:

1. bind exact source/build/artifact/digest;
2. verify package version/ABI/arch;
3. publish exact testing tag/asset through the plugin where supported, narrow fallback only for the
   missing exact function;
4. verify target SHA/tag/flags/asset identity/digest;
5. record publication identity in documentation;
6. clean temporary publication branch.

## Full semantic release

Separate from testing-package publication. Requires explicit exact new `VERSION` authority and
current product/live release gates.

Normal preparation:

- set new VERSION;
- reset `PLUGIN_REVISION=1`;
- verified release-preparation PR/merge;
- immutable semantic tag;
- release/package/pkg-repository/Pages pipeline defined by current release procedure.

Never rewrite published `main`, tags, releases, assets or package history.

## Authority boundaries

Standing owner authorization for `fix/add/change/implement/complete` covers routine task branch, Ready
PR, CI inspection, same-scope repair, squash merge, main verification and cleanup.

Stop for owner input only on material product ambiguity, relevant unpublished owner-local state,
owner-only live evidence, credentials/protected authority, destructive work affecting user/pre-existing
remote data, history rewrite/direct-main publication, unresolvable required-check failure or GitHub
plugin unavailability.
