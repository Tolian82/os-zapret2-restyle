#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"

grep -Fq 'function renderResultSummary(data)' "${VIEW}"
grep -Fq "item.profile || item.strategy" "${VIEW}"
grep -Fq 'item.protocol' "${VIEW}"
grep -Fq 'item.port' "${VIEW}"
grep -Fq 'function endpointText(item)' "${VIEW}"
grep -Fq 'item.profile_replay' "${VIEW}"
grep -Fq 'function verifiedReplay(item)' "${VIEW}"
grep -Fq 'item.profile_replay.verified === true' "${VIEW}"
grep -Fq 'if (!verifiedReplay(item)) { unverified++; return; }' "${VIEW}"
grep -Fq 'ui.unverifiedScope' "${VIEW}"
grep -Fq 'ui.savedProfiles' "${VIEW}"
grep -Fq 'strategyLabCopyProfile' "${VIEW}"
# Two green outlined rectangles next to exactly the displayed validated Job ID.
grep -Fq 'id="strategyLabCopyJob"' "${VIEW}"
grep -Fq 'class="strategy-lab-job-inline"' "${VIEW}"
grep -Fq '.strategy-lab-copy-job::before,.strategy-lab-copy-job::after' "${VIEW}"
grep -Fq 'color:#5cb85c' "${VIEW}"
grep -Fq "copyJob:'Копировать Job ID'" "${VIEW}"
grep -Fq "copyJob:'Copy Job ID'" "${VIEW}"
grep -Fq 'copyProfile(id).then(function ()' "${VIEW}"
grep -Fq 'if (!savedJobId(id)) return;' "${VIEW}"
grep -Fq 'id="strategyLabCopyJobFeedback" class="sr-only" aria-live="polite"' "${VIEW}"
grep -Fq "button.addClass('strategy-lab-job-copied')" "${VIEW}"
grep -Fq "circularTitle:'Временная циклическая проверка'" "${VIEW}"
grep -Fq 'id="strategyLabCircularHelp"' "${VIEW}"
grep -Fq "\$('#strategyLabCircularHelp').text(ui.circularHelp);" "${VIEW}"
grep -Fq 'navigator.clipboard.writeText' "${VIEW}"
grep -Fq "document.execCommand('copy')" "${VIEW}"
grep -Fq 'renderedProfiles[Number' "${VIEW}"
grep -Fq 'id="strategyLabResultBox"' "${VIEW}"
grep -Fq 'id="strategyLabResultTarget"' "${VIEW}"
grep -Fq 'id="strategyLabResultOutcome"' "${VIEW}"
grep -Fq 'id="strategyLabResultRestoration"' "${VIEW}"
grep -Fq "lang._('Complete Traffic Strategy profile')" "${VIEW}"
if grep -Fq 'data-profile=' "${VIEW}"; then
    echo 'FAIL: profile bytes must not be embedded in HTML data attributes' >&2
    exit 1
fi
# Execute the actual UI predicates for current and legacy records, rather than
# relying only on textual presence checks (no browser/server required).
node - "${VIEW}" <<'JAVASCRIPT'
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2], 'utf8');
function extract(name) {
    const pattern = new RegExp('function ' + name + '\\([^\\n]*\\) \\{[^\\n]*\\}');
    const found = source.match(pattern);
    assert.ok(found, name + ' predicate missing');
    return found[0];
}
const predicates = vm.runInNewContext(
    extract('verifiedReplay') + '\n' + extract('savedJobId') +
    '\n({verifiedReplay:verifiedReplay,savedJobId:savedJobId})'
);
assert.equal(predicates.verifiedReplay({profile_replay:{verified:true,attempt_count:1,pass_count:1}}), true);
for (const record of [{}, {profile_replay:{}}, {profile_replay:{verified:false,attempt_count:1,pass_count:1}}, {profile_replay:{verified:'true'}}]) {
    assert.equal(predicates.verifiedReplay(record), false);
}
for (const job of ['job.ABC123','job.x9']) assert.equal(predicates.savedJobId(job), true);
for (const job of ['../job.x','job.x/y','job.x-1','job.','bad','job. test']) assert.equal(predicates.savedJobId(job), false);
console.log('PASS: real Stage5 replay/ID predicates reject unverifiable legacy records and invalid job IDs');
JAVASCRIPT

echo 'PASS: terminal results expose structured evidence and safe complete-profile copy controls'
