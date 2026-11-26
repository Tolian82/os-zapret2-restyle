# Project development rules

**Status:** CANONICAL · MANDATORY LEVEL 1
**Updated:** 2026-11-26

This is the normative home for fundamental product architecture, engineering safety, ownership, versioning and release semantics. General planning and testing definitions have moved without renumbering to the linked specialist books. The six-book reference registry resolves IDs by actual physical home.

Other canonical rule domains:

- [`DEVELOPMENT_PLANNING.md`](DEVELOPMENT_PLANNING.md) — specification, planning and functional-block execution;
- [`TESTING_RULES.md`](TESTING_RULES.md) — risk, verification, acceptance and CI test selection.

- [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — documentation governance (`DOC-*`);
- [`CHAT_RULES.md`](CHAT_RULES.md) — owner/assistant communication semantics (`CHAT-*`);
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — GitHub operations (`GH-*`).

Current product facts belong in `PROJECT_STATE.md`; concrete subsystem contracts belong in requirements/architecture.

## Owner canon and engineering authority

DEV-001. **The owner's newest unambiguous project instruction, fact, or approved decision is immediately binding project canon.** It supersedes conflicting older active plans, assumptions, preferences, or normative text. It may not be silently deferred, weakened, or reinterpreted merely to preserve stale material; chat execution semantics are reinforced by `CHAT-007`, `CHAT-009`, and `CHAT-026`.

DEV-002. **Accepted owner canon remains locked until the owner explicitly changes it or fresh direct reproducible evidence disproves the factual premise.** Loss of conversational memory, an old document, or a stale test is not counter-evidence.

DEV-003. **The “Суслик” principle is permanent.** If implementation, active documentation, tests, or plans contradict the newest unambiguous owner canon, the contradiction is a project defect to reconcile; do not reinterpret the owner's words merely to preserve stale project material.

DEV-004. **Settled findings stay settled.** Do not reopen a completed investigation or design choice solely because a later session starts with less context. Reopen only for a new owner decision, changed requirement, or fresh direct evidence material to the conclusion.

DEV-005. **Source and approved intent have different authority.** Committed source is authoritative for what is implemented; owner-approved requirements/architecture/current-state documentation is authoritative for intended direction. A mismatch is explicit transition debt, not permission to silently choose one narrative.

DEV-006. **A project decision must have an evidentiary or owner-authority basis.** Do not turn a guess, convenience, benchmark projection, or tooling limitation into architecture canon.

## Engineering quality and change discipline

DEV-008. **Preserve working behavior before optimizing it.** Optimization is justified only when the relevant cost or defect is measured or otherwise demonstrated and required semantics are preserved.

DEV-009. **Do not hide behavior behind silent magic.** Important defaults, fallback, state mutation, lossy normalization, recovery, or failure handling must be explicit enough to reason about and verify.

DEV-010. **Failure classes must remain truthful.** Infrastructure, internal, restoration, or validation failures must not be reported as normal network candidate failure, completion, or success merely to simplify control flow.

DEV-018. **Do not change approved architecture merely to make an old test or old implementation path convenient.** First determine whether the contract or implementation is stale. A delivery defect is repaired in the existing architecture unless reproducible evidence establishes that architecture as the blocker and the owner approves a changed direction. Repeated internal checks alone do not justify another architecture rewrite.

## Runtime and product-safety invariants

DEV-020. **Runtime/lifecycle changes fail closed.** Preserve bounded actions, transactional mutation, explicit ownership, cleanup on success/failure/cancel, and verifiable restoration.

DEV-021. **Semantic restoration is stronger than command success.** When work temporarily changes runtime state, success requires the required final semantic state/evidence, not merely a zero exit code or new process ID.

DEV-022. **A restoration failure outranks a useful intermediate result.** Never hide `RESTORE_FAILED` or equivalent unsafe residue behind a successful search, setup, Apply, package, or diagnostic result.

DEV-023. **A subsystem has one authoritative owner for each piece of mutable state or policy.** Compatibility layers may adapt inputs/outputs but must not recreate a competing source of truth.

DEV-024. **Preserve native Zapret2 semantics.** Candidate syntax, Lua/BLOB identity, filters/ranges, and upstream behavior are not approximated or normalized into a different strategy unless a specific approved design intentionally changes them.

DEV-025. **Project source shell is POSIX `/bin/sh` unless a documented boundary explicitly requires something else.** FreeBSD-specific commands are allowed; shell-language assumptions remain deliberate and testable.

DEV-026. **Repository/package identity remains independent.** The project is `Tolian82/os-zapret2-restyle`, package `os-zapret2-restyle`, and internal service key `zapret`; inherited upstream/fork identity must not leak back into product ownership. Changing the service key or product identity requires explicit owner approval.

## Version semantics

DEV-027. **`VERSION` is the single project-version source.** Its value has exactly three numeric components `A.B.C`.

DEV-028. **`PLUGIN_REVISION` is the monotonically increasing `main` source-revision suffix `_N` for the current `VERSION`.** It identifies the exact merged source snapshot and, only when built and published, the corresponding installable OPNsense package identity. A revision may legitimately exist in `main` without a built or published `.pkg`; publication state must be stated separately.

DEV-029. **The second numeric component defines the long-lived project-state/release line.** In `v0.4.2_14`, `4` defines line `v0.4.x` and the scope of `PROJECT_STATE.md`.

DEV-030. **The third numeric component defines the current development stage/task.** In `v0.4.2_14`, `2` identifies the genuine current development stage inside `v0.4.x`.

DEV-031. **The `_N` suffix identifies one distinct merged source revision within the current `VERSION`.** In `v0.4.2_14`, `_14` identifies the source snapshot, prospective package candidate and handoff boundary. It is a revision suffix, **not** the semantic-version minor component (`B` in `A.B.C`).

DEV-032. **Every new commit incorporated into `main` increments `PLUGIN_REVISION` exactly once (`_N` -> `_N+1`) while `VERSION` remains unchanged, without exception for documentation, governance, CI, tests or packaging.** One squash-merged PR produces one `main` commit and one increment; fixup commits on an *unmerged task branch* do not consume further revisions. Never skip, reuse, decrement or manually reserve suffixes. `VERSION` does not change merely because `main` advances. A genuine authorized `VERSION` transition resets the revision to `_1` instead, under `DEV-034`–`DEV-037`.

DEV-033. **Even documentation, governance, test and CI-only changes must increment `PLUGIN_REVISION` when merged into `main`.** Such a source-only revision does **not** automatically build or publish a package, move any immutable tag, authorize owner installation or constitute a stable release. Pull-request edits, unsquashed task-branch commits, issue/PR comments, CI re-runs, GitHub metadata and release/tag publication without a new `main` commit do **not** independently increment either `VERSION` or `PLUGIN_REVISION`. GitHub enforcement is defined in `GH-014`–`GH-016` and `GH-049`.

DEV-034. **A genuine new development stage changes the third numeric component and starts at package revision `_1`.** Do not change the third component merely because many patches accumulated; it marks a real stage change.

DEV-035. **A third-component transition is not a full release by itself.** `v0.4.1_N -> v0.4.2_1` may be an internal development-stage transition with no stable/Web/pkg publication.

DEV-036. **A second-component transition is owner-controlled.** The assistant never infers or initiates `v0.4.x -> v0.5.x` from apparent readiness, scope, roadmap progress, or accumulated changes. It requires the owner's explicit transition/version instruction or explicit agreement to a proposal; GitHub enforcement is in `GH-047` and `GH-051`.

DEV-037. **A second-component transition always includes a full release and documentation-line rollover.** Therefore `second-component transition => full release`; the inverse is not true. Documentation rollover follows `DOC-028`; GitHub enforcement follows `GH-047` and `GH-051`.

DEV-038. **A full release may occur without changing the second component and may use the exact current `_N` candidate.** Publication alone does not reset `PLUGIN_REVISION`; GitHub publication follows `GH-041`.

DEV-039. **A full release means a complete installation-ready OPNsense delivery.** It is not merely a tag or uploaded file: the exact package must be published through the project package repository and be installable/upgradable through the OPNsense Web interface, with release identity/assets verified. Chat shorthand is defined by `CHAT-017`; GitHub completion is governed by `GH-039`, `GH-045`, and `GH-046`.

DEV-040. **A testing package is not a full release, but requested testing-package delivery is complete only on GitHub.** It may be persistently published for owner testing without promoting the stable project package repository or claiming stable release status. For owner patch/package shorthand, a local build, Actions artifact, chat attachment, or sandbox `.pkg`/archive is not the delivered package; completion follows `CHAT-015`–`CHAT-016`, `CHAT-027`, `GH-034`–`GH-038`, and `GH-060`–`GH-061`.

## Verification and release readiness

DEV-045. **Optimization decisions are measurement-driven.** If measured data does not show a meaningful benefit or reveals semantic cost, retain the simpler accepted production architecture and close the optimization question until new evidence appears.

DEV-046. **A development-rule change is not complete until its references are reconciled.** Apply `DOC-008` and the cross-reference integrity contract `DOC-042`–`DOC-045`. The owner's newly binding meaning still takes effect immediately while that same-scope repository reconciliation is being completed.

DEV-048. **Safety is proportional to demonstrated risk.** Preserve all established fail-closed, transactional, ownership, and restoration guarantees. New safety machinery must address an approved requirement or a concrete reproducible defect; prefer the simplest sound solution. An unknown or externally modified state must not be destructively guessed or automatically reset. Defer unproven enhancements rather than blocking already qualified user-facing acceptance indefinitely.

DEV-050. **Forward-only experimental development uses exactly one current product architecture.** This OPNsense installation is a test stand, not a legacy-upgrade compatibility target. When the owner approves a replacement for a parser, schema, strategy, service, lifecycle, engine or other behavior, implement that replacement directly, and in the same logical scope remove superseded production paths, old-version fallbacks, migration-only exceptions, dormant alternative implementations, compatibility wrappers with no active contract, their obsolete tests and their active documentation assertions. Never keep prior behavior executable just in case, and never add a legacy bridge solely to make upgrading an experimental installation transparent. Current-format IPv4 and IPv6 inputs remain valid according to the current approved grammar; an older sealed runtime or configuration format is not supported merely because it once existed. A required deliberate fresh current-format setup or Apply is preferable to another legacy code path; expose its consequence clearly. A future product-level reversal is a new explicit GitHub change using repository history, not a hidden in-program rollback branch. Preserve testing, accurate errors, one native owner and the current transaction's atomicity, cleanup, fail-closed boundaries and repair of an interrupted operation: restoring the immediately preceding state **within that same operation** to avoid incomplete Config/IPFW/process state is not reverting to an obsolete product implementation. Do not impose production-style backward-migration acceptance gates or speculative rollback scaffolding on this experimental stand.

DEV-052. **Version-independent external dependencies and platform-portable design are the default.** New and modified production code must, wherever technically reasonable, survive normal OS, package, interpreter, library and executable updates without source changes. Do not scatter hard-coded dependency versions, minor-version executable names, absolute versioned paths, kernel/ABI assumptions or OS-specific service/config/firewall calls through feature logic. Prefer a stable interface and verified capability detection to guessing from version numbers. When an exact version, supported range, ABI, path or capability restriction is genuinely necessary, define it once in **one authoritative machine-readable external-compatibility manifest** for the project; all runtime resolvers, platform adapters, packaging/build checks and tests must consume or mechanically verify their derived declarations against that source, never independently maintain competing version constants. Resolve and validate executables and required features at the appropriate install/start/use boundary; when already running under a validated interpreter, child processes reuse that interpreter. Never silently choose an unverified binary, use a missing generic symlink, or continue with an unsupported dependency; fail closed with an actionable diagnostic. **Where feasible, prefer keeping the reusable Zapret2 domain/backend logic independent of the target installation platform** (the host operating system/distribution and its configuration, service, firewall, kernel, package and ABI interfaces). This separation is a **recommendation, not a strict architectural requirement or release acceptance gate**: direct platform-dependent code is acceptable where justified by real technical constraints. Prefer narrow, tested adapters for platform-specific integration when they provide a practical benefit, **without adding speculative parallel implementations or compatibility branches** before a target platform is approved and qualified. Qualification must check the supported environments and explicit rejection of unsupported ones, including generated metadata and real platform-only behavior where applicable. Sharing an OS family or kernel base, or successfully building a package, does not by itself prove compatibility with any other target installation platform, OS release or ABI. Version locks demonstrably required for safety, immutable upstream resources or reproducible builds are permitted only as explicit centralized, validated exceptions. This external-dependency policy does **not** replace the separate project `VERSION` source, `PLUGIN_REVISION` governance, or mandatory platform/package-manager metadata.

## Portable dependency and implementation safeguards

These additive rules govern portable software engineering. They do not replace the existing development, release, documentation or platform policies. Existing product-specific identities and qualification constraints remain in their established authoritative metadata.

DEV-053. **Observe installed environment facts rather than maintaining a shadow version inventory.** Obtain actual installed package identities, versions, providers, interpreter identities and library providers from the target platform's native package manager, provider interfaces and validated resolved executables. Query or verify such observations at the relevant boundary rather than copying and synchronizing them across modules. Recorded observations in diagnostics or build receipts are not automatically compatibility restrictions. Explicitly justified supported ranges, ABI restrictions and required capabilities belong only to the project's single authoritative external-compatibility policy, not to a second inventory.

DEV-054. **Classify every external dependency and assign one provisioning owner.** When introducing or changing a dependency, record the consumer, execution environment, actual role (installed runtime, installed setup/build step, package-build-only, test-only, optional or bundled private), provider and acquisition mechanism. Use the target platform's native package manager, qualified repositories and package metadata for system-owned dependencies. Do not let ordinary feature code, package hooks and installers silently compete to install, upgrade or replace a dependency owned by that manager. A tool needed for an installed setup/build operation remains an installed dependency even if it is absent from ordinary request processing. Build/test-only tools must not be promoted to mandatory appliance dependencies without an actual installed use.

DEV-055. **Pin exact external bytes only at a demonstrated release-input or safety boundary.** Routine compatible system package, interpreter and library updates must not require source-version changes or feature-specific version locks. If a private executable or other independent external build input requires byte identity, record its qualified source, necessary selection/version, digest, platform constraints and verification procedure once in the existing authoritative external-input/compatibility policy. Validate that exact input for a release candidate; do not silently substitute upstream latest. Requalify relevant behavior when an intentionally pinned input changes. Do not introduce an independently maintained component-version table or confuse a reproducible release input with a general runtime lock.

DEV-056. **Give every added, moved or renamed production file an explicit integration contract.** Determine its subsystem and owner, caller or entrypoint, execution environment, interface and failure behavior, external dependency needs, packaging disposition and applicable tests. Integrate it through established ownership, invocation, configuration and lifecycle interfaces, not a parallel version resolver, package installer, service supervisor or configuration owner. An unclassified new production file is not automatically safe. This is change-scoped onboarding, not a requirement for a separate manually maintained complete-file catalogue.

DEV-059. **Generate and cross-check product-version representations from one authoritative source.** Builders, package metadata, version markers, release tools, update checks and generated presentations must consume the project's established product version and separately governed source revision, not maintain independently edited copies in feature files or packaging scripts. Automated checks must reject inconsistent generated versions and identities. Distinguish project identity from observed dependency versions, independent private-tool versions and explicit historical test fixtures. A newly merged source revision is not necessarily an already published package.

## Sufficient verification and automatic stop

DEV-064. **Operator lifecycle availability outranks transient Auto-detect collection.** Once the original OPNsense FD9, sealed running common generation, actual native engine+supervisor census and owned IPFW are independently proven, an explicit user Stop, Restart, Apply or protected upgrade must not be blocked **solely** by a changed wall-clock display of process start time in an existing original Auto-detect epoch receipt. A native stop-only check may accept that one discrepancy while requiring every other exact epoch/pretraffic field and reattesting the current process on both sides of the check; it must not rewrite the original immutable epoch, create a second writer or authorize minute processing/ACK on that exception. The operator explicitly accepts loss of uncommitted future Auto-detect discoveries in preference to a service that cannot be stopped or upgraded. Saved manual and already-committed found HOSTLISTs, Config, IPFW ownership, process census, verified rollback/recovery and engine service integrity are **not** disposable. A failed Stop is never package replacement authorization. When earlier blanket Auto-detect history preservation contradicts this lifecycle priority for an explicit user action, this rule takes precedence; minute maintenance must never stop/interrupt running packet handling.

DEV-065. **Service Start and Stop are implemented exactly once, under the original FD9 owner; every caller delegates.** One canonical privileged Zapret2 lifecycle implementation is the **sole** authority for choosing the sealed Common/Voice native owner versus qualified legacy owner, starting/stopping the one `dvtws2` and its supervisor, retaining/restoring Config, concluding native observer epochs/P1/ACK, applying/removing only verified plugin-owned IPFW and checking the terminal service state. A duplicate or alternative Start/Stop decision tree, direct PID/process/firewall workaround or owner-specific lifecycle clone in Strategies, Voice, System Services, GUI Apply, Strategy Lab, `Установить версию` (upstream engine installer), protected `.pkg` update, restart, callbacks or recovery is forbidden. Every service transition invoked by these contexts must call the canonical start/stop entry point **under the already-held original FD9**; never acquire a second lifecycle lock or reenter a nested service action. Restart composes these same operations; Apply and installers may retain their distinct staging, validation, rollback and immutable source/generation semantics but must delegate the service transitions, not reimplement them. Context-specific extra guards may strengthen, never bypass, common ownership, WAN, one-engine, IPFW and durable restoration verification. Equivalent user intents from different pages must produce the same protected transition and truthful final-state receipt; a genuine STOPPED state must not be silently restarted. Tests must trace every public and internal caller to the single implementation and prove RUNNING/STOPPED, refusal, interrupted stop/boot, cancellation and exact owner restoration on disposable native OPNsense. This rule applies to all future service lifecycle changes and takes precedence over historically duplicated routing patterns.
DEV-066. **Approved modular declarative runtime configuration (owner 2026-11-22): one launcher, one generated root manifest, referenced inputs.** The only service-level Start/Stop/Restart/Reload/Status interface resides in `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` per DEV-065, under the original FD9 and actual single engine; source selectors, Target Mode, ordered strategies, named HOSTLIST/IPSET, exclusions, found/managed and individual Voice settings are **NOT** embedded in that lifecycle file. A separate *pure and validated* compiler consumes authorized OPNsense/pfSense XML model data plus the existing registered list files, derives effective `enabled`/`disabled` and Target Mode `all|list|auto`, and emits **one immutable generation-bound JSON root manifest containing flags, ordered references and digests but NO domain/IP/strategy bodies**. The manifest is a sealed executable projection and NOT a second mutable copy of Config.xml. All physical transitions consume the verified manifest through the one canonical service owner; `restart` delegates the only physical Stop→Start, `reload` performs only verified in-place list reread without stopping engine/IPFW, while Apply chooses the minimal safe action after effective semantic diff. Lab, protected updater and engine-version maintenance preserve their distinct transaction pre/post contracts. No arbitrary include paths, untrusted shell `source`/`eval`, duplicate storage registry, extra engine or new Config.xml writer.

DEV-067. **Clean-install resilience, independent installed/readiness states and structured engine errors are mandatory.** First installation must tolerate absent Zapret2 binary, absent initialized user settings and absent committed manifest without unsafe Start/Stop, failed GUI rendering or speculative repair. Report separately: plugin package present, upstream engine installed/verified, user configuration initialized, sealed launch manifest available/valid, service STOPPED/RUNNING/INCOMPLETE. Seed only explicitly approved first-install defaults; reinstall must preserve user files/config, service OFF remains OFF. The sole service implementation exposes read-only status/diagnostic records including stable error `code`, failing `stage`, bounded/redacted native `dvtws2`/supervisor/setup/configd/IPFW stderr and exit status, protected operation/generation ID and actual verified last state; show errors to GUI without leaking full saved Config, raw domains/IPs, secrets or unbounded debug. Never infer successful recovery from process status alone, never auto-install engine or self-start absent user approval, and never delete foreign PID/IPFW or old operation journals to simulate success. OPNsense and pfSense XML adapters read their platform's native configuration; the shared immutable runtime manifest format remains JSON. Governed by [approved configuration contract](architecture/ZAPRET2_DECLARATIVE_RUNTIME_MANIFEST.md).
DEV-068. **Five-command canonical lifecycle and safe Apply-driven Reload (owner 2026-11-22):** The one `zapret_service.sh` exposes `start|stop|restart|reload|status` with a strictly validated, extensible action-specific argument schema. `restart` is a full guarded Stop→Start via the same one original FD9 owner; `reload` never stops `dvtws2`, pauses traffic, changes ordinary IPFW/supervisor or silently falls back to Restart. A pure compiler+diff planner may choose Reload **only** when the old/new exact engine executable+argv, native profile order/source map, WAN/divert/IPFW, Voice/Target Mode and referenced list identities stay identical, and only the content of already attached validated HOSTLIST/IPSet changes through original registry/CAS/Config writer. Structural and mixed changes require one full Restart; no-op needs neither signal nor restart; STOPPED must never auto-start. Upstream list file auto-reread and SIGHUP reload on the next packet are normative facts from the owner's canonical `docs/manual.en.md`, **never subjects of engine verification**. Confirm only the plugin's own list commit, authorized signal routing and truthful stage/result; `RELOAD_REQUESTED` records delivery without inventing a completed next-packet event. One original FD9/durable Apply operation validates and commits, with truthful rollback or uncertain receipt on failure and **no automatic Restart after failed Reload**. Capture bounded sanitized `dvtws2`/supervisor error stage/exit/stderr in the existing diagnostic path and migrate **only** stale RU/EN Start/Stop/Restart GUI errors to the real new lifecycle (not all translations); new meaningful Reload errors also receive RU/EN. No arbitrary external path, PID, argv, shell fragment or user-controlled signal is an allowed CLI option. Governed by [TZ_6v5 §5.1–5.4](architecture/TZ_6v5.md), acceptance V5-13/14.
DEV-069. **Upstream Zapret2 manual.en.md is an unquestioned canonical axiom — do NOT verify documented engine behavior (owner 2026-11-23):** The **sole authoritative engine-behavior reference** is [`bol-van/zapret2/docs/manual.en.md` on master](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md). Any behavior explicitly described there is accepted as true without experimental reproduction, upstream-code proof, source divergence comparison, native FreeBSD re-test, or CI gate asking whether the engine really behaves that way. This includes automatic hostlist/ipset file reread after modification **without process restart**, plus `SIGHUP` forcing list reread **on processing the next packet**, as documented in “Filtering by lists” and “Signals.” Test **only what that manual does NOT describe**: our own compiler, manifest, FD9/config writer, list storage, service lifecycle, exact PID-directed signal, OPNsense IPFW/configd/GUI integration, result classification and rollback. Distinguish plugin integration verification from re-proving the engine. If plugin behavior seems inconsistent, investigate the plugin/configuration rather than questioning or overriding the manual; no alternate source may supplant the canonical URL. See [canonical source and scope](architecture/ZAPRET2_UPSTREAM_MANUAL_CANON.md), [TZ_6v5](architecture/TZ_6v5.md) and [active S00–S20 plan](architecture/ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md).

DEV-070. **Explicit bounded `--force` emergency lifecycle and read-only `--help` (owner 2026-11-23):** The canonical `zapret_service.sh` must support `start --force`, `stop --force`, `restart --force` only for an explicitly authorized administrator against a **previously attested own hung** process. The flag never bypasses original FD9, exact sealed owner/epoch, PID+birth/exe+argv, existing journal/P1 safeguards, own IPFW or normal startup requirements; never kill a foreign/reused PID from a pidfile. Use the existing graceful stop first and bounded wait, then re-attest the **same** process immediately before targeted SIGKILL if still alive, with supervisor respawn suppressed and verified absence/retirement/IPFW before declaring STOPPED or starting replacement. If owner is uncertain, kernel process survives, or retirement fails, return typed refusal/INCOMPLETE, keep journal, do not create a second dvtws2. Healthy RUNNING `start --force` is not a kill request, intentionally STOPPED `restart --force` never autostarts, and `--force` never becomes implicit from GUI Apply, Lab, Auto, Boot, pkg or Reload. The script also provides `--help` and `<command> --help` with short up-to-date five-command syntax and allowed options, rc0, without FD9/Config/PID/IPFW/write side effects. Disallowed `reload/status --force`, unknown or duplicated flags return `INVALID_ARGUMENT` rc64 without mutation. Require disposable OPNsense positive/negative fault-injection and never force-kill on owner device as acceptance. Governed by [TZ_6v5 §5.5–5.6](architecture/TZ_6v5.md), V5-15/V5-16 and [S00–S20](architecture/ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md).

DEV-071. **IPFW allocation is determined only by numeric rule ranges, with no new ownership scanner (owner 2026-11-23):** Exclusively allocated numbers are **19000–19099** for normal Zapret2/Strategies/Voice, **19100–19131** for active Strategy Lab, and **19140–19200** reserved only for not-yet-implemented comparative checks. All numbers outside those intervals (including **19132–19139**) are not Zapret2's and must **never be created, changed, deleted or swept** by any normal/lab/Apply/Stop/Restart/Force/rollback/cleanup/purge code. Existing active operations may mutate only their own *active* intervals; future 19140–19200 must not be touched until implemented by a separate approved change. Rule **number alone** defines allocation; **do not add** rule-expression/divert-port matching, foreign occupancy scans, dynamic numbering or ownership databases. The canonical `zapret_service.sh` sets `RULE_BASE=19000`, `RULE_MAX=19099` and all generators/preview/purge copies must match. Cold-IPFW safety must fail closed if system `default_to_accept != 1` instead of inserting out-of-scope rule `65534`. Original FD9/Config/process/journal safety requirements remain but are separate from rule-number ownership. Governed by [TZ_6v5 §5.7](architecture/TZ_6v5.md), [V5-17](architecture/TZ_6v5.md) and [active S00–S20](architecture/ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md).

## Cross-reference registry

### Outbound references

<!-- RULE-XREF-OUT-BEGIN -->
| Source rule | Target rules |
|---|---|
| `DEV-001` | `CHAT-007`, `CHAT-009`, `CHAT-026` |
| `DEV-033` | `GH-014`, `GH-015`, `GH-016`, `GH-049` |
| `DEV-036` | `GH-047`, `GH-051` |
| `DEV-037` | `DOC-028`, `GH-047`, `GH-051` |
| `DEV-038` | `GH-041` |
| `DEV-039` | `CHAT-017`, `GH-039`, `GH-045`, `GH-046` |
| `DEV-040` | `CHAT-015`, `CHAT-016`, `CHAT-027`, `GH-034`, `GH-035`, `GH-036`, `GH-037`, `GH-038`, `GH-060`, `GH-061` |
| `DEV-046` | `DOC-008`, `DOC-042`, `DOC-043`, `DOC-044`, `DOC-045` |
<!-- RULE-XREF-OUT-END -->

### Inbound references

<!-- RULE-XREF-IN-BEGIN -->
| Target rule | Referenced by |
|---|---|
| `DEV-001` | `CHAT-007`, `CHAT-026` |
| `DEV-002` | `CHAT-007` |
| `DEV-003` | `CHAT-007`, `CHAT-009`, `CHAT-026` |
| `DEV-004` | `CHAT-007` |
| `DEV-027` | `GH-005`, `GH-014` |
| `DEV-028` | `GH-005`, `GH-014` |
| `DEV-029` | `DOC-026`, `GH-005`, `GH-014` |
| `DEV-030` | `DOC-026`, `GH-005`, `GH-014` |
| `DEV-031` | `DOC-026`, `GH-005`, `GH-014` |
| `DEV-032` | `DOC-037`, `GH-005`, `GH-014`, `GH-035`, `GH-061` |
| `DEV-033` | `DOC-037`, `GH-005`, `GH-014`, `GH-015`, `GH-061` |
| `DEV-034` | `GH-005`, `GH-014`, `GH-048` |
| `DEV-035` | `GH-005`, `GH-014`, `GH-048` |
| `DEV-036` | `DOC-028`, `GH-005`, `GH-047`, `GH-051` |
| `DEV-037` | `DOC-028`, `GH-005`, `GH-047`, `GH-051` |
| `DEV-038` | `GH-005`, `GH-041` |
| `DEV-039` | `CHAT-017`, `DOC-038`, `GH-005`, `GH-039` |
| `DEV-040` | `CHAT-016`, `GH-005`, `GH-060` |
| `DEV-069` | `DEV-072` |
<!-- RULE-XREF-IN-END -->

## Rule lifecycle

No cancelled or replaced `DEV-*` IDs currently exist. Existing IDs remain permanent and are never recycled.
