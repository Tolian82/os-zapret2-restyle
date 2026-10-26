#!/usr/bin/env python3
"""Static + JS parser acceptance for manual, bilingual Additional Resources GUI."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"
PHP = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php"
LAUNCHER = ROOT / "src/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh"
ACTIONS = ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf"

view = VIEW.read_text()
php = PHP.read_text()
launcher = LAUNCHER.read_text()
actions = ACTIONS.read_text()


def require(test: bool, reason: str) -> None:
    if not test:
        raise AssertionError(reason)


for ident in ("zapretExtraInstall", "zapretExtraInstallText",
              "zapretExtraProgress", "zapretExtraState"):
    require(view.count(f'id="{ident}"') == 1, f"duplicate/missing GUI id: {ident}")
for ident in ("zapretExtraRemove", "zapretExtraRemoveText", "zapretExtraRemoveProgress", "zapretExtraRemoveRow"):
    require(view.count(f'id="{ident}"') == 1, f"duplicate/missing Remove UI: {ident}")
require("Удалить дополнительные ресурсы" in view and "Remove Additional Resources" in view,
        "native Advanced-only RU/EN Remove label missing")
require("show_advanced_frm_GeneralSettings" in view and
        "updateResourceAdvancedVisibility()" in view and
        "isResourceAdvancedEnabled()" in view and
        "observer.observe(resourceAdvancedIcon" in view,
        "native Advanced ON/OFF is not tied to immediate Remove visibility")
require("$('#zapretExtraRemove').css({" in view and
        "$('#zapretExtraInstall').outerWidth()" in view and
        "$('#zapretExtraInstall').outerHeight()" in view,
        "Remove and Install button sizes are not linked")
require("/api/zapret/service/resourcesRemovePlan" in view and
        "data.ready !== false" in view and
        "extrasText.removeNotReady" in view and
        "url: '/api/zapret/service/resourcesRemove'," not in view,
        "Remove GUI must show a read-only plan, NOT authorize real file deletion")
require("Установить дополнительные ресурсы" in view and
        "Install Additional Resources" in view, "final agreed RU/EN labels absent")
require("Сначала запустите Zapret2" in view and
        "Start Zapret2 first" in view, "stopped tooltip missing")
require(view.count('id="zapretReleaseApply"') == 1 and
        view.count('id="reconfigureAct"') == 1,
        "existing two Apply buttons changed")
require("currentServiceState === 'started'" in view,
        "button missing fully started guard")
require("/api/zapret/service/resourcesStatus" in view and
        "/api/zapret/service/resourcesInstall" in view,
        "resource status/install routes absent")
require("$('#reconfigureAct').prop('disabled', controlsBusy)" in view,
        "lower Strategies Apply must be disabled during resource lifecycle")
require("extraBusy || extraInstallPending || extraNeedsReview" in view,
        "other manual controls ignore resource runtime ownership")
require("extraPollAttempts > 300" in view and "window.clearInterval(extraPoll)" in view,
        "resource polling is not bounded")
require("extraOperationTerminal(data, extraExpectedOperation)" in view and
        "extraNeedsReview" in view and "extraObservedBusy" not in view,
        "manual click completion still depends on catching busy=1")
require("$('#zapretExtraInstall').off('click').on('click'" in view,
        "manual click handler absent")
require("function refreshExtrasStatus()" in view, "read-only status polling absent")
require("resourcesRemovePlanAction(): array" in php and
        "'zapret extra_resources_remove_plan'" in php and
        "return ['status' => 'unavailable', 'ready' => false]" in php and
        "'ready' => false" in php,
        "Remove planning endpoint must be read-only and non-authorizing")
require("[extra_resources_remove_plan]" in actions and
        "extra_resources_launcher.sh plan" in actions and
        "extra-resources-remove-plan" in launcher,
        "read-only native Remove plan configd routing absent")
require("resourcesStatusAction(): array" in php and
        "resourcesInstallAction(): array" in php, "controller endpoints missing")
require("$runtime['service'] !== 'started'" in php and
        "$runtime['busy']" in php and "$extras['busy']" in php,
        "server fails to enforce Started/exclusivity")
require("zapret extra_resources_install" in php and
        "zapret extra_resources_status" in php and
        "bin2hex(random_bytes(16))" in php and
        "[$operation], false, 30" in php,
        "controller must issue a fresh correlated operation token")
require("parameters:%s" in actions.split("[extra_resources_install]", 1)[1].split("[", 1)[0],
        "configd does not pass operation token to manual launcher")
operation = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/extra_resources_operation.py").read_text()
require("EXTRA_RESOURCES_OPERATION_ID" in launcher and
        "EXTRA_RESOURCES_OPERATION_ID" in operation,
        "worker does not retain operation token")
require("zapret restart" not in php.split("public function resourcesInstallAction()", 1)[-1].split("public function releasesAction()", 1)[0],
        "GUI must not use independent restart")
require('phase=' in launcher and 'operation=' in launcher and 'revision=' in launcher and
        'lua=' in launcher and 'bin=' in launcher,
        "status transport is missing terminal installed counts/revision")
require("[extra_resources_install]" in actions and "[extra_resources_status]" in actions,
        "configd extra-resources actions absent")

# Catch JavaScript parser errors without requiring an OPNsense/browser runtime.
match = re.search(r"<script>\s*(.*?)\s*</script>", view, re.S)
require(match is not None, "main GUI JavaScript block not found")
if shutil.which("node") is None:
    raise AssertionError("node is required to syntax-check the GUI")
with tempfile.TemporaryDirectory() as tmp:
    script = Path(tmp) / "extra-resources-ui.js"
    script.write_text(match.group(1))
    result = subprocess.run(["node", "--check", str(script)],
                            text=True, capture_output=True)
    require(result.returncode == 0, "JavaScript parse failure: " + result.stderr)

    # Verify the real JS terminal predicate even when polling misses busy=1.
    helper = re.search(
        r"        function extraOperationTerminal\(data, operation\) \{.*?^        \}",
        view, re.M | re.S,
    )
    require(helper is not None, "correlated terminal predicate missing")
    predicate = Path(tmp) / "receipt.js"
    predicate.write_text(
        helper.group(0) + """
