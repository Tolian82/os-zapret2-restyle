# #1052 P2k8q3e2 — running native IPFW with nonblocking debug inode cut

**Candidate:** source `v0.6.5_61`, 15 November 2026. This is a bounded **disposable-guest experimental protocol and original-source negative regression**, not production debug rollover, cron, new running owner or installed appliance acceptance.

## User-safety scenario

After original P2a rotates raw while one real original generator `dvtws2` remains RUNNING, a known HOSTLIST HTTP request through the original scoped IPFW divert MUST actually complete. A second distinct unknown real HTTP/RST lands in raw:new/debug:old. A root-prepared empty debug replacement is then installed using an atomic name swap, **without removing the debug.log pathname even temporarily**, and another known diverted HTTP request must complete under the same original PID/birth/UID. The debug-old inode and original raw pending must survive; the new raw/new debug must record a separate postcut unknown. Do not signal STOP/CONT in the unquiesced acceptance branch.

## Actual changed original path

The existing `scripts/test-p2i-original-preview-native.py --native` in the SAME P2e/P2g/P2i disposable OPNsense 26.7 VM replaces its old guest-only `os.replace(debug, archive)` followed by `open(debug, O_CREAT)` gap with the no-missing-name sequence:

1. Pre-create a new root:nobody 0660 empty debug inode using O_EXCL/O_NOFOLLOW and fsync its FD.
2. Hardlink the original debug inode under a private diagnostic alias in the original producer directory; verify dev/inode and two links; fsync the parent directory.
3. Atomically `os.replace(prepared_debug, debug.log)`; fsync directory; require old archived inode one link, new live inode one link, different dev/inode, empty replacement.
4. Complete original real IPFW known HTTP both inside the raw/debug gap and after both cuts, verify counter increases and native PID/birth remains running; retain pre-/mid-/postcut unknown exact physical routes, genuine original FD9 and IPFW cleanup.
5. Inspect **all-process** FD state for the retained old debug inode through the existing P2b native inspector (observation only; never ACK).

The original `scripts/test-auto-detect-original-v2-prepare.py` adds a physical red/refusal: original P2a cuts raw first, a second positive writes to raw:new/debug:old, debug inode changes via hardlink+replace, and the current P2k8o/P2k8n source MUST refuse on two attempts without moving the cursor or acknowledging/deleting pending, modifying final auto-domains.txt, or losing either old debug or live raw. This is the honest current safety boundary.

## Qualification and remaining blockers

Fast CI directly runs the original portable test, including preservation on repeated retry. The existing P2e/P2g/P2i original OPNsense native VM runs both its unquiesced true live-IPFW path and its retained historical _58 stopped-engine negative control **sequentially** (the latter never authorizes production suspension); it is not a new VM or product signal. All exact-head CI/native/package results must be recorded after actual execution and cannot be inferred from source changes. No .pkg publication is requested.

**Not yet solved:** the authentic P2k8n v2 cursor, P2k8p original PHP Config-held destination and ACK still bind to ONE debug inode. The new read-only native cut does NOT have a durable, generation-bound old/new debug handoff across raw:new/debug:old. Old writer-FD drain, crash recovery after link/replace, 4 MiB debug/raw, 512 cursor slots, reboot/ENOSPC and production continuous operation need further proof before enabling active observer/cron. Never silently reset cursor or claim known-HOSTLIST attribution without that proof.

[Prior _60 debug prefix](P2K8Q3E1_DEBUG_PREFIX_CURSOR.md) · [Historical _55 native split](P2K8Q3C2_NATIVE_MIDCUT_RAW_DEBUG.md) · [Historical _58 stalled IPFW packet](P2K8Q3D3_NATIVE_INFLIGHT_DIVERT_STOP.md) · [Architecture](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md).
