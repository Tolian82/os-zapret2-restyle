#!/usr/bin/env python3
"""Read-only OPNsense 26.7 target provider gate BEFORE native builder cutover.

Runs only in isolated qualified KVM CI. Does not build/publish/install a
product package, touch appliance repo configuration or admit Stage 1.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
REVISION = "60"
REPOSITORY = "OPNsense"
EXPECTED_ABI = "FreeBSD:15:amd64"
PRODUCT_ABI = "26.7"
UPSTREAM_SHA = "79a5f88b7b27a706c10511ea5587c9d0e0dbdced"

# Actual dependency consumers: setup.sh, engine compile and private CA.
# Resolve package origins and versions ONLY from the target catalog.
REQUIRED = {
    "engine-build-make": ("gmake",),
    "engine-build-pkgconf": ("pkgconf",),
    "engine-runtime-luajit": ("luajit",),
    "setup-git": ("git-lite", "git"),
    "setup-json": ("jq",),
    "private-trust-CA": ("ca_root_nss",),
}

spec = importlib.util.spec_from_file_location(
    "stage0_official_mk", HERE / "stage0-opnsense-official-mk-source-package.py")
mk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mk)
if mk.REVISION != "58" or mk.UPSTREAM_SHA != UPSTREAM_SHA:
    raise RuntimeError("PINNED_MK_WITNESS_CONTRACT_CHANGED")
mk.REVISION = REVISION


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def command(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                check=False, timeout=50)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("TARGET_COMMAND_UNAVAILABLE_OR_TIMEOUT:" + args[0]) from None
    need(result.returncode == 0,
         "TARGET_COMMAND_FAILED:" + args[0] + ":" +
         str(result.returncode) + ":" + result.stderr[-180:])
    return result.stdout.strip()


def parse_catalog(raw):
    need(isinstance(raw, str), "CATALOG_RESPONSE_NOT_TEXT")
    rows = {}
    for line in raw.splitlines():
        columns = line.strip().split("|")
        need(len(columns) == 3 and all(columns) and len(line) <= 400 and
             re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+~-]*", columns[0]) and
             re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./+-]*", columns[1]) and
             "\x00" not in line, "CATALOG_ROW_MALFORMED")
        name, origin, version = columns
        need(name not in rows, "CATALOG_DUPLICATE_PROVIDER:" + name)
        rows[name] = {"name": name, "origin": origin, "version": version}
    need(len(rows) >= 700, "CATALOG_NOT_QUALIFIED_OFFICIAL_TARGET")
    return rows


def resolve(catalog, pyname):
    need(re.fullmatch(r"python3[0-9]{2}", pyname) is not None,
         "GENERIC_PYTHON_PROVIDER_NAME_INVALID")
    groups = {**REQUIRED, "python-runtime": (pyname,)}
    result = {}
    for role, candidate_names in groups.items():
        available = [catalog[n] for n in candidate_names if n in catalog]
        need(len(available) >= 1, "TARGET_PROVIDER_MISSING:" + role)
        result[role] = {"selected": available[0], "alternatives": available[1:],
                        "provenance": "official-OPNsense-catalog"}
    return result


def installed_python_crosscheck(providers, observed):
    parts = observed["installed_python_provider"].split("|")
    need(len(parts) == 3 and
         providers["python-runtime"]["selected"]["name"] == parts[0] and
         providers["python-runtime"]["selected"]["origin"] == parts[1],
         "INSTALLED_PYTHON_ORIGIN_NOT_MATCHED_TO_TARGET")
    return {"installed": observed["installed_python_provider"],
            "catalog": providers["python-runtime"]["selected"],
            "installed_version_may_lag_catalog": True}


def inventory_legacy_contracts():
    read = lambda f: (ROOT / f).read_text()
    old = read("scripts/build-pkg.sh")
    ci = read(".github/workflows/ci.yml")
    release = read(".github/workflows/release.yml")
    tests = read("scripts/test_freebsd15_package_ci.py")
    checks = {
        "own_pkg_static_create": "pkg-static create" in old,
        "own_dep_origin": "dep_origin()" in old,
        "own_manifest_json": "work/+MANIFEST" in old,
        "blanket_script_chmod": '-exec chmod 755' in old,
        "stock_FreeBSD_CI_build": 'release: "15.0"' in ci and
                                  'sh scripts/build-pkg.sh' in ci,
        "stock_FreeBSD_release_build": "release: '15.0'" in release and
                                       'sh scripts/build-pkg.sh' in release,
        "CI_legacy_python313_origin": '.deps.python313.origin == "lang/python313"' in ci,
        "legacy_contract_checks_handmade_builder": "python313)  echo" in tests,
    }
    need(all(checks.values()), "LEGACY_BUILD_PIPELINE_CHANGED_UNEXPECTEDLY")
    return checks


def main():
    try:
        mk.guest_gate()
        source_sha = mk.source_identity()
        installed_python = mk.qualify_python_provider()
        need(command("opnsense-version", "-a") == PRODUCT_ABI,
             "OPNSENSE_PRODUCT_ABI_NOT_26_7")
        need(command("pkg", "config", "ABI") == EXPECTED_ABI,
             "OPNSENSE_PKG_ABI_WRONG")
        raw = command("pkg", "rquery", "-r", REPOSITORY, "%n|%o|%v")
        catalog = parse_catalog(raw)
        providers = resolve(catalog, "python" + installed_python["native_plugin_python"])
        python_proof = installed_python_crosscheck(providers, installed_python)
        legacy = inventory_legacy_contracts()
        with tempfile.TemporaryDirectory(prefix="stage2-opnsense-provider-") as td:
            upstream = mk.clone_official(Path(td))
            plugin = mk.prepare_source(upstream)
            variables = mk.native_variables(plugin, source_sha, installed_python)
        # Baseline is deliberate and must be removed at one production cutover.
        need(variables["PLUGIN_DEPENDS"] ==
             "python" + installed_python["native_plugin_python"],
             "EXISTING_MAKEFILE_DEPENDENCIES_CHANGED")
        evidence = {
            "schema": 1, "status": "PASS_TARGET_PROVIDERS_LEGACY_CUTOVER_NOT_DONE",
            "source_sha": source_sha, "upstream_sha": UPSTREAM_SHA,
            "product_abi": PRODUCT_ABI, "pkg_abi": EXPECTED_ABI,
            "repository": REPOSITORY, "catalog_count": len(catalog),
            "catalog_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "providers": providers, "installed_python": python_proof,
            "actual_native_variables": variables, "old_pipeline": legacy,
            "production_builder_replaced": False, "new_package_installed": False,
            "product_package_published": False,
            "foreign_FreeBSD_system_pkg_installed": False,
            "owner_appliance_modified": False, "stage0_closed": False,
            "stage1_admitted": False}
        print("STAGE2_NATIVE_PROVIDERS=" + json.dumps(evidence, sort_keys=True))
        return 0
    except (Refusal, mk.Refusal, ValueError, OSError, KeyError, TypeError) as exc:
        print("STAGE2_NATIVE_PROVIDERS=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
