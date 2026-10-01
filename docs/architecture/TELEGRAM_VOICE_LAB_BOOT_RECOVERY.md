# Laboratory-only Telegram Voice ON recovery after OPNsense reboot

**Status:** design and installation procedure approved by owner request; **not yet installed or owner-live reboot tested**.  
**Scope:** independent OPNsense *laboratory* configuration, not `os-zapret2-restyle` source, package, GUI implementation or product stage 3.  
**Inputs:** [live inventory](../verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md), [existing lab operations](TELEGRAM_LAB_OPERATIONS.md), [traffic contract](TELEGRAM_TRAFFIC_POLICY.md).

## Requirement and decision

The observed experimental Voice helper was `requested=on`/`effective=on`, with the `stun-zero-fake-repeats-2` STUN-only PoC profile, Telegram IPSET and an IPFW divert rule. Its **request marker** is `/var/run/zapret2-telegram-voice-poc.enabled`; ordinary OPNsense reboot clears it. The already-packaged native `start/20-zapret` hook only starts regular Zapret2 and **does not** preserve the helper's selected ON state. `configctl zapret status` is not a Voice status test.

**Selected independent lab solution:** native **System → Settings → Cron** GUI task, invoking a **separately registered laboratory configd action** every five minutes while enabled. This is a *persistent OPNsense GUI ON/OFF selector*: **Cron task enabled = the laboratory operator wants Voice ON automatically recovered**; Cron task disabled = no automatic restoration. To turn Voice actually OFF, disable and Apply the Cron job **before** calling the plugin's existing `telegram_voice_disable` action. Do not assume disabling a Cron job alone turns off an already-active helper.

This approach does **not** create another `rc.syshook` hook, change any package-owned `actions_zapret.conf`, change the `/var/run` marker format, interfere with Squid/sing-box/PF or affect TNAS routes. Existing plugin source must **only** be changed through GitHub, and future product OPNsense-config-backed Voice Settings GUI persistence is still reserved for product **stage 3 after MEDIA_PASS and CALL_PASS**.

The registered action invokes the **same backend command** as the package's existing `zapret telegram_voice_enable` action **directly**, rather than nesting `configctl zapret ...` inside a configd action. This avoids a possible configd self-call/deadlock. The service's actual source checks that ordinary Zapret2 is already completely running, uses a lifecycle lock, and **when the marker and effective state are already ON, returns current status without reconfiguration**. Before Zapret is ready the command fails safely; the next scheduled invocation retries without force-starting/restarting ordinary Zapret2. The job is recovery, **not a daemon or strategy experiment**. A scheduled call can still fail and is *never* proof that Voice media passes.

**Boot availability:** OPNsense schedules Cron via its persistent GUI configuration. The first successful action after reboot may be up to five minutes **after ordinary Zapret2 is actually ready**; do not claim instantaneous ON. If Cron/configd never becomes operational or Zapret startup remains incomplete, this action cannot recover it. Capture the job log, actual status and boot timing during the first controlled reboot.

