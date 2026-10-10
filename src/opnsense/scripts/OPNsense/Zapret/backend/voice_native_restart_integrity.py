#!/usr/bin/env python3
"""Native FreeBSD prior-Voice restart image/UID/argv correlation.

Read-only, NO production CLI, journal cleanup, start/stop or Voice ON.
Requires a SHA-bound schema-3 previous security policy, genuinely independent
native kernel-image+credential witness, and kern.proc.args argv witness.
The SAME newly-started PIDs and start identities must occur in both sources
and remain stable under the existing lifecycle and Config inode locks.

A valid result is evidence ONLY: neither exact argv, process credentials nor
the sealed previous snapshot prove readiness, traffic delivery or reboot-safe
whole-system completion. The whole MUTATING intent must stay durable.
"""
from __future__ import annotations

from pathlib import Path

from voice_cutover_journal import SECURITY_BOUND_SCHEMA
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_freebsd_kernel_argv import FreeBSDKernelArgvReader
from voice_security_policy_evidence import (
    inspect_security_policy, verify_current_security,
)
from voice_restart_argv_attestation import inspect_restarted_argv
from voice_process_recovery_evidence import inspect_process_evidence

ROLES = ("engine", "daemon", "monitor")


class NativeRestartIntegrityError(RuntimeError):
    pass


def _attest_previous_restart(
    *, journal, previous_backup: Path, process_evidence: Path,
    security_evidence: Path, expected_scripts: dict,
    expected_supervisor_argv: dict,
    security_reader: FreeBSDProcessSecurityReader,
    argv_reader: FreeBSDKernelArgvReader,
    require_lifecycle_owner, require_config_owner,
) -> dict:
    """Correlate new PID/start on both native witnesses under caller locks.

    Real FreeBSD readers are mandatory types. Inputs remain untrusted until
    verified against the sealed schema-3 previous policy and process snapshot.
    The reader constructors must use the SAME native process-probe instance.
    No check grants permission to close journal or declare Voice recovered.
    """
    if not callable(require_lifecycle_owner) or \
       not callable(require_config_owner) or \
       not isinstance(security_reader, FreeBSDProcessSecurityReader) or \
       not isinstance(argv_reader, FreeBSDKernelArgvReader) or \
       security_reader.probe is not argv_reader.process_probe:
        raise NativeRestartIntegrityError("no shared trusted native observer and locks")
    require_lifecycle_owner()
    require_config_owner()
    initial = journal.read()
    if initial is None or initial.get("schema") != SECURITY_BOUND_SCHEMA or \
       initial.get("phase") != "mutating":
        raise NativeRestartIntegrityError("restart needs mutating schema-3 whole intent")
    previous_backup = Path(previous_backup)
    process_evidence = Path(process_evidence)
    policy = inspect_security_policy(
        Path(security_evidence), previous_backup, process_evidence,
        journal_record=initial, expected_scripts=expected_scripts,
    )
    sealed = policy["policy"]
    if security_reader.expected_scripts != sealed["scripts"] or \
       security_reader.kernel_images != sealed["images"] or \
       security_reader.credentials != sealed["credentials"] or \
       argv_reader.expected_paths != sealed["scripts"] or \
       security_reader.probe.expected != sealed["scripts"]:
        raise NativeRestartIntegrityError(
            "untrusted current native kernel-image, identity or credential policy"
        )
    old = inspect_process_evidence(
        process_evidence, previous_backup, expected_scripts, initial["previous"],
    )
    if old["observation"]["engine"]["state"] != "running":
        raise NativeRestartIntegrityError("no previous running Voice engine to restart")
    require_lifecycle_owner()
    require_config_owner()
    security = security_reader.inspect_twice()
    if not verify_current_security(security, policy):
        raise NativeRestartIntegrityError("foreign native kernel image or UID/GID")
    argv = inspect_restarted_argv(
        previous_backup, process_evidence, expected_scripts,
        expected_supervisor_argv, argv_reader,
    )
    if argv["state"] != "review-required" or \
       argv["reason"] != "new-process-argv-matches-sealed-launcher-plan":
        raise NativeRestartIntegrityError("native kernel argv is not previous launch plan")
    instances = argv["instances"]
    if any(instances[role] != {
        "pid": security["roles"][role]["pid"],
        "start_ns": security["roles"][role]["start_ns"],
    } for role in ROLES):
        raise NativeRestartIntegrityError(
            "native image, credentials and kernel argv disagree on process instances"
        )
    # Check AFTER both independent native paths. An action is never permitted
    # on the basis of a transiently matching PID, stale policy or lost locks.
    require_lifecycle_owner()
    require_config_owner()
    if journal.read() != initial or \
       inspect_security_policy(
           Path(security_evidence), previous_backup, process_evidence,
           journal_record=initial, expected_scripts=expected_scripts,
       )["policy_sha256"] != policy["policy_sha256"] or \
       inspect_process_evidence(
           process_evidence, previous_backup, expected_scripts,
           initial["previous"],
       )["previous"] != old["previous"] or \
       security_reader.inspect_twice() != security or \
       inspect_restarted_argv(
           previous_backup, process_evidence, expected_scripts,
           expected_supervisor_argv, argv_reader,
       )["instances"] != instances:
        raise NativeRestartIntegrityError("unstable native restart attestation")
    require_lifecycle_owner()
    require_config_owner()
    return {
        "state": "previous-restart-integrity-observed",
        "instances": instances,
        "security_policy_sha256": policy["policy_sha256"],
        "engine_argv_sha256": argv["engine_argv_sha256"],
        "whole_intent_phase": "mutating",
        "safe_to_enable_voice": False,
        "safe_to_finish_intent": False,
        "restart_ready": False,
        "media_pass": False,
    }

def attest_previous_restart(**kwargs) -> dict:
    """One fail-closed public native integrity boundary; never permits Apply."""
    try:
        return _attest_previous_restart(**kwargs)
    except NativeRestartIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, RuntimeError) as exc:
        raise NativeRestartIntegrityError(
            "untrusted previous Voice native restart image, credentials or argv"
        ) from exc
