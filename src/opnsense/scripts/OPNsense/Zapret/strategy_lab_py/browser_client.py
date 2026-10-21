"""Stage-1 read-only readiness contract for the private Chrome client.

Integration into the active Strategy Lab stage-00 lifecycle happens with Stage 2,
when every production HTTP/HTTPS probe is migrated to this same client.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

BASE = Path("/usr/local/libexec/zapret2-restyle/curl-impersonate")
CA_BUNDLES = (
    Path("/etc/ssl/cert.pem"),
    Path("/usr/local/share/certs/ca-root-nss.crt"),
)


class BrowserClientUnavailable(RuntimeError):
    pass


def check_ready(base: Path = BASE, *, timeout: float = 5.0) -> str:
    """Fail closed before service mutation; return the package's one Chrome profile."""
    if timeout <= 0:
        raise BrowserClientUnavailable("invalid client readiness timeout")
    executable = base / "bin" / "curl-impersonate"
    real_binary = base / "libexec" / "curl-impersonate"
    profile_path = base / "PROFILE"
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise BrowserClientUnavailable("private curl-impersonate entrypoint is missing")
    if not real_binary.is_file() or not os.access(real_binary, os.X_OK):
        raise BrowserClientUnavailable("private curl-impersonate binary is missing")
    try:
        profile = profile_path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise BrowserClientUnavailable("private Chrome profile is missing") from exc
    if re.fullmatch(r"chrome[0-9]+", profile) is None:
        raise BrowserClientUnavailable("private Chrome profile is invalid")
    if not any(path.is_file() and os.access(path, os.R_OK) for path in CA_BUNDLES):
        raise BrowserClientUnavailable("trusted system CA bundle is missing")
    try:
        proc = subprocess.run(
            [str(executable), "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BrowserClientUnavailable("private Chrome client cannot execute") from exc
    if proc.returncode != 0 or "HTTP3" not in proc.stdout:
        raise BrowserClientUnavailable("private Chrome client is unavailable or lacks HTTP3")
    return profile
