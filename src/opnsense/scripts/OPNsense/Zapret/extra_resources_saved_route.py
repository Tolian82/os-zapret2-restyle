#!/usr/local/bin/python3.13
"""Original setup.lock -> native FD9 read-only saved Strategies input preview.

This is an INPUT ATTESTATION only, NOT a compatibility preflight or remove
authorization. CLI is intentionally root-only via extra_resources_launcher.sh
and zapret_service.sh; it accepts no caller-supplied Config/resources/paths.
It cannot Stop/Start, write Config/IPFW, remove resources or change metadata.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

# Keep the original backend import resolution used by native service scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from backend.shared_apply_operation import native_lifecycle_gate
from backend.voice_ipfw_adapter import require_lifecycle_lock
from backend.voice_native_lifecycle_router import _locked_config, native_config_owner
from extra_resources_saved_strategies import locked_saved_strategies_view

CONFIG = Path("/conf/config.xml")
RUNTIME = Path("/usr/local/etc/zapret2")
MANIFEST = Path("/var/db/zapret2-restyle/extra-resources/installed.json")
SHARED = Path("/var/db/zapret2/shared-apply")


def _clear_common_journal() -> dict:
    gate = native_lifecycle_gate("common-apply", root=SHARED)
    if gate != {"state": "clear", "safe_to_mutate": True}:
        raise RuntimeError("native shared Apply journal requires review")
    return gate



CANDIDATE_COMPILER = Path(__file__).with_name("extra_resources_inert_compile.sh")
ACTIVE_REFERENCE = Path("/usr/local/etc/zapret2/runtime-v2")


def compile_inert_saved_candidate(saved_template: Path, upstream: Path,
                                 saved_xml: Path, workspace: Path) -> dict:
    """Use the EXACT native common orchestrator on private upstream-only files.

    This produces a candidate artifact; it never starts the installed
    engine or proves Lua-function dependencies. No alternative parser,
    Config.save, engine launch, kernel write or live runtime promotion.
    """
    work = workspace / "native-strategies-build"
    work.mkdir(mode=0o700)
    release = work / "release"
    try:
        result = subprocess.run(
            ["/bin/sh", str(CANDIDATE_COMPILER), str(saved_template),
             str(upstream), str(saved_xml), str(ACTIVE_REFERENCE),
             str(work), str(release)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=60, check=False,
            # The parent holds and attests FD9. It does not delegate
            # service authority to the inert compiler subprocess.
            close_fds=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("native prospective Strategies compiler unavailable") from exc
    if result.returncode:
        # Do not expose strategy arguments or native Config in diagnostics.
        raise RuntimeError("native prospective Strategies compilation rejected")
    hashes = {}
    for name in ("dvtws.args", "traffic-user.conf", "traffic.conf"):
        item = release / name
        info = item.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size == 0 or info.st_size > 4 * 1024 * 1024):
            raise RuntimeError("native prospective Strategies output is missing or unsafe")
        hashes[name] = hashlib.sha256(item.read_bytes()).hexdigest()
    return {
        "state": "native-common-candidate-compiled-input-only",
        "argv_sha256": hashes["dvtws.args"],
        "traffic_sha256": hashes["traffic.conf"],
        "saved_traffic_sha256": hashes["traffic-user.conf"],
        "engine_lua_proof": "not-run",
        "authorized": False,
    }


def preview_saved_input(
    *, config: Path = CONFIG, runtime: Path = RUNTIME, manifest: Path = MANIFEST,
    workspace: Path, gate_checker=_clear_common_journal,
    lock_checker=require_lifecycle_lock,
    owner_provider=native_config_owner, compiler=compile_inert_saved_candidate,
    **view_kwargs,
) -> dict:
    """Run a wholly read-only native Config/HEAD witness under inherited FD9.

    The caller holds setup.lock; this function acquires no *second* FD9.
    A real original Config flock is acquired and held over rendering and the
    view. Test overrides are callable only to Python test code, not to CLI.
    """
    lock_checker()
    if gate_checker() != {"state": "clear", "safe_to_mutate": True}:
        raise RuntimeError("unsafe native shared Apply journal")
    fd = os.open(config, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        owner = owner_provider()
        # Existing Config guard checks both path and fd owner after flock.
    except Exception:
        os.close(fd)
        raise
    # NOTE: _locked_config needs the exclusive lock; acquire it first.
    return _attest_fd(
        fd, config=config, runtime=runtime, manifest=manifest,
        workspace=workspace, gate_checker=gate_checker,
        lock_checker=lock_checker, owner=owner, compiler=compiler,
        **view_kwargs,
    )


def _attest_fd(fd: int, *, config: Path, runtime: Path, manifest: Path,
               workspace: Path, gate_checker, lock_checker, owner,
               compiler, **view_kwargs) -> dict:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _locked_config(config, fd, owner)
        with locked_saved_strategies_view(
            runtime, manifest, config_path=config, config_fd=fd,
            config_owner=owner, workspace_root=workspace,
            check_lifecycle=lock_checker, **view_kwargs,
        ) as (plan, prospective, saved_xml, template):
            if not saved_xml.is_file() or not template.is_file():
                raise RuntimeError("native prospective Config/template absent")
            # Compiles against hypothetical future Git HEAD files under the
            # existing lifecycle/Config lock; never the current extra set.
            native = compiler(template, prospective, saved_xml, saved_xml.parent)
            if (native.get("state") != "native-common-candidate-compiled-input-only"
                    or native.get("authorized") is not False
                    or native.get("engine_lua_proof") != "not-run"):
                raise RuntimeError("invalid read-only native compiler attestation")
            if plan["compatibility"] != "unknown" or plan["authorized"] is not False:
                raise RuntimeError("invalid prospective input-only state")
            counts = plan["counts"]
            for key in ("lua", "bin", "total"):
                if type(counts.get(key)) is not int or counts[key] < 0:
                    raise RuntimeError("invalid prospective resource counts")
            if counts["lua"] + counts["bin"] != counts["total"]:
                raise RuntimeError("invalid prospective resource count sum")
            result = {
                "state": "saved-native-input-attested",
                "compatibility": "unknown",
                "authorized": False,
                "lua": counts["lua"],
                "bin": counts["bin"],
                "total": counts["total"],
                "inventory_sha256": plan["witness"]["inventory_sha256"],
                "saved_pair": plan["saved_pair"]["status"],
                "engine_lua_proof": "not-run",
                "native_candidate": native["state"],
                "candidate_argv_sha256": native["argv_sha256"],
            }
        lock_checker()
        _locked_config(config, fd, owner)
        if gate_checker() != {"state": "clear", "safe_to_mutate": True}:
            raise RuntimeError("native shared Apply journal changed during preview")
        return result
    finally:
        os.close(fd)


def main(argv: list[str]) -> int:
    if argv != ["preview-saved"]:
        print("usage: extra_resources_saved_route.py preview-saved", file=sys.stderr)
        return 64
    try:
        require_lifecycle_lock()
        if os.environ.get("EXTRA_RESOURCES_SETUP_LOCK_OWNER") != "1":
            raise RuntimeError("original setup lock owner is missing")
        # A unique private root-owned temp directory only. The existing
        # view rejects shared/world-readable workspaces. Never persist XML.
        with tempfile.TemporaryDirectory(prefix="zapret-remove-preview-", dir="/tmp") as tmp:
            result = preview_saved_input(workspace=Path(tmp))
        print("extra-resources-saved-preview=" +
              json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        # No sensitive Config, strategy args or file paths in CLI diagnostics.
        print("ERROR: read-only saved Strategies input preview refused",
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
