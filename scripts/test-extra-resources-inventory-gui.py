#!/usr/bin/env python3
"""Contract: optional full-help view uses only cached inventory, never Git per view."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
CTRL = (ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php").read_text()
ACTIONS = (ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
POST = (ROOT / "pkg/+POST_INSTALL").read_text()
OP = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/extra_resources_operation.py").read_text()
SETUP = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh").read_text()
CACHE = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/extra_resources_inventory_cache.py").read_text()
for marker in ("zapretExtraInstall", "zapretExtraResourceHelp", "zapret-resource-columns",
               "zapret-resource-list", "show_all_help_frm_GeneralSettings",
               "MutationObserver", "/api/zapret/service/resourcesInventory",
               "text-success", "text-info", "requestResourceHelpInventory"):
    assert marker in VIEW, "missing UI integration: " + marker
assert VIEW.count('id="zapretExtraResourceHelp"') == 1
assert "Дополнительные ресурсы пока не установлены" in VIEW
assert "Additional Resources have not been installed" in VIEW
assert ".text(item.name)" in VIEW, "unsafe filename interpolation: require text()"
php_lint = subprocess.run(
    ["php", "-l", str(ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php")],
    capture_output=True, text=True,
)
assert php_lint.returncode == 0, php_lint.stdout + php_lint.stderr
assert "resourcesInventoryAction(): array" in CTRL
assert "zapret extra_resources_inventory" in CTRL
assert "[extra_resources_inventory]" in ACTIONS
assert "extra_resources_inventory_cache.py show" in ACTIONS
assert "refresh_inventory_cache(RUNTIME, STATE)" in OP
assert "refresh_inventory_help_cache" in SETUP
assert "EXTRA_INVENTORY_CACHE" in POST
assert "def read_cached" in CACHE and "def generate" in CACHE
# Detect accidentally fetching current Git/filesystem for each help toggle.
read = CACHE.split("def read_cached(", 1)[1].split("def refresh(", 1)[0]
assert "tracked_resources(" not in read and "installed_resources(" not in read
inventory_api = CTRL.split("resourcesInventoryAction(): array", 1)[1].split(
    "public function resourcesInstallAction", 1
)[0].lower()
assert not any(action in inventory_api for action in ("git -c", "ls-tree", "glob(", "scandir(", "readdir("))
with tempfile.TemporaryDirectory() as tmp:
    # The Volt JS block has no server-only expressions; parsing is enough for this contract.
    code = re.search(r"<script>\s*(.*?)\s*</script>", VIEW, re.S)
    assert code
    path = Path(tmp) / "help.js"
    path.write_text(code.group(1))
    result = subprocess.run(["node", "--check", str(path)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
print("PASS: cached Lua/BIN full help, source colors and native toggle wiring")
