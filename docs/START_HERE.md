# os-zapret2-restyle — current handoff

[PROJECT_STATE](PROJECT_STATE.md) · [DOCUMENTATION_RULES](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES](PROJECT_PRINCIPLES.md) · [CHAT_RULES](CHAT_RULES.md) · [GITHUB_PUBLICATION](GITHUB_PUBLICATION.md) · [ROADMAP](ROADMAP.md) · [INDEX](INDEX.md).

## Exact source boundary

**13 November 2026 — `v0.6.5_15`** (`VERSION=0.6.5`, `PLUGIN_REVISION=15`). This is a documentation-only reorganization of source `277ef0536b217841ab6728ae9561dbc4792fef01` / `v0.6.5_14`; no `_15.pkg` is built or published. The owner-installed stable package remains `os-zapret2-restyle-0.6.5_1.pkg`.

**Current handoff identity:** `v0.6.5_15` · `VERSION=0.6.5` · `PLUGIN_REVISION=15` · prospective `os-zapret2-restyle-0.6.5_15.pkg` **NOT PUBLISHED**.

The documentation review separates current rules, contracts, facts and navigation from revision diaries and closed plans. Original text, including duplicates and superseded statuses, is preserved in the [review archive](history/stages/documentation-2026-11-13/README.md). See the [file-by-file review](audit/DOCS-2026-11-13-INVENTORY.md) and [findings](audit/DOCS-2026-11-13.md).

The owner resolved two policy questions during this review: support includes the latest stable release, latest testing prerelease and `main`; Voice UDP ports / an additional IPv6 checkbox / P2P remain deferred long-term work, with their detailed design kept in active documentation. [Decision](decisions/DEC-2026-11-13-documentation-review-owner-clarifications.md).

## Established implementation boundary

Feature [#1052](https://github.com/Tolian82/os-zapret2-restyle/issues/1052) remains the active product workstream. P0/P1 are complete. P2a–P2d provide protected queue primitives, a FreeBSD saved-inode FD probe, detached owner attestation and original-generator source attribution. P2e (`_14`) adds an actual disposable `orchestrator_build_release()` integration witness. The scoped native OPNsense/FreeBSD original-builder witness already passed ([P2e qualification](verification/P2E_ORIGINAL_SHARED_BUILDER.md#recorded-qualification)). This is source/offline-builder proof; it does not establish a live schema-2 generation, native observer, raw/debug collection, durable destination writes or an active cron worker. P2 and P3–P5 remain open.

## One next action

After the documentation review, continue P2 with the original-generator trailing no-action observer and schema-2 current-owner/raw/debug generation contract, before any durable destination writes or cron activation. The actual offline P2e original-builder test already passed on disposable OPNsense 26.7 in [native run #43392107224](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43392107224); do not repeat that completed gate. This documentation task does not start a runtime experiment or reopen accepted features.

## Minimum specialist reading

1. [#1052 specification](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md).
2. [P0–P5 plan](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).
3. [P2e proof boundary](verification/P2E_ORIGINAL_SHARED_BUILDER.md) and its linked P2d producer contract.

Reuse unchanged P0/P1 evidence. Preserve one shared engine/Config/FD9 owner, Voice, WAN-first, native package lifecycle and immutable published artifacts. Source, CI/package qualification and owner-appliance acceptance remain distinct.
