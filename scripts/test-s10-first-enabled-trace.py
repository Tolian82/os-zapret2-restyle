#!/usr/bin/env python3
"""Portable S0 diagnostic transport: exact source, no native authority or mutation."""
import ast
import base64
import contextlib
import io
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace, ModuleType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "src/opnsense/scripts/OPNsense/Zapret"


def functions(source, names):
    nodes = [node for node in ast.parse(source).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    scope = {"json": json, "sys": sys}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<diagnostic-functions>", "exec"), scope)
    return scope


native = functions((NATIVE / "backend/neutral_schema3_quiescent_preimage.py").read_text(),
                   ("_first_enabled_checkpoint", "_relay_first_enabled_trace", "_relay_first_recovery_trace"))
source = (ROOT / "scripts/stage2-opnsense-g03-native-prepared.py").read_text()
children = [node.value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and "def first_trace_lines(raw):" in node.value]
assert len(children) == 1
fixture = functions(children[0], ("first_trace_lines", "first_reply_diagnostic"))
php = (NATIVE / "shared_apply_config.php").read_text()
helpers = php[php.index("    private static function openFirstEnabledTrace()"):
              php.index("    private static function originalLockedFileEvidence(")]
php_probe = 'class Probe {\n' + helpers + r'''
    public static function run(string $raw): int {
        $trace = self::openFirstEnabledTrace();
        if (!is_resource($trace) || file_exists(stream_get_meta_data($trace)['uri'])) { return 1; }
        $proc = proc_open([PHP_BINARY, '-r', 'fwrite(STDERR, base64_decode($argv[1], true)); echo "receipt\n"; exit(70);', base64_encode($raw)],
            [0=>['file','/dev/null','r'],1=>['pipe','w'],2=>$trace], $pipes);
        if (!is_resource($proc)) { return 1; }
        $receipt = stream_get_contents($pipes[1]);
        fclose($pipes[1]);
        $code = proc_close($proc);
        fwrite(STDERR, self::firstEnabledTrace($trace));
        @fclose($trace);
        fwrite(STDOUT, $receipt);
        return $code;
    }
}
exit(Probe::run(base64_decode($argv[1], true)));
'''
mark = b"S10_FIRST_TRACE="
for raw, wanted in (
    (mark+b"D03\nprivate\n"+mark+b"D09\n"+mark+b"D20\n", (b"D03", b"D09", b"D20")),
    (mark+b"D99\n"+mark+b"D09 private\n"+mark+b"D09\r\n"+mark+b"D10", ()),
    (mark+b"D03\n"+b"x"*8193, ()),
    ((mark+b"D03\n")*70, (b"D03",)*64),
    (b"prefix "+mark+b"D11\n"+mark+b"D30\n", (b"D30",)),
):
    expected = b"".join(mark+stage+b"\n" for stage in wanted)
    output = io.StringIO()
    with contextlib.redirect_stderr(output):
        native["_relay_first_enabled_trace"](raw)
    assert output.getvalue().encode() == expected
    result = subprocess.run(["php", "-r", php_probe, base64.b64encode(raw).decode()],
                            capture_output=True, check=False, timeout=10)
    assert (result.returncode, result.stdout, result.stderr) == (70, b"receipt\n", expected)

# First Config recovery transports only complete existing location markers.
for raw, expected in (
    (b"S10_MANAGED_TRACE=M11:1300\nS10_MANAGED_TRACE=P01:1090\n", b"S10_MANAGED_TRACE=M11:1300\nS10_MANAGED_TRACE=P01:1090\n"),
    (b"private data\nS10_MANAGED_TRACE=M11:1300 private\nS10_MANAGED_TRACE=P01:1090\r\nS10_MANAGED_TRACE=M11:1301", b""),
    (b"S10_MANAGED_TRACE=M15:1\nS10_MANAGED_TRACE=P04:1\nS10_MANAGED_TRACE=M11:0001\nS10_MANAGED_TRACE=M11:123456\n", b""),
    (b"S10_MANAGED_TRACE=M11:1\n" * 70, b"S10_MANAGED_TRACE=M11:1\n" * 64),
    (b"S10_MANAGED_TRACE=M11:1\n" + b"x" * 8193, b""),
    (None, b""),
):
    output = io.StringIO()
    with contextlib.redirect_stderr(output):
        native["_relay_first_recovery_trace"](raw)
    assert output.getvalue().encode() == expected
print("PASS: bounded first recovery source locations only")

raw = mark+b"D00\n"+mark+b"D03\n"+mark+b"D31\nERROR: original managed Config outcome requires journal review\n"
assert [line[-3:] for line in fixture["first_trace_lines"](raw)] == [b"D00", b"D03", b"D31"]
assert fixture["first_reply_diagnostic"](SimpleNamespace(returncode=70, stdout=b"", stderr=raw),
    {"phase": "activating"}, {"candidate": "private", "changed_fields": []}).endswith("stderr:review")
assert fixture["first_trace_lines"](mark+b"D99\n"+mark+b"D09 private\n"+mark+b"D10") == ()
assert fixture["first_trace_lines"]((mark+b"D00\n")*100) == (mark+b"D00",)*64

# Managed successor: the first trace alone used to hide the decisive inner error.
managed = functions((NATIVE / "backend/auto_detect_effective_known.py").read_text(),
                    ("_managed_refusal_trace",))
managed_fixture = functions(children[0], ("first_trace_lines", "managed_trace_lines",
    "first_reply_diagnostic", "coordinate_managed_diagnosed"))
inner = {"__name__": "neutral_schema3_previous_physical"}
exec(compile('def refuse():\n    raise ValueError("private domain and path")\n', "<inner>", "exec"), inner)
outer = {"__name__": "neutral_shared_apply_source_gate", "refuse": inner["refuse"]}
exec(compile('def call():\n    try:\n        refuse()\n    except ValueError:\n        raise RuntimeError("private wrapper") from None\n', "<outer>", "exec"), outer)
output = io.StringIO()
with contextlib.redirect_stderr(output):
    try:
        outer["call"]()
    except RuntimeError as error:
        managed["_managed_refusal_trace"](error)
        assert str(error) == "private wrapper"
    else:
        raise AssertionError("refusal lost")
expected = b"S10_MANAGED_TRACE=M01:5\nS10_MANAGED_TRACE=M01:3\nS10_MANAGED_TRACE=M02:2\n"
assert output.getvalue().encode() == expected
raw = (mark+b"D03\n"+expected+b"S10_MANAGED_TRACE=M15:2\nS10_MANAGED_TRACE=M01:0001\n"
       b"S10_MANAGED_TRACE=M02:2 private\nS10_MANAGED_TRACE=M03:999999\nS10_MANAGED_TRACE=M01:4")
result = subprocess.run(["php", "-r", php_probe, base64.b64encode(raw).decode()],
                        capture_output=True, check=False, timeout=10)
assert (result.returncode, result.stdout, result.stderr) == (70, b"receipt\n", mark+b"D03\n"+expected)
# A native PHP exception and its previous exception expose source locations,
# not their messages, arguments, absolute paths, or Config.
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "apply_settings.php"
    path.write_text('<?php\ntry { throw new RuntimeException("private inner"); }\n'
                    'catch (Throwable $e) { throw new RuntimeException("private outer", 0, $e); }\n')
    error_probe = 'class Probe {\n' + helpers + r'''
    public static function run(string $file): int {
        try { require $file; } catch (Throwable $error) {
            self::managedPhpRefusalTrace($error);
            return 70;
        }
        return 0;
    }
}
exit(Probe::run($argv[1]));
'''
    result_php = subprocess.run(["php", "-r", error_probe, str(path)], capture_output=True,
                                check=False, timeout=10)
    assert (result_php.returncode, result_php.stdout, result_php.stderr) == (
        70, b"", b"S10_MANAGED_TRACE=P02:3\nS10_MANAGED_TRACE=P02:2\n")
raw = (b"S10_MANAGED_STEP=write\n"+result.stderr+b"S10_MANAGED_TRACE=P02:123\n"
       b"ERROR: original managed Config outcome requires journal review\n")
assert managed_fixture["managed_trace_lines"](raw) == tuple((b"S10_MANAGED_STEP=write\n"+mark+b"D03\n"+expected+b"S10_MANAGED_TRACE=P02:123\n").splitlines())
assert managed_fixture["managed_trace_lines"](b"S10_MANAGED_STEP=invalid\nS10_MANAGED_TRACE=P04:1\nS10_MANAGED_TRACE=M02:1") == ()
assert managed_fixture["managed_trace_lines"](b"S10_MANAGED_TRACE=M01:1\n"*80) == (b"S10_MANAGED_TRACE=M01:1",)*64
import types
module = types.ModuleType("neutral_schema3_quiescent_preimage")
old_module = sys.modules.get(module.__name__)
sys.modules[module.__name__] = module
try:
    reply = SimpleNamespace(returncode=70, stdout=b"", stderr=raw)
    calls = []
    def join(command, **kwargs):
        calls.append((command, kwargs))
        return reply
    module._run_bound_restore_joined = join
    def coordinate(op, wire):
        assert wire == b"unchanged input"
        assert module._run_bound_restore_joined(["php", "managed-apply", op, "strategies"], pass_fds=(9,)) is reply
        assert module._run_bound_restore_joined(["php", "unrelated", op, "strategies"]) is reply
        raise RuntimeError("original refusal")
    for phase in ("prepared", "managed-writing", "managed-config-saving", "committed"):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            try:
                managed_fixture["coordinate_managed_diagnosed"]("id", b"unchanged input",
                    SimpleNamespace(read=lambda: {"phase": phase}),
                    {"candidate": "private", "changed_fields": ["hostlist.youtubedomains"]}, coordinate)
            except RuntimeError as error:
                assert str(error) == "original refusal"
            else:
                raise AssertionError("original refusal lost")
        assert module._run_bound_restore_joined is join
        lines = output.getvalue().splitlines()
        assert lines[-1] == "G03_MANAGED_REPLY=rc:70;receipt:empty;wal:"+phase+";stderr:review"
        assert lines[:2] == ["G03_MANAGED_STEP=write", "G03_MANAGED_TRACE=D03"]
        assert lines.count("G03_MANAGED_STEP=write") == 1
        assert "G03_MANAGED_TRACE=M02:2" in lines and "G03_MANAGED_TRACE=P02:123" in lines
        assert "private" not in output.getvalue()
    assert len(calls) == 8
finally:
    if old_module is None:
        del sys.modules[module.__name__]
    else:
        sys.modules[module.__name__] = old_module
print("PASS: managed refusal chain, exact PHP filter, four WAL phases and original joined call preserved")

shell = (NATIVE / "backend/apply_runtime.sh").read_text()
activate = shell[shell.index("apply_runtime_activate()\n{"):
                 shell.index("\n\n# Private forward seam", shell.index("apply_runtime_activate()\n{"))]
service = (NATIVE / "zapret_service.sh").read_text()
route = service[service.index("        shared-apply-first-enabled-physical)"):
                service.index("        extra-resources-preview-saved)", service.index("        shared-apply-first-enabled-physical)"))]
mock = '''
ACTIVE_DIR=$1; PYTHON_RUNTIME=$2; FAIL=$3; export FAIL
# FreeBSD 15 expr has no GNU length operator. Any attempt is an error.
expr() { echo "unexpected external expr" >&2; return 2; }
BACKUP_ROOT=$1; BACKEND_DIR=$1; APPLY_IPFW_INSTALLED=0; APPLY_OLD=-; APPLY_NEW=-
apply_runtime_preflight() { APPLY_CANDIDATE=$1; APPLY_NEW_RUNNING=$2; APPLY_OLD_RUNNING=0; [ "$FAIL" != D14 ]; }
atomic_install_tree() { [ "$FAIL" != D15 ]; }
apply_runtime_clear() { :; }
apply_runtime_original_launcher_once() { [ "$FAIL" != D16 ]; }
apply_runtime_abort_after_launcher_failure() { return 70; }
apply_runtime_abort() { return 70; }
firewall_shared_runtime() { case "$1" in install) [ "$FAIL" != D17 ] ;; verify-staged) [ "$FAIL" != D18 ] ;; *) return 0 ;; esac; }
supervisor_start() { [ "$FAIL" != D19 ]; }
'''
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    (temp / "dvtws.args").write_text("--filter-tcp=443\n")
    guard = temp / "guard"
    guard.write_text('#!/bin/sh\n[ "$FAIL" != guard ] || exit 69\nprintf "first-enabled-shell=qualified\\n"\n')
    guard.chmod(0o700)
    script = temp / "trace.sh"
    script.write_text(activate+"\n"+mock+'\nroute() { case "$1" in\n'+route+'esac; }\n'+
        "route shared-apply-first-enabled-physical "+"a"*32+" "+"b"*64+" lo0\n")
    subprocess.run(["sh", "-n", str(script)], check=True)
    for failure in ("guard", "D14", "D15", "D16", "D17", "D18", "D19", "none"):
        result = subprocess.run(["sh", str(script), directory, str(guard), failure],
                                capture_output=True, check=False, timeout=10)
        expected = [mark+b"D12"] + ([] if failure == "guard" else
                    [mark+b"D13", mark+(b"D20" if failure == "none" else failure.encode())])
        assert result.stderr.splitlines() == expected, failure
        assert (result.returncode, result.stdout) == ((0, b"first-enabled-physical=activated\n")
                if failure == "none" else (70, b"")), failure
print("PASS: finite first-enabled trace, real PHP join, 7 shell refusals + 1 success; no raw stderr or changed receipts")


def installed_proof_trace_test(source):
    """Each independent failed proof gets a distinct source line; all still refuse."""
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                and node.name == "_attest_bound_managed_installed_locked")
    class Refused(RuntimeError):
        pass
    sha = lambda data: hashlib.sha256(data).hexdigest()
    seal = ModuleType("shared_apply_seal")
    seal._stat = lambda path, owner, **kw: path.stat()
    with tempfile.TemporaryDirectory() as directory:
        active = Path(directory)
        (active / "managed").mkdir()
        target = active / "managed" / "list.txt"
        old, new = b"old.example\n", b"new.example\n"
        target.write_bytes(new)
        def identity(st):
            return [st.st_dev, st.st_ino, st.st_ctime_ns, st.st_mtime_ns,
                    st.st_size, st.st_mode, st.st_uid, st.st_gid, st.st_nlink]
        original = identity(target.stat())
        seal._release_hash = lambda path, owner: sha(target.read_bytes())
        store = SimpleNamespace(owner=target.stat().st_uid)
        scope = {"Path": Path, "DestinationRefused": Refused, "_sha": sha,
                 "_target": lambda path, owner: (path.read_bytes(), path.stat()),
                 "_target_identity": identity,
                 "_managed_write_images": lambda *args: (old, None, new, None, None, sha(new))}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<installed-proof>", "exec"), scope)
        attest = scope[node.name]
        row = {"name": target.name, "before_sha256": sha(old), "after_sha256": sha(new),
               "installed": original}
        def observe(changes=None, *, bad_tree=False):
            with patch.dict(sys.modules, {seal.__name__: seal}), patch.object(seal, "_release_hash",
                    (lambda *args: "0" * 64) if bad_tree else seal._release_hash):
                try:
                    attest(store, {"managed": {**row, **(changes or {})}}, parent=active, active=active)
                except Refused as error:
                    assert str(error) == "original_managed_installed_image_changed"
                    trace = error.__traceback__
                    while trace.tb_next is not None:
                        trace = trace.tb_next
                    return trace.tb_lineno
                return None
        assert observe() is None
        lines = [observe({"before_sha256": "0" * 64})]
        for index in (1, 2, 3, 4, 5):
            changed = original.copy()
            changed[index] += 1
            lines.append(observe({"installed": changed}))
        lines.append(observe(bad_tree=True))
        target.write_bytes(b"foreign.example\n")
        lines.append(observe())
        assert None not in lines and len(set(lines)) == len(lines), lines
        return lines

installed_proof_trace_test((NATIVE / "backend/auto_detect_destination_commit.py").read_text())
print("PASS: managed installed proof has eight distinct refusal locations; exact valid file accepted")
