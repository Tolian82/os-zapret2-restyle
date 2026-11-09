# G06 / LC-07 — native no-action and empty Traffic Strategy experiment

**Status (9 November 2026):** `v0.6.3_19` source-only experimental candidate. **Native S2 NOT YET RUN; G06 NOT ACCEPTED; owner-live NOT TESTED.** G05 `_18` [native installed S2 PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42646971454), [PR #992](https://github.com/Tolian82/os-zapret2-restyle/pull/992) merged `ae9efc5b`. No changes to production WAN, orchestration, generators, validators, firewall rules or installation.

## Mandatory experiment before implementation

LC-07 requires proof on a *real compiled* FreeBSD/OPNsense `bol-van/zapret2 v1.0.7` engine, **not** inference from upstream source `no_action`. The candidate `scripts/stage2-opnsense-g06-no-action-probe.py` reuses the one real G04 installed-native package/upstream in the **same disposable OPNsense 26.7 guest**, after genuine first configuration, actual TCP+QUIC Start/Stop, manually saved empty Traffic Strategy + YouTube Domains and same physical package reinstall. The G04 witness must PASS before G06 runs. WAN remains unused and untouched in this test.

The G06 process independently checks root/disposable CI opt-ins, exact v1.0.7 Git tag/HEAD and release marker, compiled executable SHA, persisted user-empty/disabled native Config, absence of the ordinary common PID and any existing Zapret2/Strategy Lab owned IPFW rules. It then runs real `dvtws2 --port=989 --dry-run` with **zero user profiles**. If the binary rejects that configuration, report the actual exit code and sanitized diagnostic as a **Branch B candidate only**, never claim idle engine safety.

If dry-run accepts, run a bounded private foreground `dvtws2 --port=989` process (not an installed service), ensure the PID remains live, and bind one temporary local TCP echo service on `127.0.0.1` at an OS-assigned port. Add precisely one test-owned IPFW `19000 divert 989` rule **restricted to that loopback destination, ephemeral port, egress direction and xmit lo0**. Exact request/response bytes, the corresponding nonzero divert packet counter and live engine are all mandatory; an error/timeout/missing count is **REFUSED**, not `PASS`. No public network or real WAN traffic is used.

In `finally`, delete **only** the rule the test itself created, stop/reap only the private child, preserve the native service PID existence, and require the entire original Config bytes and IPFW rule list to be unchanged. Failure to restore is an explicit blocker. The experiment never edits the user's saved ordinary profile or publishes a new service owner.

The result determines whether to proceed with **Branch A** (remove unnecessary local empty ordinary strategy restrictions while installing zero ordinary intercept rules, followed by a *separate* true shared Voice-only FD9/Apply/rollback acceptance) or **Branch B** (truthful enabled-but-inactive state with no misleading RUNNING PID and zero ordinary rules). Do **not** implement either branch on the basis of `--dry-run` alone.

## CI budget and evidence

- One source-fast syntax/self-test and **one** disposable native OPNsense 26.7 guest in `.github/workflows/g06-native-no-action-experiment.yml`. The workflow only auto-triggers on the new G06 experiment script; YAML-only edits use fast policy checks/manual dispatch per GH-067.
- Reuse existing G04 first-install/runtime evidence in the *same guest*; no second pkg build, no historical S3/Additional Resources catalog fanout, no outbound request during packet probe.
- Publish result as `G06_NATIVE_EXPERIMENT={...}`, indicating a candidate branch, not full G06 acceptance.
- Full follow-up acceptance for Voice-only, Voice + ordinary, last ordinary profile removal, Stop/Restart, reboot, FD9 and IPFW cleanup is **OPEN** pending empirical branch decision. OWNER-LIVE and real physical network are **OPEN**.
