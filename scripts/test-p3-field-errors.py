#!/usr/bin/env python3
"""P3 RU/EN Strategies/Voice field-error contract on actual browser JS.

This tests the precise native Python/PHP bridge vocabulary and JS rendering.
It is not physical OPNsense user-profile A12–A16 acceptance.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api"
VIEW = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret"

general = (VIEW / "general.volt").read_text(encoding="utf-8")
voice = (VIEW / "voice.volt").read_text(encoding="utf-8")
domain_bridge = (API / "DomainSetPolicyBridge.php").read_text(encoding="utf-8")
ipset_bridge = (API / "IPSetPolicyBridge.php").read_text(encoding="utf-8")
model = (ROOT / "src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml").read_text(encoding="utf-8")
assert "handleFormValidation('frm_GeneralSettings',\n                    localizeStrategiesFieldErrors(" in general
assert "handleFormValidation('frm_VoiceSettings', localizeVoiceErrors(" in voice
assert "Native IPSET preflight refused invalid addresses or networks" in ipset_bridge
assert "'Invalid IPSET ' . $match[1] . $line" in ipset_bridge
assert "self::ERROR_CODES[$error['code']] . ' (line ' . $error['line'] . ')'" in domain_bridge

strat_fn = re.search(
    r"^        function localizeStrategiesFieldErrors\(errors\) \{.*?^        \}",
    general, re.MULTILINE | re.DOTALL,
)
voice_fn = re.search(
    r"^    function localizeVoiceErrors\(errors\) \{.*?^    \}",
    voice, re.MULTILINE | re.DOTALL,
)
assert strat_fn and voice_fn, "Production UI field-error functions absent"
for label in (
    "Please enter a valid port number.",
    "Please enter comma-separated port numbers.",
    "Please enter IPv4/IPv6 addresses or CIDR networks; full-family coverage is forbidden.",
    "Enter IPv4/IPv6 address or CIDR per line; /0 and full-family unions are forbidden.",
):
    assert label in model and label in strat_fn.group(0), label

# Enumerate actual Python domain bridge codes, never an invented vocabulary.
codes = domain_bridge.split("private const ERROR_CODES = [", 1)[1].split("];", 1)[0]
messages = re.findall(r"'[a-z_]+'\s*=>\s*'([^']+)'", codes)
assert len(messages) == 7 and len(set(messages)) == 7
for message in messages:
    assert ("'" + message + "'") in strat_fn.group(0), message

assert "const match = /^(.+) \\(line ([1-9][0-9]{0,6})\\)$/.exec(message)" in strat_fn.group(0)
assert "Object.prototype.hasOwnProperty.call(domain, match[1])" in strat_fn.group(0)
assert "if (!isRussian || !errors" in strat_fn.group(0)
assert "if (!ru || !errors" in voice_fn.group(0)
assert "result[key] = 'Ошибка проверки поля." in strat_fn.group(0)
assert "result[key] = 'Ошибка проверки настроек." in voice_fn.group(0)
assert "Invalid IPSET [A-Za-z ()]{1,80}" in strat_fn.group(0)
assert "Invalid IPSET [A-Za-z ()]{1,80}" in voice_fn.group(0)

if shutil.which("node"):
    script = (
        "let isRussian=true;let ru=true;\n"
        + strat_fn.group(0) + "\n"
        + voice_fn.group(0) + "\n"
        + """function eq(a,b){if(a!==b)throw Error(JSON.stringify([a,b]));}
const raw={
 'zapret.hostlist.youtubedomains':'Invalid domain (line 3)',
 'zapret.hostlist.excludedomains':'Modifiers are not permitted in Exclude Domains (line 12)',
 'zapret.hostlist.excludeipset':'Invalid IPSET Telegram IPs at line 17',
 'zapret.hostlist.telegramips':'Invalid IPSET Telegram IPs',
 'zapret.general.divertport':'Please enter a valid port number.',
 'zapret.strategy.trafficargs':'PRIVATE INPUT DO NOT SHOW',
 'zapret.hostlist.userdomains':9
};
const translated=localizeStrategiesFieldErrors(raw);
eq(translated['zapret.hostlist.youtubedomains'],'Некорректный домен (строка 3)');
eq(translated['zapret.hostlist.excludedomains'],
 'Модификаторы запрещены в глобальном списке исключений доменов (строка 12)');
eq(translated['zapret.hostlist.excludeipset'],'Некорректный IPSET (строка 17).');
eq(translated['zapret.hostlist.telegramips'],'Некорректный IPSET.');
eq(translated['zapret.general.divertport'],'Укажите корректный номер порта.');
eq(translated['zapret.strategy.trafficargs'],
 'Ошибка проверки поля. Исправьте значение или проверьте журнал Zapret2.');
eq(translated['zapret.hostlist.userdomains'],9);
eq(raw['zapret.hostlist.youtubedomains'],'Invalid domain (line 3)');
if(Object.keys(translated).sort().join()!=Object.keys(raw).sort().join())
 throw Error('field key lost');
const unsafe={'zapret.hostlist.youtubedomains':
 'Invalid domain (line 3); <script>alert(1)</script>'};
eq(localizeStrategiesFieldErrors(unsafe)['zapret.hostlist.youtubedomains'],
 'Ошибка проверки поля. Исправьте значение или проверьте журнал Zapret2.');
isRussian=false;
if(localizeStrategiesFieldErrors(raw)!==raw)throw Error('EN fallback changed');
const vraw={
 'zapret.hostlist.telegramips':'Invalid IPSET Telegram IPs at line 8',
 'zapret.hostlist.discordips':'Invalid IPSET DISCORD IPs',
 'zapret.hostlist.customips':'Native IPSET preflight unavailable',
 'zapret.voice.telegram.args':'PRIVATE ARGS DO NOT SHOW'
};
const vr=localizeVoiceErrors(vraw);
eq(vr['zapret.hostlist.telegramips'],'Некорректный IPSET (строка 8)');
eq(vr['zapret.hostlist.discordips'],'Некорректный IPSET.');
eq(vr['zapret.hostlist.customips'],
 'Невозможно проверить IPSET: проверка недоступна.');
eq(vr['zapret.voice.telegram.args'],
 'Ошибка проверки настроек. Обновите страницу или проверьте журнал Zapret2.');
ru=false;
if(localizeVoiceErrors(vraw)!==vraw)throw Error('Voice EN fallback changed');
"""
    )
    run = subprocess.run(
        ["node", "-"], input=script, text=True, capture_output=True, check=False
    )
    assert run.returncode == 0, run.stderr

print("PASS: P3 actual bridge/model field errors; RU/EN Strategies + Voice, safe lines and fallback")
