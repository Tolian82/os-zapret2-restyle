#!/usr/bin/env python3
"""Strict disposable OPNsense official-Mk source package with signed private curl.

A *nonpublishable, noninstallable qualification artifact*. Never run against
an owner appliance. Never install fetched FreeBSD latest system packages.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE_REVISION = "59"
PREDECESSOR_REVISION = "58"
PRIVATE_REL = "libexec/zapret2-restyle"
BIN_REL = PRIVATE_REL + "/curl-impersonate/bin/curl-impersonate"
LAUNCHERS = ("check-curl-impersonate.sh", "run-curl-impersonate.sh")
PROFILE = "curl-impersonate/CHROME_PROFILE"
META = ("SOURCE_PKG_SHA256", "BINARY_SHA256", "CHROME_PROFILE",
        "FREEBSD_ABI", "UPSTREAM_VERSION")
OLD_PATH = HERE / "stage0-opnsense-official-mk-source-package.py"

spec = importlib.util.spec_from_file_location("stage0_native_mk", OLD_PATH)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
# Reuse the *already proven* official-Mk provenance/hooks provider checks
# on this exact one-source-revision successor. Do not rewrite the old test.
if old.REVISION != PREDECESSOR_REVISION:
    raise RuntimeError("HISTORICAL_NATIVE_MK_CONTRACT_MOVED")
old.REVISION = SOURCE_REVISION


def require(condition, reason):
    old.need(condition, reason)


def run_binary(argv, timeout=30, allowed=(0,)):
    try:
        p = subprocess.run(argv, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise old.Refusal("PRIVATE_COMMAND_UNAVAILABLE_OR_TIMEOUT:" + argv[0]) from None
    require(p.returncode in allowed,
            "PRIVATE_COMMAND_FAILED:" + Path(argv[0]).name +
            ":code=" + str(p.returncode))
    return p


def tracked_file(path, expected_mode=None):
    relative = str(path.relative_to(ROOT))
    line = old.cmd(["git", "-c", "safe.directory=" + str(ROOT), "-C", str(ROOT),
                    "ls-tree", "HEAD", relative])
    match = re.fullmatch(r"(100644|100755) blob ([a-f0-9]{40})\t" +
                         re.escape(relative), line)
    require(match is not None and
            (expected_mode is None or match.group(1) == expected_mode),
            "UNQUALIFIED_TRACKED_PRIVATE_SOURCE:" + relative)
    require(path.is_file() and not path.is_symlink() and
            stat.S_IMODE(path.stat().st_mode) ==
            int(match.group(1)[-3:], 8),
            "PRIVATE_SOURCE_MODE_NOT_TRACKED:" + relative)
    require(old.cmd(["git", "hash-object", str(path)]) == match.group(2),
            "PRIVATE_SOURCE_BYTES_NOT_TRACKED:" + relative)
    return match.group(2)


def artifact_hex(path):
    require(path.is_file() and not path.is_symlink(),
            "PRIVATE_PROVENANCE_FILE_MISSING:" + path.name)
    value = path.read_text(encoding="ascii").strip()
    require(re.fullmatch(r"[a-f0-9]{64}", value) is not None,
            "PRIVATE_PROVENANCE_HASH_INVALID:" + path.name)
    return value


def validate_bundle(folder):
    private = folder / "curl-impersonate"
    binary = private / "bin/curl-impersonate"
    require(binary.is_file() and not binary.is_symlink() and
            stat.S_IMODE(binary.stat().st_mode) == 0o755,
            "PRIVATE_BINARY_NOT_0755")
    blob = binary.read_bytes()
    require(len(blob) > 1000 and blob[:4] == b"\x7fELF" and
            blob[4] == 2 and blob[5] == 1 and
            struct.unpack_from("<H", blob, 18)[0] == 62,
            "PRIVATE_BINARY_NOT_AMD64_ELF")
    sha = hashlib.sha256(blob).hexdigest()
    require(artifact_hex(private / "BINARY_SHA256") == sha,
            "PRIVATE_SIGNED_BINARY_SHA_MISMATCH")
    source_sha = artifact_hex(private / "SOURCE_PKG_SHA256")
    abi = (private / "FREEBSD_ABI").read_text().strip()
    require(abi == "FreeBSD:15:amd64", "PRIVATE_SOURCE_ABI_MISMATCH")
    profile = (private / "CHROME_PROFILE").read_text().strip()
    require(re.fullmatch(r"chrome[0-9]+", profile) is not None,
            "PRIVATE_CHROME_PROFILE_UNQUALIFIED")
    version = (private / "UPSTREAM_VERSION").read_text().strip()
    require(bool(re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._,+~$-]{0,127}", version)),
            "PRIVATE_SIGNED_VERSION_UNQUALIFIED:diagnostic=" +
            repr(version[:120]) + ":length=" + str(len(version)))
    license_files = [x for x in (private / "licenses").rglob("*") if x.is_file()]
    require(len(license_files) > 0, "PRIVATE_SIGNED_LICENSES_MISSING")
    for entry in (private / "licenses").rglob("*"):
        require(not entry.is_symlink(), "PRIVATE_SIGNED_LICENSE_SYMLINK_REFUSED")
    for name in LAUNCHERS:
        launcher = folder / name
        require(launcher.is_file() and not launcher.is_symlink() and
                stat.S_IMODE(launcher.stat().st_mode) == 0o755,
                "PRIVATE_LAUNCHER_NOT_0755:" + name)
        source = ROOT / "scripts" / name
        require(launcher.read_bytes() == source.read_bytes(),
                "PRIVATE_LAUNCHER_SOURCE_MISMATCH:" + name)
    return {"signed_freebsd_latest_package_sha256": source_sha,
            "private_binary_sha256": sha, "profile": profile,
            "latest_version_diagnostic": version, "license_file_count": len(license_files)}


def native_ldd(binary):
    res = run_binary(["ldd", str(binary)], timeout=20)
    output = (res.stdout + b"\n" + res.stderr).decode("utf-8", "replace")
    require("not found" not in output.lower(), "PRIVATE_UNRESOLVED_ELF_LIBRARY")
    matches = re.findall(r"(?m)^\s*(lib[0-9A-Za-z_+.-]+\.so\.[0-9]+)"
                         r"\s+=>\s+(/[^\s(]+)", output)
    require(len(matches) >= 1 and len(set(n for n, _ in matches)) == len(matches),
            "PRIVATE_ELF_LDD_EMPTY_OR_DUPLICATE")
    qualified = {}
    for name, resolved in matches:
        location = Path(resolved)
        require(location.is_file() and
                (resolved.startswith("/lib/") or
                 resolved.startswith("/usr/lib/") or
                 resolved.startswith("/usr/local/lib/")),
                "PRIVATE_LIBRARY_PATH_NOT_QUALIFIED:" + name)
        if resolved.startswith("/usr/local/"):
            owner = old.cmd(["pkg", "which", "-q", resolved])
            provider = old.cmd(["pkg", "query", "%n|%o|%v", owner])
            parts = provider.split("|")
            require(len(parts) == 3 and parts[0] and parts[1] and parts[2],
                    "PRIVATE_LIBRARY_PKG_PROVIDER_UNQUALIFIED:" + name)
            qualified[name] = {"resolved": resolved,
                               "provenance": "installed-target-opnsense-pkg",
                               "provider": provider}
        else:
            qualified[name] = {"resolved": resolved,
                               "provenance": "target-opnsense-base"}
    return qualified


def smoke_private_launchers(folder):
    private = folder / "curl-impersonate"
    # No WAN. Strictly require actual loader/HTTP3/HTTPS and a loopback
    # connection refusal, not CLI success, TLS ClientHello or QUIC handshake.
    version = run_binary([str(private / "bin/curl-impersonate"), "-V"])
    output = version.stdout.decode("utf-8", "replace")
    require("HTTP3" in output and
            re.search(r"(?m)^Protocols:.*\bhttps\b", output, re.IGNORECASE),
            "PRIVATE_BINARY_MISSING_HTTPS_OR_HTTP3")
    ca = next((p for p in ("/usr/local/etc/ssl/cert.pem",
                            "/usr/local/share/certs/ca-root-nss.crt")
               if Path(p).is_file() and
               Path(p).read_bytes().startswith(b"-----BEGIN CERTIFICATE-----")),
              None)
    require(ca is not None, "PRIVATE_OPNSENSE_CA_BUNDLE_MISSING")
    env = dict(os.environ, ZAPRET2_IMPERSONATE_ROOT=str(private),
               ZAPRET2_IMPERSONATE_CA_BUNDLE=ca)
    # A dedicated child invocation exercises the actual unmodified launcher
    # and hardcoded ECH-off at the END; no proxy or external network.
    try:
        result = subprocess.run(
            [str(folder / "run-curl-impersonate.sh"),
             "--silent", "--show-error", "--connect-timeout", "1",
             "--max-time", "2", "--output", os.devnull,
             "https://127.0.0.1:1/"],
            env=env, capture_output=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError):
        raise old.Refusal("PRIVATE_LAUNCHER_CANNOT_EXECUTE") from None
    require(result.returncode in (7, 28),
            "PRIVATE_CHROME_ECH_OFF_LOOPBACK_NOT_QUALIFIED:" +
            str(result.returncode))
    return {"https_http3_advertised": True,
            "launcher_chrome_ech_off_loopback_refused": True,
            "ca_bundle_from_target": ca,
            "public_tls_clienthello_verified": False,
            "real_quic_handshake_verified": False}


def prepare_private(plugin, work):
    dest = plugin / "src" / PRIVATE_REL
    require(not dest.exists(), "PRIVATE_NATIVE_SOURCE_COLLISION")
    dest.mkdir(parents=True)
    source = ROOT / "scripts/build-curl-impersonate.sh"
    tracked_file(source, "100755")
    for name in LAUNCHERS:
        tracked_file(ROOT / "scripts" / name, "100755")
    # Existing production signed repo path is isolated REPOS_DIR, the pkg
    # catalog signature must pass; never touch live FreeBSD.conf / pkgdb.
    old.cmd(["sh", str(source), str(dest / "curl-impersonate")], timeout=295)
    for name in LAUNCHERS:
        shutil.copy2(ROOT / "scripts" / name, dest / name)
    evidence = validate_bundle(dest)
    evidence["target_ldd_libraries"] = native_ldd(
        dest / "curl-impersonate/bin/curl-impersonate")
    evidence.update(smoke_private_launchers(dest))
    return dest, evidence


def verify_native_private_archive(pkg, source_dir, provenance, plugin, provider):
    # Retain the exact original OPNsense native manifest and hook gate.
    raw = old.cmd(["tar", "-xOf", str(pkg), "+MANIFEST"])
    try:
        manifest = json.loads(raw)
    except ValueError:
        raise old.Refusal("PRIVATE_NATIVE_MANIFEST_INVALID") from None
    original_count = old.manifest_identity(manifest, plugin, provider)
    files = manifest["files"]
    require(len(files) > original_count - 1 and
            "/usr/local/" + BIN_REL in files,
            "PRIVATE_NATIVE_MANIFEST_BINARY_NOT_INCLUDED")
    names = old.cmd(["tar", "-tf", str(pkg)]).splitlines()
    for src in source_dir.rglob("*"):
        if not src.is_file():
            continue
        require(not src.is_symlink(), "PRIVATE_NATIVE_SYMLINK_REFUSED")
        rel = src.relative_to(plugin / "src").as_posix()
        installed = "/usr/local/" + rel
        require(installed in files, "PRIVATE_NATIVE_MANIFEST_FILE_MISSING:" + rel)
        member = old.exact_installed_tar_member(names, rel)
        target = run_binary(["tar", "-xOf", str(pkg), member]).stdout
        require(target == src.read_bytes(),
                "PRIVATE_NATIVE_ARCHIVE_BYTES_MISMATCH:" + rel)
    for name in (*LAUNCHERS, "curl-impersonate/bin/curl-impersonate"):
        member = old.exact_installed_tar_member(names, PRIVATE_REL + "/" + name)
        lines = old.cmd(["tar", "-tvf", str(pkg)]).splitlines()
        found = [x for x in lines if x.rstrip().endswith(" " + member)]
        require(len(found) == 1 and found[0].split()[0] == "-rwxr-xr-x",
                "PRIVATE_NATIVE_ARCHIVE_EXECUTABLE_MODE_NOT_0755:" + name)
    service = old.exact_installed_tar_member(names, old.SERVICE)
    service_mode = [x.split()[0] for x in old.cmd(["tar", "-tvf", str(pkg)]).splitlines()
                    if x.rstrip().endswith(" " + service)]
    require(service_mode == ["-rwxr-xr-x"], "NATIVE_SERVICE_MODE_REGRESSION")
    return {"native_archive_sha256": hashlib.sha256(pkg.read_bytes()).hexdigest(),
            "source_files_in_native_archive": len(files),
            "private_signed_binary_archive_sha256": provenance["private_binary_sha256"],
            "source_service_archive_mode": "0755",
            "private_launchers_archive_mode": "0755"}


def run():
    old.guest_gate()
    project = old.source_identity()
    provider = old.qualify_python_provider()
    # Prevent a compatible-looking but untracked source from contaminating a
    # valid SHA witness, including source package extraction shell.
    for name in (*LAUNCHERS, "build-curl-impersonate.sh"):
        tracked_file(ROOT / "scripts" / name, "100755")
    with tempfile.TemporaryDirectory(prefix="stage2-official-private-") as td:
        framework = old.clone_official(Path(td))
        plugin = old.prepare_source(framework)
        variables = old.native_variables(plugin, project, provider)
        private, bundle = prepare_private(plugin, Path(td))
        old.cmd(["make", "-C", str(plugin), "PLUGIN_HASH=" + project,
                 "PLUGIN_WWW=https://github.com/Tolian82/os-zapret2-restyle",
                 "package"], timeout=290)
        pkg = plugin / "work/pkg" / (
            old.NAME + "-" + old.VERSION + "_" + SOURCE_REVISION + ".pkg")
        require(pkg.is_file(), "OFFICIAL_NATIVE_PRIVATE_ARCHIVE_MISSING")
        native = verify_native_private_archive(pkg, private, bundle, plugin, provider)
    return {"schema": 1,
            "status": "PASS_OFFICIAL_MK_PRIVATE_SIGNED_SOURCE_WITH_LIMITS",
            "project_source_sha": project,
            "official_framework_sha": old.UPSTREAM_SHA,
            "source_only_version": old.VERSION + "_" + SOURCE_REVISION,
            "resolved_variables": variables,
            "target_python_provider": provider,
            **bundle, **native,
            "signed_latest_source_pkg_installed_to_system": False,
            "native_package_installed": False,
            "production_builder_replaced": False,
            "official_final_package_qualified": False,
            "owner_gateway_modified": False,
            "stage0_closed": False, "stage1_admitted": False}


def main():
    try:
        result = run()
    except (old.Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        print("STAGE2_NATIVE_PRIVATE=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE2_NATIVE_PRIVATE=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
