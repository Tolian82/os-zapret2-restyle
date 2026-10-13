#!/usr/bin/env python3
"""Old Telegram PoC quiescence: durable owner-only STOP INTENT, no actuator.

Existing original FD9 and original /conf/config.xml flock are required. The
write-once, fsynced intent is bound to the exact old five-resource previous
archive and reverse-plan seal. It lives BESIDE the strict six-stage journal,
which must remain byte-for-byte unchanged. No process/IPFW/Config/marker
mutation occurs here. A future actuator must independently attest the live
old process/kernel epochs and revalidate this intent before EVERY mutation.

The sibling intent is retained after power loss, including when the primary
cutover root disappears; the ordinary lifecycle guard MUST reject it.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import tempfile
import sys

from voice_cutover_backup import _private_dir, _read_private_file, _sync_dir
from voice_cutover_config_restore import _pinned_regular
from voice_native_recovery_quiescence import _locked_config
from voice_native_legacy_previous_seal import NAME, _digest, _write_once, inspect_legacy_previous
from voice_native_legacy_restore_plan import PLAN_NAME, PLAN_LIMIT, inspect_legacy_restore_plan
import voice_ipfw_runtime as native

SCHEMA=1
FILES=frozenset(("intent.json","intent.sha256"))
SUFFIX="-legacy-quiescence-intent"
LIMIT=16384

class LegacyQuiescenceIntentError(RuntimeError):
    pass


def intent_directory(root):
    root=Path(root)
    return root.with_name(root.name+SUFFIX)


def _canonical(record):
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(raw)>LIMIT:
        raise LegacyQuiescenceIntentError("quiescence intent too large")
    return raw


def inspect_legacy_quiescence_intent(root):
    """Read only the immutable sibling intent; never authorize an actuator."""
    directory=intent_directory(root)
    _private_dir(directory)
    if set(os.listdir(directory))!=FILES:
        raise LegacyQuiescenceIntentError("partial or foreign quiescence intent")
    raw=_read_private_file(directory/"intent.json",LIMIT)
    seal=_read_private_file(directory/"intent.sha256",65)
    if seal!=(_digest(raw)+"\n").encode("ascii"):
        raise LegacyQuiescenceIntentError("corrupt quiescence intent")
    record=json.loads(raw)
    previous=inspect_legacy_previous(root)
    plan=inspect_legacy_restore_plan(root)
    expected={
        "schema":SCHEMA,"phase":"old-poc-stop-intent-not-executed",
        "previous_five":previous["previous_five"],
        "process_security_policy_sha256":previous["process_security_policy_sha256"],
        "legacy_ipfw_structure_sha256":previous["legacy_ipfw_structure_sha256"],
        "restore_plan_sha256":_digest(
            _read_private_file(Path(root)/PLAN_NAME/"plan.json",PLAN_LIMIT)),
        "safe_to_execute":False,"safe_to_mutate":False,
        "safe_to_enable_voice":False,"public_voice_apply":False,
        "boot_recovery_validated":False,"media_pass":False,
    }
    if record!=expected or _canonical(record)!=raw or (
        plan["previous_five"]!=previous["previous_five"]
        or plan["process_security_policy_sha256"]!=
           previous["process_security_policy_sha256"]
    ):
        raise LegacyQuiescenceIntentError("intent not bound to predecessor")
    return {**record,"state":"old-poc-quiescence-intent-sealed-execution-pending"}


def prepare_legacy_quiescence_intent(
    *, root,config_path,config_fd,config_owner,require_lifecycle_owner,
):
    """Seal STOP intent with no process or kernel writes, no implicit retry."""
    if not callable(require_lifecycle_owner):
        raise LegacyQuiescenceIntentError("original lifecycle owner required")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    _pinned_regular(Path(config_path),config_fd,owner=config_owner)
    root=Path(root)
    _private_dir(root)
    if set(os.listdir(root))!={NAME,PLAN_NAME}:
        raise LegacyQuiescenceIntentError("old previous/plan not exact; cannot arm stop")
    previous=inspect_legacy_previous(root)
    plan=inspect_legacy_restore_plan(root)
    if (plan["previous_five"]!=previous["previous_five"] or
        plan["process_security_policy_sha256"]!=
           previous["process_security_policy_sha256"]):
        raise LegacyQuiescenceIntentError("old PoC five-domain seal unbound")
    dest=intent_directory(root)
    if os.path.lexists(dest):
        raise LegacyQuiescenceIntentError("existing intent never rearmed automatically")
    record={
        "schema":SCHEMA,"phase":"old-poc-stop-intent-not-executed",
        "previous_five":previous["previous_five"],
        "process_security_policy_sha256":previous["process_security_policy_sha256"],
        "legacy_ipfw_structure_sha256":previous["legacy_ipfw_structure_sha256"],
        "restore_plan_sha256":_digest(
            _read_private_file(root/PLAN_NAME/"plan.json",PLAN_LIMIT)),
        "safe_to_execute":False,"safe_to_mutate":False,
        "safe_to_enable_voice":False,"public_voice_apply":False,
        "boot_recovery_validated":False,"media_pass":False,
    }
    raw=_canonical(record)
    _private_dir(dest.parent)
    tmp=Path(tempfile.mkdtemp(prefix=".legacy-quiescence-",dir=dest.parent))
    os.chmod(tmp,0o700)
    _sync_dir(dest.parent)
    _write_once(tmp/"intent.json",raw)
    _write_once(tmp/"intent.sha256",(_digest(raw)+"\n").encode("ascii"))
    _sync_dir(tmp)
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    if (set(os.listdir(root))!={NAME,PLAN_NAME} or
        inspect_legacy_previous(root)!=previous or
        inspect_legacy_restore_plan(root)!=plan or
        os.path.lexists(dest)):
        raise LegacyQuiescenceIntentError("predecessor changed before STOP intent seal")
    os.rename(tmp,dest)
    _sync_dir(dest.parent)
    return inspect_legacy_quiescence_intent(root)


def main(argv):
    # Operator-only; never a configd, GUI, boot or service stop dispatcher.
    if argv!=["arm-stop-intent"]:
        print("usage: voice_native_legacy_quiescence_intent.py arm-stop-intent",
              file=sys.stderr)
        return 64
    fd=None
    try:
        native.require_native_lock()
        fd=os.open(native.CONFIG,os.O_RDWR|getattr(os,"O_NOFOLLOW",0))
        _pinned_regular(native.CONFIG,fd,owner=(0,0))
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        report=prepare_legacy_quiescence_intent(
            root=native.WHOLE,config_path=native.CONFIG,
            config_fd=fd,config_owner=(0,0),
            require_lifecycle_owner=native.require_native_lock,
        )
        if report["state"]!="old-poc-quiescence-intent-sealed-execution-pending":
            raise LegacyQuiescenceIntentError("untrusted STOP intent")
        print("legacy-voice-stop-intent=sealed-not-executed")
        print("native-voice-public-apply=disabled")
        return 0
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):
        print("ERROR: old PoC stop intent rejected; manual recovery review required",
              file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
