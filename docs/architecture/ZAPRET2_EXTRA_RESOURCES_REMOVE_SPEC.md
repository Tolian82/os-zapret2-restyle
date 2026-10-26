# Remove Additional Resources — approved requirements

**Project:** os-zapret2-restyle (OPNsense 26.7.x, FreeBSD 15)
**Owner decision:** 24 October 2026; **superseding decision:** 26 October 2026
**Status:** APPROVED REVISED SPECIFICATION — native transaction with temporary resource quarantine and actual service restart. Earlier Jail/isolated-engine proof requirement CANCELLED by owner; implementation and installed acceptance still pending.
**Related contracts:** [Additional Resources installation/GUI](ZAPRET2_EXTRA_RESOURCES_GUI.md), [new implementation plan](ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md).

**Owner-approved Config persistence boundary (26 October 2026):** Ordinary Strategies/Voice GUI Apply persists changed settings through the **native OPNsense model** and `OPNsense\Core\Config::save()` (via the existing shared `SharedConfigCommit::persist()`); there is no independent plugin-specific settings writer. Remove changes **no** saved Strategies/Voice settings: use the existing common `prepareSavedUnchanged` compiler and fresh full Config `preflight`/`saved` readback with `changed_fields=[]`, but do not call `Config::save()` or create an extra Config revision. The Remove trial's shared phase `config-saved` means verified already-persisted unchanged Config, not a fresh save. Its eventual interrupted-state recovery must restore the exact original native common owner through existing attested Apply/runtime/IPFW mechanisms, **not** blindly call normal `shared_apply_recover_saved_service` (which may activate the new release). Unproven restoration retains journals and fails closed. [Approved rationale](../DECISIONS.md).

## 1. Scope and invariants

Add an explicitly user-invoked **Remove Additional Resources** operation on the Strategies page. It must **physically remove** every top-level .lua file in /usr/local/etc/zapret2/lua/ and every top-level .bin file in /usr/local/etc/zapret2/files/fake/ which is **not tracked by the locally installed Zapret2 upstream Git HEAD**. Only the verified standard resources of the **same installed upstream revision** remain. Do not use the current extra-resources GitHub catalog to decide what to remove; no network/GitHub access is needed for this operation.

The approved exact-set policy applies equally to manual, outdated, unknown and plugin-managed non-upstream files. The earlier proposal to preserve manually added Lua/BIN was explicitly superseded by the owner's final decision. Never delete unrelated paths, file types, OPNsense state, saved user settings or strategies.

The acceptance criterion is **the real installed Zapret2 service starts successfully with the actual saved Strategies and native Voice settings, using only locally installed Git HEAD standard Lua/BIN files**, by the same existing native GUI Apply/validation and lifecycle path. A successful service/engine startup and its existing owner/IPFW health checks are sufficient; actual DPI bypass, site reachability and real voice calls are **not** acceptance conditions. A trial may legitimately Stop/Start the service and temporarily move extras after user confirmation. On rejection or unsuccessful startup, restore original resources and service state with an informative warning. Never silently modify saved user settings or strategies.

This is an additional native operation, **not** a new clean-reinstall/repair tool; the owner-cancelled clean-plugin repair remains out of scope.

## 2. Exact local upstream inventory

- Use the actual installed Git checkout at /usr/local/etc/zapret2 and inspect Git HEAD via git ls-tree -r HEAD. Do not use a hard-coded version, filename list, count, upstream web catalog, or the extra-resource repository.
- Restrict the inventory and the removal plan to direct .lua children of lua/ and direct .bin children of files/fake/. Preserve the native path and filename case.
- Verify Git repository/root/HEAD provenance, tracked file type, allowed mode, file bytes, Git blob identity, bounds and symlink/path safety; an untrusted or modified tracked resource blocks the operation.
- Independently enumerate and attest the exact current on-disk Lua/BIN set, including untracked files. Refuse unsafe files, symlinks and races; do not follow links or delete foreign paths.
- Compute **remove = actual installed Lua/BIN minus Git-HEAD-tracked upstream Lua/BIN**, exact relative-path comparison. Every upstream file must remain byte-identical; any non-upstream file in these two direct directories is in scope.
- Discovery of an indirect Lua dependency is handled by the **actual native compilation and startup**, not a new Jail or exhaustive lexical/transitive proof. Retain existing GUI checks as they are; do not promise semantics beyond successful startup.
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

## 3. Native GUI-path checks and trial service start (supersedes isolated proof)

### 3.1 Before service Stop

