#!/usr/bin/env python3
"""#1052 P2i: P2h ORIGINAL builder preview -> real dvtws2, disposable guest.

This is not installed Apply, a second production engine, or a durable worker.
Only the existing P2e isolated OPNsense VM invokes --native; the old P0
guest/IPFW guard, pinned upstream SHA and loopback flow helper are reused.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
import auto_detect_origin_map as origin
import auto_detect_owner as owner
from auto_detect_storage import (_prepare, ROOT as PRODUCER, RAW_PATH, DEBUG_PATH)

MARK = "P2I_ORIGINAL_FD9_PREVIEW_NATIVE"
KNOWN = "youtube.com"
UNKNOWN = "unknown.p2i.invalid"
PORT = 6545
DIVERT = 19899
RULES = (19351, 19352)


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def load(name: str, file: Path):
    spec = importlib.util.spec_from_file_location(name, file)
    need(spec is not None and spec.loader is not None, "REQUIRED_TEST_MODULE_MISSING")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def components():
    p0 = load("p2i_reused_p0_guard", HERE / "test-p0-native-auto-observer.py")
    fixture = load("p2i_original_shared_fixture", HERE / "test-p2e-original-shared-build.py")
    return p0, fixture


def _fixture(native_root: Path):
    """Use the original orchestrator, not P0's constructed test profile."""
    _, original = components()
    case = original.OriginalSharedGeneration("runTest")
    case.setUp()
    try:
        case.root.chmod(0o755)
        for lua in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua"):
            real = native_root / "lua" / lua
            need(real.is_file() and not real.is_symlink(), "PINNED_UPSTREAM_LUA_MISSING")
            shutil.copyfile(real, case.static / "lua" / lua)
            (case.static / "lua" / lua).chmod(0o644)
        mapped, args = case.build(
            f"--filter-tcp={PORT}\n--filter-l7=http\n<HOSTLIST:youtube>\n"
            "--payload=http_req\n--lua-desync=multisplit:pos=method+2\n",
            voice_on=False, mode="auto")
        source = case.check_nonactivating(mapped, args)
        need(any(p["status"] == "known-hostlist" and p["hostlist"] == "youtube"
                 for p in source["profiles"]), "ORIGINAL_KNOWN_SOURCE_NOT_ATTESTED")
        original_argv = args.read_bytes()
        (case.work / "plan.json").write_text(json.dumps({
            "page": "strategies",
            "candidate": {"general": {"enabled": "1"}},
            "changed_fields": [], "dependencies": "a" * 64,
        }))
        digest = "b" * 64  # Synthetic digest, not an OPNsense PHP receipt.
        preview = origin.stage_original_preview(case.work, digest)
        need(origin.verify_original_preview(case.work, digest) == preview,
             "SEALED_PREVIEW_RECONSTRUCTION_MISMATCH")
        need(args.read_bytes() == original_argv and
             not (case.release / owner.MAP_NAME).exists(),
             "INERT_RELEASE_ARGV_OR_OWNER_MAP_CHANGED")
        planned = (case.release / "auto-detect-observer-preview.args").read_bytes()
        expected_sha = preview["final_args_sha256"]
        need(hashlib.sha256(planned).hexdigest() == expected_sha,
             "SEALED_PREVIEW_DIGEST_MISMATCH")
        need(preview["evidence"] == "P2H_ORIGINAL_FD9_SEALED_PREVIEW_NONACTIVATING"
             and preview["activation_authorized"] is False,
             "PREVIEW_IMPROPERLY_AUTHORIZED")
        return case, planned, preview
    except BaseException:
        case.doCleanups()
        raise


