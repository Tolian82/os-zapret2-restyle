# DEC-2026-08-13 — GitHub-only owner package delivery

Status: **ACTIVE**
Date: 2026-08-13

## Context

The project already had an installable-patch shorthand, but its wording was too narrow. It explicitly mapped phrases such as `дай мне патч для установки` to a persistent GitHub `.pkg`, while a request such as `сделай пакет для тестирования` could still be interpreted as permission to stop at a GitHub Actions artifact or to hand the owner a local/sandbox copy.

That distinction is wrong for this project. The owner keeps project deliverables on GitHub so package bytes, source identity and documentation are not lost or detached from repository history. GitHub Actions artifacts are useful build evidence, but they expire and are not the final owner-facing delivery channel.

A second process defect was exposed at the same time: required documentation can be returned by tools in truncated chunks. Merely opening a required file is not equivalent to reading it. Required documents must be consumed through EOF before action.

## Decision

### 1. Every owner-facing package is delivered from GitHub

Whenever the owner asks to build, make, give, publish, install or test a package/patch — including obvious Russian equivalents such as `пакет`, `пакет для тестирования`, `тестовый пакет`, `патч`, `патч для установки`, `дай пакет`, `собери пакет` — the requested deliverable is a persistent GitHub-hosted `.pkg`.

The request itself authorizes publication of the deterministic current testing package candidate needed for that request. Do not ask for an additional publication confirmation merely because GitHub technically stores the package in a prerelease container.

The normal delivery path is:

1. complete the ordinary branch → Ready PR → latest-head CI → exact-head squash merge cycle when source changes are required;
2. use the verified FreeBSD 15 package build as evidence/input;
3. publish the exact `.pkg` persistently on GitHub using the repository's testing-package publication mechanism;
4. verify source SHA/tag, package filename, size/digest and direct GitHub download URL;
5. document why the package exists, what it contains, and its exact publication identity;
6. return the direct GitHub `.pkg` URL or csh-safe OPNsense installation command.

### 2. Actions artifacts are build evidence, never final delivery

A GitHub Actions artifact may be retained and reused as immutable build evidence, but it is not completion of an owner package request.

Do not present any of the following as the final project package:

- an Actions artifact ZIP or artifact-download procedure;
- a local/container/sandbox file link;
- a temporary file that is not persistently hosted by this GitHub repository.

If a package has only been built in CI, the state is `BUILD ARTIFACT READY / GITHUB PACKAGE PUBLICATION PENDING`, not `PACKAGE READY FOR OWNER TESTING`.

### 3. “Package, not release” means no full project release

The owner's wording `не релиз, а пакет` (and equivalent wording) means:

- do **not** change semantic `VERSION` merely to deliver the package;
- do **not** perform a stable/full project release;
- do **not** publish GitHub Pages or promote the pkg repository;
- **do** persistently publish the requested testing `.pkg` on GitHub.

The repository may technically use a GitHub prerelease/tag as the storage container for the testing `.pkg`. That technical container is **testing package publication**, not a stable/full project release. Do not use the word “release” in a way that implies a semantic project release when reporting this operation to the owner.

### 4. Required documentation must be read through EOF

For every document that `AGENTS.md`, `docs/INDEX.md` or the current specialist scope marks as required:

- start at the first line and continue until EOF before taking project action;
- if a connector/tool response is truncated, paginated, clamped or range-limited, fetch the remaining ranges until the complete document has been consumed;
- do not treat a successful `fetch_file`/open call as proof that the whole document was read;
- if a required document cannot be read completely, stop before mutation and report the boundary instead of guessing from partial text or chat memory.

This completion rule applies especially before GitHub mutation, package delivery, release work, OPNsense command generation and source changes.

## Boundaries

This decision does not automatically authorize:

- a stable semantic release;
- `VERSION` changes unrelated to the requested package;
- GitHub Pages publication;
- pkg-repository promotion;
- rewriting existing published tags/assets;
- unrelated source changes.

An owner instruction explicitly requesting **build/CI evidence only and no package delivery** may stop at the Actions artifact. That is the narrow exception; ordinary wording asking for a package is not such an exception.

## Supersession

This decision broadens and supersedes the narrow phrase-matching boundary in `DEC-2026-08-07-installable-patch-shorthand.md`. That older decision remains valid for the mechanics of deterministic testing-package publication and one-command OPNsense installation.

It also supersedes any active wording that describes an Actions artifact or local/sandbox copy as sufficient owner delivery of a requested package.

## Affected controls

- `AGENTS.md`;
- `docs/INDEX.md`;
- `docs/PROJECT_STATE.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/GITHUB_WORKFLOW.md`;
- `docs/decisions/DEC-2026-08-07-installable-patch-shorthand.md`;
- current package/verification records that incorrectly describe an Actions artifact as owner-ready delivery.
