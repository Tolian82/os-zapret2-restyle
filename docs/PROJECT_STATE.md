# os-zapret2-restyle — current state v0.6.x

State-line scope: **`v0.6.x`**. Current-work flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

Current source increment: **`v0.6.5_22`** (`VERSION=0.6.5`, `PLUGIN_REVISION=22`, prospective `os-zapret2-restyle-0.6.5_22.pkg` **NOT PUBLISHED**, dormant P2k1 bounded P2c-generation native debug/raw **candidate** reader, no durable checkpoint or active observer).

## Identity and delivery

| Item | Current fact | Evidence / owner |
|---|---|---|
| Source | `VERSION=0.6.5`, `PLUGIN_REVISION=22`; P2k1 dormant native debug/raw candidate window and proposed in-memory cursor, runtime unchanged | `VERSION`, `Makefile`, [handoff](START_HERE.md) |
| Latest stable package | `os-zapret2-restyle-0.6.5_1.pkg`; immutable tag `v0.6.5` | [release](releases/v0.6.5.md), [publication receipt](verification/evidence/2026-11-12-v0.6.5-full-release-publication.md) |
| Owner installation | Final stable `_1.pkg` successfully installed through OPNsense GUI | Owner statement: «`0.6.5_1.pkg` успешно установил через GUI OPNsense» |
| Current source package | No `_22.pkg` published; source revisions do not imply installation | [handoff](START_HERE.md) |
| Supported targets | Qualified OPNsense / FreeBSD ABI and dependencies come from `compatibility.json` and native package metadata | [packaging contract](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) |

## Settled product facts