def _remap_managed(case, planned: bytes) -> list[str]:
    """Same native validator map as installed engine, never rewrite selectors."""
    reference = str(case.active).rstrip("/") + "/"
    public = case.root / "native-public"
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    (public / "managed").mkdir(mode=0o755)
    (public / "managed").chmod(0o755)
    allowed = {"--hostlist", "--hostlist-exclude", "--ipset",
               "--ipset-exclude"}
    result = []
    for token in planned.decode("utf-8").split():
        key, equal, value = token.partition("=")
        if equal and value.startswith(reference):
            need(key in allowed, "UNEXPECTED_MAPPED_ENGINE_OPTION")
            rel = Path(value[len(reference):])
            need(len(rel.parts) == 2 and rel.parts[0] == "managed"
                 and re.fullmatch(r"(?:hostlist|ipset)-[a-z0-9-]+\.txt",
                                  rel.parts[1]) is not None,
                 "UNTRUSTED_MANAGED_REFERENCE")
            source = case.release / rel
            need(source.is_file() and not source.is_symlink(),
                 "MISSING_ORIGINAL_MANAGED_SOURCE")
            destination = public / rel
            if not destination.exists():
                shutil.copyfile(source, destination)
                destination.chmod(0o644)
            token = key + "=" + str(destination)
        result.append(token)
    need(result and result[0] == f"--port={DIVERT}" and
         any(t == f"--hostlist-auto={RAW_PATH}" for t in result) and
         any(t == f"--hostlist-auto-debug={DEBUG_PATH}" for t in result),
         "ORIGINAL_OBSERVER_ARGS_NOT_IN_NATIVE_VIEW")
    need(all(not (x.startswith(reference) or "shared-work" in x) for x in result),
         "PRIVATE_FD9_PATH_REACHES_POST_DROP_NATIVE")
    return result


def _native_file_modes(gid: int, *, phase: str) -> None:
    root = PRODUCER.lstat()
    pending = (PRODUCER / "pending").lstat()
    need(stat.S_ISDIR(root.st_mode) and root.st_uid == 0 and
         root.st_gid == gid and stat.S_IMODE(root.st_mode) == 0o710,
         "NATIVE_ROOT_OWNER_OR_MODE_CHANGED")
    need(stat.S_ISDIR(pending.st_mode) and pending.st_uid == 0 and
         pending.st_gid == 0 and stat.S_IMODE(pending.st_mode) == 0o700,
         "NATIVE_PENDING_PRIVATE_MODE_CHANGED")
    need(set(os.listdir(PRODUCER)) ==
         {"pending", "inbox.txt", "debug.log"},
         "UNEXPECTED_NATIVE_PRODUCER_ARTIFACT")
    for file in (RAW_PATH, DEBUG_PATH):
        info = file.lstat()
        actual_mode = stat.S_IMODE(info.st_mode)
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
             actual_mode == 0o660 and info.st_uid == 0 and info.st_gid == gid,
             f"NATIVE_FILE_OWNER_OR_MODE_CHANGED:{phase}:{file.name}:"
             f"mode={actual_mode:04o}:uid={info.st_uid}:gid={info.st_gid}:"
             f"expected_gid={gid}:links={info.st_nlink}")


def _reattest_root_after_native_drop(before: dict, nobody) -> None:
    """Test ONLY: restore exact root inode ownership before installing IPFW.

    Upstream v1.0.7 takes ownership of the auto hostlist after root startup
    while preparing to drop privileges. The pending queue must NEVER trust
    a nobody-owned inode. The stopped traffic path in this disposable guest
    permits an exact FD9-like root reownership before adding scoped divert.
    """
    changed = []
    for file in (RAW_PATH, DEBUG_PATH):
        pre = before[file.name]
        now = file.lstat()
        need(stat.S_ISREG(now.st_mode) and
             (now.st_dev, now.st_ino, now.st_nlink) == pre and
             now.st_gid == nobody.pw_gid and
             stat.S_IMODE(now.st_mode) == 0o660 and
             now.st_uid in (0, nobody.pw_uid),
             "NATIVE_STARTUP_OWNERSHIP_OR_INODE_UNSAFE:" + file.name)
        if now.st_uid == nobody.pw_uid:
            os.chown(file, 0, nobody.pw_gid, follow_symlinks=False)
            changed.append(file.name)
        again = file.lstat()
        need((again.st_dev, again.st_ino, again.st_nlink) == pre and
             again.st_uid == 0 and again.st_gid == nobody.pw_gid and
             stat.S_IMODE(again.st_mode) == 0o660,
             "ROOT_POST_DROP_REOWNERSHIP_NOT_ATTESTED:" + file.name)
    need("inbox.txt" in changed, "PINNED_UPSTREAM_AUTO_INBOX_CHOWN_NOT_OBSERVED")
    _native_file_modes(nobody.pw_gid, phase="before-ipfw")
    print(MARK + "_UPSTREAM_STARTUP_CHOWN=OBSERVED_AND_ROOT_RESTORED_BEFORE_IPFW",
          flush=True)


def _debug_match(content: str, number: int) -> bool:
    return any(f" : profile {number} " in line and
               " : adding to " + str(RAW_PATH) in line and
               UNKNOWN in line for line in content.splitlines())


