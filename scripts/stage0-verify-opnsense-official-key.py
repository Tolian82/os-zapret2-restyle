#!/usr/bin/env python3
"""Read-only OPNsense 26.7 installed fingerprint vs independent official release key.

The official PEM is transcribed from the OPNsense 26.7 release announcement:
https://docs.opnsense.org/releases/CE_26.7.html
Its SHA256 over the exact PEM file, including trailing LF, must equal the
trusted pkg fingerprint from independently pinned opnsense/core source:
https://github.com/opnsense/core/blob/ac08367416c1d66dea87df0ef0de24c315b5d5bc/src/etc/pkg/fingerprints/OPNsense/trusted/pkg.opnsense.org.20260608

No network, pkg invocation, state change, key disclosure or recovery action.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

OFFICIAL_26_7_PEM = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAziSNKuzrL2cwLx5LXmLn
cWS5Lk+i9CzRMXO/4xQYBQCaSnd8GBg/HA/g4aPoTUa6ovAI0AHfW8KQJQyBkFzn
pi6MLZJ9tEaFcn0CiV+tSTJd1RV4bB8jtpKl5oTkgFrPsyaB7iBlG5Cd49VCW19h
DxClQ24lkWkVoYfsfCQEt4ADNGLygWCPyf4bxGD/t6/tiW9SsOs2+gfOZ9C/G2d/
EBhJFoBEoz5lvULVxTdfY5PScYrHD/waZnk3rGc2A+9pI/SM2JAwKqsgZ6MSFbXO
DNocSjqFUUkdqhty+Qcc0OJ+hMbKKVE+f3QJBQIwT3ayys8QK0m5CCo91/f+DjoN
noj+t5YN9x8GREkF0wrdIi7hevkwrL2/SJQbq1bL1BLB+mMSXYR611lgT8YfYjyZ
7tmpNVC3O5Pj7l20snm1lVUSqS0PsFBvh6HQtBRwQDGppaIIhH1Nt9yIatmSiGZt
2YrMVNBzbQrJzSX+vWcAulkaPIt4t+XxmpO5IDNZ+4uMZ7XyJq1lAhIeyXx+Falf
v7S+ZpJWFVNz0/N5z6lBbADD855i+gFY6B5209xGyhd6FwaPOjISgQKkgBwF1AiW
MDuTuP9lkh/U5gGBZIFTnbdEMgOAL4P+Hsw9Nozav+3QIpiU3Pv9F29a1erCkq09
rpQyNglY7Jqme/RipzbYia8CAwEAAQ==
-----END PUBLIC KEY-----
"""
OFFICIAL_26_7_PKG_SHA256 = "9f3b76ffef38fb6405595038b324b61043c9a2c375ae5c151d628508e9a845ce"
OFFICIAL_26_7_TRUSTED_FILENAME = "pkg.opnsense.org.20260608"
TRUST_ROOT = Path("/usr/local/etc/pkg/fingerprints/OPNsense")


class Refusal(Exception):
    pass


def official_pem_fingerprint():
    digest = hashlib.sha256(OFFICIAL_26_7_PEM.encode("ascii")).hexdigest()
    if digest != OFFICIAL_26_7_PKG_SHA256:
        raise Refusal("OFFICIAL_PEM_AND_CORE_REFERENCE_DISAGREE")
    return digest


def safe_directory(path, root_owner=True):
    try:
        if path.is_symlink():
            raise Refusal("UNSAFE_KEYSTORE_SYMLINK")
        info = path.stat()
    except OSError:
        raise Refusal("TRUST_DIRECTORY_UNAVAILABLE") from None
    if (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022 or
            (root_owner and info.st_uid != 0)):
        raise Refusal("UNSAFE_KEYSTORE_DIRECTORY")
    return path


def safe_regular_file(path, root_owner=True):
    try:
        if path.is_symlink():
            raise Refusal("UNSAFE_FINGERPRINT_SYMLINK")
        info = path.stat()
    except OSError:
        raise Refusal("FINGERPRINT_FILE_MISSING") from None
    if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or
            (root_owner and info.st_uid != 0) or not (0 < info.st_size <= 4096)):
        raise Refusal("UNSAFE_FINGERPRINT_FILE")
    try:
        return path.read_text(encoding="ascii")
    except (OSError, UnicodeError):
        raise Refusal("FINGERPRINT_FILE_UNREADABLE") from None


def parse_fingerprint(contents):
    fields = {}
    for line in contents.splitlines():
        match = re.fullmatch(r'\s*(function|fingerprint)\s*:\s*"?([a-zA-Z0-9]+)"?\s*', line)
        if not match or match.group(1) in fields:
            raise Refusal("FINGERPRINT_FORMAT_AMBIGUOUS")
        fields[match.group(1)] = match.group(2)
    if set(fields) != {"function", "fingerprint"} or fields["function"].lower() != "sha256":
        raise Refusal("FINGERPRINT_FORMAT_UNSUPPORTED")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", fields["fingerprint"]):
        raise Refusal("FINGERPRINT_FORMAT_UNSUPPORTED")
    return fields["fingerprint"].lower()


def verify_trust(root=TRUST_ROOT, root_owner=True):
    official = official_pem_fingerprint()
    # Only inspect this OPNsense-specific keystore, never any repo config.
    safe_directory(root, root_owner)
    trusted = safe_directory(root / "trusted", root_owner)
    revoked = safe_directory(root / "revoked", root_owner)
    try:
        trusted_names = sorted(x.name for x in trusted.iterdir())
        revoked_names = sorted(x.name for x in revoked.iterdir())
    except OSError:
        raise Refusal("KEYSTORE_ENUMERATION_FAILED") from None
    if trusted_names != [OFFICIAL_26_7_TRUSTED_FILENAME]:
        raise Refusal("EXTRA_MISSING_OR_ALTERNATE_TRUSTED_KEYS")
    raw = safe_regular_file(trusted / OFFICIAL_26_7_TRUSTED_FILENAME, root_owner)
    installed = parse_fingerprint(raw)
    if installed != official:
        raise Refusal("INSTALLED_KEY_DIFFERS_FROM_OFFICIAL_26_7")
    for name in revoked_names:
        if name in (".", ".."):
            continue
        if not re.fullmatch(r"[a-zA-Z0-9._-]{1,150}", name):
            raise Refusal("UNSAFE_REVOKED_FILENAME")
        digest = parse_fingerprint(safe_regular_file(revoked / name, root_owner))
        if digest == official:
            raise Refusal("OFFICIAL_26_7_KEY_IS_REVOKED")
    return {"official_release_series": "26.7",
            "official_key_source": "opnsense.org/26.7 + pinned opnsense/core 26.7",
            "official_pem_sha256_matches_pinned_core": True,
            "trusted_filename": OFFICIAL_26_7_TRUSTED_FILENAME,
            "official_fingerprint_sha256": official,
            "installed_key_matches_independent_official_reference": True,
            "additional_trusted_keys": False, "official_key_found_in_revoked": False,
            "no_on_device_file_changed": True}


def main():
    report = {"schema": 1, "proof": "read-only-installed-opnsense-trust-key",
              "stage0_closed": False, "pkg_hooks_fd9_verified": False}
    try:
        report["key"] = verify_trust()
        report["status"] = "PASS_OFFICIAL_26_7_KEY_MATCH"
    except Refusal as exc:
        report["status"] = "NOT_VERIFIED"
        report["refusal"] = str(exc)
    print("STAGE0_OFFICIAL_KEY=" + json.dumps(report, sort_keys=True))
    return 0 if report["status"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
