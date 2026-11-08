#!/usr/bin/env python3
"""G04: one real pkg install, saved Config clear, same-archive reinstall."""
import hashlib
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
    original_archive = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()

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
