# G06 / LC-07 — native no-action and empty Traffic Strategy experiment

**Status (9 November 2026):** `_19` real FreeBSD v1.0.7 no-action packet S2 PASS [#42650456520](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42650456520); `_20` pure merger merged; `_21` zero ordinary production path [PR #995](https://github.com/Tolian82/os-zapret2-restyle/pull/995) source/CI PASS; `_22` installed original FD9 one-engine Voice-only/combined/empty Stop/Start [native S2 PASS #42669040205](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42669040205), [PR #996](https://github.com/Tolian82/os-zapret2-restyle/pull/996) merged `1fde537e`. `_23` targeted post-activation fault/rollback is **PENDING**. Unmodified browser-fault, physical owner, real WAN/media/IPv6/reboot remain OPEN. Published stable `v0.6.3_1` unchanged.

## Mandatory experiment before implementation

LC-07 requires proof on a *real compiled* FreeBSD/OPNsense `bol-van/zapret2 v1.0.7` engine, **not** inference from upstream source `no_action`. The candidate `scripts/stage2-opnsense-g06-no-action-probe.py` reuses the one real G04 installed-native package/upstream in the **same disposable OPNsense 26.7 guest**, after genuine first configuration, actual TCP+QUIC Start/Stop, manually saved empty Traffic Strategy + YouTube Domains and same physical package reinstall. The G04 witness must PASS before G06 runs. WAN remains unused and untouched in this test.

The G06 process independently checks root/disposable CI opt-ins, exact v1.0.7 Git tag/HEAD and release marker, compiled executable SHA, persisted user-empty/disabled native Config, absence of the ordinary common PID and any existing Zapret2/Strategy Lab owned IPFW rules. It then runs real `dvtws2 --port=989 --dry-run` with **zero user profiles**. If the binary rejects that configuration, report the actual exit code and sanitized diagnostic as a **Branch B candidate only**, never claim idle engine safety.

If dry-run accepts, run a bounded private foreground `dvtws2 --port=989` process (not an installed service), ensure the PID remains live, and bind one temporary local TCP echo service on `127.0.0.1` at an OS-assigned port. Add precisely one test-owned IPFW `19000 divert 989` rule **restricted to that loopback destination, ephemeral port, egress direction and xmit lo0**. Exact request/response bytes, the corresponding nonzero divert packet counter and live engine are all mandatory; an error/timeout/missing count is **REFUSED**, not `PASS`. No public network or real WAN traffic is used.

In `finally`, delete **only** the rule the test itself created, stop/reap only the private child, preserve the native service PID existence, and require the entire original Config bytes and IPFW rule list to be unchanged. Failure to restore is an explicit blocker. The experiment never edits the user's saved ordinary profile or publishes a new service owner.

The result determines whether to proceed with **Branch A** (remove unnecessary local empty ordinary strategy restrictions while installing zero ordinary intercept rules, followed by a *separate* true shared Voice-only FD9/Apply/rollback acceptance) or **Branch B** (truthful enabled-but-inactive state with no misleading RUNNING PID and zero ordinary rules). Do **not** implement either branch on the basis of `--dry-run` alone.

## G06 Stage 1 (`_20` source only)

The pure `voice_traffic_merge.py::merge_profiles` must accept an explicitly empty ordinary user Strategy (including whitespace-only) without inventing a `--new` segment. When Voice is OFF, preserve user-empty bytes exactly; when Voice is ON, return exactly the real staged Voice profile(s), without a fake trailing ordinary profile. Keep NUL/CR/malformed boundaries, STUN scope protection, and exclusive CLI output creation. Focused source unit tests do **not** prove installed shared Voice-only FD9/IPFW. Parser, generator, validator and firewall integration remain separate gated G06 work.

## G06 Stage 2 (`_21` source candidate; installed acceptance OPEN)

A genuinely blank user Traffic Strategy must produce parser count `0` and no `profile-*.conf`. Target Mode validation, normalization, mapped target resolution, blob and port artifact generation must preserve zero; malformed or trailing `--new` remains an error. Both validator variants accept blank traffic only with two empty ordinary port artifacts; any nonblank invalid strategy or inconsistent ports fails closed. The generator emits `--port` and the actual Voice profiles only, with no artificial trailing `--new`.

Shared `prepare_desired` installs no ordinary TCP/UDP divert rules when both port artifacts are blank, while retaining every authentic destination-scoped Voice table/rule and existing ownership/rollback checks. Legacy ordinary-only adoption still rejects missing ordinary ownership evidence. The common manifest attests an unchanged SHA-bound blank `traffic-user.conf` instead of requiring a nonexistent ordinary profile. No alternative engine, FD9 owner, WAN resolver, or firewall range is introduced.

Source regressions: `scripts/test-profile-pipeline.sh`, `scripts/test-voice-common-runtime.py`, and `scripts/test-voice-firewall-transaction.py` cover zero, malformed nonempty, Voice-only, combined, no-action, retained foreign rules and staged corruption. They are NOT a native installed or owner-live proof.

**Next native S2 gate:** use one disposable OPNsense 26.7 with real v1.0.7, original FD9, saved effective WAN and authenticated existing shared Apply. Collect before/after Config bytes, original FD9 identity, PID/engine argv, scoped `19000–19010` IPFW list and tables, foreign-rule witness. Move through Voice-only → Voice+ordinary → Voice-only → no-action and back, include rejection before mutation plus failed activation/rollback and Stop/Restart. Assert precisely zero **ordinary** intercepts in Voice-only/no-action, exactly Voice destination-scoped rules when Voice ON, foreign state unchanged, and no second engine. Full G06/A09/A11 acceptance requires actual native PASS; current source and synthetic fixtures do not qualify. Reboot, IPv6 on a real native stack and owner-browser scenarios remain separate.

## G06 Stage 3 (`_22` native candidate)

New `scripts/stage2-opnsense-g06-native-shared-voice.py` and its path-filtered one-guest workflow `.github/workflows/g06-native-shared-voice.yml` reuse a real G04 first-install/reinstall archive and upstream v1.0.7 on the **same** disposable OPNsense 26.7. All candidate changes use only the installed cookie+CSRF protected `/api/zapret/settings/apply` and `/api/zapret/voice/apply`, then existing configctl Stop/Start under original FD9. No direct Config/IPFW/test-owned independent engine.

Witness: saved `TRAFFIC_ARGS=\"\"` and WAN `lo0`; no-action real engine with zero owned IPFW; only destination-scoped Voice UDP when enabled, no broad ordinary UDP; adding ordinary TCP `65431` yields exactly one additional ordinary IPFW; deleting restores Voice-only without `--new` ghost; disabling Voice removes every Zapret2 rule; stopped and restarted no-action retains same committed journal and one real engine PID; stale Voice snapshot refused unchanged; foreign Config/IPFW remain intact. Localhost test only, documentation IPs, no actual Voice media.

The `_22` workflow must finish native SUCCESS on its **exact PR head** before G06 A09/A11 acceptance; until then this is a planned test, not PASS. The separate injected **post-activation** automatic rollback, boot/reboot, native IPv6 and physical owner-browser/real VPN remain OPEN.

## G06 Stage 4 (`_23` private native post-activation rollback candidate)

`scripts/stage2-opnsense-g06-native-fault-rollback.py` reuses exactly the existing G05 `fault_copy()` and `restored_predecessor()` guards, with no new lifecycle, IPFW, Config or Python backend. ONE G04 native first-install/real upstream v1.0.7 disposable guest creates a saved empty ordinary + committed Voice-only shared FD9 owner via the installed cookie/CSRF HTTPS API. A private root-owned copy of the *same installed native service* replaces only its actual Config-save call with return 69, after `apply_runtime_attest_activated` has succeeded and the new ordinary TCP/IPFW owner was really activated. The test then requires exact persisted Config bytes, terminal `restored.previous` original Voice-only identity, new single real engine PID, original Voice-only IPFW/table, zero ordinary rules and untouched unrelated IPFW. Two subsequent unmodified HTTPS ordinary Add/Remove Applies and final native Stop must PASS.

The `_23` test is **instrumented** (private service copy), NOT unmodified browser fault or power-loss proof. This is separate from the already completed `_22` positive native transitions. Never claim `_23` PASS without exact-head run evidence. Reboot, native IPv6 packets, physical owner-browser and actual media remain OPEN.

## CI budget and evidence

- One source-fast syntax/self-test and **one** disposable native OPNsense 26.7 guest in `.github/workflows/g06-native-no-action-experiment.yml`. The workflow only auto-triggers on the new G06 experiment script; YAML-only edits use fast policy checks/manual dispatch per GH-067.
- Reuse existing G04 first-install/runtime evidence in the *same guest*; no second pkg build, no historical S3/Additional Resources catalog fanout, no outbound request during packet probe.
- Publish result as `G06_NATIVE_EXPERIMENT={...}`, indicating a candidate branch, not full G06 acceptance.
- Full follow-up acceptance for Voice-only, Voice + ordinary, last ordinary profile removal, Stop/Restart, reboot, FD9 and IPFW cleanup is **OPEN** pending empirical branch decision. OWNER-LIVE and real physical network are **OPEN**.
