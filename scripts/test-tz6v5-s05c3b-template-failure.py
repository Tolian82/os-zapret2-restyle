#!/usr/bin/env python3
"""Source-only S05c3b original function; real native HTTP in S03e3f."""
from pathlib import Path
import shlex
import subprocess
ROOT=Path(__file__).resolve().parents[1]
SH=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
PHP=(ROOT/"src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php").read_text()
GUI=(ROOT/"src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
LEG=(ROOT/"scripts/test-tz6v5-s03e3f-legacy-positive.py").read_text()
MARK="zapret-api-lifecycle-v1:start:refused:template-generation-failed"
def need(ok,why):
    if not ok: raise SystemExit("S05C3B_REFUSED="+why)
start=SH.index("refresh_generated_configuration()\n{")
end=SH.index("\n# Run the staged-only Voice ON refusal",start)
producer=SH[start:end]
need(SH.count(MARK)==1 and "config_reload_template OPNsense/Zapret" in producer
     and "if orchestrator_fail_stage" in producer and "1 13 config" in producer
     and "_service_receipt_action" in producer, "ORIGINAL_STAGE13_PRODUCER_ONLY")
need(PHP.count(MARK)==1 and "trim($raw) === '"+MARK+"'" in PHP
     and "strlen($raw) <= 128" in PHP
     and "Zapret2 Start refused: configuration template generation failed." in PHP,
     "STRICT_PHP_REFUSAL")
need("Zapret2 Start refused: configuration template generation failed." in GUI
     and "Zapret2 could not generate its configuration. Check the service log." in GUI
     and "Не удалось сформировать конфигурацию Zapret2." in GUI
     and "Object.prototype.hasOwnProperty.call(nativeStartErrors, nativeError)" in GUI,
     "SAFE_RU_EN_ALLOWLIST")
need("S05C3B_REAL_STAGE13_HTTP_QUALIFIED_CAUSE=PASS" in LEG
     and "S05C3A_ORIGINAL_STAGE13_NOT_OBSERVED" in LEG,
     "SAME_NATIVE_VM_PROOF")
for name,reload_ok,stage_ok,action,rc,out in (
    ("private-saved-stage",False,True,"start",1,MARK+"\n"),
    ("public-saved-stage",False,True,"",1,""),
    ("restart-saved-stage",False,True,"restart",1,""),
    ("failed-stage-write",False,False,"start",1,""),
    ("successful-reload",True,True,"start",0,""),
):
    src=producer+"\n"
    src+="config_reload_template() { "+("return 0" if reload_ok else "return 1")+"; }\n"
    src+="orchestrator_fail_stage() { "+("return 0" if stage_ok else "return 1")+"; }\n"
    src+="STAGE_FILE=/dev/null\n_service_receipt_action="+shlex.quote(action)+"\n"
    src+="refresh_generated_configuration\n"
    r=subprocess.run(["/bin/sh"],input=src,capture_output=True,text=True,timeout=5)
    need(r.returncode==rc and r.stdout==out and not r.stderr,"ACTUAL_FUNCTION_"+name)
print("S05C3B_PRIVATE_STAGE13_NEGATIVE_MATRIX=PASS")
