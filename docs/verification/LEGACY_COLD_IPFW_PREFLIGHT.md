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

Under the existing native lifecycle FD9 lock, the probe demands:

1. Root execution, the **exact** installed `0.5.7_10` identity, the original
   readable non-symlinked journal and native inspection dependencies.
2. Both `ipfw` and `ipdivert` modules absent, reported by `kldstat`
   with exit status 1, plus `ipfw -q list` exit 71 and the English
   `retrieving config failed: Protocol not available` diagnostic.
3. The original, **installed** `voice_live_inspect.py` returns status 2 and
   JSON containing the native common owner, the exact cold-kernel false-foreign
   condition, `can_activate=false` and `runtime.state=stopped`. The installed
   service itself must also return status 2.
4. An independent process census examines each full process command line,
   including `daemon`/`sh` wrappers, and refuses any engine or supervisor
   reference. Empty, malformed, or unreadable `ps` output is not proof of
   absence.
5. The entire kernel/service/native-inspector/process-census sequence runs
   **twice** under the same original FD9. Any second-pass disagreement refuses
   rather than returning a stale positive observation.

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
process/status/inspector changes, lock refusal, linked/missing evidence and
marker preservation.
CI success demonstrates only the mocked source contract; real FreeBSD behavior
and **owner-installed _10** remain unverified until actual root-console output
is provided. A safe recovery procedure must be separately reasoned about,
implemented, and evaluated before the old-package upgrade is attempted.
