#!/usr/bin/env python3
"""TZ6v5 S04c — physical five-case installed inventory on disposable OPNsense.
Fixtures mutate only test VMs BEFORE observation. The inventory never mutates.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
INSTALLED = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend/component_inventory_opnsense.py")
SOURCE = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret/backend/component_inventory_opnsense.py"
ROOTS = tuple(map(Path, ("/var/db/zapret2", "/var/db/pkg",
                         "/usr/local/etc/zapret2/runtime-v2", "/var/db/zapret2-restyle")))
LIMIT = 8000


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def run(argv, timeout=50):
    try:
        return subprocess.run(argv, capture_output=True, text=True, check=False,
                              timeout=timeout,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except (OSError, subprocess.SubprocessError):
        raise Refusal("S04C_NATIVE_COMMAND_UNAVAILABLE") from None


def required(argv, reason, timeout=50):
    p = run(argv, timeout)
    need(p.returncode == 0, reason + "_RC_" + str(p.returncode))
    return p.stdout


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_record(path):
    s = path.lstat()
    row = [stat.S_IFMT(s.st_mode), s.st_dev, s.st_ino, s.st_uid, s.st_gid,
           stat.S_IMODE(s.st_mode), s.st_nlink, s.st_size, s.st_mtime_ns]
    if stat.S_ISLNK(s.st_mode):
        row.append(os.readlink(path))
    elif stat.S_ISREG(s.st_mode):
        need(s.st_size <= 134217728, "S04C_FILE_TOO_LARGE")
        hash_ = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hash_.update(chunk)
        row.append(hash_.hexdigest())
    return row


def snapshot_tree():
    tree = {}
    def add(p):
        need(len(tree) < LIMIT, "S04C_TREE_LIMIT")
        tree[str(p)] = file_record(p)
    for root in ROOTS:
        if not root.exists() and not root.is_symlink():
            tree[str(root)] = "ABSENT"
            continue
        add(root)
        need(not root.is_symlink(), "S04C_UNTRUSTED_TREE_ROOT")
        for folder, dirs, files in os.walk(root, followlinks=False):
            dirs.sort()
            files.sort()
            for child in (*dirs, *files):
                add(Path(folder) / child)
    for p in sorted(Path("/var/run").glob("*")):
        if p.name.startswith(("zapret2", "dvtws2")):
            add(p)
    return tree


def snapshot_kernel():
    commands = {
        "rules": ["/sbin/ipfw", "-q", "list"],
        "tables": ["/sbin/ipfw", "table", "all", "list"],
        "ipfw_module": ["/sbin/kldstat", "-q", "-m", "ipfw"],
        "ipdivert_module": ["/sbin/kldstat", "-q", "-m", "ipdivert"],
    }
    states = {}
    for key, argv in commands.items():
        result = run(argv, timeout=15)
        need(len(result.stdout) + len(result.stderr) < 2097152,
             "S04C_KERNEL_OUTPUT_UNBOUNDED")
        states[key] = [result.returncode, hashlib.sha256(
            (result.stdout + "\0" + result.stderr).encode()).hexdigest()]
    return states


def snapshot_process():
    proc = run(["/bin/ps", "axww", "-o", "pid=", "-o", "command="], timeout=15)
    need(proc.returncode == 0 and len(proc.stdout) < 1048576,
         "S04C_PROCESS_CENSUS_FAILED")
    # Side-effect comparison ONLY, never a substitute for original attester.
    rows = [s for s in proc.stdout.splitlines()
            if str(ENGINE) in s or "/Zapret/supervisor_loop.sh" in s]
    return sorted(rows)


def snapshot():
    return {
        "config": file_record(CONFIG),
        "engine": file_record(ENGINE) if ENGINE.exists() else "ABSENT",
        "tree": snapshot_tree(),
        "kernel": snapshot_kernel(),
        "process": snapshot_process(),
    }


def witness(label, expected, *, preinstall=False):
    before = snapshot()
    # In a genuinely empty installation there can be no installed CLI.
    # Execute the exact checked-out source adapter against physical native
    # pkg/Config/engine/journal; after installation prove byte equivalence.
    reader = SOURCE if preinstall else INSTALLED
    need(reader.is_file() and not reader.is_symlink(), "S04C_READER_SOURCE_MISSING")
    if preinstall:
        need(not INSTALLED.exists(), "S04C_FRESH_READER_WAS_INSTALLED")
    p = run(["/usr/local/bin/python3", str(reader)], timeout=90)
    after = snapshot()
    if before != after:
        # Bounded RED diagnosis by resource class, never print Config, argv,
        # a PID, IPFW rule text, an address or any filesystem path.
        changed = []
        for section in ("config", "engine", "process"):
            if before[section] != after[section]:
                changed.append(section)
        for section in ("rules", "tables", "ipfw_module", "ipdivert_module"):
            if before["kernel"][section] != after["kernel"][section]:
                changed.append("kernel_" + section)
        old_tree, new_tree = before["tree"], after["tree"]
        if old_tree != new_tree:
            for category, prefix in (
                ("shared", "/var/db/zapret2/"),
                ("pkgdb", "/var/db/pkg/"),
                ("active", "/usr/local/etc/zapret2/runtime-v2/"),
                ("setup", "/var/db/zapret2-restyle/"),
                ("pid", "/var/run/"),
            ):
                keys = set(old_tree) | set(new_tree)
                altered = [k for k in keys if k.startswith(prefix) and
                           old_tree.get(k) != new_tree.get(k)]
                if altered:
                    added = sum(k not in old_tree for k in altered)
                    removed = sum(k not in new_tree for k in altered)
                    changed.append("tree_" + category + "_" + str(len(altered))
                                   + "_new" + str(added) + "_del" + str(removed))
                    if category == "pkgdb":
                        # Only fixed generic SQLite file classes/field names.
                        # No pathname, database content or absolute argv.
                        for key in sorted(altered)[:2]:
                            filename = Path(key).name
                            kind = ("shm" if filename.endswith("-shm") else
                                    "wal" if filename.endswith("-wal") else
                                    "sqlite" if filename.endswith(".sqlite") else
                                    "other")
                            before_row, after_row = old_tree.get(key), new_tree.get(key)
                            fields = []
                            if isinstance(before_row, list) and isinstance(after_row, list):
                                for index, field in ((2, "inode"), (7, "size"),
                                                     (8, "mtime"), (9, "content")):
                                    if len(before_row) > index and len(after_row) > index and before_row[index] != after_row[index]:
                                        fields.append(field)
                            else:
                                fields.append("type")
                            changed.append("pkgdb_" + kind + "_" +
                                           ("-".join(fields) if fields else "unspecified"))
            if not any(s.startswith("tree_") for s in changed):
                changed.append("tree_root")
        raise Refusal("S04C_INVENTORY_STATE_DRIFT_" + label + "__" +
                      "_".join(changed[:12]))
    need(p.returncode == 0, "S04C_INVENTORY_REFUSED_" + label)
    try:
        record = json.loads(p.stdout)
    except (ValueError, TypeError):
        raise Refusal("S04C_INVENTORY_NOT_JSON_" + label) from None
    need(type(record) is dict and type(record.get("components")) is dict,
         "S04C_INVENTORY_WRONG_SCHEMA_" + label)
    for key, value in expected.items():
        actual = record["classification"] if key == "classification" else record["components"].get(key)
        need(actual == value, "S04C_UNEXPECTED_" + label + "_" + key + "_" + str(actual))
    need(record["authorization"] == "NONE" and
         record["physical_transition_allowed"] is False and
         record["original_fd9_attestation_required"] is True,
         "S04C_INVENTORY_PHYSICAL_AUTHORITY")
    need(set(record) == {"schema", "components", "classification", "authorization",
                         "physical_transition_allowed", "original_fd9_attestation_required"},
         "S04C_INVENTORY_EXTRA_FIELDS")
    need(not any(secret in p.stdout for secret in ("/conf/", "argv", "pid", "secret")),
         "S04C_INVENTORY_LEAK")
    return {"case": label, "classification": record["classification"],
            "components": record["components"], "unchanged": True}


def guest_gate(mode):
    env = {"GITHUB_ACTIONS": "true",
           "ZAPRET2_NATIVE_BUILD_CI": "1",
           "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK": "1",
           "ZAPRET2_STAGE2_REAL_CLEAN_INSTALL": "1",
           "ZAPRET2_S04C_DISPOSABLE_NATIVE": "1"}
    need(mode in ("cold", "hot") and all(os.environ.get(k) == v for k, v in env.items()),
         "S04C_DISPOSABLE_ONLY")
    need(os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
         CONFIG.is_file() and not CONFIG.is_symlink() and
         Path("/usr/local/opnsense").is_dir() and
         re.fullmatch(r"[a-f0-9]{40}", os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")),
         "S04C_NATIVE_IDENTITY_REFUSED")


def install(clean):
    clean.preflight()
    product = clean.native.build()
    need(product["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY",
         "S04C_ORIGINAL_NATIVE_BUILDER_REFUSED")
    archive = clean.native.ROOT / product["output"]
    need(archive.is_file() and not archive.is_symlink(), "S04C_PACKAGE_MISSING")
    clean.pkg_add(archive)
    manifest, _ = clean.installed_pkg_manifest(archive)
    clean.verify_installed_files(archive, manifest)
    need(INSTALLED.is_file() and not INSTALLED.is_symlink(),
         "S04C_INSTALLED_ADAPTER_MISSING")
    need(INSTALLED.read_bytes() == SOURCE.read_bytes(),
         "S04C_INSTALLED_READER_SOURCE_BYTES_DIFFER")


def upstream():
    g03 = load("s04c_g03", "stage2-opnsense-g03-first-install.py")
    result = g03.dispatch_and_poll()
    need(result["installed"] == "1" and result["service"] == "stopped" and
         result["version"] == "v1.0.7" and ENGINE.is_file() and
         not ENGINE.is_symlink(), "S04C_REAL_UPSTREAM_NOT_READY")


def fixture_php(code):
    p = run(["/usr/local/bin/php", "-r", code], timeout=45)
    need(p.returncode == 0, "S04C_NATIVE_CONFIG_FIXTURE_REFUSED")


def drop_config():
    fixture_php(r'''require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance(); $c->lock();
try { $r = $c->object();
  if (!isset($r->OPNsense->Zapret)) { throw new \RuntimeException("no subtree"); }
  unset($r->OPNsense->Zapret);
  $c->save(["description"=>"S04c disposable Config-absent fixture"]);
} finally { $c->unlock(); }''')
    need(ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret") is None,
         "S04C_CONFIG_NOT_ABSENT")


def corrupt_config():
    fixture_php(r'''require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance(); $c->lock();
try { $r = $c->object();
  if ((string)$r->OPNsense->Zapret->general->enabled !== "1")
    { throw new \RuntimeException("not running Config"); }
  $r->OPNsense->Zapret->general->enabled = "malformed-s04c-test";
  $c->save(["description"=>"S04c disposable invalid-toggle fixture"]);
} finally { $c->unlock(); }''')
    need(ET.fromstring(CONFIG.read_bytes()).findtext(
         "./OPNsense/Zapret/general/enabled") == "malformed-s04c-test",
         "S04C_CONFIG_NOT_INVALID")


def foreign_rule():
    prior = required(["/sbin/ipfw", "-q", "list"], "S04C_PRE_FOREIGN_IPFW")
    need(not any(s.lstrip().startswith("19098 ") for s in prior.splitlines()),
         "S04C_FOREIGN_SLOT_BUSY")
    # Count = nonblocking. This is a test-owned foreign rule on disposable lo0.
    required(["/sbin/ipfw", "add", "19098", "count", "ip", "from", "any",
              "to", "any", "out", "via", "lo0"], "S04C_FOREIGN_FIXTURE_FAILED")
    after = required(["/sbin/ipfw", "-q", "list"], "S04C_POST_FOREIGN_IPFW")
    need(sum(s.lstrip().startswith("19098 ") for s in after.splitlines()) == 1,
         "S04C_FOREIGN_RULE_NOT_PRESENT")


def cold():
    clean = load("s04c_clean", "stage2-opnsense-real-native-clean-install.py")
    clean.preflight()
    need(ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret") is None and
         not ENGINE.exists(), "S04C_NOT_CLEAN_INITIAL_GUEST")
    rows = [witness("nothing", {"plugin": "absent", "engine": "absent",
             "config": "absent", "manifest": "missing",
             "classification": "PLUGIN_NOT_INSTALLED"}, preinstall=True)]
    install(clean)
    need(not ENGINE.exists(), "S04C_PLUGIN_ONLY_HAS_ENGINE")
    rows.append(witness("plugin-no-engine", {"plugin": "installed",
                "engine": "absent", "config": "initialized",
                "manifest": "missing", "classification": "ENGINE_NOT_INSTALLED"}))
    upstream()
    drop_config()
    rows.append(witness("engine-no-config", {"plugin": "installed",
                "engine": "valid", "config": "absent", "manifest": "missing",
                "classification": "CONFIG_UNINITIALIZED"}))
    return rows


def hot():
    clean = load("s04c_hot_clean", "stage2-opnsense-real-native-clean-install.py")
    install(clean)
    upstream()
    g04 = load("s04c_g04", "stage2-opnsense-g04-native-runtime.py")
    node = g04.model()
    traffic = node.findtext("strategy/trafficargs") or ""
    youtube = node.findtext("hostlist/youtubedomains") or ""
    need(traffic.count("--new") == 1 and len(youtube.splitlines()) == 10,
         "S04C_INITIAL_G04_STRATEGY_CHANGED")
    g04.authenticated_first_apply(traffic, youtube)
    rows = [witness("healthy-running-control", {
        "plugin": "installed", "engine": "valid", "config": "initialized",
        "manifest": "valid", "runtime": "RUNNING",
        "classification": "RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION"})]
    corrupt_config()
    rows.append(witness("running-invalid-config", {
        "plugin": "installed", "engine": "valid", "config": "invalid",
        "manifest": "valid", "runtime": "RUNNING",
        "classification": "CONFIG_INVALID"}))
    foreign_rule()
    rows.append(witness("foreign-ipfw", {
        "plugin": "installed", "engine": "valid", "config": "invalid",
        "manifest": "valid", "runtime": "FOREIGN_OR_UNVERIFIED",
        "classification": "FOREIGN_OWNER"}))
    # Never Stop/recover under damaged Config + foreign owner. VM is discarded.
    return rows


def main(argv):
    if argv == ["--self-test"]:
        tree = ast.parse(Path(__file__).read_text())
        unsafe = {"kill", "rmtree", "unlink", "remove", "replace", "rename"}
        need(not any(isinstance(node, ast.Call) and
                     isinstance(node.func, ast.Attribute) and
                     node.func.attr in unsafe
                     for node in ast.walk(tree)),
             "S04C_TEST_RUNNER_UNSAFE")
        print("PASS_S04C_SOURCE_GATE")
        return 0
    if len(argv) != 1 or argv[0] not in ("cold", "hot"):
        return 64
    try:
        guest_gate(argv[0])
        rows = cold() if argv[0] == "cold" else hot()
        print("S04C_NATIVE=" + json.dumps({"mode": argv[0], "cases": rows,
              "all_inventory_reads_no_write": True,
              "owner_hardware_touched": False,
              "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"]},
              sort_keys=True, separators=(",", ":")))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError) as error:
        print("S04C_NATIVE=REFUSED:" + str(error).split(":", 1)[0][:120],
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
