#!/usr/bin/env python3
"""Install immutable predecessor with original hooks in disposable OPNsense 26.7 CI VM.

Real archive bytes/files/scripts and native installed pkg DB are verified.
Original package hooks execute ONLY inside this throwaway VM; no owner gateway.
This is real original fresh-install lifecycle, NOT old-service FD9 or successor acceptance.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


pre = load("stage0-installed-predecessor-readonly.py", "predecessor")
guest = load("stage0-opnsense-guest-readonly.py", "guest")

# -I drops hook metadata; --script-no-exec refuses hooks that execute binaries.
# Execute original scripts only in disposable OPNsense, never owner gateway.
# No --accept-missing/--force and do not change repository configuration.
ADD_COMMAND = ("pkg", "-o", "REPO_AUTOUPDATE=false", "add")


def query_installed(name):
    result = subprocess.run(("pkg", "info", "-e", name), check=False,
                            capture_output=True, timeout=20)
    if result.returncode not in (0, 1):
        raise pre.Refusal("PACKAGE_DATABASE_QUERY_FAILED")
    return result.returncode == 0


def preflight(archive, system, archive_manifest):
    guest.evaluate(system)  # real OPNsense, FreeBSD 15 amd64, KVM, no old pkg
    if archive_manifest.get("name") != pre.NAME or archive_manifest.get("version") != pre.VERSION:
        raise pre.Refusal("PUBLISHED_PREDECESSOR_IDENTITY_MISMATCH")
    if archive_manifest.get("abi") != pre.ABI:
        raise pre.Refusal("PUBLISHED_PREDECESSOR_ABI_MISMATCH")
    if archive_manifest.get("arch") != "freebsd:15:x86:64":
        raise pre.Refusal("PUBLISHED_PREDECESSOR_ARCH_MISMATCH")
    deps = archive_manifest.get("deps", {})
    if not isinstance(deps, dict):
        raise pre.Refusal("PUBLISHED_PREDECESSOR_DEPS_MALFORMED")
    # Never let package addition install new system dependencies. The later
    # native dependency provisioning scope will cover their signed providers.
    missing = [name for name in sorted(deps) if not query_installed(name)]
    if missing:
        raise pre.Refusal("MISSING_PREINSTALLED_TARGET_DEPENDENCIES:" + ",".join(missing))
    if query_installed(pre.NAME):
        raise pre.Refusal("PREDECESSOR_ALREADY_INSTALLED")
    if not archive.is_file():
        raise pre.Refusal("PUBLISHED_PREDECESSOR_NOT_LOCAL_REGULAR_FILE")


def execute_add(archive):
    try:
        result = subprocess.run([*ADD_COMMAND, str(archive)], check=False,
                                capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError):
        raise pre.Refusal("ORIGINAL_HOOK_PACKAGE_ADD_UNAVAILABLE_OR_TIMEOUT") from None
    if result.returncode:
        diagnostic = " ".join(result.stderr.split())[:240]
        raise pre.Refusal("ORIGINAL_HOOK_PACKAGE_ADD_FAILED:" + str(result.returncode)
                          + ":" + diagnostic)
    if "os-zapret2-restyle was installed." not in result.stdout:
        raise pre.Refusal("ORIGINAL_POST_INSTALL_SUCCESS_SIGNATURE_ABSENT")
    return True


def install_and_verify(archive):
    archived, _payload = pre.archive_data(archive)  # SHA gate before any install
    system = guest.observe()
    preflight(archive, system, archived)
    postinstall_observed = execute_add(archive)
    # The production readonly checker re-opens immutable archive, reads ACTUAL
    # pkgdb + installed service bytes/owner/mode and does not modify anything.
    host = pre.run("hostname", "-s").decode().strip()
    report = pre.run_guest(archive, host)
    if report.get("status") != "PASS_READ_ONLY_PROVENANCE":
        raise pre.Refusal("ACTUAL_INSTALLED_PREDECESSOR_PROVENANCE_NOT_PASS")
    if any(report.get(k) for k in ("real_fd9_tested", "actual_pkg_replacement",
                                   "native_successor_package_tested",
                                   "isolated_environment_independently_attested")):
        raise pre.Refusal("PROVENANCE_WITNESS_CLAIMS_UNTESTED_LIFECYCLE")
    return {
        "schema": 1,
        "status": "PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE",
        "package": report["package"],
        "archive_sha256": pre.ARCHIVE_SHA,
        "installed_service_sha256": report["service_sha256"],
        "four_hook_sha256": report["original_hooks_sha256"],
        "product_abi": system["product_abi"],
        "package_abi": system["package_abi"],
        "virtualization": system["virtualization"],
        "original_post_install_success_message_observed": postinstall_observed,
        "dependencies_preinstalled_only": True,
        "actual_predecessor_package_installed": True,
        "actual_fresh_install_hooks_executed": True,
        "official_vm_image_bytes_independently_verified": False,
        "real_service_fd9_tested": False,
        "actual_pkg_replacement": False,
        "native_successor_package_tested": False,
        "stage0_closed": False,
    }


def main():
    if len(sys.argv) != 2:
        print("STAGE0_INSTALLED_PREDECESSOR=REFUSED:REQUIRES_EXACT_ARCHIVE_PATH", file=sys.stderr)
        return 2
    try:
        witness = install_and_verify(Path(sys.argv[1]))
    except (pre.Refusal, guest.Refusal, OSError, ValueError, KeyError) as exc:
        print("STAGE0_INSTALLED_PREDECESSOR=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_INSTALLED_PREDECESSOR=" + json.dumps(witness, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
