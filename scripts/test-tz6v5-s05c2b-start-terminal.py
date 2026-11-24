#!/usr/bin/env python3
"""S05c2b actual source Start terminal proof + inert negative matrix.

Not an installed proof. G07 and S03e3f are the real native HTTP witnesses.
"""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
S=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
A=(ROOT/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
P=(ROOT/"src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php").read_text()
G=(ROOT/"src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
G07=(ROOT/"scripts/stage2-opnsense-g07-native-lifecycle.py").read_text()
LEG=(ROOT/"scripts/test-tz6v5-s03e3f-legacy-positive.py").read_text()
def need(ok,code):
    if not ok: raise SystemExit("S05C2B_SOURCE_REFUSED="+code)
def block(label,after):
    a=S.find(label+"()\n{")
    b=S.find(after+"()\n{",a+1)
    need(a>=0 and b>a,"HELPER_SOURCE_MISSING_"+label)
    return S[a:b]
need("service_api_complete()" in S and
     "start:0)" in S and
     "zapret-api-lifecycle-v1:start:running" in S and
     'start|stop|restart)' in S,"SINGLE_FD9_START_RECEIPT_MISSING")
need(S.count('shared_apply_boot_service "$_shared_owner"\n')==4 and
     S.count('service_api_complete "$?"')>=5 and
     'shared_apply_recover_saved_service "$_shared_owner"\n'
     '                            service_api_complete "$?"' in S,
     "COMMON_AND_RECOVERY_START_RETURN_NOT_VERIFIED")
need("[start]\ncommand:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh start\n"
     "parameters:\ntype:script\n" in A, "LEGACY_START_CHANGED")
need("[start_verified]\ncommand:/usr/local/opnsense/scripts/OPNsense/Zapret/"
     "zapret_service.sh start --configd-receipt\nparameters:\ntype:script_output\n"
     "errors:no\n" in A,"PRIVATE_CONFIGD_START_MISSING")
need("return $this->verifiedLifecycleAction('start');" in P and
     "zapret wan_preflight" in P and
     "'zapret-api-lifecycle-v1:start:running'" in P and
     "strlen($raw) <= 8192" in P and
     "'verified' => true" in P and
     "Zapret2 Start refused: original lifecycle lock is busy." in P,
     "PHP_START_WAN_AND_FAIL_CLOSED_CONSUMER_MISSING")
need("receipt.action !== action" in G and
     "receipt.verified !== true" in G and
     "Запуск Zapret2 не подтверждён" in G and
     "fd9BusyStart" in G and
     "Запуск Zapret2 отклонён: другая операция удерживает блокировку службы." in G,
     "GUI_START_200_OR_CAUSE_GUARD_MISSING")
need('G07_FD9_BUSY_START_CAUSE_NOT_DELIVERED' in G07 and
     'if name in ("start", "stop", "restart")' in G07 and
     'if name in ("start", "stop", "restart")' in LEG,
     "INSTALLED_NATIVE_START_WITNESS_DISCONNECTED")
fn=block("service_api_terminal_receipt","service_with_lifecycle_lock")
fn=fn[:fn.rfind("\n}")+2]
for command_rc,observed_rc,expected_rc,expected in (
    (0,0,0,"zapret-api-lifecycle-v1:start:running\n"),
    (75,0,75,""), (69,0,69,""), (0,1,70,""), (0,2,70,""),
):
    script=(fn+"\nshared_apply_status_service(){ return "+str(observed_rc)+"; }\n"
            "service_api_terminal_receipt start "+str(command_rc)+"\n")
    done=subprocess.run(["/bin/sh"],input=script,text=True,capture_output=True,timeout=5)
    need(done.returncode==expected_rc and done.stdout==expected and
         not done.stderr,"ORIGINAL_START_TERMINAL_MATRIX_"+str(command_rc)+"_"+str(observed_rc))
print("S05C2B_SOURCE_AND_ORIGINAL_START_NEGATIVE_MATRIX=PASS")
