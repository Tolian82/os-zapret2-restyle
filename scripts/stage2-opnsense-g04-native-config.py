#!/usr/bin/env python3
"""G04: one real pkg install, saved Config clear, same-archive reinstall."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from stage2_source_revision import revision_from_makefile, version_from_file

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "dist" / (
    "os-zapret2-restyle-" + version_from_file() + "_" +
    revision_from_makefile() + ".pkg"
)
CONFIG = Path("/conf/config.xml")


def load_original_clean_witness():
    source = ROOT / "scripts/stage2-opnsense-real-native-clean-install.py"
    spec = importlib.util.spec_from_file_location("g04_original_clean", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


clean = load_original_clean_witness()


def verify_native_pkg_and_first_config():
    # Reuse the stock original Mk/package admissibility and installed-file
    # checks without changing that historical test (which is subscribed by
    # many unrelated Stage 2 VMs).
    prior_bytes = clean.preflight()
    native_pkg = clean.native.build()
    require(native_pkg["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY",
            "G04_OFFICIAL_MK_BUILDER_NOT_QUALIFIED")
    package = clean.native.ROOT / native_pkg["output"]
    require(package == PACKAGE and package.is_file(),
            "G04_BUILT_PACKAGE_IDENTITY_MISMATCH")
    archive_sha = hashlib.sha256(package.read_bytes()).hexdigest()
    clean.pkg_add(package)
    require(hashlib.sha256(package.read_bytes()).hexdigest() == archive_sha,
            "G04_PACKAGE_CHANGED_DURING_INSTALL")
    manifest, _pkgdb = clean.installed_pkg_manifest(package)
    clean.verify_installed_files(package, manifest)
    clean.cold_status()

    before = ET.fromstring(prior_bytes)
    after = ET.fromstring(CONFIG.read_bytes())
    require(before.find("./OPNsense/Zapret") is None,
            "G04_GUEST_NOT_A_TRULY_CLEAN_ZAPRET_CONFIG")
    node = after.find("./OPNsense/Zapret")
    require(node is not None, "G04_NATIVE_SAVED_ZAPRET_MISSING")
    traffic = node.findtext("strategy/trafficargs")
    domains = node.findtext("hostlist/youtubedomains")
    require(traffic is not None and domains is not None and
            "--filter-tcp=80,443" in traffic and
            "--filter-udp=443" in traffic and
            traffic.count("--new") == 1 and
            domains.splitlines() == [
                "youtube.com", "googlevideo.com", "yt.be", "youtu.be",
                "ytimg.com", "youtubei.googleapis.com", "youtube.googleapis.com",
                "youtube-nocookie.com", "ggpht.com", "ssl.gstatic.com"],
            "G04_NATIVE_INSTALLED_CONFIG_NOT_EXACT_OWNER_PROFILE")
    general = node.find("general")
    require(general is not None and
            general.findtext("enabled", "0") == "0" and
            not (general.findtext("waninterface") or "").strip(),
            "G04_INITIAL_CONFIG_AUTO_ENABLED_OR_SELECTED_WAN")
    # The ORIGINAL predecessor-archive oracle must see only firmware changes
    # once the precisely allowed new plugin subtree is taken out of the
    # comparison copy. The production Config stays untouched here.
    normalized = copy.deepcopy(after)
    parent = normalized.find("./OPNsense")
    require(parent is not None, "G04_NAMESPACE_MISSING")
    parent.remove(parent.find("Zapret"))
    if before.find("./OPNsense") is None and len(parent) == 0:
        normalized.remove(parent)
    clean.verify_official_first_install_registration(
        prior_bytes, ET.tostring(normalized, encoding="utf-8"))
    return archive_sha



class Refusal(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Refusal(message)


def run(arguments, timeout=150):
    return subprocess.run(arguments, capture_output=True, text=True,
                          check=False, timeout=timeout)


def subtree():
    root = ET.fromstring(CONFIG.read_bytes())
    node = root.find("./OPNsense/Zapret")
    require(node is not None, "G04_NATIVE_ZAPRET_CONFIG_MISSING")
    return ET.tostring(node, encoding="utf-8")


def get_saved_model():
    source = r'''require_once('script/load_phalcon.php');
$m = new \OPNsense\Zapret\Zapret();
$n = $m->getNodes();
echo json_encode([
  'traffic' => $n['strategy']['trafficargs'] ?? null,
  'youtube' => $n['hostlist']['youtubedomains'] ?? null,
  'enabled' => $n['general']['enabled'] ?? null
], JSON_THROW_ON_ERROR);'''
    result = run(["/usr/local/bin/php", "-r", source])
    require(result.returncode == 0, "G04_NATIVE_MODEL_FRESH_READ_FAILED")
    return json.loads(result.stdout)


def clear_as_user_save():
    source = r'''require_once('script/load_phalcon.php');
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
  $m = new \OPNsense\Zapret\Zapret();
  if ($m->setNodeByReference('strategy.trafficargs', '') !== true ||
      $m->setNodeByReference('hostlist.youtubedomains', '') !== true ||
      count($m->performValidation(false)) !== 0 ||
      !$m->serializeToConfig(false, true)) { throw new \RuntimeException('refused'); }
  $c->save(['description'=>'G04 disposable owner-like empty settings test']);
} finally {
  $c->unlock();
}'''
    result = run(["/usr/local/bin/php", "-r", source])
    require(result.returncode == 0, "G04_NATIVE_USER_CLEAR_SAVE_FAILED")


def main():
    require(os.environ.get("GITHUB_ACTIONS") == "true" and
            os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
            os.environ.get("ZAPRET2_G04_DISPOSABLE_NATIVE") == "1",
            "G04_DISPOSABLE_GUEST_OPTIN_REQUIRED")
    require(os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
            Path("/usr/local/opnsense").is_dir(),
            "G04_NOT_ROOT_OPNSENSE_GUEST")
    require(PACKAGE.is_file() and not PACKAGE.is_symlink(),
            "G04_INSTALLED_ARCHIVE_MISSING")
    original_archive = verify_native_pkg_and_first_config()

    # Stage2 preceding witness has already verified exact native first values,
    # firmware registration and the full unrelated Config preservation.
    first = get_saved_model()
    require(isinstance(first["traffic"], str) and
            "--filter-tcp=80,443" in first["traffic"] and
            "--filter-udp=443" in first["traffic"] and
            isinstance(first["youtube"], str) and
            first["youtube"].splitlines()[0] == "youtube.com" and
            len(first["youtube"].splitlines()) == 10 and
            first["enabled"] in ("0", 0, False),
            "G04_FRESH_GUI_MODEL_DID_NOT_READ_SAVED_INITIAL_CONFIG")

    clear_as_user_save()
    edited = get_saved_model()
    require(edited["traffic"] == "" and edited["youtube"] == "",
            "G04_EMPTY_USER_SAVE_DID_NOT_PERSIST")
    empty_config = subtree()
    # Same physical native .pkg, no other source/build/revision in this guest.
    reinstall = run(["pkg", "-o", "REPO_AUTOUPDATE=false",
                     "add", "-f", str(PACKAGE)], timeout=210)
    require(reinstall.returncode == 0 and
            "zapret-config=preserved" in reinstall.stdout,
            "G04_REAL_REINSTALL_DID_NOT_SKIP_EXISTING_CONFIG:rc=" +
            str(reinstall.returncode) + ":" +
            (reinstall.stdout + reinstall.stderr)[-240:])
    require(hashlib.sha256(PACKAGE.read_bytes()).hexdigest() == original_archive,
            "G04_PHYSICAL_ARCHIVE_CHANGED")
    require(subtree() == empty_config and get_saved_model() == edited,
            "G04_SAVED_EMPTY_USER_CONFIG_CHANGED_ON_REINSTALL")
    print("G04_NATIVE=" + json.dumps({
        "status": "PASS_G04_INITIAL_NATIVE_CONFIG_AND_EMPTY_REINSTALL",
        "first_installed_config_readable_from_fresh_model": True,
        "user_empty_save_persisted": True,
        "same_physical_archive_reinstalled": True,
        "existing_zapret_subtree_preserved": True,
        "first_install_init_skipped_on_reinstall": True,
        "owner_browser_tested": False
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print("G04_NATIVE=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(1)
