# DEC-2026-08-03 — Publish Zapret2 Service as v0.3.0

Status: Active
Date: 2026-08-03

## Decision

Publish the completed and live-verified Zapret2 Service construction as immutable
release `v0.3.0` with package revision reset to `1` and package name:

```text
os-zapret2-restyle-0.3.0_1.pkg
```

Use the existing repository-owned release trigger. The release-preparation squash
subject must be exactly:

```text
release: prepare v0.3.0
```

The trigger creates annotated tag `v0.3.0` at the verified release-preparation merge
and dispatches the existing Release workflow. GitHub Release assets and the
FreeBSD:15:amd64 GitHub Pages pkg repository must be generated from the same tag.

The existing workflow continues to mark the GitHub Release as a prerelease. This
release classification does not reduce the accepted status of the Zapret2 Service
construction; it reflects the wider project release policy and remaining unrelated
backlog.

## Reason

The complete Service work package has passed focused CI, FreeBSD package builds, and
live OPNsense verification:

- release cache reuse;
- stable selected-release installation;
- Started/Stopped preservation;
- package replacement with no reboot or manual service work;
- automatic firewall prerequisites after cold reboot;
- runtime-safe Lua permissions after privilege drop;
- successful live downgrade v1.0.4 → v1.0.3;
- exact active-release marker synchronization;
- automatic rollback behavior covered by focused tests.

The project owner explicitly accepted the construction as working and authorized the
v0.3.0 publication.

## Consequences

- `VERSION` becomes `0.3.0`.
- `PLUGIN_REVISION` resets from `13` to `1`.
- The expected immutable tag is `v0.3.0`.
- The expected release asset is `os-zapret2-restyle-0.3.0_1.pkg`.
- Previous v0.2.x tags and packages remain immutable.
- Milestone 8 Task 1, GUI management of bol-van/zapret2 through setup.sh, is complete.
- Newer-release notification remains a separate future change.
- Additional BLOB-repository management remains blocked until the project owner
  supplies and approves its repository and contract.

## Affected documentation

- `README.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`
- `docs/architecture/ZAPRET2_SERVICE.md`
- `docs/audit/AUDIT-2026-08-03-ZAPRET2-SERVICE.md`
- `docs/devlog/2026-08-03-v0.3.0.md`
- `docs/releases/v0.3.0.md`