References: [OPNsense native configd custom actions](https://docs.opnsense.org/development/backend/configd.html), [OPNsense GUI Cron](https://docs.opnsense.org/manual/settingsmenu.html#cron), [OPNsense native boot ordering](https://docs.opnsense.org/development/backend/overview.html), [current project source service dispatch](../../src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh), [existing hook](../../src/etc/rc.syshook.d/start/20-zapret).

## Prepare without affecting today's active traffic

OPNsense owner console is **csh**, not POSIX `sh`. Every console command below is deliberately **one line compatible with the default csh**. No interactive multiline scripts/heredocs. The package's backend uses its own `#!/bin/sh` and is launched directly by configd. Do not restart Zapret2, Squid or sing-box for installation.

Before installation:

```text
configctl zapret status
configctl zapret telegram_voice_status
ls -l /usr/local/opnsense/service/conf/actions.d/actions_tgvoice_lab_restore.conf
```

The last `ls` is a **collision guard**: expected `No such file or directory`. If it exists, STOP and inspect it; do **not** overwrite it. Ensure the current Voice state is the intended ON baseline. Record current uptime if a future boot time comparison is planned.

With the expected file absent, install the **single independent lab action**; the literal command is one line despite its display wrapping:

```sh
/usr/bin/printf '%s\n' '[ensure]' 'command:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh telegram-voice-enable' 'parameters:' 'type:script' 'message:Ensuring lab Telegram Voice ON' 'description:Ensure lab Telegram Voice ON' 'timeout:600' > /usr/local/opnsense/service/conf/actions.d/actions_tgvoice_lab_restore.conf
```

The `printf` invocation is `csh` compatible, with no shell variable assignments, conditionals or heredocs. It **must not** be pasted as multiple separately executed lines. Then verify before starting the action:

```text
cat /usr/local/opnsense/service/conf/actions.d/actions_tgvoice_lab_restore.conf
pkg which /usr/local/opnsense/service/conf/actions.d/actions_tgvoice_lab_restore.conf
service configd restart
configctl tgvoice_lab_restore ensure
configctl zapret telegram_voice_status
```

The `pkg which` check should report no owning package; this separate operator-created lab file must not masquerade as plugin source. `service configd restart` reloads **configd**, not Zapret2/Squid/sing-box; perform only when safe to briefly interrupt configd control actions. The newly registered action is deliberately `type:script` (returns status only), so the manual call may print nothing on success; **always** inspect the independent Voice status output.

Expected *status content* after the test with the currently live ON baseline: `telegram_voice_poc.requested=on`, `effective=on`, `service=running`, `active_profile=on`, `table_present=yes`, a nonempty IPSET and a real Voice-specific divert rule. IPSET entry count and numeric rule assignment can legitimately differ from the historical 14/`19000`. If the action returns error or state is not fully ON, do **not** create the Cron job; inspect errors first.

## Register the desired ON state through native OPNsense GUI

Only **after the manual registered action passed**:

1. OPNsense GUI **System → Settings → Cron** → **+** new job.
2. Enable: **ON**. `Minutes=*/5`; `Hours=*`; `Days=*`; `Months=*`; `Weekdays=*`.
3. **Command:** `Ensure lab Telegram Voice ON` (registered action's exact description). **Parameters:** blank. **Description:** `Telegram Voice independent lab ON recovery`.
4. Save **and Apply**. Confirm the job is enabled/present; optionally inspect the generated cron entry, without directly editing the generated crontab.

If the command description does not appear, first check the action file's exact name, the `description` field and whether configd was restarted. Do not invent a different command or edit package-owned actions to force it.

**Operating mode:** With the Cron job enabled, healthy ON is a no-op on future checks. If reboot clears the marker, the recurring action re-enables it after normal Zapret is ready. If the user **intentionally stops** Voice during a test, **first disable and Apply** this particular job in the GUI, then `configctl zapret telegram_voice_disable` and verify the full status. After the experiment, `configctl zapret telegram_voice_enable` followed by re-enabling and Applying this **same** Cron task restores the selected persistent laboratory ON mode. Do **not** run a baseline/candidate comparison that expects Voice to stay OFF while this task remains enabled.

**Do not** schedule TNAS route repair or Docker container startup. The owner rejected those automations. The existing, owner-tested TNAS routes remain a **manual** OPNsense SSH command described in [lab operations](TELEGRAM_LAB_OPERATIONS.md#tnas-host-routing-and-manually-operated-docker-lab).

## Acceptance: test the actual boot, not merely registration

Record **before** OPNsense reboot: exact Cron enabled state, `configctl zapret status`, complete `configctl zapret telegram_voice_status`, actual Voice IPFW divert/target table, and any service file changes. Save existing Squid and sing-box active configuration hashes and listeners via the [operations runbook](TELEGRAM_LAB_OPERATIONS.md) before any controlled reboot.

After an owner-controlled OPNsense reboot, **do not manually enable Voice while measuring auto recovery**. Allow at least **two scheduled intervals after regular Zapret reports running** (10 minutes with `*/5`, accounting for task time). Confirm the same GUI task is still enabled, `configctl zapret status` shows regular Zapret running, and independent `configctl zapret telegram_voice_status` reports requested=on, effective=on, active_profile=on, real Telegram table and actual IPFW Voice rule. Capture startup/cron/configd logs and actual boot-to-Voice timing. Successful re-enabling of experimental intercept is **LAB_VOICE_AUTO_RESTORE_PASS**; it is **not** Telegram `MEDIA_PASS` or `CALL_PASS`. If no action runs, inspect GUI task persistence and cron/configd state. If it runs before readiness, first expected failure is permitted **only if a later scheduled retry succeeds**. No actual reboot result exists yet.

Optional separate test (planned, not a prerequisite for basic reboot proof): after starting a controlled experimental Voice OFF interval, verify Cron-disabled survives reboot and leaves Voice OFF rather than silently restoring it. Re-enable only with deliberate owner action.

## Recovery, removal and backups

- If the job starts interfering with a controlled experiment: disable **only this** Cron task through GUI, Apply, then optionally use `configctl zapret telegram_voice_disable`. Do not disable the OPNsense Cron service globally.
- If the laboratory action file must be removed: first disable and delete **this** GUI task and Apply; then only after checking the exact file path, remove `/usr/local/opnsense/service/conf/actions.d/actions_tgvoice_lab_restore.conf` and reload configd. Do **not** remove package-owned `actions_zapret.conf` or native `start/20-zapret`.
- The Cron job's enabled flag/schedule is part of OPNsense native configuration; the manually added `actions_tgvoice_lab_restore.conf` is **not guaranteed included in OPNsense config.xml backups or retained through upgrades**. Back up that specific non-secret file **separately**, verify it after upgrades, and preserve the exact operational instructions in GitHub.
- This design uses **no permanent new script** beyond the tiny laboratory configd action file and no change to production package revision. The source implementation already exists, and the helper's temporary marker remains deliberately temporary. Only the independent lab's GUI schedule provides the durable desired ON preference.
