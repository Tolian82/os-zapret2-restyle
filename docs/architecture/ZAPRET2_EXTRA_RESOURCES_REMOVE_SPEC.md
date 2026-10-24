# Remove Additional Resources — approved requirements

**Project:** os-zapret2-restyle (OPNsense 26.7.x, FreeBSD 15)
**Owner decision:** 24 October 2026
**Status:** APPROVED SPECIFICATION; implementation, testing package, appliance acceptance and release NOT started.
**Related contracts:** [Additional Resources installation/GUI](ZAPRET2_EXTRA_RESOURCES_GUI.md), [new implementation plan](ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md).

## 1. Scope and invariants

Add an explicitly user-invoked **Remove Additional Resources** operation on the Strategies page. It must **physically remove** every top-level .lua file in /usr/local/etc/zapret2/lua/ and every top-level .bin file in /usr/local/etc/zapret2/files/fake/ which is **not tracked by the locally installed Zapret2 upstream Git HEAD**. Only the verified standard resources of the **same installed upstream revision** remain. Do not use the current extra-resources GitHub catalog to decide what to remove; no network/GitHub access is needed for this operation.

The approved exact-set policy applies equally to manual, outdated, unknown and plugin-managed non-upstream files. The earlier proposal to preserve manually added Lua/BIN was explicitly superseded by the owner's final decision. Never delete unrelated paths, file types, OPNsense state, saved user settings or strategies.

Before any resource deletion, **prove that ordinary saved Strategies AND saved Voice profiles can run using only the standard upstream resource set**. An incompatible or unprovable case must fail closed before stopping the service or changing any resource file. No automatic strategy modification is authorized.

This is an additional native operation, **not** a new clean-reinstall/repair tool; the owner-cancelled clean-plugin repair remains out of scope.

## 2. Exact local upstream inventory

- Use the actual installed Git checkout at /usr/local/etc/zapret2 and inspect Git HEAD via git ls-tree -r HEAD. Do not use a hard-coded version, filename list, count, upstream web catalog, or the extra-resource repository.
- Restrict the inventory and the removal plan to direct .lua children of lua/ and direct .bin children of files/fake/. Preserve the native path and filename case.
- Verify Git repository/root/HEAD provenance, tracked file type, allowed mode, file bytes, Git blob identity, bounds and symlink/path safety; an untrusted or modified tracked resource blocks the operation.
- Independently enumerate and attest the exact current on-disk Lua/BIN set, including untracked files. Refuse unsafe files, symlinks and races; do not follow links or delete foreign paths.
- Compute **remove = actual installed Lua/BIN minus Git-HEAD-tracked upstream Lua/BIN**, exact relative-path comparison. Every upstream file must remain byte-identical; any non-upstream file in these two direct directories is in scope.
- Detect strategies depending on removed files **and** Lua exported functions or transitive dependencies, including usage that does not spell out a filename.
- All affected old bytes, metadata and ownership evidence must have a durable authenticated transaction snapshot before any destructive mutation.

### Observed installed-state evidence (not hard-coded requirements)

On 24 October 2026 the owner ran a read-only installed-system inventory:

| Set | Lua | BIN | Total |
| --- | ---: | ---: | ---: |
| Installed upstream v1.0.6 | 6 | 46 | 52 |
| Managed extra catalog commit ccdd8fae375e9d3fcb2592a803e10a10d52c49f2 | 19 | 54 | 73 |
| Actual installed | 25 | 100 | 125 |
| Unmanaged files | 0 | 0 | 0 |

The integrity report contained no modified or missing resource notices. These counts are **owner-observed evidence only**, not an implementation constant or an assertion that the new removal operation has been tested.

## 3. Mandatory read-only preflight against the POST-removal resource set

The preflight executes **before Stop, resource removal, metadata changes, Config save or IPFW mutation**. It must work with a verified, isolated representation of **upstream-only** files. Never temporarily delete production files to test a strategy; do not infer future compatibility from the fact that the full current set works.

Reuse authoritative native parsing, compilation, candidate generation, shared-config preflight and resource resolution code; avoid a second simplified parser or solely searching raw Config XML for filenames.

### 3.1 Saved ordinary Strategies

Read the **persisted** Strategies config, not unsaved browser edits. Validate the complete Traffic Strategy including all --new profiles, Extra Arguments, declared BLOB payload references, implicit and explicit Lua initialization and invoked Lua functions, transitive Lua/BIN dependencies and the engine-argv/runtime compilation required by native Apply.

