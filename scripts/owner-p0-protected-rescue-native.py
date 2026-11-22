#!/usr/bin/env python3
"""#1213 genuine disposable _107 -> _109 failed protected update, rescued by _111.

Original installed zapret_service.sh retains FD9, SCRIPT_DIR, service callback,
Config, pkg hooks and kernel ownership. Only package-attested 111 backend Python
modules are privately overlaid to finish the old 109 guarded operation.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
BACKEND = SERVICE.parent / "backend"
CONFIG = Path("/conf/config.xml")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
RECORD = Path("/var/db/zapret2/pkg-update/operation.json")
MARKER = Path("/var/run/zapret2-restyle/pkg-replacement.restart")
PIDFILE = Path("/var/run/dvtws2.pid")
NAME = "os-zapret2-restyle"
OLD = ("0.6.5_107", "85d8e6a1d00cc81d22e13aec6d3b8d1a59e65de6d223c5e4947c0e62e93ad8d7")
BROKEN = ("0.6.5_109", "1e08caf8dae9552e86085abf1d7f5c8db1e85a5640da4bfc197f9462f25e7d8a")
FIXED = ("0.6.5_111", "7257f54d74ef10fedc30d75e5e4a13861253bc8ad64d64ab232c537c2a56fae3")
PATCH = ("global_exclusions.py", "auto_detect_origin_map.py", "auto_detect_owner.py")
STAGE = Path("/var/db/zapret2/owner-p0-guarded-rescue")


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def run(argv, *, timeout=180, env=None, binary=False):
    return subprocess.run(argv, capture_output=True, check=False,
                          text=not binary, timeout=timeout, env=env)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def module(file, identity):
    spec = importlib.util.spec_from_file_location(identity, HERE / file)
    need(spec is not None and spec.loader is not None, "ORIGINAL_TEST_HELPER_MISSING")
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


def manifest(pkg):
    result = run(["/usr/bin/tar", "-xOf", str(pkg), "+MANIFEST"], timeout=40)
    need(result.returncode == 0 and len(result.stdout) < 512000,
         "PUBLISHED_NATIVE_MANIFEST_MISSING")
    return json.loads(result.stdout)


def pin_archive(version_sha):
    ver, sha = version_sha
    pkg = Path("/root") / (NAME + "-" + ver + ".pkg")
    need(not pkg.exists() and not pkg.is_symlink(), "OLD_ARCHIVE_ON_DISPOSABLE")
    url = "https://github.com/Tolian82/os-zapret2-restyle/releases/download/v" + ver + "/" + pkg.name
    need(run(["/usr/bin/fetch", "-o", str(pkg), url], timeout=120).returncode == 0
         and digest(pkg) == sha, "PUBLISHED_PKG_SHA_MISMATCH")
    data = manifest(pkg)
    need(data.get("version") == ver and data.get("name") == NAME and
         data.get("abi") == run(["pkg", "config", "ABI"]).stdout.strip(),
         "PUBLISHED_PKG_ABI_MISMATCH")
    return pkg, data


def installed():
    q = run(["pkg", "query", "%v", NAME], timeout=30)
    need(q.returncode == 0, "PKGDB_NOT_AVAILABLE")
    return q.stdout.strip()


def state():
    return json.loads(JOURNAL.read_bytes())


def status():
    return run([str(SERVICE), "status"], timeout=40).returncode


def gate():
    needed = ("GITHUB_ACTIONS", "ZAPRET2_OWNER_P0_DISPOSABLE",
              "ZAPRET2_NATIVE_BUILD_CI", "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK")
    need(all(os.environ.get(x) in ("true", "1") for x in needed) and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64" and
         run(["pkg", "info", "-e", NAME]).returncode == 1 and
         run(["pkg", "config", "ABI"]).returncode == 0 and
         run(["opnsense-version", "-a"]).stdout.strip().startswith("26.7") and
         not RECORD.exists() and not MARKER.exists() and not STAGE.exists(),
         "REQUIRES_PRISTINE_DISPOSABLE_OPNSENSE_267")


def set_exclusions():
    # Original Model + original Config lock, disposable guest ONLY.
    script = r'''require_once("script/load_phalcon.php");
require_once("/usr/local/opnsense/scripts/OPNsense/Zapret/initialize_config.php");
$c=\OPNsense\Core\Config::getInstance();$c->lock();try{
$m=new \OPNsense\Zapret\Zapret();
if (!$m->setNodeByReference("hostlist.excludedomains","ads.example.com\n") ||
    !$m->setNodeByReference("hostlist.excludeipset","198.51.100.0/24\n") ||
    count($m->performValidation(false)) || !$m->serializeToConfig(false,true))
 throw new \RuntimeException("disposable exclusion Model refused");
$c->save(["description"=>"disposable P0 #1213 native exclusions"]);
}finally{$c->unlock();}'''
    need(run(["/usr/local/bin/php", "-r", script], timeout=45).returncode == 0,
         "REAL_DISPOSABLE_MODEL_EXCLUSIONS_REFUSED")


def stage_backend(pkg, m):
    # Exact 111 package members only. All other backend bytes from installed
    # 109. No files in installed package, runtime, Config or journal modified.
    STAGE.mkdir(mode=0o700)
    STAGE.chmod(0o700)
    dest = STAGE / "backend"
    shutil.copytree(BACKEND, dest, symlinks=False)
    dest.chmod(0o700)
    listed = run(["/usr/bin/tar", "-tf", str(pkg)], timeout=35)
    need(listed.returncode == 0 and len(listed.stdout) < 4000000,
         "111_ARCHIVE_INDEX_UNAVAILABLE")
    members = listed.stdout.splitlines()
    for name in PATCH:
        relative = "usr/local/opnsense/scripts/OPNsense/Zapret/backend/" + name
        match = [x for x in members if x.lstrip("/").removeprefix("./") == relative]
        need(len(match) == 1 and "/" + relative in m.get("files", {}),
             "111_BACKEND_MEMBER_NOT_UNIQUE_AND_MANIFESTED")
        result = run(["/usr/bin/tar", "-xOf", str(pkg), match[0]],
                     binary=True, timeout=35)
        trusted = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend" / name
        need(result.returncode == 0 and 100 < len(result.stdout) < 262144
             and result.stdout == trusted.read_bytes(),
             "111_PACKAGE_BACKEND_SHA_OR_SOURCE_MISMATCH")
        item = dest / name
        need(item.is_file() and not item.is_symlink() and
             item.stat().st_nlink == 1, "FOREIGN_STAGED_MEMBER")
        item.write_bytes(result.stdout)
        item.chmod(0o644)
        need(digest(item) == hashlib.sha256(result.stdout).hexdigest(),
             "STAGED_REPAIR_INODE_DRIFTED")
    return dest


def main():
    gate()
    protected = module("stage5-native-protected-update.py", "p0_protected")
    bridge = module("test-own70-native-package-handoff.py", "p0_model")
    wan = module("p5b2b-native-witness.py", "p0_wan")
    g03 = module("stage2-opnsense-g03-first-install.py", "p0_g03")
    old, _ = pin_archive(OLD)
    broken, _ = pin_archive(BROKEN)
    fixed, manifest111 = pin_archive(FIXED)
    result = run(["pkg", "-o", "REPO_AUTOUPDATE=false", "add", "-f", str(old)],
                 timeout=240)
    need(result.returncode == 0 and installed() == OLD[0] and status() == 1,
         "PUBLISHED_107_INSTALL_FAILED")
    wan.set_guest_lo0()
    bridge.set_guest_list_mode()
    set_exclusions()
    protected.seed_qualified_stable_tag_for_disposable_guest(g03)
    upstream = g03.dispatch_and_poll()
    need(upstream.get("installed") == "1" and upstream.get("service") == "stopped",
         "G03_PINNED_UPSTREAM_NOT_READY")
    for mode in ("list", "auto"):
        result = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                      "strategies", bridge.request(mode)], timeout=300)
        need(result.returncode == 0 and "applied-id=" in result.stdout
             and status() == 0, "ORIGINAL_SCHEMA2_MODEL_APPLY_REFUSED")
    old_state = state()
    schema, _ = protected.original_auto_generation(old_state["detail"]["id"], True)
    need(schema == 2, "ORIGINAL_SCHEMA2_PROFILE_NOT_RUNNING")
    config_sha = digest(CONFIG)
    engine = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    engine_sha = digest(engine)
    refused = run([str(SERVICE), "pkg-update", str(broken)], timeout=450)
    pkg_record = json.loads(RECORD.read_bytes()) if RECORD.is_file() else {}
    observed = {
        "protected_rc69": refused.returncode == 69,
        "guarded_review_refusal":
            "pkg-update-refused=RUNTIME_RESTORE_REQUIRES_REVIEW" in
            (refused.stderr + refused.stdout),
        "original_boot_stage": "stage:boot" in
            (refused.stderr + refused.stdout),
        "original_restore_guard_known": any(
            marker in (refused.stderr + refused.stdout)
            for marker in ("guard:unknown", "guard:config-save",
                           "guard:committed-probe", "guard:saved-probe",
                           "guard:ipfw-commit")),
        "postinstall_attested": pkg_record.get("phase") == "postinstall-attested",
        "original_from107": pkg_record.get("from_version") == OLD[0],
        "successor109": pkg_record.get("to_version") == BROKEN[0],
        "immutable_109_hash": pkg_record.get("sha256") == BROKEN[1],
        "previously_running": pkg_record.get("was_running") is True,
        "installed109": installed() == BROKEN[0],
        "shared_committed": state().get("phase") == "committed",
        "engine_stopped": status() == 1,
        "restart_marker": MARKER.is_file(),
        "child_pid_absent": not PIDFILE.exists(),
        "saved_config_unchanged": digest(CONFIG) == config_sha,
        "dvtws_binary_unchanged": digest(engine) == engine_sha,
    }
    # The first pkg-update protection may classify its failed child as
    # stage:unknown (rc69) even though the SAME stopped, attested successor
    # later reaches the exact P2 build-preflight on a one-time explicit finish.
    # Both steps occurred on the real router. Do not misclassify the first
    # bounded reason as evidence that the restored generation was qualified.
    expected_refusal = all(v for k, v in observed.items()
                           if k not in ("original_boot_stage",
                                        "original_restore_guard_known"))
    print("P0_OWNER_NATIVE_109_REFUSAL=" +
          json.dumps({"reproduced": expected_refusal, "checks": observed},
                     sort_keys=True), flush=True)
    need(expected_refusal, "REAL_107_TO_109_OWNER_FAILURE_NOT_REPRODUCED")
    # The owner next attempted this exactly once, seeing P2 canonical
    # global-exclusion refusal. Qualify that same original installed service
    # path BEFORE touching even the private repair overlay.
    attempted = run([str(SERVICE), "pkg-update-finish", BROKEN[1], BROKEN[0]],
                    timeout=300)
    combined = attempted.stdout + "\n" + attempted.stderr
    p2_refusal = (
        attempted.returncode == 70 and
        "P2 source-only provenance unavailable: native profile exclusion policy is missing or incorrectly ordered" in combined and
        "native-common-boot-guard=build-preflight" in combined and
        "pkg-update-finish-failed=boot" in combined and
        RECORD.is_file() and
        json.loads(RECORD.read_bytes()).get("phase") == "postinstall-attested" and
        status() == 1 and installed() == BROKEN[0] and
        digest(CONFIG) == config_sha and digest(engine) == engine_sha)
    print("P0_OWNER_NATIVE_109_P2_BOOT_REFUSAL=" +
          json.dumps({"reproduced": p2_refusal, "finish_rc": attempted.returncode,
                      "exact_p2_exclusion_reason":
                      "native profile exclusion policy is missing or incorrectly ordered" in combined,
                      "guard_build_preflight":
                      "native-common-boot-guard=build-preflight" in combined,
                      "phase_postinstall_attested": RECORD.is_file() and
                      json.loads(RECORD.read_bytes()).get("phase") == "postinstall-attested"},
                     sort_keys=True), flush=True)
    need(p2_refusal, "ORIGINAL_SECOND_OWNER_P2_REFUSAL_NOT_REPRODUCED")
    staged = stage_backend(fixed, manifest111)
    env = {**os.environ, "BACKEND_DIR": str(staged), "PYTHONDONTWRITEBYTECODE": "1"}
    finish = run([str(SERVICE), "pkg-update-finish", BROKEN[1], BROKEN[0]],
                 env=env, timeout=330)
    # Once the 109 record is durably closed, a standalone installed 109
    # status consumer may differ from the same original-FD9 native attester
    # supplied with patched canonical learning sources. Capture both, plus
    # the actual native process census; no inferred PID or status success.
    staged_rc = run([str(SERVICE), "status"], env=env, timeout=50).returncode
    ordinary_rc = status()
    census = run(["ps", "-axo", "comm="], timeout=30)
    names = census.stdout.splitlines() if census.returncode == 0 else []
    engine_present = any(name.strip().rsplit("/", 1)[-1] == "dvtws2"
                         for name in names)
    monitor_present = Path("/var/run/zapret2-supervisor-monitor.pid").is_file()
    measured = {
        "finish_rc0": finish.returncode == 0,
        "finish_receipt": "zapret-pkg-update-committed=1" in finish.stdout,
        "staged_attester_running": staged_rc == 0,
        "installed109_attester_running": ordinary_rc == 0,
        "pid_file_present": PIDFILE.is_file(),
        "real_dvtws2_process_present": engine_present,
        "monitor_pid_file_present": monitor_present,
        "pkg_is_109": installed() == BROKEN[0],
        "record_closed": not RECORD.exists(),
        "restart_marker_closed": not MARKER.exists(),
        "shared_apply_committed": state().get("phase") == "committed",
        "config_sha_unchanged": digest(CONFIG) == config_sha,
        "engine_sha_unchanged": digest(engine) == engine_sha,
    }
    # Keep this first pass strict. A false stage/installed state indicates
    # the original package owner cannot yet claim safely-running service.
    recovered = all(measured.values())
    print("P0_OWNER_NATIVE_GUARDED_109_FINISH=" +
          json.dumps({"verified": recovered, "checks": measured},
                     sort_keys=True), flush=True)
    need(recovered, "ORIGINAL_FD9_GUARDED_109_RECOVERY_REFUSED")
    # Normal installed package-owned protected upgrade, no direct pkg add.
    upgrade = run([str(SERVICE), "pkg-update", str(fixed)],
                  env=env, timeout=480)
    updated_state = state()
    id_ = updated_state.get("detail", {}).get("id", "")
    schema3, profiles = (0, [])
    if status() == 0 and re.fullmatch(r"[a-f0-9]{32}", id_):
        schema3, profiles = protected.original_auto_generation(id_, True)
    accepted = (upgrade.returncode == 0 and
                "pkg-update=verified-installed-and-restored" in upgrade.stdout and
                installed() == FIXED[0] and status() == 0 and schema3 == 3
                and len(profiles) >= 1 and updated_state.get("phase") == "committed"
                and not RECORD.exists() and not MARKER.exists() and
                digest(CONFIG) == config_sha and digest(engine) == engine_sha)
    print("P0_OWNER_NATIVE_111_RECONCILED=" +
          json.dumps({"verified": accepted, "rc": upgrade.returncode,
                      "pkg": installed(), "running": status() == 0,
                      "schema": schema3, "learning": len(profiles),
                      "config_unchanged": digest(CONFIG) == config_sha,
                      "backend_stage_preserved": STAGE.is_dir()}), flush=True)
    need(accepted, "111_NATIVE_PROTECTED_OWNER_RECONCILIATION_REFUSED")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, KeyError, TypeError, ValueError,
            subprocess.SubprocessError) as error:
        # No raw user data, Config XML, transient archive paths or stderr.
        print("P0_NATIVE_GUARDED_RESCUE=REFUSED:" + type(error).__name__,
              file=sys.stderr)
        sys.exit(1)
