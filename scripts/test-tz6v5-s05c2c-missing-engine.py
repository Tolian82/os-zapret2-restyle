#!/usr/bin/env python3
"""S05c2c: execute real original missing-engine function, with negative guards."""
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
S = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
P = (ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php").read_text()
G = (ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
FIXED = "zapret-api-lifecycle-v1:start:refused:engine-not-installed"
RESTART_FIXED = "zapret-api-lifecycle-v1:restart:refused:engine-not-installed"

def need(ok, why):
    if not ok:
        raise SystemExit("S05C2C_REFUSED=" + why)

a = S.index("ensure_runtime_components()\n{")
b = S.index("\nrefresh_generated_configuration()\n{", a)
original = S[a:b]
need(S.count(FIXED) == 1, "ONE_PRODUCER")
need("_service_receipt_action" in original and
     '[ ! -e ' in original and '[ ! -L ' in original,
     "PRIVATE_ACTUAL_ABSENCE_ONLY")
need(P.count(FIXED) == 1 and "trim($raw) === '" + FIXED + "'" in P and
     "strlen($raw) <= 128" in P and
     "Zapret2 Start refused: engine is not installed." in P, "PHP_BOUND")
need("Zapret2 Start refused: engine is not installed." in G and
     "Движок Zapret2 не установлен." in G and
     "receipt.verified !== true" in G, "RU_EN_STRICT_GUI")
need(S.count(RESTART_FIXED) == 1 and P.count(RESTART_FIXED) == 1 and
     "trim($raw) === '" + RESTART_FIXED + "'" in P and
     "Zapret2 Restart refused: engine is not installed." in P, "RESTART_HTTP_BOUND")
need("service_api_terminal_receipt()" in S and
     "service_with_lifecycle_lock()" in S, "ORIGINAL_FD9_UNCHANGED")

with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    absent = t / "missing-dvtws2"
    executable = t / "executable-dvtws2"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o700)
    dangling = t / "dangling-dvtws2"
    dangling.symlink_to(t / "never-created")
    for name, binary, action, rc, stdout in (
        ("private-absent", absent, "start", 1, FIXED + "\n"),
        ("public-absent", absent, "", 1, ""),
        ("restart-absent", absent, "restart", 1, RESTART_FIXED + "\n"),
        ("foreign-symlink", dangling, "start", 1, ""),
        ("foreign-symlink-restart", dangling, "restart", 1, ""),
        ("present-executable", executable, "start", 0, ""),
    ):
        script = (original + "\nDVTWS_BIN=" + shlex.quote(str(binary)) +
                  "\n_service_receipt_action=" + shlex.quote(action) +
                  "\nensure_runtime_components\n")
        result = subprocess.run(["/bin/sh"], input=script, capture_output=True,
                                text=True, timeout=5)
        need(result.returncode == rc and result.stdout == stdout,
             "EXEC_" + name)
        need(not result.stderr if rc == 0 else
             "ERROR: zapret2 runtime is not installed" in result.stderr,
             "STDERR_" + name)

print("S05C2C_ACTUAL_ORIGINAL_PRODUCER=PASS")
