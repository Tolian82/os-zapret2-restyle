# Installed v0.5.7_10 cold-IPFW preflight (operator-only)

## Purpose and authority

This standalone, read-only diagnostic targets **only** an already installed
`os-zapret2-restyle 0.5.7_10` on OPNsense/FreeBSD 15. It is **not** installed by
the plugin, does not change the running service, and does not authorize a
package upgrade. Unlike source `v0.5.7_29`, it can be run from a root console
*before* the blocked upgrade.

The published old `PRE_DEINSTALL` calls Stop after receiving status 2; an
incoming package cannot replace that old hook before it runs. The new safe
`PRE_DEINSTALL` only applies to later installed packages. Never use this
diagnostic's positive result as permission to bypass the old hook.

## Checks performed

The published `v0.5.7_10` `zapret_service.sh status` **acquires FD9 by itself**.
The first source-only diagnostic incorrectly called it while already holding
FD9. The owner observed `REFUSED`, which is consistent with this nested-lock
defect but does not establish that all other checks passed. The corrected
diagnostic calls the old public `status` *before* and *after* the separately
locked inspection. It does not reenter the old lock.

The probe demands:

1. Root execution, the **exact** installed `0.5.7_10` identity, the original
   readable non-symlinked journal and native inspection dependencies.
2. Both `ipfw` and `ipdivert` modules absent, reported by `kldstat`
   with exit status 1, plus `ipfw -q list` exit 71 and the English
   `retrieving config failed: Protocol not available` diagnostic.
3. The original, **installed** `voice_live_inspect.py` returns status 2 and
   JSON containing the native common owner, the exact cold-kernel false-foreign
   condition, `can_activate=false` and `runtime.state=stopped`. The installed
   service itself must also return status 2 in two **separate** calls, one
   before acquiring our FD9 lock and the other after releasing it.
4. An independent process census examines each full process command line,
   including `daemon`/`sh` wrappers, and refuses any engine or supervisor
   reference. Empty, malformed, or unreadable `ps` output is not proof of
   absence.
5. The kernel-signature, native-inspector and process-census sequence runs
   **twice** under one original FD9 lock. The two separate old-service status
   calls occur **outside** that lock to avoid the old nested-lock bug.
   A failure emits only a bounded `FAILED_CHECK=kernel-signature-pass-N`,
   `native-inspector-pass-N`, or `process-census-pass-N` label (or a
   concise old-service-status refusal), not the raw journal or process output.
   These separated observations are not an atomic proof of host state.

An ambiguous, changing or partial state, a busy lifecycle, another package
version, foreign process, missing evidence or unexpected exit code means
**REFUSED**. The probe does not delete or rewrite journals, restore markers,
installed files, IPFW rules or services. It may create the normal lifecycle
lock file when obtaining FD9; this is not a wholly zero-write observation.

## Optional root-console use after source review

Review [the script](../../scripts/legacy-cold-ipfw-preflight.sh) in the exact
repository revision before retrieving it. Then, from the OPNsense root
console (commands are `csh`-compatible):

```sh
fetch -o /root/legacy-cold-ipfw-preflight.sh https://raw.githubusercontent.com/Tolian82/os-zapret2-restyle/main/scripts/legacy-cold-ipfw-preflight.sh
/bin/sh /root/legacy-cold-ipfw-preflight.sh
```

The positive diagnostic prints these **bounded** fields:

```text
PACKAGE=0.5.7_10
DIAGNOSIS=cold-ipfw-committed-stopped
UPGRADE_AUTHORIZED=no
NEXT=owner-reviewed-recovery-required
```

A refusal also prints `UPGRADE_AUTHORIZED=no`. A positive diagnosis does
**not** mean the old installed package can be updated, that IPFW can safely
be loaded, or that the host is fully healthy. No automatic `kldload`,
`Stop`, `Start`, `pkg add`, reboot, firewall reset, or journal deletion
is part of this workflow.

## Evidence and remaining gate

Source regression: `python3.13 scripts/test-legacy-cold-ipfw-preflight.py`
with mocked versions, kernel exit codes, inspector replies, direct and
wrapped engine/supervisor census, invalid or empty process output, second-pass
process/inspector changes, **old _10 status rejecting inherited FD9**, first
and post-lock status changes, bounded refusal gates, lock refusal,
linked/missing evidence and marker preservation.
CI success demonstrates only the mocked source contract; real FreeBSD behavior
and **owner-installed _10** remain unverified until actual root-console output
is provided. A safe recovery procedure must be separately reasoned about,
implemented, and evaluated before the old-package upgrade is attempted.
