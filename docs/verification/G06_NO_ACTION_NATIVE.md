# G06 / LC-07 — native no-action and empty Traffic Strategy experiment

**Status (9 November 2026):** `_19` upstream zero-profile real FreeBSD 15 native packet PASS [#42650456520](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42650456520), `_20` pure Voice composer merged [PR #994](https://github.com/Tolian82/os-zapret2-restyle/pull/994). `_21` is the **source-only** extension through zero ordinary parser/pipeline/generator/validator and shared firewall manifest. Actual authenticated OPNsense FD9 Voice-only Apply/rollback and all owner-live tests remain **OPEN**. Published stable `v0.6.3_1` is unchanged.

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

## CI budget and evidence

- One source-fast syntax/self-test and **one** disposable native OPNsense 26.7 guest in `.github/workflows/g06-native-no-action-experiment.yml`. The workflow only auto-triggers on the new G06 experiment script; YAML-only edits use fast policy checks/manual dispatch per GH-067.
- Reuse existing G04 first-install/runtime evidence in the *same guest*; no second pkg build, no historical S3/Additional Resources catalog fanout, no outbound request during packet probe.
- Publish result as `G06_NATIVE_EXPERIMENT={...}`, indicating a candidate branch, not full G06 acceptance.
- Full follow-up acceptance for Voice-only, Voice + ordinary, last ordinary profile removal, Stop/Restart, reboot, FD9 and IPFW cleanup is **OPEN** pending empirical branch decision. OWNER-LIVE and real physical network are **OPEN**.