const assert = require('node:assert/strict');
const id = 'a'.repeat(32), stale = 'b'.repeat(32);
for (const phase of ['ready','failed','restore_failed','recovery_required']) {
    assert.equal(extraOperationTerminal({operation:id,phase,busy:false},id), true);
    assert.equal(extraOperationTerminal({operation:stale,phase,busy:false},id), false);
    assert.equal(extraOperationTerminal({operation:id,phase,busy:true},id), false);
}
for (const phase of ['unknown','downloading','verifying','installing']) {
    assert.equal(extraOperationTerminal({operation:id,phase,busy:false},id), false);
}
assert.equal(extraOperationTerminal({operation:id,phase:'ready',busy:false},''), false);
"""
    )
    result = subprocess.run(["node", str(predicate)], text=True, capture_output=True)
    require(result.returncode == 0, "GUI receipt predicate failure: " + result.stderr)

    # Exercise the shell status transport using an actual terminal receipt.
    status = Path(tmp) / "status.json"
    status.write_text(json.dumps({
        "schema": 1, "operation": "a" * 32, "phase": "ready",
        "revision": "c" * 40, "lua": 19, "bin": 54,
    }))
    env = {**os.environ, "STATUS": str(status), "RUN_DIR": tmp,
           "PID_FILE": str(Path(tmp) / "absent.pid"), "PYTHON_BIN": "python3"}
    result = subprocess.run(["sh", str(LAUNCHER), "status"],
                            text=True, capture_output=True, env=env)
    require(result.returncode == 0, "launcher status failed: " + result.stderr)
    require("operation=" + "a" * 32 in result.stdout and
            "phase=ready" in result.stdout and "busy=0" in result.stdout,
            "fast terminal receipt not transported")

    result = subprocess.run(["sh", str(LAUNCHER), "install", "invalid"],
                            text=True, capture_output=True, env=env)
    require(result.returncode == 64, "invalid manual operation token accepted")
print("PASS: bilingual Additional Resources GUI and correlated fast-job receipt")
