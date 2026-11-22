#!/usr/bin/env python3
"""#1213 genuine disposable _107 -> _109 failed protected update, rescued by _111.

A verified native candidate supplies the existing service/FD9 code from private
staging. The failed old record is retained in the same atomic journal; ordinary
pkg installs the whole 111 payload BEFORE its installed owner launches dvtws2.
No installed source graft and no intermediate 109 engine are used.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
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


def crash_coordinator(stage, fixed, record_sha, boundary):
    """Kill only the disposable coordinator after an actual native boundary.

    Production package bytes remain untouched. A test-only native-command
    adapter exits without finally after the real FD9 transition or real pkg;
    the ordinary production recovery then resumes the exact durable record.
    """
    script = r'''import importlib.util,os,sys
from pathlib import Path
stage=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("actual_pkg_coordinator",stage/"protected_pkg_update.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m.native_command
boundary=sys.argv[4]
def fault(args,*a,**kw):
 result=original(args,*a,**kw)
 hit=(boundary=="prepared" and "pkg-update-continue-prepare" in args or
      boundary=="postinstall" and args[0]=="/usr/sbin/pkg" and "add" in args)
 if hit and result.returncode==0:
  print("P0_COORDINATOR_ABRUPT_EXIT="+boundary,flush=True)
  os._exit(91 if boundary=="prepared" else 92)
 return result
m.native_command=fault
m.continue_postinstall(Path(sys.argv[2]),sys.argv[3])
raise SystemExit(3)
'''
    return run([str(stage / "python_runtime.sh"), "-c", script,
                str(stage), str(fixed), record_sha, boundary], timeout=420)


def main():
    gate()
    protected = module("stage5-native-protected-update.py", "p0_protected")
    bridge = module("test-own70-native-package-handoff.py", "p0_model")
    wan = module("p5b2b-native-witness.py", "p0_wan")
    g03 = module("stage2-opnsense-g03-first-install.py", "p0_g03")
    builder = module("native-opnsense-package.py", "p0_candidate_builder")
    builder.gate()
    built = builder.build()
    candidate = ROOT / built["output"]
    need(digest(candidate) == built["real_native_pkg"]["sha256"],
         "NATIVE_RECOVERY_CODE_PACKAGE_MISMATCH")
    print("P0_RECOVERY_CODE_PKG_SHA256=" + digest(candidate), flush=True)
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
    original_raw = RECORD.read_bytes()
    original_record_sha = hashlib.sha256(original_raw).hexdigest()
    original_stage = Path(pkg_record["stage"])
    shared_before = JOURNAL.read_bytes()
    installed_sources = {path: digest(path) for path in (
        SERVICE, BACKEND / "global_exclusions.py",
        BACKEND / "auto_detect_origin_map.py", BACKEND / "auto_detect_owner.py")}
    STAGE.mkdir(mode=0o700)
    STAGE.chmod(0o700)
    bootstrap_key = "usr/local/opnsense/scripts/OPNsense/Zapret/protected_pkg_update.py"
    candidate_members = run(["/usr/bin/tar", "-tf", str(candidate)], timeout=40)
    need(candidate_members.returncode == 0, "RECOVERY_CODE_PACKAGE_INDEX_MISSING")
    bootstrap_member = bridge.qualified_archive_member(candidate_members.stdout.splitlines(), bootstrap_key)
    payload = run(["/usr/bin/tar", "-xOf", str(candidate), bootstrap_member], binary=True, timeout=40)
    need(payload.returncode == 0 and payload.stdout ==
         (ROOT / "src/opnsense/scripts/OPNsense/Zapret/protected_pkg_update.py").read_bytes(),
         "RECOVERY_BOOTSTRAP_NOT_EXACT_PACKAGE_SOURCE")
    bootstrap = STAGE / "bootstrap.py"
    with bootstrap.open("xb") as output:
        output.write(payload.stdout)
        output.flush()
        os.fsync(output.fileno())
    bootstrap.chmod(0o600)
    spec = importlib.util.spec_from_file_location("p0_packaged_bootstrap", bootstrap)
    packaged = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packaged)
    staged = packaged.stage_recovery_code(candidate, digest(candidate))
    # The complete code tree, including the coordinator and original FD9
    # service, is read byte-for-byte from ONE genuine current native .pkg.
    # First stop the real coordinator without finally after atomic handoff.
    first = crash_coordinator(staged, fixed, original_record_sha, "prepared")
    record_prepared = json.loads(RECORD.read_bytes())
    prepared_raw = RECORD.read_bytes()
    held = (first.returncode == 91 and
            "P0_COORDINATOR_ABRUPT_EXIT=prepared" in first.stdout and
            record_prepared.get("phase") == "prepared" and
            record_prepared.get("to_version") == FIXED[0] and
            record_prepared.get("sha256") == FIXED[1] and
            record_prepared.get("was_running") is True and
            record_prepared.get("continuation", {}).get("record", "").encode() == original_raw and
            record_prepared.get("continuation", {}).get("sha256") == original_record_sha and
            JOURNAL.read_bytes() == shared_before and
            all(digest(path) == before for path, before in installed_sources.items()) and
            installed() == BROKEN[0] and status() == 1 and MARKER.is_file() and
            digest(original_stage) == BROKEN[1] and digest(CONFIG) == config_sha)
    print("P0_NATIVE_CONTINUATION_PREPARED_CRASH=" +
          json.dumps({"verified": held, "rc": first.returncode,
                      "old_code_unchanged": all(digest(p) == h for p, h in installed_sources.items()),
                      "old_record_exactly_retained": record_prepared.get("continuation", {}).get("record", "").encode() == original_raw}),
          flush=True)
    need(held, "ATOMIC_CONTINUATION_NOT_DURABLE")
    premature = run([str(SERVICE), "pkg-update-finish", FIXED[1], FIXED[0]], timeout=60)
    need(premature.returncode == 69 and RECORD.read_bytes() == prepared_raw and
         status() == 1 and digest(CONFIG) == config_sha,
         "CONTINUATION_PREMATURE_FINISH_ALLOWED")
    # Resume that exact protected operation, execute real native pkg once,
    # then abruptly lose its coordinator after original POST_INSTALL attests.
    second = crash_coordinator(staged, fixed, original_record_sha, "postinstall")
    attested = json.loads(RECORD.read_bytes()) if RECORD.is_file() else {}
    survived = (second.returncode == 92 and installed() == FIXED[0] and
                attested.get("phase") == "postinstall-attested" and
                attested.get("continuation", {}).get("record", "").encode() == original_raw and
                status() == 1 and MARKER.is_file() and
                JOURNAL.read_bytes() == shared_before and
                digest(CONFIG) == config_sha and digest(engine) == engine_sha and
                digest(original_stage) == BROKEN[1])
    print("P0_NATIVE_CONTINUATION_POSTINSTALL_CRASH=" +
          json.dumps({"verified": survived, "rc": second.returncode,
                      "installed111_stopped": installed() == FIXED[0] and status() == 1,
                      "old_record_retained": attested.get("continuation", {}).get("record", "").encode() == original_raw}),
          flush=True)
    need(survived, "CONTINUATION_POSTINSTALL_NOT_DURABLE")
    # Original package-owned 111 finish, with CLEAN environment, must now
    # launch the first corrected engine. No 109 engine/3-file graft exists.
    upgrade = run([str(SERVICE.parent / "python_runtime.sh"), str(bootstrap),
                   "bootstrap-continuation", str(candidate), digest(candidate),
                   str(fixed), original_record_sha], timeout=480)
    updated_state = state()
    id_ = updated_state.get("detail", {}).get("id", "")
    schema3, profiles = (0, [])
    if status() == 0 and re.fullmatch(r"[a-f0-9]{32}", id_):
        schema3, profiles = protected.original_auto_generation(id_, True)
    accepted = (upgrade.returncode == 0 and
                "pkg-recovery=verified-installed-and-restored" in upgrade.stdout and
                installed() == FIXED[0] and status() == 0 and schema3 == 3
                and len(profiles) >= 1 and updated_state.get("phase") == "committed"
                and not RECORD.exists() and not MARKER.exists() and
                digest(CONFIG) == config_sha and digest(engine) == engine_sha)
    print("P0_OWNER_NATIVE_111_RECONCILED=" +
          json.dumps({"verified": accepted, "rc": upgrade.returncode,
                      "pkg": installed(), "running": status() == 0,
                      "schema": schema3, "learning": len(profiles),
                      "config_unchanged": digest(CONFIG) == config_sha,
                      "package_code_stage_preserved": STAGE.is_dir(),
                      "original_archive_preserved": original_stage.is_file() and digest(original_stage) == BROKEN[1]}), flush=True)
    need(accepted, "111_NATIVE_PROTECTED_OWNER_RECONCILIATION_REFUSED")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, KeyError, TypeError, ValueError,
            subprocess.SubprocessError) as error:
        # No raw user data, Config XML, transient archive paths or stderr.
        reason = str(error)
        if re.fullmatch(r"[A-Z0-9_]{1,96}", reason) is None:
            reason = type(error).__name__
        print("P0_NATIVE_GUARDED_RESCUE=REFUSED:" + reason, file=sys.stderr)
        sys.exit(1)