| Subsystem | Established result | Current technical contract |
|---|---|---|
| Native packaging | Official `Mk/plugins.mk`, native `pkg` dependencies, configd/rc and four package hooks; no external pkg-approval infrastructure | [native packaging](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) |
| Lifecycle | G01–G11 / lifecycle v1.3 completed and owner accepted on 11 November: GUI update/clean install of stable `v0.6.4_1`, ordinary uninstall/reinstall with saved settings, full purge, WAN, empty/populated Strategies, STOPPED/RUNNING Lab, domain test and agreed Voice service scope | [lifecycle specification](architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md), [G11 evidence](verification/G11_PUBLISHED_EXISTING_UPGRADE_PURGE_CLEAN.md) |
| Strategies / localization / preview | #936 P0–P6 and visual follow-up #1084 completed and owner accepted on 12 November; functional acceptance on installed `_48`, Laboratory Help appearance on `_50` | [#936 contract](architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md) |
| List semantics | Python `domain_policy.py`, `ipset_policy.py` and `profile_policy.py` own domain, IP and profile processing; PHP/shell are adapters | [architecture](ARCHITECTURE.md), [#936 contract](architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md) |
| Dual stack / exclusions | Mixed IPv4/IPv6 managed IPSETs, global Exclude IPSet and opt-in Laboratory IPv6 shipped in stable v0.6.2; unavailable owner IPv6 was waived, not passed | [dual-stack specification](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md), [v0.6.2](releases/v0.6.2.md) |
| Additional Resources | Manual Install/repeat/Remove and cache-backed Lua/BIN help accepted in the recorded bounded scopes; exact native transaction and resource ownership remain authoritative | [Install contract](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md), [Remove contract](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md), [owner acceptance](verification/REMOVE_NATIVE_OWNER_ACCEPTANCE.md) |
| Laboratory | Python owns the asynchronous job; Model C is normal Stage-60 production; private Chrome client, finite budgets, exact finalist replay, cancellation and Stage-90 restoration retained | [Lab architecture](architecture/STRATEGY_LAB.md), [browser probes](architecture/STRATEGY_LAB_BROWSER_HTTP.md) |
| Voice | Five-service native page and common Strategies/Voice Config/Apply/engine/firewall lifecycle; service acceptance does not establish media/call bypass | [Voice contract](architecture/VOICE_TRANSMISSION_GUI.md) |

## Active #1052 implementation boundary

P0 generated-native observer feasibility and P1 canonical domain/PSL policy are complete. P2a protected queue, P2b genuine FreeBSD FD inspection, P2c detached common-owner attestation and P2d nonactivating original-generator source map are merged. [P2e](verification/P2E_ORIGINAL_SHARED_BUILDER.md) adds the actual original shared-builder witness at `_14`; the original `orchestrator_build_release()` runs against a disposable offline candidate, with only the kernel-interface resolver locally stubbed.

The scoped native original-builder run [#43392107224](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43392107224) passed before the `_14` merge. Source `_16` added a **nonactivating in-memory P2f trailing no-action observer proposal** from that original same-build map. Source `_17` ties this read-only proposal into the original FD9 Apply after its PHP candidate digest is attested, without changing its release argv. TCP ranges from the original port extractor are supported. It returns a deliberately unauthorized schema-2-shaped preview (`P2F_OFFLINE_PLAN_ONLY`) that the running-owner attester refuses; it does not modify original `dvtws.args`, provision raw/debug files, or change any active runtime. [P2f contract](verification/P2F_OFFLINE_OBSERVER_PLAN.md). Source `_18` adds the import-only P2g root:group producer layout and makes the dormant queue/FD validators recognize precisely qualified `0660` native writer inodes, with private root-owned pending. The protected raw/debug path moves out of nontraversable `/var/db/zapret2` to `/var/db/zapret2-auto-detect`. Native nobody credential proof and original engine activation are distinct; [P2g contract](verification/P2G_NATIVE_WRITER_STORAGE.md). Exact `_18` CI/native qualification and installed acceptance must be recorded separately from P2e's earlier run. The first P2i native attempt exposed a specific **upstream startup chown**: despite correct P2g `root:nobody-group 0660` initial files, `dvtws2 --user=nobody` changed the inbox owner to nobody after startup. This fails the strict root-owned queue invariant. P2i tests whether root can safely restore the same inode *after engine credential drop and before adding any diversion rule* while permitting later native group-write appends; production FD9 ordering and reconciliation are still not implemented. [P2i](verification/P2I_NATIVE_ORIGINAL_PREVIEW_LOOPBACK.md).

Source `_19` sealed an inert original-FD9 preview; source `_20` qualifies its true generated bytes against pinned native FreeBSD `dvtws2` in the existing disposable P2e/P2g VM with real TCP/HTTP and the protected writer-path model. The test explicitly preserves the unchanged live runtime. [P2i evidence boundary](verification/P2I_NATIVE_ORIGINAL_PREVIEW_LOOPBACK.md). Source `_21` introduces an **import-only** P2j bridge that retains pending unless a same-generation owner, `DRAINED` saved inode, confirmed debug and complete durable commit all agree; P2a `rotate(generation=...)` opt-in persists the owner ID in the pending basename, and an interrupted same-generation hardlink is finished before processing. Different/untagged previous-generation pending is kept for future authentic replay, never attributed to current PID. Source `_22` adds read-only **bounded** native-debug/raw candidate inspection: P2c generation, protected inode, byte offsets and SHA256 prefix, strict trailing observer number and ordered complete raw matches; its positive `adding` entries cannot authorize a pending deletion because upstream logs before the actual append. **No persisted trusted generation-specific debug cursor, raw/FD-to-debug transaction, final durable HOSTLIST sink, worker invocation, authorized schema2, startup root-restoration or package installation exists.** [P2k1 proof](verification/P2K1_DEBUG_RAW_WINDOW.md). [P2j](verification/P2J_SAME_GENERATION_DURABLE_CYCLE.md). A running native observer, authorized sealed schema-2 real-process raw/debug generation, durable routing, pending acknowledgement, cron/configd, editable Auto Hostlist and scheduled Auto Restart **remain unimplemented**. P2 and P3–P5 remain open under the [approved plan](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). Exact next action belongs only to [START_HERE](START_HERE.md).

## Retained constraints and evidence limits

- One native Config writer and original FD9/common owner; one normal `dvtws2`; candidate validation, atomic activation and same-operation rollback remain in force.
- WAN-first applies before any engine/Voice/Lab launch. WAN Save, Stop and setup remain available independently. The accepted interface resolver is unchanged; assigned OPT/TUN are not excluded by their names.
- Owned IPFW rule numbers are ordinary `19000–19010` and Laboratory `19100–19131`. Existing safe cold IPFW loading and current PF handling are retained; no allocator, shaper-flush monitor or new PF recovery subsystem is authorized.
- Final stable `_1` installation is owner confirmed; it is not a newly repeated functional/Voice/IPFW/IPv6/provider matrix on those bytes. Earlier functional acceptance keeps its actual package attribution.
- No general blocked-ISP/physical IPv6/Voice-media guarantee is inferred from packaging, loopback native tests, counters, parser dry-run or generic owner acceptance. The closed Telegram campaign did not obtain direct-provider MEDIA/CALL PASS.
- #954 was closed as nonreproducible on the owner's physical appliance, not as a proven source fix. Old pending statements in historical records do not reopen accepted lifecycle or #936 work.
- Voice UDP ports / the additional IPv6 checkbox / P2P remain deferred long-term work under the owner's latest 13 November instruction; their [future design](architecture/VOICE_PORTS_IPV6_P2P_FUTURE.md) remains active documentation. pfSense remains a future separate target, not a qualified current platform.

## Documentation and engineering memory

Current chronology is the [v0.6.x ledger](history/current/v0.6.x.md). Superseded handoffs/state assertions, source-level chronology and their evidence pointers remain complete in the [13 November review archive](history/stages/documentation-2026-11-13/README.md). [INDEX](INDEX.md) routes current contracts and deep records. [Review findings](audit/DOCS-2026-11-13.md) record the completed documentation scope; [SECURITY](SECURITY.md) owns the owner-clarified support policy.

## Completed version-line archives

[v0.1.x archive](history/archive/v0.1.x.md) · [v0.2.x archive](history/archive/v0.2.x.md) · [v0.3.x archive](history/archive/v0.3.x.md) · [v0.4.x archive](history/archive/v0.4.x.md) · [v0.5.x archive](history/archive/v0.5.x.md) · [v0.5.x chronology](history/archive/v0.5.x-ledger.md).

Source `_19` inserts a nonactivating, refusal-marked observer preview in the original shared FD9 release after native PHP preflight and before the one seal; engine argv is unchanged. [P2h contract](verification/P2H_ORIGINAL_FD9_SEALED_PREVIEW.md).
