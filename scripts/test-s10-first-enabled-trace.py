#!/usr/bin/env python3
"""Portable S0 diagnostic transport: exact source, no native authority or mutation."""
import ast
import base64
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "src/opnsense/scripts/OPNsense/Zapret"


def functions(source, names):
    nodes = [node for node in ast.parse(source).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    scope = {"json": json}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<diagnostic-functions>", "exec"), scope)
    return scope


native = functions((NATIVE / "backend/neutral_schema3_quiescent_preimage.py").read_text(),
                   ("_first_enabled_checkpoint", "_relay_first_enabled_trace"))
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

raw = mark+b"D00\n"+mark+b"D03\n"+mark+b"D31\nERROR: original managed Config outcome requires journal review\n"
assert [line[-3:] for line in fixture["first_trace_lines"](raw)] == [b"D00", b"D03", b"D31"]
assert fixture["first_reply_diagnostic"](SimpleNamespace(returncode=70, stdout=b"", stderr=raw),
    {"phase": "activating"}, {"candidate": "private", "changed_fields": []}).endswith("stderr:review")
assert fixture["first_trace_lines"](mark+b"D99\n"+mark+b"D09 private\n"+mark+b"D10") == ()
assert fixture["first_trace_lines"]((mark+b"D00\n")*100) == (mark+b"D00",)*64

shell = (NATIVE / "backend/apply_runtime.sh").read_text()
activate = shell[shell.index("apply_runtime_activate()\n{"):
                 shell.index("\n\n# Private forward seam", shell.index("apply_runtime_activate()\n{"))]
service = (NATIVE / "zapret_service.sh").read_text()
route = service[service.index("        shared-apply-first-enabled-physical)"):
                service.index("        extra-resources-preview-saved)", service.index("        shared-apply-first-enabled-physical)"))]
mock = '''
ACTIVE_DIR=$1; PYTHON_RUNTIME=$2; FAIL=$3; export FAIL
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
