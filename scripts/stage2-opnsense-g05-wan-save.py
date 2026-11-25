#!/usr/bin/env python3
"""G05 LC-06: authenticated WAN-only Apply in one genuine disposable OPNsense VM.

No simulated configd, no runtime install requirement for the first WAN save.
Uses same physical qualified package; never targets the owner's firewall.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONF = Path("/conf/config.xml")
PKGNAME = "os-zapret2-restyle"


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(path, tag):
    spec = importlib.util.spec_from_file_location(tag, ROOT / "scripts" / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(argv, timeout=180):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=timeout, check=False)


def node():
    root = ET.fromstring(CONF.read_bytes())
    n = root.find("./OPNsense/Zapret")
    need(n is not None, "G05_NATIVE_ZAPRET_SUBTREE_ABSENT")
    return n


def exact_saved_wan(value):
    n = node()
    need(n.findtext("general/waninterface", "") == value,
         "G05_NATIVE_CONFIG_WAN_NOT_PERSISTED")
    need(n.findtext("general/enabled", "0") == "0",
         "G05_NATIVE_WAN_CHANGE_UNEXPECTEDLY_ENABLED_SERVICE")


def selected(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        selected_items = [key for key, option in value.items()
                          if isinstance(option, dict) and
                          str(option.get("selected")) in ("1", "True")]
        return selected_items[0] if len(selected_items) == 1 else None
    return None


def no_runtime_mutation(before_engine, before_ipfw, before_config=None):
    if before_config is not None:
        need(CONF.read_bytes() == before_config,
             "G05_FAILED_WAN_APPLY_MUTATED_CONFIG")
    engine = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    need(engine.exists() == before_engine,
         "G05_WAN_ONLY_INSTALLED_OR_DELETED_UPSTREAM_ENGINE")
    for name in ("dvtws2.pid", "zapret2-supervisor-monitor.pid",
                 "zapret2-supervisor-daemon.pid"):
        need(not (Path("/var/run") / name).exists(),
             "G05_WAN_ONLY_CREATED_ENGINE_PROCESS")
    ipfw = run(["/sbin/ipfw", "-q", "list"], timeout=10)
    # Kernel may be unloaded in a genuinely fresh guest. The exact raw
    # before/after rc/output pair must remain unchanged in WAN-only Apply.
    now = (ipfw.returncode, ipfw.stdout, ipfw.stderr)
    need(now == before_ipfw, "G05_WAN_ONLY_MODIFIED_IPFW_OR_LOADED_KERNEL")


# S10/LC-06 is NOT an engine-qualified START/SAVE_ONLY planning route.
# First Save with no upstream may only reuse the already deployed WAN-only
# Config writer under the existing original FD9. Prove the original immutable
# root, journal and ordinary process owner were never created, without
# inventing an alternate transaction or calling native_plan_original_prepared_fd9.
_S10_NO_ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
_S10_ORIGINAL_WAL = Path("/var/db/zapret2/shared-apply/operation.json")
_S10_ORIGINAL_WORK = Path("/var/db/zapret2/shared-work")
# Exact original zapret_service.sh ACTIVE_DIR / voice_live_inspect.COMMON_ACTIVE.
_S10_ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
_S10_MANIFEST_NAMES = ("manifest.json", "dvtws.args", "voice-plan.json")
_S10_FOUND_FILES = (
    Path("/var/db/zapret2/auto-detect-owned/youtube.txt"),
    Path("/var/db/zapret2/auto-detect-owned/user.txt"),
    Path("/usr/local/etc/zapret2/ipset/auto-domains.txt"),
)


def _s10_native_cold_no_engine_witness():
    """Read-only original S10 absence and P1 ownership witness; no new writer.

    Refuses an already staged/committed previous owner or unknown runtime.
    Comparing before/after permits only the native WAN leaf/Config revision
    change, not an ordinary immutable-root build or Found hot-write.
    """
    for path in (_S10_NO_ENGINE, _S10_ORIGINAL_WAL,
                 *(_S10_ACTIVE / name for name in _S10_MANIFEST_NAMES)):
        need(not path.exists() and not path.is_symlink(),
             "S10_COLD_WAN_ORIGINAL_OWNER_OR_ENGINE_PRESENT")
    if _S10_ACTIVE.exists() or _S10_ACTIVE.is_symlink():
        need(_S10_ACTIVE.is_dir() and not _S10_ACTIVE.is_symlink() and
             not any(_S10_ACTIVE.iterdir()),
             "S10_COLD_WAN_ACTIVE_RUNTIME_RESIDUE")
    if _S10_ORIGINAL_WORK.exists() or _S10_ORIGINAL_WORK.is_symlink():
        need(_S10_ORIGINAL_WORK.is_dir() and
             not _S10_ORIGINAL_WORK.is_symlink() and
             not any(_S10_ORIGINAL_WORK.iterdir()),
             "S10_COLD_WAN_STAGED_GENERATION_PRESENT")
    native = run([
        "/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh", "status"
    ], timeout=30)
    need(native.returncode == 1 and
         native.stdout.strip() == "zapret is not running",
         "S10_COLD_WAN_UNKNOWN_OR_INCOMPLETE_OWNER")
    preserved = []
    for path in _S10_FOUND_FILES:
        need(not path.is_symlink(), "S10_COLD_WAN_FOUND_SYMLINK")
        if path.exists():
            need(path.is_file(), "S10_COLD_WAN_FOUND_NONREGULAR")
            preserved.append(path.read_bytes())
        else:
            preserved.append(None)
    return tuple(preserved)


def _s10_native_model_without_wan(web):
    """Original authenticated Settings getNodes() model, excluding ONLY WAN.

    Config::save may materialize native default XML nodes or format the
    subtree without an effective user-setting change. Comparing raw XML
    bytes, or even its root child count, is not an admissible proof that
    another setting changed. Compare *all* original typed GUI model fields,
    preserving list text and profile order, except the one approved WAN leaf.
    """
    reply = web.api("GET", "/api/zapret/settings/get")
    model = reply.get("zapret") if isinstance(reply, dict) else None
    need(isinstance(model, dict) and
         isinstance(model.get("general"), dict) and
         isinstance(model.get("hostlist"), dict) and
         isinstance(model.get("strategy"), dict),
         "S10_COLD_WAN_NATIVE_MODEL_UNAVAILABLE")
    copy_model = copy.deepcopy(model)
    need("waninterface" in copy_model["general"],
         "S10_COLD_WAN_MODEL_FIELD_MISSING")
    del copy_model["general"]["waninterface"]
    return copy_model


def _s10_no_other_model_change(web, before, expected_wan):
    """Read real native Config WAN and compare all other typed user fields."""
    need(node().findtext("general/waninterface", "") == expected_wan,
         "S10_COLD_WAN_NOT_SAVED")
    current = _s10_native_model_without_wan(web)
    if current != before:
        # No private list contents or tokens ever appear in native CI logs.
        names = sorted(set(current).union(before))
        changed = [name for name in names if current.get(name) != before.get(name)]
        print("S10_G05_TYPED_MODEL_CHANGED_SECTIONS=" +
              json.dumps(changed[:8]), file=sys.stderr)
        raise Refusal("S10_COLD_WAN_MODIFIED_UNRELATED_PLUGIN_FIELD")


def request(web, wan, baseline):
    return web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", baseline),
        ("zapret[general][waninterface]", wan),
    ])


def gui_wan(web):
    model = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(isinstance(model, dict), "G05_WAN_GUI_MODEL_NOT_READABLE")
    general = model.get("general")
    hostlist = model.get("hostlist")
    need(isinstance(general, dict) and isinstance(hostlist, dict),
         "G05_WAN_GUI_MODEL_INCOMPLETE")
    baseline = hostlist.get("telegramips")
    need(isinstance(baseline, str), "G05_WAN_TELEGRAM_BASELINE_MISSING")
    return selected(general.get("waninterface")), baseline



def _wan_first_jobs():
    """Only real Lab jobs/sessions count; launcher lockfiles are not jobs."""
    roots = (Path("/var/run/zapret2-restyle/strategy-lab/jobs"),
             Path("/var/run/zapret2-restyle/strategy-lab/circular/sessions"))
    return tuple(sorted(str(p) for root in roots if root.is_dir()
                        for p in root.glob("job.*")))


def _wan_first_unchanged(config_bytes, ipfw_baseline, jobs, label):
    no_runtime_mutation(False, ipfw_baseline, config_bytes)
    need(_wan_first_jobs() == jobs,
         "G05_WAN_FIRST_CREATED_LAB_JOB_" + label)


def _wan_first_command(argv, code, fragment, name):
    status = run(argv, timeout=50)
    # Direct shell invocations return their own exact rc. Configd
    # script_output may serialize its refusal with a different transport rc:
    # require the specific refusal payload, not a guessed wrapper rc.
    reply = (status.stdout + status.stderr).strip()
    need((code is None or status.returncode == code) and fragment in reply,
         "G05_WAN_FIRST_" + name + "_WRONG_REFUSAL" +
         ":rc=" + str(status.returncode) +
         ":reply=" + repr(reply[:180]))
    return status


def _wan_first_configd(argv, reason, message, label):
    # In OPNsense configd, errors:no is the standard contract for preserving
    # a script_output payload from a nonzero CLI command. Neither rc=0 nor
    # an HTTP 200 means success: the typed JSON status remains "error".
    result = run(argv, timeout=50)
    need(result.returncode == 0, "G05_CONFIGD_" + label + "_TRANSPORT_FAILED")
    reply = json.loads(result.stdout)
    need(isinstance(reply, dict) and reply.get("status") == "error" and
         reply.get("reason") == reason and reply.get("message") == message,
         "G05_CONFIGD_" + label + "_TYPED_REFUSAL_MISSING")
    return reply


def _wan_first_lab_form(mode, language):
    # Deliberately invalid target: WAN / engine must win over target grammar.
    return [("target", "invalid_target"), ("mode", mode),
            ("language", language), ("enable_quic", "0"),
            ("ipv6_enabled", "0")]


def _wan_first_cold_matrix(web, baseline, ipfw_baseline):
    """Actual cookie/CSRF and installed configd/Voice/Lab before first WAN Save."""
    saved = CONF.read_bytes()
    jobs = _wan_first_jobs()
    script = "/usr/local/opnsense/scripts/OPNsense/Zapret/"
    _wan_first_command([script + "wan_preflight.sh", "require"],
                       0, "wan-required", "SAVED_PROBE")
    _wan_first_command(["/usr/local/sbin/configctl", "zapret", "wan_preflight"],
                       0, "wan-required", "CONFIGD_PROBE")
    _wan_first_command([script + "zapret_service.sh", "start"],
                       64, "WAN_REQUIRED", "DIRECT_START")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "START")

    missing = web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", baseline),
        ("zapret[general][enabled]", "1"),
        ("zapret[strategy][trafficargs]", "--not-a-valid-strategy")])
    need(missing.get("result") == "failed" and
         missing.get("applied") is not True and
         missing.get("requires_review") is not True and
         "Select a WAN interface" in str(missing.get("message", "")),
         "G05_WAN_FIRST_GUI_STRATEGIES_MASKED_MISSING_WAN")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "STRATEGIES")

    voice = web.api("GET", "/api/zapret/voice/load")
    model, snapshot = voice.get("zapret"), voice.get("snapshot")
    need(isinstance(model, dict) and isinstance(snapshot, str) and
         len(snapshot) == 64 and
         all(c in "0123456789abcdef" for c in snapshot),
         "G05_WAN_FIRST_NATIVE_VOICE_LOAD_MISSING")
    form = [("zapret[sync][snapshot]", snapshot)]
    for name in ("telegram", "discord", "x", "sip", "custom"):
        item = model["voice"][name]
        need(str(item["enabled"]) == "0",
             "G05_WAN_FIRST_NOT_COLD_VOICE_OFF")
        form.extend([
            ("zapret[voice][" + name + "][enabled]",
             "1" if name == "telegram" else "0"),
            ("zapret[voice][" + name + "][args]", str(item["args"])),
            ("zapret[hostlist][" + name + "ips]",
             str(model["hostlist"][name + "ips"]))])
    voice_rejected = web.api("POST", "/api/zapret/voice/apply", form)
    need(voice_rejected.get("result") == "failed" and
         voice_rejected.get("requires_review") is not True and
         "Select a WAN interface" in str(
             voice_rejected.get("validations", {}).get(
                 "zapret.voice.waninterface", "")),
         "G05_WAN_FIRST_GUI_VOICE_MASKED_MISSING_WAN")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "VOICE")

    for mode, language, expected in (
        ("standard", "ru", "Укажите WAN интерфейс"),
        ("extended", "en", "Select a WAN interface"),
    ):
        refused = web.api("POST", "/api/zapret/strategy_lab/start",
                          _wan_first_lab_form(mode, language))
        need(refused.get("status") == "error" and
             refused.get("reason") == "wan-required" and
             refused.get("message") == expected,
             "G05_WAN_FIRST_GUI_LAB_" + mode.upper())
        _wan_first_unchanged(saved, ipfw_baseline, jobs, "LAB_" + mode.upper())

    # Original launchers and configd, not a synthetic WAN resolver.
    _wan_first_configd([
        "/usr/local/sbin/configctl", "zapret", "strategy_lab_start",
        "invalid_target", "standard", "ru", "0", "-", "-", "-", "0"],
        "wan-required", "Укажите WAN интерфейс", "LAB_WAN")
    _wan_first_configd([
        "/usr/local/sbin/configctl", "zapret", "strategy_lab_circular_start",
        "job.G05WithoutWAN"],
        "wan-required", "Select a WAN interface", "CIRCULAR_WAN")
    _wan_first_command([
        script + "strategy_lab_circular_launcher.sh",
        "start", "job.G05WithoutWAN"],
        64, "Select a WAN interface", "CIRCULAR_LAB")
    _wan_first_command([script + "zapret_service.sh", "telegram-voice-enable"],
                       64, "WAN_REQUIRED", "DIRECT_VOICE_ON")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "INTERNAL")
    return True


def _wan_first_saved_no_engine_matrix(web, ipfw_baseline):
    """WAN now saved; engine is the second prerequisite, before Job/target."""
    saved = CONF.read_bytes()
    jobs = _wan_first_jobs()
    script = "/usr/local/opnsense/scripts/OPNsense/Zapret/"
    _wan_first_command([script + "wan_preflight.sh", "require"],
                       0, "wan-ready", "SAVED_WAN_READY")
    _wan_first_command([script + "zapret_service.sh", "start"],
                       1, "runtime is not installed", "ENGINE_SECOND")
    for mode, language, expected in (
        ("standard", "ru", "Служба zapret2 не установлена"),
        ("extended", "en", "The zapret2 service is not installed"),
    ):
        refused = web.api("POST", "/api/zapret/strategy_lab/start",
                          _wan_first_lab_form(mode, language))
        need(refused.get("status") == "error" and
             refused.get("reason") == "engine-not-installed" and
             refused.get("message") == expected,
             "G05_WAN_FIRST_NO_ENGINE_BEFORE_LAB_" + mode.upper())
    _wan_first_command([
        script + "strategy_lab_launcher.sh", "start", "invalid_target",
        "standard", "en", "0", "-", "-", "-", "0"],
        64, "The zapret2 service is not installed", "DIRECT_LAB_ENGINE")
    _wan_first_configd([
        "/usr/local/sbin/configctl", "zapret", "strategy_lab_start",
        "invalid_target", "standard", "en", "0", "-", "-", "-", "0"],
        "engine-not-installed", "The zapret2 service is not installed",
        "LAB_ENGINE")
    _wan_first_configd([
        "/usr/local/sbin/configctl", "zapret", "strategy_lab_circular_start",
        "job.G05NoEngine"],
        "engine-not-installed", "The zapret2 service is not installed",
        "CIRCULAR_ENGINE")
    _wan_first_command([
        script + "strategy_lab_circular_launcher.sh",
        "start", "job.G05NoEngine"],
        64, "The zapret2 service is not installed", "CIRCULAR_NO_ENGINE")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "ENGINE_PRE_JOB")
    return True


def verify_s06_ordinary_remove_reinstall(web, package, archive_sha, ipfw_before):
    """One real no-engine guest; verify pkg delete is not a purge."""
    save = r"""require_once('script/load_phalcon.php');
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
  $m = new \OPNsense\Zapret\Zapret();
  $values = [
    'hostlist.userdomains' => "s06-manual-user.example.org\n",
    'hostlist.excludedomains' => "s06-excluded.example.org\n",
    'hostlist.excludeipset' => "198.51.100.0/24\n",
    'hostlist.telegramips' => "192.0.2.0/24\n",
    'voice.telegram.args' => "--filter-udp=443\n--filter-l7=stun\n"
  ];
  foreach ($values as $ref => $value) {
    if ($m->setNodeByReference($ref, $value) !== true) exit(71);
  }
  if (count($m->performValidation(false)) !== 0 ||
      !$m->serializeToConfig(false, true)) exit(72);
  $c->save(['description'=>'S06 disposable saved-user data before normal removal']);
} finally {
  $c->unlock();
}"""
    saved = run(["/usr/local/bin/php", "-r", save], timeout=45)
    need(saved.returncode == 0, "S06_USER_CONFIG_MODEL_SAVE_REFUSED")
    expected = ET.tostring(node(), encoding="utf-8")
    n = node()
    need(n.findtext("general/enabled", "0") == "0" and
         n.findtext("general/waninterface", "") == "wan" and
         (n.findtext("strategy/trafficargs") or "") == "" and
         (n.findtext("hostlist/youtubedomains") or "") == "" and
         n.findtext("hostlist/userdomains") == "s06-manual-user.example.org\n" and
         n.findtext("hostlist/excludedomains") == "s06-excluded.example.org\n" and
         n.findtext("hostlist/excludeipset") == "198.51.100.0/24\n" and
         n.findtext("hostlist/telegramips") == "192.0.2.0/24\n",
         "S06_SAVED_MODEL_USER_AND_EMPTY_FIELDS_NOT_ATTESTED")
    files = {
        Path("/var/db/zapret2/auto-detect-owned/youtube.txt"): b"s06-youtube-found.example.org\n",
        Path("/var/db/zapret2/auto-detect-owned/user.txt"): b"s06-user-found.example.org\n",
        Path("/usr/local/etc/zapret2/ipset/auto-domains.txt"): b"s06-shared-found.example.org\n",
    }
    for path, content in files.items():
        need(not path.exists() and not path.is_symlink(),
             "S06_NOT_A_CLEAN_FOUND_FILE_FIXTURE")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        need(path.parent.is_dir() and not path.parent.is_symlink(),
             "S06_FOUND_PARENT_UNSAFE")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    def assert_preserved(reason):
        need(ET.tostring(node(), encoding="utf-8") == expected,
             "S06_SAVED_CONFIG_CHANGED_" + reason)
        for path, content in files.items():
            need(path.is_file() and not path.is_symlink() and
                 path.read_bytes() == content,
                 "S06_FOUND_DATA_CHANGED_" + reason)
        no_runtime_mutation(False, ipfw_before)
    assert_preserved("BEFORE_DELETE")
    deleted = run(["/usr/sbin/pkg", "delete", "-y", PKGNAME], timeout=240)
    need(deleted.returncode == 0 and
         run(["/usr/sbin/pkg", "info", "-e", PKGNAME]).returncode == 1 and
         not Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").exists(),
         "S06_REAL_ORDINARY_UNINSTALL_NOT_CONFIRMED")
    assert_preserved("AFTER_DELETE")
    installed = run(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                     "add", "-f", str(package)], timeout=240)
    need(installed.returncode == 0 and
         "zapret-config=preserved" in installed.stdout and
         run(["/usr/sbin/pkg", "info", "-e", PKGNAME]).returncode == 0 and
         hashlib.sha256(package.read_bytes()).hexdigest() == archive_sha,
         "S06_REAL_IDENTICAL_ARCHIVE_REINSTALL_NOT_CONFIRMED")
    assert_preserved("AFTER_REINSTALL")
    page = web.request("GET", "/ui/zapret")
    need("frm_GeneralSettings" in page and gui_wan(web)[0] == "wan",
         "S06_REINSTALLED_SAVED_WAN_NOT_VISIBLE_IN_GUI")
    print("S06_G05_REAL_PKG_DELETE_REINSTALL_PRESERVES_USER_AND_FOUND=PASS", flush=True)
    return True



def verify_s07_installed_readonly_projection():
    """Qualify S07a on this already installed G05 guest without another VM."""
    sys.dont_write_bytecode = True  # No __pycache__ under installed backend.
    s04 = load("tz6v5-s04c-opnsense-native-inventory.py", "g05_s07_original_s04")
    backend = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
    source = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
    names = ("neutral_config_model.py", "config_projection_opnsense.py",
             "registry.sh", "component_inventory_opnsense.py")
    for name in names:
        installed = backend / name
        upstream = source / name
        need(installed.is_file() and not installed.is_symlink() and
             upstream.is_file() and installed.read_bytes() == upstream.read_bytes(),
             "S07_INSTALLED_SOURCE_NOT_THE_TESTED_PACKAGE")
    # Existing accepted S04 read-only physical witness includes saved Config
    # bytes/inode/mode/mtime, pkgdb, FD9/journal/release, PID, IPFW and engine.
    before = s04.snapshot()
    module_bytes = {name: s04.file_record(backend / name) for name in names}
    sys.path.insert(0, str(backend))
    try:
        import config_projection_opnsense as opnsense_projector
        model = opnsense_projector.read_saved()
    finally:
        sys.path.remove(str(backend))
    need(model.schema == 1 and model.authorization == "NONE" and
         model.physical_transition_allowed is False and
         model.enabled is False and model.saved_wan == "wan" and
         model.wan_state == "NEEDS_NATIVE_RESOLUTION" and
         len(model.registered_sources) == 8,
         "S07_SAVED_NATIVE_MODEL_UNQUALIFIED")
    fields = {row.key: row for row in model.list_fields}
    need(fields["youtubedomains"].present and fields["youtubedomains"].empty and
         all(fields[key].present and fields[key].empty is False
             for key in ("userdomains", "excludedomains",
                         "excludeipset", "telegramips")) and
         model.voice[0].service == "telegram" and model.voice[0].args_present,
         "S07_NATIVE_SAVED_EMPTY_OR_USER_FIELDS_LOST")
    # Only the ORIGINAL native WAN resolver may determine an actual device.
    # The projection itself must never infer physical assignments.
    mapping = run(["/bin/sh",
                   "/usr/local/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh",
                   "device"], timeout=30)
    resolved = mapping.stdout.strip()
    need(mapping.returncode == 0 and bool(resolved) and
         len(resolved) <= 32 and
         all(c.isalnum() or c in "_.:-" for c in resolved) and
         not mapping.stderr.strip(),
         "S07_ORIGINAL_SAVED_WAN_RESOLVER_UNQUALIFIED")
    after = s04.snapshot()
    need(before == after and module_bytes == {
         name: s04.file_record(backend / name) for name in names},
         "S07_READONLY_PROJECTION_MUTATED_NATIVE_CONFIG_FD9_PKGDB_PID_IPFW")
    print("S07_G05_REAL_INSTALLED_READONLY_PROJECTION_NO_WRITE=PASS", flush=True)
    return True


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G05_DISPOSABLE_NATIVE") == "1" and
         os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
         Path("/usr/local/opnsense").is_dir(),
         "G05_GENUINE_DISPOSABLE_ROOT_GUEST_REQUIRED")
    g04 = load("stage2-opnsense-g04-native-config.py", "g05_g04_builder")
    sha = g04.verify_native_pkg_and_first_config()
    package = g04.PACKAGE
    need(hashlib.sha256(package.read_bytes()).hexdigest() == sha,
         "G05_NATIVE_INITIAL_ARCHIVE_SHA_CHANGED")
    engine = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    need(not engine.exists(), "G05_NOT_A_COLD_UPSTREAM_GUEST")
    ipfw = run(["/sbin/ipfw", "-q", "list"], timeout=10)
    ipfw_before = (ipfw.returncode, ipfw.stdout, ipfw.stderr)
    core = load("stage2-opnsense-real-native-voice-http.py", "g05_https")
    web = core.GuestHttps()
    core.login(web)
    page = web.request("GET", "/ui/zapret")
    need("frm_GeneralSettings" in page and
         "/api/zapret/settings/apply" in page,
         "G05_NATIVE_AUTHENTICATED_GUI_APPLY_MISSING")
    old, baseline = gui_wan(web)
    need(old in ("", None), "G05_FIRST_WAN_NOT_EMPTY")

    # An actual clean package has no original S10 WAL/root/old owner.
    # No-engine WAN-only Save must not be diverted into the S10 planner.
    s10_cold = _s10_native_cold_no_engine_witness()
    _wan_first_cold_matrix(web, baseline, ipfw_before)
    need(_s10_native_cold_no_engine_witness() == s10_cold,
         "S10_COLD_WAN_PREFLIGHT_CREATED_RUNTIME_OWNER")

    # Stale tab + unknown logical interface must refuse with no mutation.
    initial = CONF.read_bytes()
    stale = request(web, "lo0", "__g05_stale_telegram__")
    need(stale.get("result") == "failed" and
         stale.get("requires_review") is not True,
         "G05_STALE_TAB_DID_NOT_FAIL_BEFORE_CONFIG")
    no_runtime_mutation(False, ipfw_before, initial)
    invalid = request(web, "unassigned0", baseline)
    need(invalid.get("result") == "failed" and
         invalid.get("requires_review") is not True,
         "G05_UNASSIGNED_WAN_NOT_REJECTED")
    no_runtime_mutation(False, ipfw_before, initial)

    # Actual first GUI/API Save with NO upstream engine and original FD9.
    pre_wan_model = _s10_native_model_without_wan(web)
    result = request(web, "lo0", baseline)
    need(result.get("result") == "saved" and
         result.get("status") == "ok" and
         result.get("applied") is False,
         "G05_COLD_FIRST_WAN_CONFIG_ONLY_APPLY_FAILED:" +
         str(result.get("message", "no-message"))[:150])
    exact_saved_wan("lo0")
    _s10_no_other_model_change(web, pre_wan_model, "lo0")
    no_runtime_mutation(False, ipfw_before)
    need(_s10_native_cold_no_engine_witness() == s10_cold,
         "S10_COLD_WAN_FIRST_SAVE_CREATED_S10_OWNER_OR_CHANGED_P1")
    print("S10_G05_NO_ENGINE_WAN_FIRST=PASS_REAL_ORIGINAL_FD9_CONFIG_ONLY_NO_S10_ROOT",
          flush=True)
    reread, baseline = gui_wan(web)
    need(reread == "lo0", "G05_WAN_NOT_VISIBLE_AFTER_FRESH_GET")

    _wan_first_saved_no_engine_matrix(web, ipfw_before)

    # Manual emptying of previously populated strategy/domains MUST NOT
    # obstruct the next WAN-only Save, trigger backend compilation, or
    # recreate either empty user field.
    g04.clear_as_user_save()
    saved_empty = node()
    need((saved_empty.findtext("strategy/trafficargs") or "") == "" and
         (saved_empty.findtext("hostlist/youtubedomains") or "") == "",
         "G05_EMPTY_SAVED_FIELDS_NOT_PRESERVED")
    pre_empty_wan_model = _s10_native_model_without_wan(web)
    result = request(web, "wan", baseline)
    need(result.get("result") == "saved" and
         result.get("applied") is False,
         "G05_EMPTY_STRATEGY_WAN_ONLY_SAVE_FAILED")
    exact_saved_wan("wan")
    _s10_no_other_model_change(web, pre_empty_wan_model, "wan")
    no_runtime_mutation(False, ipfw_before)
    need(_s10_native_cold_no_engine_witness() == s10_cold,
         "S10_COLD_WAN_EMPTY_STRATEGY_CREATED_S10_OWNER_OR_CHANGED_P1")
    print("S10_G05_NO_ENGINE_WAN_EMPTY=PASS_SAVED_EMPTY_FIELDS_NO_S10_ROOT",
          flush=True)
    after, _ = gui_wan(web)
    need(after == "wan", "G05_SECOND_WAN_NOT_VISIBLE_AFTER_F5_GET")
    need((node().findtext("strategy/trafficargs") or "") == "" and
         (node().findtext("hostlist/youtubedomains") or "") == "",
         "G05_WAN_SAVE_BACKFILLED_EXPLICIT_EMPTY_FIELDS")

    # Same archive reinstall may update pkgdb/firmware metadata, but must
    # never change the saved Zapret WAN or regenerate the erased fields.
    previous = ET.tostring(node(), encoding="utf-8")
    again = run(["pkg", "-o", "REPO_AUTOUPDATE=false", "add", "-f",
                 str(package)], timeout=240)
    need(again.returncode == 0 and "zapret-config=preserved" in again.stdout,
         "G05_NATIVE_SAME_ARCHIVE_REINSTALL_FAILED")
    need(hashlib.sha256(package.read_bytes()).hexdigest() == sha and
         ET.tostring(node(), encoding="utf-8") == previous,
         "G05_REINSTALL_MODIFIED_USER_WAN_OR_EMPTY_FIELDS")
    need(_s10_native_cold_no_engine_witness() == s10_cold,
         "S10_COLD_WAN_SAME_ARCHIVE_REINSTALL_CREATED_S10_OWNER_OR_CHANGED_P1")
    # S06: same genuine G05 guest and same native package, ordinary delete,
    # not a force reinstall; preserve saved Config and all three Found files.
    s06_preserved = verify_s06_ordinary_remove_reinstall(web, package, sha, ipfw_before)
    s07_readonly = verify_s07_installed_readonly_projection()
    print("G05_NATIVE=" + json.dumps({
        "status": "PASS_G05_COLD_NO_ENGINE_WAN_ONLY_HTTPS_CONFIG_AND_REINSTALL",
        "first_api_authenticated": True,
        "first_save_without_upstream_engine": True,
        "s10_no_engine_original_root_absent_across_saves_and_reinstall": True,
        "wan_first_gui_configd_voice_lab_ru_en": True,
        "wan_first_engine_second_before_job": True,
        "empty_strategy_and_domains_preserved": True,
        "wan_get_after_f5": True,
        "no_dvtws_or_ipfw_mutation": True,
        "same_archive_sha256": sha,
        "s06_ordinary_remove_reinstall_saved_fields": s06_preserved,
        "s07_installed_readonly_no_write": s07_readonly,
        "owner_browser_tested": False,
        "running_wan_rollback_tested": False,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as e:
        print("G05_NATIVE=REFUSED:" + str(e), file=sys.stderr)
        sys.exit(1)
