# Additional Resources M5 — bounded operator-selected clean repair gate

**Status:** qualifying contract / implementation gap as of `0.5.7_47`; **not** an executable repair procedure or authorization to alter an installed system.

## Goal and exact boundary

Provide a **separate, explicit console-selected** way to install a fresh operational `os-zapret2-restyle` plugin when a damaged or inconsistent installation cannot be safely replaced by the existing normal-preservation package hooks. Replacing a *normal* working plugin continues using existing transactional hooks. Do not weaken those hooks, reinterpret status 2 as stopped or add generalized Git worktree remediation.

No new Web UI or background daemon is necessary. The operator may accept loss of **plugin-owned** settings, strategies, jobs and extra-resource transaction history in this specific clean repair. Other OPNsense plugins, global firewall/Config state, foreign files, OS/pkg DB health and all unrelated services must be preserved. Bad pkg DB/filesystem/OS is outside the guaranteed repair scope.

## Required stop-before-write observations

1. **Snapshot and console:** owner confirms a *recoverable* VM snapshot (or equivalent rollback) of the affected machine; hypervisor console is already confirmed. Do not attempt live destructive test before this.
2. **Exact artifact:** verify immutable testing package identity, source commit/tag/asset SHA-256, FreeBSD 15 architecture and availability for reinstall; never download an arbitrary latest binary during repair.
3. **One plugin package:** validate the installed package identity and the exact removal set. Removal must not cascade to other packages or apply recursively.
4. **Native ownership:** obtain independent, read-only engine/supervisor PID and command identity, plugin IPFW rule/table ownership, active Strategy Lab/Additional Resources/Voice/Apply operations, setup/runtime rollback state and lifecycle-lock availability. A missing script or `status=INCOMPLETE` is **not** proof of stopped. Any foreign owner, active process, unknown IPFW entry, untrusted pending rollback or uncertain identity **blocks** the clean repair, preserving evidence.
5. **Config and files:** inventory exact package-owned files vs runtime resources under plugin-specific roots; reject unexpected symlink traversal, target replacement outside owned roots or ambiguous foreign data. Never blanket-delete shared OPNsense config, global package DB, firewall state, unrelated user directories or other-plugin settings.

## Repair semantics to implement and test

- **Explicit operator opt-in:** separate command/confirmation mode, no automatic invocation from `pkg add`, setup button or failed routine update.
- **Provably quiescent native runtime first:** normal verified Stop if possible; with incomplete state, require independent and trustworthy quiescence evidence or refuse. Do not treat force flags or unavailable status as proof of safety.
- **Bounded package surgery only:** FreeBSD's `pkg delete --no-scripts` may bypass a broken deinstall hook *after* the above proof and snapshot, but cannot silently remove dependencies, auto-purge foreign directories or suppress the reinstall's normal plugin-registration actions. Determine the smallest safe pkg invocation and its behavior in isolated tests before owner use. `pkg add -f` alone is not guaranteed clean repair.
- **Plugin-owned state reset:** if required, identify every reset entry specifically, attest the operator's selected scope, prevent symlink escapes, preserve unrelated OPNsense configuration and leave evidence for rollback. Reset of plugin-owned config is permitted, but never make global `/conf/config.xml` or shared global firewall state collateral damage.
- **Reinstall and verify:** after package install, verify OPNsense plugin registration, configd actions/template, native setup, expected Service Started/Stopped transition, healthy engine, correct compiled/upstream and optional extra-resource status, and absence of leftover plugin process/IPFW/locks. If it fails, report a truthful, explicit terminal failure and retain evidence; never output `INSTALLED` merely because `pkg` succeeded.
- **Idempotent/fail-closed:** abort on wrong package identity, running/incomplete foreign owner, kernel object ambiguity, script error, package removal mismatch, untrusted backup or failed verification. Repeated inspect is read-only; interrupted repair has a documented recovery from the VM snapshot rather than an automatic blind cleanup.
- **Isolated source tests:** with temporary package-filesystem fixtures/mock pkg and native outputs, cover normal safe stopped owner, missing package scripts, incomplete owner refusal, foreign PID, foreign IPFW rule, symlink escape, package mismatch, failed reinstall action, wrong artifact digest, and preservation of an unrelated mock plugin/config. Only then offer bounded owner-live trial.

## Status and next engineering action

Current offline resource/rollback negative tests have source CI proof, but **none implements and qualifies this end-to-end clean-package repair**. Next bounded code increment is the minimal *operator-selected and safe* entrypoint plus isolated test contract, not a package-hook bypass or a speculative general recovery engine. Advance version only if packaged runtime source changes; documentation and CI-only increments keep `0.5.7_47`. A new testing candidate requires fresh package/CI and owner-installed evidence before M5 PASS. `v0.5.8` release remains separately owner-authorized.
