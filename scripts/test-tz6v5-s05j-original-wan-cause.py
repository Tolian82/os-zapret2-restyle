#!/usr/bin/env python3
"""S05j: real original WAN-first function and exact private HTTP refusal."""
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
S = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
P = (ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php").read_text()
G = (ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
N = (ROOT / "scripts/test-tz6v5-s03e3-native-wan-refusal.py").read_text()

def need(ok, reason):
    if not ok:
        raise SystemExit("S05J_SOURCE_REFUSED=" + reason)

start = S.index("wan_first_service()\n{")
end = S.index("\nensure_runtime_components()\n{", start)
original = S[start:end]
need("service_wan_first_private()\n{" in original and
     S.count("service_wan_first_private start require") == 1 and
     S.count("service_wan_first_private restart if-start") == 1 and
     "telegram-voice-enable) wan_first_service require || return $? ;;" in S,
     "ORIGINAL_FD9_AND_VOICE_SCOPE")
need('if [ "${_service_receipt_action:-}" = "${_service_wan_verb}" ]' in original and
     "64:wan-required" in original and "64:wan-invalid" in original and
     "69:wan-unavailable" in original,
     "UNQUALIFIED_PRIVATE_WAN_PRODUCER")
need("if (!$isStop && strlen($raw) <= 128)" in P and
     "trim($raw) === 'zapret-api-lifecycle-v1:' . $action . ':refused:' . $cause" in P and
     "throw new UserException($safeText" in P,
     "HTTP_MARKER_NOT_STRICT")
for kind, safe in (
    ("wan-required", "Select a WAN interface"),
    ("wan-invalid", "Selected WAN interface is not assigned or unavailable"),
    ("wan-unavailable", "Saved WAN preflight is unavailable"),
):
    need("'"+kind+"' => '"+safe+"'" in P and "'"+safe+"'" in G,
         "SAFE_MESSAGE_MISSING_"+kind)
need("Object.prototype.hasOwnProperty.call(nativeStartErrors, nativeError)" in G and
     "localizeStrategiesApplyError(message)" in G and
     "S05J_ORIGINAL_FD9_WAN_REQUIRED=PASS" in N,
     "NATIVE_GUI_BOUNDARY_NOT_LINKED")

with tempfile.TemporaryDirectory() as temp:
    fake = Path(temp) / "wan_preflight.sh"
    for action, mode, reply, child_rc, receipt, rc, cause in (
        ("start", "require", "wan-required", 0, "start", 64, "wan-required"),
        ("start", "require", "wan-invalid", 0, "start", 64, "wan-invalid"),
        ("start", "require", "wan-unavailable", 69, "start", 69, "wan-unavailable"),
        ("restart", "if-start", "wan-required", 0, "restart", 64, "wan-required"),
        ("restart", "if-start", "wan-invalid", 0, "restart", 64, "wan-invalid"),
        ("restart", "if-start", "wan-unavailable", 69, "restart", 69, "wan-unavailable"),
        ("start", "require", "wan-ready", 0, "start", 0, ""),
        ("restart", "if-start", "wan-not-required", 0, "restart", 0, ""),
        ("start", "require", "wan-required", 0, "", 64, ""),
        ("restart", "if-start", "wan-required", 0, "start", 64, ""),
        ("start", "require", "wan-ready", 69, "start", 69, ""),
        ("start", "require", "wan-invalid", 69, "start", 69, ""),
        ("start", "require", "garbage", 0, "start", 69, ""),
        ("start", "require", "", 69, "start", 69, ""),
    ):
        fake.write_text("#!/bin/sh\nprintf '%s\\n' "+shlex.quote(reply)+
                        "\nexit "+str(child_rc)+"\n")
        fake.chmod(0o700)
        script=(original+"\nSCRIPT_DIR="+shlex.quote(temp)+"\n"+
                "_service_receipt_action="+shlex.quote(receipt)+"\n"+
                "service_wan_first_private "+action+" "+mode+"\n")
        result=subprocess.run(["/bin/sh"],input=script,text=True,
                              capture_output=True,timeout=5)
        want=("zapret-api-lifecycle-v1:"+action+":refused:"+cause+"\n") if cause else ""
        need((result.returncode,result.stdout)==(rc,want),
             "ORIGINAL_FUNCTION_"+action+"_"+reply+"_"+str(child_rc)+"_"+receipt)
        need("zapret-api-lifecycle" not in result.stderr,
             "PRIVATE_RECEIPT_LEAKED_TO_STDERR")
print("S05J_ORIGINAL_SOURCE_WAN_MATRIX=PASS_14")