Compute the exact upstream-only removal plan using current local Git HEAD and original locked Config, under existing setup.lock → original FD9 coordination. Reuse the **exact currently deployed native Strategies+Voice common GUI Apply build path** without constructing a substitute argument file, parser, option whitelist, resource list or second test compiler. That path is `shared_apply_prepare_service()` → `orchestrator_build_release(..., shared-candidate)`, driven by the **original persisted Config** (not the unsaved browser form or a hard-coded duplicate model). The original `parser.sh`, `profile_pipeline.sh`, `targets_prepare_managed`, `exclude_prepare`, `blobs_resolve_file_append`, `voice_release_stage.py`, `generator.sh` and their future native extensions must process the real user input unchanged. Existing placeholders `<HOSTLIST:user>`, `<HOSTLIST:youtube>`, YouTube Domains, Telegram IPs, User Domains and future fields are resolved ONLY by those normal modules. The Remove code does not know or reproduce their names, counts, syntax, mappings or parameters.

**Critical distinction:** `start_service()` is the old ordinary path and may refuse saved Voice ON; a blind `restart`/`shared_apply_boot_service()` may boot an already-compiled cached release, not compile the saved user configuration without extra files. Neither alone qualifies the trial. Reuse the common GUI Apply candidate build AND its native runtime activation/health checks, preserving unchanged saved Config. Do not invoke GUI Apply in a way that writes Config again; any minimal internal orchestration must call the same already existing compiler and actuator internals rather than cloning them. A failed built-in check blocks the operation with zero service/file mutation. Read-only plan/preview is not sufficient to approve deletion without a real trial start.

Do **not** change `Exclude Domains`, its existing `--hostlist-exclude` handling, or add `--ipset-exclude` to this feature. These topics are explicitly deferred to a separate future owner decision.

### 3.2 Saved Voice behavior

The five services (Telegram, Discord, X, SIP, Custom) are checked through the **same saved settings, native GUI validation/draft-preview and combined Strategies+Voice candidate preparation** used on an ordinary user request. Enabled services are included in the real common runtime start. For meaningful saved disabled drafts, reuse the existing GUI candidate/draft validation behavior **without enabling them in the persisted Config**; genuinely incomplete disabled drafts are treated exactly as the GUI would treat them. Do not manufacture a distinct Voice subsystem, promise an actual call, or mislabel a disabled profile as exercised by the live start.

### 3.3 Actual simulation and decision

After the user confirms the exact planned Lua/BIN counts, the normal locked native transaction performs its usual Stop; temporarily moves only attested non-upstream direct Lua/BIN files into protected recoverable quarantine; verifies Git HEAD standard resource bytes remain untouched; then reuses the **real installed** native common GUI Apply **candidate build and activation path**, with the original saved Config as its source. A reload of the previously built common release is not an acceptable compatibility test: compilation MUST occur only AFTER extra resources are absent. There is no separate test-only compiler, XML field copying, placeholder substitution, options rewriter or synthetic engine. Require existing definitive Started/new-process/managed-IPFW health evidence, not merely a zero command exit code. This **actual startup** is the only runtime compatibility criterion; network/DPI/voice-media functionality is out of scope.

If the native GUI checks, resource transition or actual startup fail: stop the failed candidate if necessary, restore original bytes, metadata and prior service state through the **existing** recovery engine, and show a localized failure warning. If restoration itself is unconfirmed, retain recovery evidence and report `RESTORE_FAILED` instead of a success. Do not commit removed/not-installed metadata before successful start.

### 3.4 Rejection message

RU: **«Не удалось запустить Zapret2 с оставшимися стандартными ресурсами. Исходные ресурсы и состояние службы восстановлены.»** — only if restoration was actually confirmed.

EN: **“Zapret2 could not start with only standard resources. The original resources and service state have been restored.”** — only after proven restoration.

For a precheck refusal say which existing validation blocked the trial, without claiming a startup test occurred. For incomplete restoration use the existing explicit `RESTORE_FAILED` warning and leave the journal/backups available. Never expose private Config contents, raw sensitive arguments or credentials.

## 4. GUI and RU/EN

Place a new button immediately **below** the existing Install Additional Resources button:

- RU: **«Удалить дополнительные ресурсы»**
- EN: **“Remove Additional Resources”**
- Exact same button width and height as Install Additional Resources.
- Use the native OPNsense button style; button text has the existing OPNsense **text-info** blue of **«Остальные установленные ресурсы»** / **“Other installed resources”**.
- The Remove button is **visible only while the native Strategies “Advanced mode / Расширенный режим” toggle is ON** (show_advanced_frm_GeneralSettings). Hiding/showing must be immediate, including across F5 and any existing persisted toggle behavior.
- The existing Install button remains in place. The **Full Help / Справка** toggle remains independent and does not control Remove visibility.
- On click, request the existing read-only exact-file removal plan and built-in prechecks, then confirm the precise Lua/BIN counts **and the brief service restart**. Server-side locks and plan/Config verification must still occur before moving files; precheck alone does not authorize commit.
- While busy, use the existing per-operation ID, finite polling/spinner and disable conflicting controls. A directly invoked API must still apply the full server-side security and lifecycle guards.
- A no-op removal plan must have a truthful terminal result without needless Stop/Start.

