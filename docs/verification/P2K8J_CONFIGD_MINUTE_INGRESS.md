# #1052 P2k8j — registered OPNsense configd minute ingress, no cron activation

**Source candidate:** `v0.6.5_40`, 14 November 2026. **Only a safe registered dispatch surface; native Auto-detect recording, durable worker, cron and pending ACK remain DISABLED.** No installable `_40.pkg` is published by this increment.

## Concrete user route and acceptance

The approved eventual route is **OPNsense cron every 60 seconds → registered configd action → one short Python worker**. Do not insert cron earlier: at source `_39` neither an active sealed schema-2 generation, a genuine current/old pending writer-FD closure and debug cursor nor real acknowledged durable commits are authorized. Simply scheduling `auto_detect_cycle.run_native_cycle()` would leave an unbounded producer, repeatedly fail or invent attribution. The owner-approved schedule is not a license to acknowledge raw before actual processing.

This increment installs the *registration*, not the *timer*:

- Existing `actions_zapret.conf` registers **`[auto_detect_minute]`** with no caller arguments, native `python_runtime.sh`, `type:script_output`, timeout 30s and no Cron-dropdown description. It neither edits `config.xml` nor calls the original shared Apply.
- New `backend/auto_detect_minute.py` is a short registered entrypoint. On actual FreeBSD root, a missing normal runtime or a protected original `runtime-v2/dvtws.args` **without** native `--hostlist-auto*` and without the active sealed `auto-detect-generation.json` returns only `auto-detect-minute=inactive`. It does **not** open, create, rotate, parse or delete `inbox.txt`, `pending`, root-private epochs, target HOSTLISTs or `config.xml`.
- A forged/dangling generation map, any native-auto flag (including `--hostlist-auto-debug` without raw), corrupted/foreign/symlinked original release path or argv, oversized bytes, non-FreeBSD invocation or non-root execution refuses. A made-up status file, CLI parameter, environment override or a spoofed process cannot claim that the worker is ready. The original P2k8i shared-FD9 engine gate remains independently refusing `authorize`.

## Verification and evidence boundaries

`scripts/test-auto-detect-minute.py` exercises actual source introspection, exact registered configd command, **absence** of both installed `src/opnsense/etc/cron.d/zapret2-auto-detect*` schedules, real private temporary file identities, repeated ordinary idle ticks, all auto-native flags, forged and symlinked generation files, symlink/foreign mode, corrupted argv, CLI-arg refusal, and preservation of an unrelated pending inode. The tests run in existing *fast changed-path CI*; no additional VM or new matrix. S0 preparatory tests: **7/7 PASS** using exact new Python file and the corresponding existing owner helper's read contract; final repo exact-head CI remains a separate gate.

The source-native package build may verify payload and OPNsense Python compatibility, but **neither a source test nor a package build means installed configd action reload or cron firing were qualified**. The action has no automatic schedule: no extra daemon, no persistent watcher, no service restart per discovery and no Config second writer. The owner appliance remains on separately reported stable package `0.6.5_1`.

## Required next gate (still OPEN)

Complete the *genuine* original-generation seal and remaining FD/drain, debug/PSL, full Config-held P1→durable P2k2b target commits, old-generation replay and **ACK only after acknowledged durable success**. Then, while the exact original singleton worker lock prevents overlapping runs, replace `auto_detect_minute.py`'s intentional active-state refusal with the real one-pass queue consumer, qualify that native end-to-end, and **only then** register the native 60-second cron job and allow the original shared-FD9 `authorize` gate to admit passive recording. Observe the existing no-implicit-`<HOSTLIST:auto>` rule and never import `zapret-hosts-auto.txt`.

[Normative specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [Plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [Original FD9 seam](P2K8I_ORIGINAL_FD9_PRE_IPFW_BRIDGE.md).
