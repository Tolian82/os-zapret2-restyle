#!/usr/bin/env python3
"""TZ6v2: qualify three found drafts inside the ONE original FD9 staging.

No CLI can save Config, write found files, start a service, create a journal,
or grant Apply success. The only production caller is the original locked PHP
SharedApplyRequest stage. The unchanged common executor still refuses found
intent until Config + all sources + generated release have durable recovery.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys

from auto_detect_destination_commit import (
    DestinationRefused, SHARED_FOUND_NAMES, _plan_shared_found_under_original_locks,
)
from auto_detect_gui_hostlist import AUTO_HOSTLIST, AUTO_LOCK
from auto_detect_owned_sources import OWNED_ROOT, read_owned
from auto_detect_original_lock_handoff import (
    CONFIG_PATH, assert_inherited_config_fd,
)

MAX_INPUT = 4 * 1024 * 1024
MAX_OUTPUT = 512 * 1024
REVISION = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)


class FoundStageRefused(ValueError):
    """Never include untrusted domains or user file contents in diagnostics."""


def qualify_readonly(payload: dict, targets: dict, owned: dict, *, uid: int) -> dict:
    """Private pure-intent + locked-file binding; caller holds Config -> P2.

    A successful return is only a candidate PREIMAGE, not a commit receipt.
    In particular, any minute-worker write after releasing P2 invalidates
    the subsequent inode/ctime/mtime+bytes CAS, rather than losing a find.
    """
    if (not isinstance(payload, dict) or
            list(payload) != ["schema_version", "kind", "config_revision",
                              "found_intent", "manual", "global_exclude"] or
            type(payload["schema_version"]) is not int or
            payload["schema_version"] != 1 or
            payload["kind"] != "tz6v2-found-root-stage" or
            not isinstance(payload["config_revision"], str) or
            not REVISION.fullmatch(payload["config_revision"]) or
            not isinstance(payload["found_intent"], dict) or
            not isinstance(payload["manual"], dict) or
            list(payload["manual"]) != ["youtube", "user"] or
            any(type(value) is not str for value in payload["manual"].values()) or
            type(payload["global_exclude"]) is not str or
            not isinstance(owned, dict) or list(owned) != ["youtube", "user"] or
            any(type(owned.get(name)) is not str for name in ("youtube", "user"))):
        raise FoundStageRefused("incomplete_original_found_stage")
    intent = payload["found_intent"]
    if (list(intent) != ["schema_version", "kind", "sources",
                        "config_revision", "cross_source_validated",
                        "commit_authorized"] or
            type(intent["schema_version"]) is not int or
            intent["schema_version"] != 1 or
            intent["kind"] != "tz6v2-found-intent" or
            intent["config_revision"] != payload["config_revision"] or
            intent["cross_source_validated"] is not False or
            intent["commit_authorized"] is not False or
            not isinstance(intent["sources"], dict) or
            list(intent["sources"]) != list(SHARED_FOUND_NAMES)):
        raise FoundStageRefused("unqualified_original_found_intent")

    baselines, drafts = {}, {}
    for name in SHARED_FOUND_NAMES:
        record = intent["sources"][name]
        if (not isinstance(record, dict) or list(record) != ["base", "draft"] or
                not isinstance(record["base"], dict) or
                list(record["base"]) != ["status", "revision", "content"] or
                type(record["draft"]) is not str):
            raise FoundStageRefused("unqualified_original_found_source")
        baselines[name], drafts[name] = record["base"], record["draft"]
    rows, preview = _plan_shared_found_under_original_locks(
        baselines, drafts, payload["manual"], payload["global_exclude"],
        targets, uid=uid)
    if (preview["cross_source_validated"] is not True or
            preview["commit_authorized"] is not False or
            any(rows[name]["before"] != owned[name] for name in ("youtube", "user"))):
        raise FoundStageRefused("original_known_owner_changed")
    return {
        "schema_version": 1,
        "kind": "tz6v2-found-readonly-candidate",
        "found_batch": rows,
        "cross_source_validated": True,
        "commit_authorized": False,
        "config_committed": False,
    }


def main(argv: list[str]) -> int:
    if argv != ["prepare-locked"]:
        return 64
    # Both descriptors are inherited from the ORIGINAL service + PHP native
    # Config owner, not looked up by path or reacquired by this child.
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        return 69
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        assert_inherited_config_fd(4, CONFIG_PATH, owner_uid=None)
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if not raw or len(raw) > MAX_INPUT:
            raise FoundStageRefused("oversized_found_stage_input")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise FoundStageRefused("invalid_found_stage_input")
        from auto_detect_destination_commit import exclusive_destination_lock
        with exclusive_destination_lock(AUTO_LOCK, 0):
            owned = read_owned(OWNED_ROOT, owner_uid=0)
            if owned is None:
                raise FoundStageRefused("uninitialized_original_known_owner")
            targets = {
                "youtube": OWNED_ROOT / "youtube.txt",
                "user": OWNED_ROOT / "user.txt",
                "auto": AUTO_HOSTLIST,
            }
            result = qualify_readonly(data, targets, owned, uid=0)
            # Original Config file lock must still be the same held native FD.
            assert_inherited_config_fd(4, CONFIG_PATH, owner_uid=None)
        output = (json.dumps(result, ensure_ascii=True, sort_keys=False,
                             separators=(",", ":")) + "\n").encode("ascii")
        if len(output) > MAX_OUTPUT:
            raise FoundStageRefused("oversized_found_stage_output")
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
        return 0
    except (OSError, ValueError, TypeError, RuntimeError, UnicodeError):
        # Never log or echo a domain, raw Config or private file path here.
        print("ERROR: original found stage preflight refused", file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
