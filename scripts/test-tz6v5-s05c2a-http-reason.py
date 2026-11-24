#!/usr/bin/env python3
"""S05c2a strict source review, not a substitute for real native HTTP."""
from pathlib import Path
import re
import sys

R=Path(__file__).resolve().parents[1]
S=(R/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
P=(R/"src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php").read_text()
G=(R/"src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
B=(R/"scripts/stage5-browser-wan.py").read_text()
A=(R/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
def need(x,label):
    if not x: raise SystemExit("S05C2A_SOURCE_REFUSED="+label)
need('if [ "${_service_fd9_refusal_rc}" -eq 75 ] &&' in S,
     "REAL_LOCKF_RC_ONLY")
need('printf \'zapret-api-lifecycle-v1:%s:refused:fd9-busy\\n\'' in S,
     "BOUNDED_SHELL_MARKER_MISSING")
need('_service_receipt_action' in S and
     'return 75' in S and 'service_api_terminal_receipt()' in S,
     "SINGLE_ORIGINAL_DISPATCH")
for v in ("stop","restart"):
    need(v+"_verified]" in A, "ORIGINAL_CONFIGD_MISSING_"+v)
    need('Zapret2 '+v.title()+' refused: original lifecycle lock is busy.' in P,
         "FIXED_HTTP_CAUSE_MISSING_"+v)
    need('S05C2A_REAL_NATIVE_FD9_CAUSE_NOT_DELIVERED_' in B,
         "REAL_BROWSER_UNQUALIFIED")
need("strlen($raw) <= 128 && trim($raw) === $fd9Refusal" in P,
     "PHP_STRICT_MARKER_MISSING")
need("'verified' => true" in P and
     "substr_count($raw, 'zapret-api-lifecycle-v1:') === 1" in P,
     "TERMINAL_SUCCESS_WEAKENED")
need("nativeError === 'Zapret2 Stop refused: original lifecycle lock is busy.'" in G,
     "GUI_STOP_FIXED_ALLOWLIST_MISSING")
need('Остановка Zapret2 отклонена: другая операция удерживает блокировку службы.' in G,
     "GUI_RUSSIAN_STOP_MISSING")
need("action === 'stop' ? ''" in G and
     "receipt.verified !== true" in G,
     "GUI_UNTRUSTED_ERROR_OR_SUCCESS_REGRESSION")
need("S05C2A_REAL_NATIVE_FD9_CAUSE_NOT_DELIVERED_" in B and
     "S03E3C_NATIVE_HTTP_CONFIG_IPFW_ENGINE_UNCHANGED=PASS" in B,
     "GENUINE_NATIVE_NOT_CONNECTED")
print("S05C2A_FIXED_CAUSAL_SOURCE_GATE=PASS")
