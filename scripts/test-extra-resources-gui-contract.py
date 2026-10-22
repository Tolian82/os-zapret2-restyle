#!/usr/bin/env python3
"""Static + JS parser acceptance for manual, bilingual Additional Resources GUI."""
from __future__ import annotations

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
require("extraObservedBusy" in view and "extraNeedsReview" in view,
        "asynchronous completion incorrectly assumes immediate success")
require("$('#zapretExtraInstall').off('click').on('click'" in view,
        "manual click handler absent")
require("function refreshExtrasStatus()" in view, "read-only status polling absent")
require("resourcesStatusAction(): array" in php and
        "resourcesInstallAction(): array" in php, "controller endpoints missing")
require("$runtime['service'] !== 'started'" in php and
        "$runtime['busy']" in php and "$extras['busy']" in php,
        "server fails to enforce Started/exclusivity")
require("zapret extra_resources_install" in php and
        "zapret extra_resources_status" in php,
        "controller is not using configd actions")
require("zapret restart" not in php.split("public function resourcesInstallAction()", 1)[-1].split("public function releasesAction()", 1)[0],
        "GUI must not use independent restart")
require('phase=' in launcher and 'revision=' in launcher and
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
print("PASS: bilingual manual extra-resources GUI, bounded status and service gate")