Relevant existing code includes backend/parser.sh, backend/profile_pipeline.sh, backend/blobs.sh, backend/orchestrator.sh and shared Apply preparation. Refactor common validation minimally so it can accept an isolated upstream-only inventory and build an inert candidate.

### 3.2 Saved Voice

Inspect all five saved Voice services: Telegram, Discord, X, SIP and Custom. Include actively enabled profiles and **saved disabled drafts with meaningful content**. A disabled draft referencing a removed dependency must block removal even if it is not currently active; a deliberately incomplete OFF draft must not be treated as a runnable ON profile or rejected solely for being incomplete.

Reuse VoiceCandidateValidator.php, VoiceController.php, voice_profile_compiler.py, voice_native_lifecycle_router.py, voice_native_draft_preview_route.py and the authoritative common Voice+Strategies compilation stages where applicable. The GUI Validate action is **only a detached model/syntax preview**; it does not itself prove availability of post-removal dependencies. The saved OFF draft preview is a read-only guarded selection, not a proof that the compiled engine starts. Implement the missing upstream-only compatibility layer without inventing a new Voice service.

### 3.3 Combined result

Build and inspect the combined Strategies+Voice candidate using the real compiler and the hypothetical upstream-only resources. A structured result is one of **compatible**, **incompatible**, or **unknown**. Only **compatible** authorizes a transaction. The test must prove resource paths/digests, relevant Lua exports and initialization, resolved BLOBs and config/argv compatibility; it does **not** claim that DPI bypass succeeds or that a live Voice call connects.

Read and pin the source Config and resource inventory under the existing safe lock ordering. Revalidate the exact Config generation, upstream commit and resource digests immediately before entering a mutating transaction. Any change or an uncertain validation result rejects the operation; the owner may retry after correcting settings.

### 3.4 Rejection message

RU: **«Ваши стратегии используют удаляемые ресурсы. Нужно привести стратегии в соответствие.»**

EN: **“Your strategies use resources scheduled for removal. Update your strategies to use the resources included in the installed Zapret2 version.”**

Show a bounded, localized diagnosis: Strategies or Voice page, specific profile, missing or incompatible Lua/BIN/function, and reason. No private XML, credentials or raw sensitive arguments. On preflight rejection: **zero file deletion, zero service Stop/Start, zero Config/IPFW edits and no change to installed-resource status.**

## 4. GUI and RU/EN

Place a new button immediately **below** the existing Install Additional Resources button:

- RU: **«Удалить дополнительные ресурсы»**
- EN: **“Remove Additional Resources”**
- Exact same button width and height as Install Additional Resources.
- Use the native OPNsense button style; button text has the existing OPNsense **text-info** blue of **«Остальные установленные ресурсы»** / **“Other installed resources”**.
- The Remove button is **visible only while the native Strategies “Advanced mode / Расширенный режим” toggle is ON** (show_advanced_frm_GeneralSettings). Hiding/showing must be immediate, including across F5 and any existing persisted toggle behavior.
- The existing Install button remains in place. The **Full Help / Справка** toggle remains independent and does not control Remove visibility.
- On click, first request the read-only plan and preflight. If compatible, show a confirmation with the exact planned Lua/BIN deletion counts before the mutation. A previously issued result cannot bypass server-side revalidation.
- While busy, use the existing per-operation ID, finite polling/spinner and disable conflicting controls. A directly invoked API must still apply the full server-side security and lifecycle guards.
- A no-op removal plan must have a truthful terminal result without needless Stop/Start.

## 5. Native transaction and recovery

Re-use the existing **ServiceController → configd → setup.lock → original native FD9 → resource transaction** path. No independent service manager, nested FD9 or alternate IPFW cleanup.

Required preconditions: an attested healthy **Started** owner, no competing setup, resource install, release switch, shared Strategies/Voice Apply, Strategy Lab or incomplete recovery journal, and a verified upstream-only compatibility preflight. A Stopped/unknown service owner is not silently started or assumed safe.

