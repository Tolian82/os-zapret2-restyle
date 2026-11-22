#!/usr/bin/env python3
"""TZ6v5 S03: original production generator baseline + REAL expected-RED probes.

Offline source-runner only: no installed engine, FD9, Config.xml, IPFW, root
writes or subscriber traffic. Uses the EXISTING P2e orchestrator_build_release
fixture, and genuine auto_detect_origin_map.plan_learning_tier. Observed RED
is not a native/owner PASS. It is intentionally NOT a new physical launcher.

Usage:
  python3 scripts/test-tz6v5-s03-original-red.py --capture --report /tmp/s03.json
  python3 scripts/test-tz6v5-s03-original-red.py --target --report /tmp/s03.json
  python3 scripts/test-tz6v5-s03-original-red.py --verify-red --report /tmp/s03.json

--target MUST fail on still-missing V5 contract requirements.
--verify-red MUST succeed only if the exact expected failures were observed
from actual test output. When a requirement turns GREEN, replace this RED gate
with real positive tests; never silently accept missing evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SERVICE = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
BACKEND = SERVICE.parent / "backend"
PRODUCER = HERE / "test-p2e-original-shared-build.py"
SCHEMA = 1
EXPECTED_RED = (
    "AUTO_LEARNING_FAIL_THRESHOLD_MISSING",
    "CLI_GLOBAL_HELP_UNIMPLEMENTED",
    "CLI_RELOAD_HELP_UNIMPLEMENTED",
    "REFERENCE_MANIFEST_UNAVAILABLE",
)
NATIVE_EXPECTED_RED = (
    "STATUS_READONLY_FD9_SIDE_EFFECT",
    "STATUS_JSON_UNIMPLEMENTED",
)
EXPECTED_LIST = ["youtube", "youtube", "user"]
STRATEGY = (
    "--filter-tcp=443\n--filter-l7=tls\n"
    "--lua-desync=fake\n"
)
EXPLICIT = (
    "--filter-tcp=443\n--filter-l7=tls\n<HOSTLIST:youtube>\n"
    "--lua-desync=fake\n"
)
ORDERED = (
    "--filter-tcp=443\n--filter-l7=tls\n<HOSTLIST:youtube>\n"
    "--lua-desync=fake\n--new\n--filter-udp=443\n"
    "--filter-l7=quic\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
    "--new\n--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n"
)


class ProbeFailure(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProbeFailure(code)


def load_original():
    spec = importlib.util.spec_from_file_location("s03_real_original_p2e", PRODUCER)
    need(spec is not None and spec.loader is not None,
         "ORIGINAL_SHARED_GENERATOR_FIXTURE_MISSING")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic_sample(name: str, count: int) -> str:
    return "".join(f"{name}{n:05d}.example.org\n" for n in range(count))


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def one_original_run(fixture, name: str, strategy: str, *,
                     mode: str = "auto", voice_on: bool = False,
                     youtube_domains: str = "youtube.com",
                     user_domains: str = "example.org",
                     excluded: bool = False,
                     want_learning: bool = False) -> tuple[dict, dict]:
    old = fixture.OriginalSharedGeneration("runTest")
    old.setUp()
    try:
        mapped, argv_file = old.build(
            strategy, mode=mode, voice_on=voice_on,
            youtube_domains=youtube_domains,
            user_domains=user_domains, rule_max="19099",
            exclude_domains="ads.example.org\n" if excluded else "",
            exclude_ipset="198.51.100.0/24\n" if excluded else "",
        )
        data = argv_file.read_bytes()
        need(data.startswith(b"--port=19899\n"),
             f"{name}:PRODUCTION_GENERATOR_WRONG_DIVERT")
        need(b"--hostlist-auto=" not in data,
             f"{name}:OLD_GENERATION_INCORRECTLY_ACTIVATED_AUTO")
        need(not (old.static / "binaries/my/dvtws2").exists(),
             f"{name}:ENGINE_NOT_ACTUALLY_ABSENT")
        # Original emitter is NOT invoked for all/list. For auto it must
        # produce the native source map, never a test-constructed map.
        mapping = old.check_nonactivating(mapped, argv_file) if mode == "auto" else None
        if mode != "auto":
            need(not mapped.exists(), f"{name}:UNEXPECTED_OLD_SOURCE_MAP")
        normalized = data.decode("utf-8").replace(str(old.root), "{TMP_ROOT}")
        profiles = [] if mapping is None else [
            {key: row.get(key) for key in
             ("native_number", "role", "status", "selector", "hostlist",
              "source_number", "source_has_ipset")}
            for row in mapping["profiles"]
        ]
        # Use source-identical, *actual* emitted bytes before sanitization.
        row = {
            "mode": mode, "voice_on": voice_on,
            "sha256_original": file_hash(data),
            "sha256_normalized": file_hash(normalized.encode()),
            "size": len(data), "argc": len(normalized.split()),
            "native_profile_count": normalized.split().count("--new") + 1,
            "native_profiles": profiles,
            "engine_present": False,
            "rule_min": 19000, "rule_max": 19099,
            "manifest_present": (old.release / "manifest.json").is_file(),
            "manifest_reference_only": False,
        }
        if row["manifest_present"]:
            try:
                root = json.loads((old.release / "manifest.json").read_bytes())
            except (ValueError, UnicodeError):
                root = {}
            # Exact V5 root schema: active generation + immutable refs,
            # never hostlist text or arbitrary inline executable args.
            row["manifest_reference_only"] = (
                isinstance(root, dict)
                and root.get("schema") in (1, "1")
                and isinstance(root.get("generation"), str)
                and isinstance(root.get("refs"), dict)
                and "dvtws.args" in root["refs"]
                and "hostlists" not in root
                and "args" not in root
            )
        extra = {}
        if want_learning:
            need(mode == "auto" and mapping is not None,
                 f"{name}:SOURCE_MAPPING_REQUIRED")
            sys.path.insert(0, str(BACKEND))
            import auto_detect_origin_map as origin
            projection, proposal = origin.plan_learning_tier(
                mapping, data,
                owner_id=old.work.name,
                owner_candidate_sha256="d" * 64,
            )
            learners = [p for p in proposal["profiles"]
                        if p["role"] == "learning"]
            need([p["hostlist"] for p in learners] == EXPECTED_LIST,
                 f"{name}:REAL_LEARNING_FIRST_MATCH_ORDER_CHANGED")
            need(projection.startswith(data.split(b"\n", 1)[0]),
                 f"{name}:REAL_LEARNING_ORIGINAL_PREAMBLE_CHANGED")
            need(argv_file.read_bytes() == data,
                 f"{name}:PROJECTION_MUTATED_ORIGINAL_PRODUCER")
            extra["learning_count"] = len(learners)
            extra["fail_threshold_one_count"] = projection.count(
                b"--hostlist-auto-fail-threshold=1")
            extra["auto_selector_count"] = projection.count(
                b"--hostlist-auto=")
            extra["original_preserved"] = argv_file.read_bytes() == data
        return row, extra
    finally:
        old.doCleanups()


def invalid_case(fixture, name: str, strategy: str, mode: str) -> dict:
    old = fixture.OriginalSharedGeneration("runTest")
    old.setUp()
    try:
        try:
            old.build(strategy, mode=mode, rule_max="19099")
        except AssertionError:
            # Assertion originated in P2e after real shell producer nonzero.
            return {"name": name, "original_generator_rejected": True}
        raise ProbeFailure(name + ":INVALID_INPUT_ACCEPTED_BY_REAL_GENERATOR")
    finally:
        old.doCleanups()


def help_probe(argv: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="s03-cli-offline-") as tmp:
        path = Path(tmp) / "native-fd9-should-stay-absent"
        env = {**os.environ, "SCRIPT_DIR": str(SERVICE.parent),
               "BACKEND_DIR": str(BACKEND),
               "LIFECYCLE_LOCK_FILE": str(path),
               "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(
            ["/bin/sh", str(SERVICE), *argv],
            env=env, capture_output=True, text=True, timeout=12,
            cwd=ROOT, check=False)
        need(not path.exists(), "HELP_OR_UNSUPPORTED_CLI_MUTATED_FD9_FILE")
        return {"argv": argv, "rc": result.returncode,
                "stdout_bytes": len(result.stdout.encode()),
                "stderr_bytes": len(result.stderr.encode()),
                "no_fd9_io": True}


def disposable_native_status() -> dict:
    """Native source CLI on a DISPOSABLE engine-absent OPNsense, never owner.

    This read-only *test intent* observes the old Status lockfile mutation
    under a private path; no original FD9, kernel rules or installed engine
    are controlled. Requires explicit CI, FreeBSD root and environment opt-in.
    """
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("ZAPRET2_S03_DISPOSABLE_NATIVE") != "1"):
        raise ProbeFailure("STATUS_DISPOSABLE_FREEBSD_OPT_IN_REQUIRED")
    installed = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    child = Path("/var/run/dvtws2.pid")
    need(not installed.exists() and not installed.is_symlink()
         and not child.exists() and not child.is_symlink(),
         "STATUS_PROBE_REFUSES_INSTALLED_ENGINE_OR_CHILD")
    with tempfile.TemporaryDirectory(prefix="s03-status-only-") as tmp:
        fd9 = Path(tmp) / "status-must-not-create-fd9"
        env = {**os.environ, "SCRIPT_DIR": str(SERVICE.parent),
               "BACKEND_DIR": str(BACKEND),
               "LIFECYCLE_LOCK_FILE": str(fd9),
               "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(
            ["/bin/sh", str(SERVICE), "status", "--json"],
            env=env, capture_output=True, text=True, timeout=15,
            cwd=ROOT, check=False)
        try:
            response = json.loads(result.stdout)
        except ValueError:
            response = None
        return {
            "status_cli_exit": result.returncode,
            "private_fd9_created": fd9.exists() or fd9.is_symlink(),
            "json_status_valid": (
                isinstance(response, dict)
                and response.get("state") in
                ("RUNNING", "STOPPED", "INCOMPLETE", "FOREIGN_OR_UNVERIFIED")
            ),
            "stdout_bytes": len(result.stdout.encode()),
            "stderr_bytes": len(result.stderr.encode()),
            "real_engine_absent": True,
            "no_ordinary_start_or_kernel_write": True,
        }


def capture(*, native_status: bool = False) -> dict:
    fixture = load_original()
    cases = [
        ("implicit_all", STRATEGY, dict(mode="all")),
        ("implicit_list", STRATEGY, dict(mode="list")),
        ("implicit_auto", STRATEGY, dict(mode="auto")),
        ("youtube_explicit_list", EXPLICIT, dict(mode="list")),
        ("ordered_auto_voice", ORDERED, dict(mode="auto", voice_on=True,
                                            want_learning=True)),
        ("global_exclusions_auto", ORDERED, dict(mode="auto", excluded=True)),
        ("empty_strategy_all", "", dict(mode="all")),
        ("large_manual_list", EXPLICIT, dict(
            mode="list", youtube_domains=synthetic_sample("yt", 1024),
            user_domains=synthetic_sample("user", 1024))),
    ]
    matrix, extras = {}, {}
    for name, strategy, opts in cases:
        row, extra = one_original_run(fixture, name, strategy, **opts)
        matrix[name] = row
        if extra:
            extras[name] = extra
    # No assumed first-match from a hostname: actual qualified native
    # source/number sequence comes from the old producer map.
    native = matrix["ordered_auto_voice"]["native_profiles"]
    need([p["hostlist"] for p in native
          if p["status"] == "known-hostlist"] == EXPECTED_LIST,
         "ORIGINAL_KNOWN_SOURCE_ORDER_CHANGED")
    need(matrix["implicit_all"]["native_profile_count"] == 1,
         "TARGET_ALL_CHANGED_PROFILE_COUNT")
    need(matrix["implicit_list"]["native_profile_count"] == 3,
         "TARGET_LIST_CHANGED_PROFILE_COUNT")
    need(matrix["implicit_auto"]["native_profile_count"] == 3,
         "TARGET_AUTO_CHANGED_PROFILE_COUNT")
    need(matrix["empty_strategy_all"]["native_profile_count"] == 1,
         "EMPTY_ALLOWED_ORDINARY_STRATEGY_CHANGED")
    need(matrix["large_manual_list"]["size"] > 0,
         "LARGE_MANUAL_LIST_GENERATION_EMPTY")
    # Three categories are deliberately REAL producer invocations: empty
    # Target Mode and malformed placeholder must not be accepted as valid.
    invalid = [
        invalid_case(fixture, "bad_hostlist_selector",
                     "--filter-tcp=443\n<HOSTLIST:absent>\n--lua-desync=fake\n",
                     "auto"),
        invalid_case(fixture, "invalid_target_mode",
                     STRATEGY, "unsupported-mode"),
    ]
    help_global = help_probe(["--help"])
    help_reload = help_probe(["reload", "--help"])
    learning = extras["ordered_auto_voice"]
    need(learning["learning_count"] == 3
         and learning["auto_selector_count"] == 3
         and learning["original_preserved"],
         "UNEXPECTED_PRODUCTION_LEARNING_BASELINE")
    got_red = []
    if learning["fail_threshold_one_count"] != learning["learning_count"]:
        got_red.append("AUTO_LEARNING_FAIL_THRESHOLD_MISSING")
    if help_global["rc"] != 0:
        got_red.append("CLI_GLOBAL_HELP_UNIMPLEMENTED")
    if help_reload["rc"] != 0:
        got_red.append("CLI_RELOAD_HELP_UNIMPLEMENTED")
    if not matrix["ordered_auto_voice"]["manifest_reference_only"]:
        got_red.append("REFERENCE_MANIFEST_UNAVAILABLE")
    native = disposable_native_status() if native_status else None
    if native is not None:
        if native["private_fd9_created"]:
            got_red.append("STATUS_READONLY_FD9_SIDE_EFFECT")
        if not native["json_status_valid"]:
            got_red.append("STATUS_JSON_UNIMPLEMENTED")
    all_expected = list(EXPECTED_RED) + (list(NATIVE_EXPECTED_RED) if native is not None else [])
    return {
        "schema": SCHEMA,
        "scope": "S03_REAL_OLD_ORCHESTRATOR_SOURCE_ONLY_NO_ENGINE_NO_NATIVE_ACCEPTANCE",
        "source_baseline": "main 3742188bb2418627242099ab55ae1b83ad8a20bd",
        "source_builder": "orchestrator_build_release shared-candidate",
        "instrumentation": "existing P2e; real target_mode/profile_pipeline/Voice/source-map",
        "cases": matrix,
        "learning": extras,
        "invalid": invalid,
        "help": [help_global, help_reload],
        "observed_red": sorted(got_red),
        "expected_red": sorted(all_expected),
        "native_disposable_status": native,
        "not_tested": [
            "native FreeBSD/OPNsense, installed dvtws2, real IPFW packets",
            "real Config.xml and WAN-only G05->Lab G08",
            "PID birth/epoch and FD9/reused PID force kill",
            "status --json on installed/running engine (disposable engine-absent only)",
            "real GUI handler/tooltip and RU/EN HTTP",
            "Lab stage90/99 real restoration and upstream provider Auto traffic",
            "upstream manual reread/SIGHUP behavior (deliberately prohibited)",
        ],
    }


def verify(report: dict, target: bool) -> None:
    need(report.get("schema") == SCHEMA and
         report.get("scope") ==
         "S03_REAL_OLD_ORCHESTRATOR_SOURCE_ONLY_NO_ENGINE_NO_NATIVE_ACCEPTANCE",
         "SOURCE_BASELINE_REPORT_UNTRUSTED")
    cases = report.get("cases", {})
    need(isinstance(cases, dict)
         and {"implicit_all", "implicit_list", "implicit_auto",
              "ordered_auto_voice", "global_exclusions_auto",
              "empty_strategy_all", "large_manual_list",
              "youtube_explicit_list"} == set(cases),
         "ORIGINAL_MATRIX_INCOMPLETE")
    red = sorted(report.get("observed_red", []))
    if target:
        if red:
            raise ProbeFailure("EXPECTED_RED_FROM_REAL_PRODUCERS=" + ",".join(red))
        print("S03_TARGET_CONTRACT_GREEN=1")
    else:
        need(red == sorted(report.get("expected_red", [])),
             "EXPECTED_RED_SET_CHANGED_UPDATE_SPECIFIC_CONTRACT=" +
             ",".join(red))
        print("S03_EXPECTED_RED_VERIFIED=1")
        print("S03_FAILING_TARGET_ASSERTIONS=" + ",".join(red))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--capture", action="store_true")
    action.add_argument("--target", action="store_true")
    action.add_argument("--verify-red", action="store_true")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--disposable-native-status", action="store_true",
                        help="Only on root disposable FreeBSD CI; refuse installed engine")
    args = parser.parse_args()
    try:
        if args.capture:
            payload = capture(native_status=args.disposable_native_status)
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(payload, sort_keys=True, indent=2) + "\n",
                encoding="utf-8")
            print("S03_REAL_GENERATOR_CAPTURE=1")
            print("S03_BASELINE_CASES=" + str(len(payload["cases"])))
            print("S03_INVALID_REJECTIONS=" + str(len(payload["invalid"])))
            print("S03_OBSERVED_RED=" + ",".join(payload["observed_red"]))
        else:
            payload = json.loads(args.report.read_text(encoding="utf-8"))
            verify(payload, target=args.target)
    except (AssertionError, ProbeFailure, ValueError, OSError,
            subprocess.TimeoutExpired) as exc:
        # Never leak raw engine args, Config XML or user domains in CI log.
        code = str(exc)
        if not (code.startswith("EXPECTED_RED_FROM_REAL_PRODUCERS=") or
                code.startswith("S03_") or code.isupper() or
                "ORIGINAL" in code or "TARGET" in code or
                "GENERATOR" in code or "HELP" in code or
                "INVALID" in code):
            code = type(exc).__name__
        print("S03_FAIL=" + code[:440], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
