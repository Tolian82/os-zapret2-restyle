# TZ6v5 S07a — historical source-only XML projection candidate

**Status update:** the pre-acceptance candidate described below is now qualified by [formal S07 native GO](ZAPRET2_TZ6V5_S07_NATIVE_XML_PROJECTION_GO.md), source [PR #1308](https://github.com/Tolian82/os-zapret2-restyle/pull/1308) merged `main v0.6.5_190 717d37dd`. Any native-pending text below is historical, not the current project state.

**24 November 2026 — candidate v0.6.5_190, NOT formal S07 GO.** [Tracked S07 #1307](https://github.com/Tolian82/os-zapret2-restyle/issues/1307). Accepted base is [main v0.6.5_189](https://github.com/Tolian82/os-zapret2-restyle/commit/2f907b3f3c5865259148017aedd3fb7b2f5c42e5) after formal native [S06 GO](ZAPRET2_TZ6V5_S06_NATIVE_INSTALL_REINSTALL_GO.md).

## Narrow delivered source boundary

- `backend/neutral_config_model.py`: pure frozen typed projection, saved WAN remains MISSING/EMPTY/NEEDS_NATIVE_RESOLUTION, Target Mode, selected booleans, approved port ranges, Voice request, empty-vs-missing legacy list metadata and ordered registry IDs. No access to Config, shell, FD9, daemon, runtime or IPFW. `authorization=NONE`, `physical_transition_allowed=False`.
- `backend/config_projection_opnsense.py`: parse only the native `opnsense/OPNsense/Zapret` mount; duplicated, foreign, invalid or malformed source nodes reject. Reuse exact S04 `component_inventory_opnsense._read_fixed` with native `wwwonly` ownership, size and race checks for `/conf/config.xml`; read only root-owned existing `registry.sh::registry_build()` static declarations, not a second registry. Do not use `voice.waninterface`, stale `zapret.conf`, shell, `Config::save()` or another writer.
- Existing `registry.sh`, `wan_preflight.sh`, `config.sh::config_resolve_interface()`, platform model, original FD9, runtime and package hooks are unchanged. The in-memory candidate is **not** an active manifest or permission to start. Legacy fields are metadata only; actual file-backed list content remains owned by existing storage/registry.
- This first increment makes no pfSense reader and does not implement S08 compiler, S09 manifest or any lifecycle action.

## S0 verification and open native gate

Local Python 3 source tests: **7/7 PASS** for missing/empty and invalid controls, deterministic frozen types, source registry eight IDs, untrusted list declarations, malformed/double XML, OPT/TUN selected-but-unverified and no-write/no-spawn injected reader. Exact uploaded Git blobs compared with local `git hash-object` for all three new Python sources. Source tests are **not** installed/native OPNsense qualification; PR exact-head CI and one existing disposable native no-write Config/FD9/pkgdb/engine/IPFW witness remain mandatory before **S07 GO**. Do not expand to unrelated G01/G03/G08 or upstream list-reread tests.

**Next:** prove original installed OPNsense saved-XML projection and strict read-only invariants on the same suitable existing native witness; qualify actual assigned IPv4-less OPT/TUN only through the original WAN resolver; then formal S07 GO and ordered S08. No public `os-zapret2-restyle-0.6.5_190.pkg`, no owner-router action.
