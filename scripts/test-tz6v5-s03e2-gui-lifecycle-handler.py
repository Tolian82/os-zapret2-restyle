#!/usr/bin/env python3
"""TZ6v5 S03e2: execute real Strategies JS click handler with inert AJAX.

This is a SOURCE-EXTRACTED Node handler harness, not an OPNsense browser/GUI
click or physical lifecycle test. It must never dispatch configd or start/stop
a service. Only Start/Stop lifecycle failure text is under test (V5-12).
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
GENERAL = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"
VOICE = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt"


def assert_source() -> str:
    general = GENERAL.read_text(encoding="utf-8")
    voice = VOICE.read_text(encoding="utf-8")
    assert 'id="voiceServiceControl"' not in voice
    assert "voiceControlPending" not in voice
    assert "$('#voiceServiceControl').on('click'" not in voice
    assert "url:'/api/zapret/service/' + action" not in voice
    for marker in (
        'id="voiceServiceState"', 'id="voiceIPFWState"',
        'id="voiceApply"', "refreshVoiceHealthSettled().always(function ()",
        "/api/zapret/service/runtime", "/api/zapret/voice/inspect",
        "'/api/zapret/voice/apply'", "'/api/zapret/voice/saveDraft'",
    ):
        assert marker in voice, f"Voice read-only/Apply control lost: {marker}"
    assert "voiceRuntimeAligned()" in voice
    assert "voiceApplyNeedsReview" in voice
    assert "serviceError: isRussian ? 'Ошибка управления службой' : 'Service operation failed'" in general
    # Match the literal production selector without hand-escaped nested parens.
    prefix = "        $('#zapretServiceControl').off('click').on('click', function(event) {"
    click = re.search(
        r"^" + re.escape(prefix) + r".*?^        \}\);",
        general, re.MULTILINE | re.DOTALL,
    )
    assert click is not None, "Actual Strategies service click handler missing"
    return click.group(0)


def test_js_handler(click: str) -> None:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("S03E2_NODE_REQUIRED: the actual handler must execute")
    script = r"""
"use strict";
let clickHandler = null, currentServiceState = 'started';
let strategiesApplyPending = false, strategiesApplyNeedsReview = false;
let runtimeWasBusy = false, extraBusy = false;
let extraInstallPending = false, extraNeedsReview = false;
let isRussian = true, runtimeText = { serviceError: 'Ошибка управления службой' };
let requests = [], shown = [], refreshCount = 0, successCount = 0;
const button = { disabled: false, prop(key, value) {
  if (key !== 'disabled') throw Error('unexpected button prop');
  if (value === undefined) return this.disabled;
  this.disabled = value; return this;
}};
function $(arg) {
  if (arg === button) return button;
  if (arg === '#zapretServiceControl') return {
    off(name){if (name !== 'click') throw Error('wrong event');return this;},
    on(name,fn){if(name !== 'click')throw Error('wrong event');clickHandler=fn;return this;}
  };
  throw Error('unexpected UI target ' + arg);
}
$.ajax = function(opts) {
  const task = {opts, done:null, fail:null};
  requests.push(task);
  return {done(fn){task.done=fn;return this;},
          fail(fn){task.fail=fn;return this;}};
};
function localizeStrategiesApplyError(message) {return 'mapped:' + message;}
function showRuntimeError(title, body) {shown.push([title, body]);}
function refreshRuntime() {refreshCount++;}
function updateServiceControlUI(svc) {if(svc!=='zapret')throw Error('wrong service');successCount++;}
function check(cond,msg){if(!cond)throw Error(msg);}
""" + click + r"""
check(typeof clickHandler === 'function', 'real handler not bound');

function clickOne(state, locale, failure, expectedPhrase) {
  currentServiceState = state;
  isRussian = locale === 'ru';
  runtimeText.serviceError = isRussian ? 'Ошибка управления службой' : 'Service operation failed';
  button.disabled = false;
  let prevented = false;
  const initialCount = requests.length, initialShown = shown.length;
  const initialRefresh = refreshCount;
  clickHandler.call(button, { preventDefault(){prevented=true;} });
  check(prevented && button.disabled, 'service button click did not lock UI');
  check(requests.length === initialCount + 1, 'unexpected AJAX count');
  const req = requests[requests.length - 1];
  check(req.opts.url === '/api/zapret/service/' + (state==='started'?'stop':'start'), 'wrong action');
  check(req.opts.type === 'POST' && req.opts.timeout === 600000, 'wrong transport contract');
  check(typeof req.fail === 'function', 'failure consumer is unreachable');
  req.fail(failure === null ? {} : {responseJSON:{message:failure}});
  check(shown.length === initialShown + 1, 'failure not visible');
  check(shown.at(-1)[0] === runtimeText.serviceError, 'wrong lifecycle error title');
  check(shown.at(-1)[1].includes(expectedPhrase), 'wrong RU/EN verb or message: '+shown.at(-1)[1]);
  check(refreshCount === initialRefresh + 1, 'failed service action did not refresh');
}
clickOne('started', 'ru', null, 'Не удалось остановить Zapret2.');
clickOne('started', 'en', null, 'Zapret2 could not be stopped.');
clickOne('stopped', 'ru', null, 'Не удалось запустить Zapret2.');
clickOne('stopped', 'en', null, 'Zapret2 could not be started.');
clickOne('started', 'ru', 'Select a WAN interface', 'mapped:Select a WAN interface');
strategiesApplyPending = true;
const before = requests.length;
clickHandler.call(button, {preventDefault(){}});
check(requests.length === before, 'busy-guard allowed a mutation');
strategiesApplyPending = false;
currentServiceState = 'started';
clickHandler.call(button, {preventDefault(){}});
const req = requests.at(-1), beforeSuccess = successCount, beforeRefresh = refreshCount;
req.done();
check(successCount === beforeSuccess + 1 && refreshCount === beforeRefresh + 1,
      'success route no longer refreshes common service');
console.log('S03E2_ACTUAL_STRATEGIES_HANDLER_INERT_RU_EN_PASS');
"""
    result = subprocess.run([node, "-"], input=script, text=True,
                            capture_output=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RuntimeError("S03E2_HANDLER_FAILED: " + result.stderr[-3000:])
    if "S03E2_ACTUAL_STRATEGIES_HANDLER_INERT_RU_EN_PASS" not in result.stdout:
        raise RuntimeError("S03E2_HANDLER_MISSING_WITNESS")
    print(result.stdout.strip())


def main() -> None:
    handler = assert_source()
    test_js_handler(handler)
    print("S03E2_VOICE_READONLY_SOURCE_CONTRACT_PASS")
    print("S03E2_NATIVE_GUI_RU_EN_CLICK_NOT_TESTED=1")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"S03E2_FAIL={type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
