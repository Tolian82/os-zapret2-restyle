#!/usr/bin/env python3
"""Isolated OPNsense 26.7 signed-catalog and installed ELF qualification.

Run on the owner's qualified appliance only. This does not install or
upgrade packages, execute package hooks, alter system pkg databases,
touch FreeBSD.conf, start/stop services, or change IPFW/Config.
Only an auto-cleaned private temporary pkg catalog is written.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

REPO = "OPNsense"
ABI = "FreeBSD:15:amd64"
PRODUCT_ABI = "26.7"
FINGERPRINTS = "/usr/local/etc/pkg/fingerprints/OPNsense"
ELF = Path("/usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate")
PROFILE = ELF.parent.parent / "CHROME_PROFILE"
ELF_SHA = "e4af7ba05b6ad8dd997aefeae3a9c15a08be2700534d043cd93c7987f97c451f"
SONAMES = ("libc++.so.1", "libc.so.7", "libcxxrt.so.1",
           "libgcc_s.so.1", "libm.so.5", "libthr.so.3")
PROVIDERS = ("opnsense", "python313", "php85", "git", "gmake",
             "jq", "luajit", "pkgconf")


class Refusal(Exception):
    pass


def cmd(argv, env=None, timeout=30):
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              env=env, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("COMMAND_UNAVAILABLE_OR_TIMEOUT") from None


def require(result, status):
    if result.returncode:
        raise Refusal(status)
    return result.stdout


def parse_pkg_repos(output):
    # Parse effective pkg -vv, not a guessed file path. Never echo URLs,
    # authentication details, repository overrides or entire pkg output.
    matches = list(re.finditer(r"(?m)^\s{2,}OPNsense:\s*\{\s*$", output))
    if len(matches) != 1:
        raise Refusal("ACTIVE_REPO_AMBIGUOUS")
    tail = output[matches[0].end():]
    end = re.search(r"(?m)^\s+\}\s*,?\s*$", tail)
    if not end:
        raise Refusal("ACTIVE_REPO_BLOCK_UNPARSEABLE")
    values = {}
    for line in tail[:end.start()].splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'\s*([a-z_]+)\s*:\s*(?:"([^"]*)"|([^,\s]+))\s*,?\s*', line)
        if not match or match.group(1) in values:
            raise Refusal("ACTIVE_REPO_FIELDS_AMBIGUOUS")
        values[match.group(1)] = match.group(2) if match.group(2) is not None else match.group(3)
    if (values.get("enabled", "").lower() not in ("yes", "true") or
        values.get("signature_type", "").lower() != "fingerprints" or
        values.get("fingerprints") != FINGERPRINTS or
        not values.get("url", "").endswith("/FreeBSD:15:amd64/26.7/latest")):
        raise Refusal("ACTIVE_REPO_TRUST_OR_ABI_MISMATCH")
    return True


def trusted_key_count(root=FINGERPRINTS):
    trusted = Path(root) / "trusted"
    if trusted.is_symlink() or not trusted.is_dir():
        raise Refusal("TRUSTED_FINGERPRINT_DIRECTORY_MISSING")
    count = 0
    for path in trusted.iterdir():
        if path.is_symlink():
            raise Refusal("SYMLINKED_TRUSTED_FINGERPRINT_REFUSED")
        metadata = path.stat()
        if stat.S_ISREG(metadata.st_mode) and metadata.st_size and not metadata.st_mode & 0o022:
            count += 1
    if count == 0:
        raise Refusal("NO_READABLE_TRUSTED_FINGERPRINT")
    return count


def parse_ldd(output):
    if re.search(r"\bnot found\b", output, re.I):
        raise Refusal("ELF_LIBRARY_UNRESOLVED")
    found = {}
    for name in SONAMES:
        m = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=>\s*(/[^\s(]+)", output)
        if not m or not Path(m.group(1)).is_file():
            raise Refusal("ELF_LIBRARY_UNRESOLVED")
        found[name] = m.group(1)
    return found


def verify_catalog():
    if require(cmd(["opnsense-version", "-a"]), "PRODUCT_ABI_UNVERIFIED").strip() != PRODUCT_ABI:
        raise Refusal("PRODUCT_ABI_UNSUPPORTED")
    if require(cmd(["pkg", "config", "ABI"]), "PKG_ABI_UNVERIFIED").strip() != ABI:
        raise Refusal("PKG_ABI_UNSUPPORTED")
    installed = require(cmd(["pkg", "query", "%n|%v|%o", "os-zapret2-restyle"]),
                        "INSTALLED_PREDECESSOR_UNVERIFIED").strip()
    if installed != "os-zapret2-restyle|0.6.2_1|opnsense/os-zapret2-restyle":
        raise Refusal("INSTALLED_PREDECESSOR_CHANGED")
    parse_pkg_repos(require(cmd(["pkg", "-vv"]), "ACTIVE_REPO_CONFIG_UNAVAILABLE"))
    key_count = trusted_key_count()
    # Official OPNsense firmware connectivity check also isolates PKG_DBDIR.
    # Never update the system catalog. Drop the temporary catalog on exit.
    with tempfile.TemporaryDirectory(prefix="zapret2-stage0-pkg-") as tmp:
        os.chmod(tmp, 0o700)
        cachedir = Path(tmp) / "cache"
        cachedir.mkdir(mode=0o700)
        env = os.environ.copy()
        env.update(PKG_DBDIR=tmp, PKG_CACHEDIR=str(cachedir))
        require(cmd(["pkg", "update", "-f", "-r", REPO], env, 180),
                "ISOLATED_SIGNED_CATALOG_UPDATE_FAILED")
        providers = {}
        for name in PROVIDERS:
            result = require(cmd(["pkg", "-o", "REPO_AUTOUPDATE=false",
                                  "rquery", "-r", REPO, "%n|%v|%o|%R", name],
                                 env, 30), "QUALIFIED_PROVIDER_UNAVAILABLE")
            rows = [x.split("|") for x in result.splitlines() if x.strip()]
            if len(rows) != 1 or len(rows[0]) != 4 or rows[0][0] != name or rows[0][3] != REPO:
                raise Refusal("PROVIDER_REPO_IDENTITY_MISMATCH")
            providers[name] = {"version": rows[0][1], "origin": rows[0][2]}
    return {"catalog_update_in_isolated_database": True,
            "catalog_checked_with_configured_fingerprints": True,
            "trusted_fingerprint_files": key_count, "provider_candidates": providers,
            "official_trust_anchor_independently_compared": False}


def verify_elf():
    if ELF.is_symlink() or not ELF.is_file():
        raise Refusal("INSTALLED_PRIVATE_ELF_MISSING_OR_SYMLINK")
    if hashlib.sha256(ELF.read_bytes()).hexdigest() != ELF_SHA:
        raise Refusal("INSTALLED_PRIVATE_ELF_DIGEST_MISMATCH")
    libs = parse_ldd(require(cmd(["ldd", str(ELF)]), "ELF_LDD_FAILED"))
    version = require(cmd([str(ELF), "-V"]), "INSTALLED_ELF_EXEC_FAILED")
    if "HTTP3" not in version or not re.search(r"(?m)^Protocols:.*\bhttps\b", version, re.I):
        raise Refusal("ELF_HTTPS_HTTP3_UNAVAILABLE")
    try:
        profile = PROFILE.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        raise Refusal("CHROME_PROFILE_UNAVAILABLE") from None
    if not re.fullmatch(r"chrome[0-9]+", profile):
        raise Refusal("CHROME_PROFILE_INVALID")
    smoke = cmd([str(ELF), "-q", "--impersonate", profile, "--ech", "false",
                 "--noproxy", "*", "--connect-timeout", "1", "--max-time", "2",
                 "--silent", "--output", os.devnull, "https://127.0.0.1:1/"], timeout=12)
    if smoke.returncode not in (7, 28):
        raise Refusal("ELF_LOCAL_ECH_OFF_SMOKE_FAILED")
    return {"installed_private_elf_sha256": ELF_SHA, "resolved_sonames": libs,
            "chrome_profile": profile, "https_http3_advertised": True,
            "ech_off_loopback_parsed": True, "external_tls_quic_verified": False}


def main():
    report = {"schema": 1, "proof": "owner-installed-OPNsense-26.7-isolated-pkg-and-ELF",
              "stage0_closed": False, "old_new_pkg_hooks_fd9_verified": False,
              "official_trust_anchor_independently_compared": False}
    try:
        report["repository"] = verify_catalog()
        report["runtime"] = verify_elf()
    except Refusal as error:
        report["status"] = "NOT_VERIFIED"
        report["refusal"] = str(error)
        print("STAGE0_TARGET_QUALIFICATION=" + json.dumps(report, sort_keys=True))
        return 1
    report["status"] = "PASS_CONFIGURED_TRUST_AND_LOCAL_RUNTIME"
    print("STAGE0_TARGET_QUALIFICATION=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