- Before Stop, durably capture and verify a full original resource-byte snapshot, original managed manifest/status (including absence), Config generation, Git HEAD, exact old/new digest inventory, journal and recovery witnesses. The existing transaction engine should own this operation.
- Under inherited locks, recheck the preflight binding; perform native Stop; delete only the attested non-upstream direct Lua/BIN paths; verify **exactly** the Git HEAD resource set remains and all original tracked upstream bytes remain unchanged.
- Perform native Start and attest healthy Started status/new process and the existing IPFW/shared ownership constraints. Commit terminal operation result only after verified restoration of a healthy running service and exact file set.
- On any failure, restore the **entire** previous resource bytes/metadata and previous native service state from the sealed snapshot. Retain evidence; on unprovable restoration, report **RESTORE_FAILED** and refuse unsafe retries. Do not modify saved user strategies, Voice configs, HOSTLIST/IPSET or unrelated files.
- Keep the existing installation semantics unchanged: the separate Install action still reconciles to installed upstream HEAD **plus** the verified immutable extra catalog, with its own restart/rollback policy.

## 6. Installed state, Full Help, cache and Strategy Lab

On verified success, the managed extra set is **not installed**, even though standard upstream Lua/BIN remain on disk:

- The active installed.json must no longer signal installed extras; retain historical audit/transaction proof separately.
- Update status.json and correlated operation receipt to mean **removed / not_installed**, not stale ready/installed. Never show “Installed Lua 19 BIN 54” after a successful removal.
- Atomically refresh or invalidate the Lua/BIN help cache. Existing cache-only GUI reads must not perform filesystem/Git work on each Full Help toggle, and stale data must not be displayed as current.
- With Full Help ON, show the existing bilingual **“Additional Resources have not been installed”** explanatory message instead of the two installed-resource columns. The Install button remains available under its existing safe conditions.
- New Strategy Lab Jobs dynamically discover the **actual remaining upstream** resources and omit extras. Previously completed Job records are immutable; do not rewrite historical findings.
- A fresh successful Install restores the normal green upstream / blue extra resource listing.

## 7. README.md documentation gate — immediately before a future stable release

Before publication of the **future release containing this Remove Additional Resources feature**, update the repository-root [README.md](../../README.md). This is an explicit **penultimate delivery milestone immediately before the separately owner-authorized stable release**; it does **not** retroactively reopen or block the independently authorized v0.5.8 release.

In **“Useful runtime paths”**, list these two exact installed Zapret2 directories alongside the existing paths:

- /usr/local/etc/zapret2/lua/ — installed Lua scripts;
- /usr/local/etc/zapret2/files/fake/ — installed BIN packet payloads.

Explain that these paths contain both current upstream resources and, when installed, supplementary resources; they are not extra-catalog-only directories.

In **“Additional Resources — installed Lua/BIN help”**, rework the introduction to clearly state that this plugin lets users **optionally install and use an expanded, integrity-verified Lua/BIN resource pack from the project's curated and verified repository** [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources). Clearly distinguish the upstream Zapret2-owned base files from the optional pack and link to its actual GitHub repository. Keep the existing factual explanation of the manual Install action, verified native restart/rollback, cached two-column Full Help inventory and its green/blue classification; explain the new Advanced-only Remove capability only after it is implemented and verified.

Use precise English in README.md. "Verified" must mean verified **source/integrity/provenance and integration controls**, **not** that every Lua module or BIN payload has independently proved a successful DPI bypass, protocol compatibility or Voice-media connectivity. Do not market unsupported candidates as tested successful bypasses. Preserve existing user-facing context and other README sections.

**Gate:** README path accuracy, repository link, manual-install/optional-use wording, existing help semantics, new feature availability claims and README/Markdown link tests all PASS on the exact release candidate. No future stable release of this feature is complete without this penultimate README review.

## 8. Required verification and acceptance

Source/offline tests must cover: dynamic HEAD selection, tracked-byte tamper, foreign/symlink paths, manually added files, exact deletion list, a saved ordinary profile referencing an extra BLOB or Lua export, active Voice dependency, OFF-draft dependency, legitimate incomplete OFF draft, valid upstream-only combined compile, unknown result, changed Config/resource generation, read-only preflight non-mutation, journal and rollback faults, disabled controls and native FD9 serialization, idempotent no-op, cache refresh/invalidation, RU/EN/Advanced/F5, new-Job dynamic inventory and repeat Install.

Use isolated/mocked fault injection; do not require destructive live OPNsense testing without an approved safety boundary. Do not label unexecuted power-cut or Voice-media scenarios as PASS.

**Owner acceptance is separate from source CI and package build.** The installed appliance must confirm the true before/after Lua/BIN list, preserved upstream digests, refusal before mutation for incompatible saved Strategies/Voice, native service health following removal, Full Help proposal, new-Job discovery and reinstallation. Stable release requires a **new explicit owner instruction**; accepting this specification authorizes documentation, not a package or release.
