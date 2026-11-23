#!/usr/bin/env python3
"""TZ6v5 S03e1: real legacy public CLI strict-options expected RED + GUI source route.

Native mode is allowed ONLY on cold disposable FreeBSD CI, BEFORE any engine
installation. No real start/stop/restart reaches the dispatcher: mutating
verbs are invoked ONLY while the actual ORIGINAL lockf FD9 is provably held
on a private temp path; all must return BUSY. Other commands are plain
status/unsupported/help, with exact Config/IPFW before-after fingerprints.
This is not a V5-14/16 implementation and not a native GUI locale proof.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
SERVICE = SCRIPT / "zapret_service.sh"
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
PID = Path("/var/run/dvtws2.pid")
CONFIG = Path("/conf/config.xml")
IPFW = Path("/sbin/ipfw")
PS = Path("/bin/ps")
LOCKF = Path("/usr/bin/lockf")
CONTROLLER = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php"
GENERAL = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"
VOICE = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt"
ACTION = ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf"


class Refusal(RuntimeError):
    pass


def check(ok: bool, code: str) -> None:
    if not ok:
        raise Refusal(code)


def cmd(args: list[str], *, env=None, timeout=10) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True,
                          env=env, timeout=timeout, check=False)


def file_digest(path: Path) -> tuple[bool, str]:
    check(not path.is_symlink(), "S03E_SYMLINK_" + path.name)
    if not path.exists():
        return False, ""
    check(path.is_file(), "S03E_FOREIGN_FILE_TYPE_" + path.name)
    return True, hashlib.sha256(path.read_bytes()).hexdigest()


def ipfw_snapshot() -> tuple[int, str, str]:
    # Cold OPNsense may not yet have the ipfw kernel module loaded.
    # Like the already accepted S03d genuine native test, retain the
    # exact (rc, stdout, stderr) as a pre/post NON-MUTATION witness.
    # Requiring rc0 here would falsely reject a healthy engine-absent
    # disposable guest before the actual CLI tests.
    p = cmd([str(IPFW), "-q", "list"])
    return p.returncode, p.stdout, p.stderr


def source_routes() -> dict:
    """Read updated PHP/Volt/configd routes. SOURCE only; old CLI remains RED."""
    files = {name: path.read_text(encoding="utf-8") for name, path in
             (("controller", CONTROLLER), ("general", GENERAL),
              ("voice", VOICE), ("actions", ACTION),
              ("service", SERVICE))}
    c, g, v, a, s = (files[name] for name in
                     ("controller", "general", "voice", "actions", "service"))
    for verb in ("start", "stop", "restart"):
        check(("[{verb}]".format(verb=verb)) in a and
              ("/zapret_service.sh " + verb) in a,
              "S03E_CONFIGD_ROUTE_MISSING_" + verb)
    check("public function startAction(): array" in c and
          "configdRun('zapret wan_preflight'" in c and
          "return parent::startAction();" in c,
          "S03E_CONTROLLER_START_ROUTE_CHANGED")
    check("gettext('Select a WAN interface')" in c and
          "gettext('Selected WAN interface is not assigned or unavailable')" in c,
          "S03E_CONTROLLER_WAN_GETTEXT_CHANGED")
    check("$('#zapretServiceControl').off('click').on('click'" in g and
          "url: '/api/zapret/service/' + action" in g and
          "localizeStrategiesApplyError(message)" in g,
          "S03E_STRATEGIES_PRODUCER_CONSUMER_CHANGED")
    check("const isRussian" in g and
          "Не удалось запустить Zapret2. Проверьте WAN интерфейс." in g and
          "Zapret2 could not be started. Check the WAN interface." in g,
          "S03E_STRATEGIES_RU_EN_FALLBACK_MISSING")
    # After S03e2 owner approval, Voice no longer advertises lifecycle
    # Start/Stop. This updates only source observations; the original CLI
    # RED fixture below still executes unmodified actual shell handlers.
    check('id="voiceServiceControl"' not in v and
          "$('#voiceServiceControl').on('click'" not in v and
          "url:'/api/zapret/service/' + action" not in v and
          "voiceControlPending" not in v and
          "voiceServiceState" in v and
          "voiceIPFWState" in v and
          "id=\"voiceApply\"" in v,
          "S03E_VOICE_RETIRED_BUTTON_SOURCE_CONTRACT_FAILED")
    gstart = g.index("$('#zapretServiceControl').off('click').on('click'")
    gend = g.index("$('#zapretReleaseApply').off('click').on('click'", gstart)
    gen_handler = g[gstart:gend]
    check("currentServiceState === 'started' ? 'stop' : 'start'" in gen_handler and
          ".fail(function(xhr)" in gen_handler and
          "Не удалось запустить Zapret2." in gen_handler and
          "Не удалось остановить Zapret2." in gen_handler and
          "Zapret2 could not be stopped." in gen_handler and
          "action === 'stop'" in gen_handler,
          "S03E_STRATEGIES_START_STOP_ACTION_FALLBACK_SOURCE_CHANGED")
    check("case \"\u0024{1:-}\" in" in s and
          "shared_apply_status_service" in s and
          "service_with_lifecycle_lock" in s,
          "S03E_SERVICE_SOURCE_BASELINE_CHANGED")
    results = {
        "configd_start_stop_restart_paths_source": True,
        "strategies_start_stop_ajax_failure_ru_en_source": True,
        "voice_lifecycle_button_retired_source": True,
        "controller_wan_gettext_to_parent_start_source": True,
        "strategies_stop_fallback_action_specific_source": True,
        "native_gui_click_or_translation_render_not_claimed": True,
    }
    print("S03E_SOURCE_ONLY_LIFECYCLE_ROUTES=" +
          json.dumps(results, sort_keys=True, ensure_ascii=False), flush=True)
    return results


def native_preflight() -> None:
    # BEFORE ANY process/file/kernel calls. Not runnable on owner systems.
    check(sys.platform.startswith("freebsd") and os.geteuid() == 0,
          "S03E_FREEBSD_ROOT_ONLY")
    check(os.environ.get("GITHUB_ACTIONS") == "true" and
          os.environ.get("ZAPRET2_S03E_DISPOSABLE_NATIVE") == "1" and
          Path("/usr/local/opnsense").is_dir(),
          "S03E_NATIVE_DISPOSABLE_OPT_IN_REQUIRED")
    check(all(x.is_file() for x in (SERVICE, IPFW, PS, LOCKF)),
          "S03E_NATIVE_SOURCE_TOOL_MISSING")
    check(not ENGINE.exists() and not ENGINE.is_symlink() and
          not PID.exists() and not PID.is_symlink(),
          "S03E_REFUSE_ANY_INSTALLED_OR_OWNED_DVTWS")
    ps = cmd([str(PS), "-ax", "-o", "command="])
    check(ps.returncode == 0 and
          not any("binaries/my/dvtws2" in x or
                  "strategy_lab_worker.sh" in x
                  for x in ps.stdout.splitlines()),
          "S03E_REFUSE_LIVE_ENGINE_OR_LAB_WORKER")


def invoke(args: list[str], env: dict, timeout: float = 10):
    return cmd(["/bin/sh", str(SERVICE), *args], env=env, timeout=timeout)


def assert_foreign_same(before_config, before_ipfw) -> None:
    check(file_digest(CONFIG) == before_config and
          ipfw_snapshot() == before_ipfw and
          not ENGINE.exists() and not ENGINE.is_symlink() and
          not PID.exists() and not PID.is_symlink(),
          "S03E_FOREIGN_CONFIG_IPFW_OR_ENGINE_MUTATION")


def native_cli() -> dict:
    native_preflight()
    before_config, before_ipfw = file_digest(CONFIG), ipfw_snapshot()
    with tempfile.TemporaryDirectory(prefix="tz6v5-s03e-native-", dir="/tmp") as dirname:
        private = Path(dirname)
        lock = private / "original-fd9.lock"
        env = {**os.environ, "SCRIPT_DIR": str(SCRIPT),
               "BACKEND_DIR": str(SCRIPT / "backend"),
               "LIFECYCLE_LOCK_FILE": str(lock),
               "LOCKF_BIN": str(LOCKF),
               "PYTHONDONTWRITEBYTECODE": "1"}
        # These commands are never mutating verbs and must never reach FD9
        # in the current baseline. They currently emit old usage rc64.
        unsupported = (
            ("--help",), ("reload", "--help"), ("reload", "--check"),
            ("reload", "--check", "--json"), ("reload", "--force"),
            ("unknown-verb",),
        )
        for args in unsupported:
            p = invoke(list(args), env)
            check(p.returncode == 64 and
                  "usage: zapret_service.sh" in p.stderr and
                  not lock.exists(),
                  "S03E_UNSUPPORTED_USAGE_RED_CHANGED_" + "_".join(args))
            assert_foreign_same(before_config, before_ipfw)
        # Status is genuinely read-only for Config and kernel but still
        # OPENS/TRUNCATES the private original FD9 lock file in old code.
        plain = invoke(["status"], env)
        check(plain.returncode == 1 and
              "zapret is not running" in plain.stdout and lock.exists(),
              "S03E_PLAIN_COLD_STATUS_BASELINE_CHANGED")
        status_cases = (
            ("--json",), ("--help",), ("--force",),
            ("--json", "--json"), ("--unknown",),
        )
        for opts in status_cases:
            p = invoke(["status", *opts], env)
            check((p.returncode, p.stdout, p.stderr) ==
                  (plain.returncode, plain.stdout, plain.stderr),
                  "S03E_OLD_STATUS_UNCHECKED_OPTIONS_RED_CHANGED_" +
                  "_".join(opts))
            assert_foreign_same(before_config, before_ipfw)
        try:
            json.loads(invoke(["status", "--json"], env).stdout)
        except ValueError:
            pass
        else:
            raise Refusal("S03E_LEGACY_STATUS_UNEXPECTEDLY_VALID_JSON")
        # Positive control of real FreeBSD descriptor-only lockf.
        positive = cmd(["/bin/sh", "-c",
                        'exec 9>"$1"; /usr/bin/lockf -s -t 0 9',
                        "s03e-positive-fd9", str(lock)])
        check(positive.returncode == 0,
              "S03E_FD9_POSITIVE_CONTROL_FAILED")
        holder = subprocess.Popen(
            ["/bin/sh", "-c",
             'exec 9>"$1"; /usr/bin/lockf -s -t 0 9 || exit $?; /bin/sleep 90',
             "s03e-lock-holder", str(lock)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            ready = False
            for _ in range(30):
                check(holder.poll() is None, "S03E_FD9_OWNER_EXITED")
                contender = cmd(
                    ["/bin/sh", "-c",
                     'exec 9>"$1"; /usr/bin/lockf -s -t 0 9',
                     "s03e-lock-contender", str(lock)])
                if contender.returncode != 0:
                    ready = True
                    break
                time.sleep(0.1)
            check(ready, "S03E_FD9_BUSY_NOT_VERIFIED")
            # Even --help is routed THROUGH the real FD9 in the old CLI.
            # No Start/Stop/Restart CAN reach the dispatcher. Launch these
            # concurrent on the same verified BUSY lock, otherwise each
            # native timeout would take 30 s serially.
            blocked = [
                ("start", "--help"),
                ("stop", "--help"),
                ("restart", "--help"),
                ("start", "--force", "--force"),
                ("stop", "--force", "--force"),
                ("restart", "--force", "--force"),
                ("start", "--unknown"),
                ("stop", "--check"),
                ("status", "--help"),
            ]
            pending = [subprocess.Popen(["/bin/sh", str(SERVICE), *args],
                       env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True)
                       for args in blocked]
            try:
                for i, p in enumerate(pending):
                    try:
                        out, err = p.communicate(timeout=39)
                    except subprocess.TimeoutExpired as exc:
                        raise Refusal("S03E_BUSY_CLI_HUNG_" +
                                      "_".join(blocked[i])) from exc
                    check(p.returncode == 75 and
                          not out.strip() and
                          (blocked[i][0] == "status" or
                           "another zapret lifecycle operation is already running" in err),
                          "S03E_OLD_CLI_LOCKS_BEFORE_PARSING_" +
                          "_".join(blocked[i]) + "_rc_" + str(p.returncode))
                check(holder.poll() is None, "S03E_FD9_OWNER_LEFT_BEFORE_DENIALS")
                assert_foreign_same(before_config, before_ipfw)
            finally:
                for p in pending:
                    if p.poll() is None:
                        p.terminate()
                        try:
                            p.communicate(timeout=2)
                        except subprocess.TimeoutExpired:
                            p.kill()
                            p.communicate(timeout=2)
        finally:
            if holder.poll() is None:
                holder.terminate()
                try:
                    holder.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    holder.kill()
                    holder.wait(timeout=2)
    assert_foreign_same(before_config, before_ipfw)
    result = {
        "unsupported_reload_and_global_help_usage_rc64": len(unsupported),
        "status_ignored_options_identical_to_plain": len(status_cases),
        "status_json_not_json_and_private_fd9_created": True,
        "private_real_fd9_busy_rejects_unparsed_cli_rc75": len(blocked),
        "config_ipfw_engine_unchanged": True,
        "native_gui_locale_clicks_not_claimed": True,
        "no_mutating_verb_reached_dispatch": True,
    }
    print("S03E_NATIVE_LEGACY_PUBLIC_CLI_RED=" + json.dumps(result, sort_keys=True))
    print("S03E_ACTUAL_ORIGINAL_SERVICE_CLI_EXPECTED_RED=PASS")
    print("S03E_NEW_CLI_HELP_JSON_RELOAD_FORCE_NOT_IMPLEMENTED=1")
    return result


def main() -> None:
    source_routes()
    if sys.argv[1:] == ["--source-routes"]:
        print("S03E_SOURCE_ROUTE_ONLY_PASS")
        return
    if sys.argv[1:] != ["--native"]:
        raise Refusal("S03E_USAGE_SOURCE_ROUTES_OR_NATIVE")
    native_cli()


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, ValueError, subprocess.TimeoutExpired) as ex:
        reason = str(ex)
        if not reason.startswith("S03E_"):
            reason = type(ex).__name__
        print("S03E_FAIL=" + reason[:230], file=sys.stderr)
        raise SystemExit(1)
