#!/usr/bin/env python3
"""TZ6v5 S03c1: genuine Strategy Lab entrypoint PRE-JOB refusal on disposable OPNsense.

This is NOT G05/G08 full native installed-plugin acceptance. It executes the
unaltered production strategy_lab_launcher.sh + strategy_lab/launch.sh chain
using real FreeBSD lockf and jq, with ONE explicitly substituted saved-WAN
preflight boundary. No installed engine, no ordinary Start, no temporary Lab
dvtws, no runtime Config writer, no IPFW mutation. Tests exact refusal
priority, RU/EN reasons, zero Job and exact foreign state.

Never call this on an owner router. It refuses without explicit CI/native
flags and checks absent engine/ordinary PID/process before running.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "src/opnsense/scripts/OPNsense/Zapret"
MODULE = SCRIPT / "strategy_lab"
LAUNCHER = SCRIPT / "strategy_lab_launcher.sh"
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
ORDINARY_PID = Path("/var/run/dvtws2.pid")
LOCKF = Path("/usr/bin/lockf")
JQ = Path("/usr/local/bin/jq")
IPFW = Path("/sbin/ipfw")
PS = Path("/bin/ps")

CASES = (
    ("missing_standard_ru", "wan-required", "standard", "ru", 64,
     "wan-required", "Укажите WAN интерфейс"),
    ("missing_extended_en", "wan-required", "extended", "en", 64,
     "wan-required", "Select a WAN interface"),
    ("missing_extended_ru", "wan-required", "extended", "ru", 64,
     "wan-required", "Укажите WAN интерфейс"),
    ("invalid_standard_en", "wan-invalid", "standard", "en", 64,
     "wan-invalid", "Selected WAN interface is not assigned or unavailable"),
    ("preflight_unavailable", "wan-unavailable", "standard", "en", 69,
     "wan-unavailable", "Saved WAN preflight is unavailable"),
    ("engine_missing_standard_ru", "wan-ready", "standard", "ru", 64,
     "engine-not-installed", "Служба zapret2 не установлена"),
    ("engine_missing_extended_en", "wan-ready", "extended", "en", 64,
     "engine-not-installed", "The zapret2 service is not installed"),
)


class Refusal(RuntimeError):
    pass


def require(ok: bool, code: str):
    if not ok:
        raise Refusal(code)


def cmd(*args: str, timeout: int = 12) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          check=False)


def filesnapshot(path: Path) -> tuple[bool, str]:
    require(not path.is_symlink(), "SOURCE_NATIVE_SYMLINK_" + path.name)
    if not path.exists():
        return False, ""
    require(path.is_file(), "SOURCE_NATIVE_NONREGULAR_" + path.name)
    return True, hashlib.sha256(path.read_bytes()).hexdigest()


def kernel_snapshot() -> tuple[int, str, str]:
    require(IPFW.is_file(), "NATIVE_IPFW_QUERY_MISSING")
    p = cmd(str(IPFW), "-q", "list")
    return p.returncode, p.stdout, p.stderr


def native_preconditions() -> None:
    require(sys.platform.startswith("freebsd") and os.geteuid() == 0,
            "S03C_FREEBSD_ROOT_ONLY")
    require(os.environ.get("GITHUB_ACTIONS") == "true" and
            os.environ.get("ZAPRET2_S03C_DISPOSABLE_NATIVE") == "1",
            "S03C_DISPOSABLE_CI_OPT_IN_REQUIRED")
    require(LAUNCHER.is_file() and (MODULE / "launch.sh").is_file(),
            "S03C_PRODUCTION_LAB_ENTRY_MISSING")
    require(LOCKF.is_file() and os.access(LOCKF, os.X_OK) and
            JQ.is_file() and os.access(JQ, os.X_OK),
            "S03C_NATIVE_LOCKF_JQ_REQUIRED")
    require(not ENGINE.exists() and not ENGINE.is_symlink() and
            not ORDINARY_PID.exists() and not ORDINARY_PID.is_symlink(),
            "S03C_REFUSE_INSTALLED_OR_OWNED_ENGINE")
    p = cmd(str(PS), "-ax", "-o", "command=")
    require(p.returncode == 0, "S03C_PROCESS_INVENTORY_UNAVAILABLE")
    require(not any("binaries/my/dvtws2" in line or
                    "strategy_lab_worker.sh" in line
                    for line in p.stdout.splitlines()),
            "S03C_REFUSE_RUNNING_ENGINE_OR_LAB_WORKER")


def test() -> None:
    native_preconditions()
    before_config = filesnapshot(CONFIG)
    before_ipfw = kernel_snapshot()
    observations = {}
    with tempfile.TemporaryDirectory(prefix="tz6v5-s03c-native-", dir="/tmp") as t:
        base = Path(t)
        shim = base / "shim"
        shim.mkdir(mode=0o700)
        wan = shim / "wan_preflight.sh"
        wan.write_text(
            "#!/bin/sh\n"
            '[ "$1" = require ] || exit 64\n'
            'printf "%s\\n" "$S03C_WAN_RESULT"\n'
            '[ "$S03C_WAN_RESULT" != wan-unavailable ] || exit 69\n',
            encoding="utf-8",
        )
        wan.chmod(0o700)
        lab_root = base / "lab"
        jobs = lab_root / "jobs"
        lock = lab_root / "launcher.lock"
        deny = base / "UNAVAILABLE_EXECUTION_REFUSED"
        base_env = {**os.environ,
                    "SCRIPT_DIR": str(shim), "MODULE_DIR": str(MODULE),
                    "STRATEGY_LAB_RUN_DIR": str(lab_root),
                    "STRATEGY_LAB_JOBS_DIR": str(jobs),
                    "STRATEGY_LAB_LOG_DIR": str(base / "logs"),
                    "STRATEGY_LAB_LOCK_FILE": str(lock),
                    "STRATEGY_LAB_JQ": str(JQ),
                    "LOCKF_BIN": str(LOCKF),
                    # None of these are executable: fail closed if the
                    # genuine launcher accidentally advances past preflight.
                    "STRATEGY_LAB_DVTWS_BIN": str(deny),
                    "DAEMON_BIN": str(deny),
                    "WORKER_SCRIPT": str(deny),
                    "TRANSACTION_SCRIPT": str(deny),
                    "PYTHONDONTWRITEBYTECODE": "1"}
        for name, boundary, mode, language, rc, reason, message in CASES:
            env = {**base_env, "S03C_WAN_RESULT": boundary}
            # Deliberately malformed target must lose to WAN/engine preflight.
            p = subprocess.run(
                ["/bin/sh", str(LAUNCHER), "start", "!invalid_target",
                 mode, language],
                env=env, cwd=REPO, capture_output=True, text=True,
                timeout=20, check=False)
            try:
                result = json.loads(p.stdout)
            except ValueError as ex:
                raise Refusal("S03C_MALFORMED_PRODUCTION_REFUSAL_" + name) from ex
            require(p.returncode == rc, "S03C_WRONG_RC_" + name)
            require(result == {"status": "error", "reason": reason,
                               "message": message},
                    "S03C_WRONG_REASON_OR_LOCALE_" + name)
            require(not p.stderr.strip(), "S03C_UNEXPECTED_STDERR_" + name)
            require(jobs.is_dir() and not list(jobs.iterdir()),
                    "S03C_JOB_ALLOCATED_" + name)
            require(not (lab_root / "active.job").exists() and
                    not (lab_root / "latest.job").exists(),
                    "S03C_LAB_POINTER_CREATED_" + name)
            require(not any(base.rglob("job.*")),
                    "S03C_JOB_ARTIFACT_CREATED_" + name)
            require(filesnapshot(CONFIG) == before_config,
                    "S03C_NATIVE_CONFIG_MUTATED_" + name)
            require(kernel_snapshot() == before_ipfw,
                    "S03C_FOREIGN_IPFW_MUTATED_" + name)
            require(not ENGINE.exists() and not ORDINARY_PID.exists(),
                    "S03C_ORDINARY_ENGINE_OR_PID_CREATED_" + name)
            observations[name] = {"rc": rc, "reason": reason, "language": language,
                                  "job_created": False}
    print("TZ6V5_S03C1_REAL_LAB_LAUNCHER_REFUSAL_BASELINE=" +
          json.dumps(observations, sort_keys=True, ensure_ascii=False))
    print("S03C1_GENUINE_LAB_ENTRYPOINT_ON_DISPOSABLE_NATIVE=PASS")
    print("S03C1_G05_G08_FULL_INSTALLED_NATIVE_NOT_CLAIMED=1")
    print("S03C1_PHYSICAL_START_STOP_OR_FORCE_NOT_TESTED=1")


if __name__ == "__main__":
    try:
        test()
    except (Refusal, OSError, subprocess.TimeoutExpired) as ex:
        marker = str(ex)
        if not marker.startswith("S03C_"):
            marker = type(ex).__name__
        print("S03C1_FAIL=" + marker[:200], file=sys.stderr)
        raise SystemExit(1)