def _native(checkout: Path) -> None:
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
         "FREEBSD_ROOT_ONLY")
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_P2I_DISPOSABLE_NATIVE") == "1" and
         os.environ.get("ZAPRET2_P4C3_DISPOSABLE_NATIVE") == "1",
         "EXPLICIT_DISPOSABLE_VM_OPT_IN_REQUIRED")
    p0, _ = components()
    guard = p0.guard_module()
    native_root, engine, initial_rules = guard.guest_gate(checkout)
    nobody = pwd.getpwnam("nobody")
    need(nobody.pw_uid > 0 and nobody.pw_gid > 0,
         "UNQUALIFIED_NATIVE_ENGINE_USER")
    need(not PRODUCER.exists() and not PRODUCER.is_symlink(),
         "PRODUCER_ROOT_NOT_CLEAN_DISPOSABLE_VM")

    case = None
    process = None
    installed = []
    started = False
    logfile = None
    observed_native_log = ""
    observed_debug_log = ""
    try:
        case, planned, preview = _fixture(native_root)
        _prepare(PRODUCER, uid=0, engine_gid=nobody.pw_gid)
        _native_file_modes(nobody.pw_gid, phase="prepared")
        producer_ids = {file.name: (file.stat().st_dev, file.stat().st_ino,
                                    file.stat().st_nlink)
                        for file in (RAW_PATH, DEBUG_PATH)}
        print(MARK + "_PREPARED_NATIVE_PRODUCER=PASS", flush=True)
        args = _remap_managed(case, planned)
        # First check the uninstrumented preview with real native parser.
        dry = subprocess.run([str(engine), *args, "--user=nobody", "--dry-run"],
                             capture_output=True, timeout=15, check=False)
        need(dry.returncode == 0, "NATIVE_ORIGINAL_PREVIEW_DRY_RUN_REJECTED")
        print(MARK + "_DRY_RUN=PASS_NATIVE_PARSER", flush=True)
        need(RAW_PATH.read_bytes() == b"" and DEBUG_PATH.read_bytes() == b"",
             "DRY_RUN_PRODUCED_RAW_OR_DEBUG")
        # Inject ONLY native --debug for flow-selection evidence; it is not a
        # product argv change, and all target/filter/profile flags are intact.
        diagnostic = [args[0], "--debug=1", *args[1:], "--user=nobody"]
        logfile = case.root / "native-preview-engine.log"
        with logfile.open("wb") as output:
            process = subprocess.Popen([str(engine), *diagnostic],
                                       cwd=native_root, stdout=output,
                                       stderr=subprocess.STDOUT)
            time.sleep(0.6)
            need(process.poll() is None, "NATIVE_PREVIEW_ENGINE_DID_NOT_START")
            started = True
            uid = guard.cmd("ps", "-p", str(process.pid), "-o", "uid=")
            need(uid.returncode == 0 and uid.stdout.strip() == str(nobody.pw_uid),
                 "REAL_ENGINE_DID_NOT_DROP_TO_NOBODY")
            birth = guard.cmd("ps", "-p", str(process.pid), "-o", "lstart=")
            need(birth.returncode == 0 and birth.stdout.strip(),
                 "NATIVE_PROCESS_BIRTH_MISSING")
            _reattest_root_after_native_drop(producer_ids, nobody)
            for rule, item in zip(RULES, p0.rules()):
                need(guard.cmd("/sbin/ipfw", "-q", "add",
                               str(rule), *item).returncode == 0,
                     "SCOPED_NATIVE_DIVERT_ADD_REFUSED")
                installed.append(rule)
            delivered = p0.exchange(KNOWN, force_rst=False)
            need(delivered == p0.request(KNOWN),
                 "AUTHORIZED_KNOWN_HTTP_NOT_DELIVERED")
            time.sleep(0.1)
            need(RAW_PATH.read_bytes() == b"",
                 "KNOWN_PROFILE_COVERTLY_ENTERED_OBSERVER")
            before = p0.exchange(UNKNOWN, force_rst=True)
            need(before == p0.request(UNKNOWN), "UNKNOWN_HTTP_CHANGED_BEFORE_APPEND")
            time.sleep(0.7)
            need(RAW_PATH.read_text(encoding="ascii").splitlines() == [UNKNOWN],
                 "REAL_NATIVE_RAW_APPEND_MISSING_OR_DUPLICATED")
            after = p0.exchange(UNKNOWN, force_rst=False)
            need(after == p0.request(UNKNOWN), "UNKNOWN_HTTP_CHANGED_AFTER_APPEND")
            need(RAW_PATH.read_text(encoding="ascii").splitlines() == [UNKNOWN],
                 "NATIVE_RAW_APPEND_DUPLICATED_AFTER_INCLUDED")
            current = guard.cmd("ps", "-p", str(process.pid), "-o", "lstart=")
            need(process.poll() is None and current.returncode == 0 and
                 birth.stdout == current.stdout, "NATIVE_PROCESS_IDENTITY_CHANGED")
            for rule in RULES:
                count = guard.cmd("/sbin/ipfw", "-a", "list", str(rule))
                need(count.returncode == 0 and
                     re.search(rf"(?m)^0*{rule}\s+[1-9]\d*\s+", count.stdout),
                     "LOOPBACK_DIVERT_RULE_NOT_EXERCISED")
            _native_file_modes(nobody.pw_gid, phase="after-native-append")
            need(all((file.stat().st_dev, file.stat().st_ino,
                      file.stat().st_nlink) == producer_ids[file.name]
                     for file in (RAW_PATH, DEBUG_PATH)),
                 "INODE_REPLACED_DURING_NATIVE_APPEND")
    finally:
        failures = []
        for rule in reversed(installed):
            if guard.cmd("/sbin/ipfw", "-q", "delete", str(rule)).returncode:
                failures.append("SCOPED_DIVERT_RULE_LEAKED")
        if process is not None:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        rules_now = guard.cmd("/sbin/ipfw", "-q", "list")
        if rules_now.returncode != 0 or rules_now.stdout != initial_rules:
            failures.append("IPFW_NOT_RESTORED_TO_INITIAL_RULES")
        # Capture only bounded local evidence before disposable cleanup.
        if logfile is not None and logfile.is_file():
            observed_native_log = logfile.read_text(errors="replace")[-262144:]
        if DEBUG_PATH.is_file():
            observed_debug_log = DEBUG_PATH.read_text(errors="replace")[-32768:]
        if started and guard.cmd("pgrep", "-x", "dvtws2").returncode != 1:
            failures.append("ISOLATED_ENGINE_NOT_STOPPED")
        if PRODUCER.is_dir() and not PRODUCER.is_symlink():
            shutil.rmtree(PRODUCER)
        if PRODUCER.exists() or PRODUCER.is_symlink():
            failures.append("PRODUCER_ROOT_NOT_CLEANED")
        if case is not None:
            case.doCleanups()
        need(not failures, ";".join(failures))
    need(started and logfile is not None, "ENGINE_NOT_EXERCISED")
    native_number = preview["observer_native_number"]
    need(_debug_match(observed_debug_log, native_number),
         "RAW_APPEND_DEBUG_PROFILE_NOT_CORRELATED")
    need(f"autohostlist profile {native_number} " in observed_native_log,
         "NATIVE_OBSERVER_PROFILE_NOT_SELECTED")
    need("desync profile 1 " in observed_native_log,
         "NATIVE_KNOWN_FIRST_MATCH_NOT_SELECTED")
    need("* lua 'multisplit" in observed_native_log,
         "ORIGINAL_AUTHORIZED_LUA_NOT_EXERCISED")
    # No raw, debug or process output retained; no owner-machine changes.
    print(MARK + "=PASS_NATIVE_PINNED_PREVIEW_FIRST_MATCH_RAW_DEBUG_ONLY",
          flush=True)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            p0, _ = components()
            need(_debug_match(f"hello : profile 2 (tail) : client 127.0.0.1:111 : "
                              f"proto http : adding to {RAW_PATH} {UNKNOWN}", 2),
                 "DEBUG_CORRELATION_PARSER_REJECTED_VALID")
            need(not _debug_match("hello : profile 1 : adding to /tmp/wrong", 2),
                 "DEBUG_CORRELATION_FALSE_POSITIVE")
            print(MARK + "_SELF_TEST=PASS_SOURCE_ONLY")
        elif len(sys.argv) == 3 and sys.argv[1] == "--native":
            _native(Path(sys.argv[2]))
        else:
            raise RuntimeError("usage: --self-test | --native /tmp/p4c3-native-*")
    except Exception as exc:
        print(MARK + "=REFUSED:" + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