## 5. Native trial transaction and simple rollback

Use only **ServiceController → configd → setup.lock → original FD9 → existing resource transaction and common Apply/Start**. Do not create Jail, a second service manager, a different IPFW owner, or a second native strategy/Voice validator. A healthy running owner and no unresolved competing setup/Apply/Lab/transaction/recovery are required.

Under inherited locks: verify the exact Git HEAD/upstream and candidate bytes, Config identity and current service; preserve original extra Lua/BIN bytes and metadata in a recoverable journal/snapshot using the existing transaction machinery. Stop the common service normally, move exactly the attested removal candidates into private quarantine outside active Lua/BIN directories, and verify only standard Git HEAD Lua/BIN remain. Rebuild from original saved Config via exactly the same current common GUI Apply compiler and activate with the existing native common runtime service checks, with no user Config changes. An old cached release and a successful start without new compilation are NOT an acceptance result.

- **Startup and health checks PASS:** finalize file removal, update installed/status/cache state and end the operation. Only one normal shared service must remain running.
- **Any precheck, move or startup FAILURE:** restore all quarantined files and original metadata and reestablish the previous native Started owner using existing rollback. Show the informative warning. Keep saved Strategies, Voice settings, managed targets, Exclude Domains and unrelated files unchanged.
- **Rollback unproven:** do not claim success or restoration; keep snapshot/journal, return `RESTORE_FAILED` and require manual recovery rather than blindly retrying.
- **No extra files:** report a truthful no-op, without restarting.
- **Power interruption:** on next entry, the existing durable journal must prevent an unsafe new operation and permit the existing guarded recovery path.

No new engine, sandbox, quarantine service, or excessive preflight framework is authorized. Existing Install remains upstream HEAD + pinned verified extra pack, independently of Remove.

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

- `/usr/local/etc/zapret2/lua/` — installed Lua scripts;
- `/usr/local/etc/zapret2/files/fake/` — installed BIN packet payloads.

Explain that these paths contain both current upstream resources and, when installed, supplementary resources; they are not extra-catalog-only directories.

In **“Additional Resources — installed Lua/BIN help”**, rework the introduction to clearly state that this plugin lets users **optionally install and use an expanded, integrity-verified Lua/BIN resource pack from the project's curated and verified repository** [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources). Clearly distinguish the upstream Zapret2-owned base files from the optional pack and link to its actual GitHub repository. Keep the existing factual explanation of the manual Install action, verified native restart/rollback, cached two-column Full Help inventory and its green/blue classification; explain the new Advanced-only Remove capability only after it is implemented and verified.

Use precise English in README.md. "Verified" must mean verified **source/integrity/provenance and integration controls**, **not** that every Lua module or BIN payload has independently proved a successful DPI bypass, protocol compatibility or Voice-media connectivity. Do not market unsupported candidates as tested successful bypasses. Preserve existing user-facing context and other README sections.

**Gate:** README path accuracy, repository link, manual-install/optional-use wording, existing help semantics, new feature availability claims and README/Markdown link tests all PASS on the exact release candidate. No future stable release of this feature is complete without this penultimate README review.

## 8. Required verification and acceptance

Source/offline tests must cover: dynamic HEAD selection; tracked-byte tamper; symlinks/foreign or manual extras; exact removal counts; existing Strategies/Voice GUI compiler and validators; meaningful OFF draft GUI preview/incomplete OFF draft handling; real shared native Stop→quarantine→Apply/Start→post-start health; startup failure and proven original-file/service rollback; incomplete restoration and retained journal; Config drift; lock/FD9 concurrency; no-op; cache/Help; RU/EN/Advanced/F5; new Job and repeat Install. Do not introduce jail tests or a separate strategy/Voice engine.

Use isolated/mocked fault injection; do not require destructive live OPNsense testing without an approved safety boundary. Do not label unexecuted power-cut or Voice-media scenarios as PASS.

**Owner acceptance is separate from source CI and package build.** The installed appliance must confirm the true before/after Lua/BIN list, preserved upstream digests, refusal before mutation for incompatible saved Strategies/Voice, native service health following removal, Full Help proposal, new-Job discovery and reinstallation. Stable release requires a **new explicit owner instruction**; accepting this specification authorizes documentation, not a package or release.
