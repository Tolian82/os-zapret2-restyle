#!/usr/bin/env node
// Exercise the actual pure GUI terminal classifier from the embedded Volt JS.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const view = fs.readFileSync(new URL('../src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt', import.meta.url), 'utf8');
const start = view.indexOf('        function releaseTerminalOutcome(');
const end = view.indexOf('\n        function stopRuntimePolling()', start);
assert(start !== -1 && end > start, 'missing real upstream terminal classifier');
const classifier = vm.runInNewContext('(' + view.slice(start, end).trim() + ')');

const state = (version, setup, busy = false, service = 'started') =>
    ({installed: true, version, setup, busy, service});

assert.equal(classifier(state('v1.0.5.2', 'ready'), 'v1.0.5.2', 'v1.0.6', 'started', false), 'success',
    'fast valid release switch must finish without a seen busy pulse');
assert.equal(classifier(state('v1.0.6', 'ready'), 'v1.0.6', 'v1.0.6', 'started', false), 'pending',
    'stale terminal receipt cannot complete same-version install');
assert.equal(classifier(state('v1.0.6', 'ready'), 'v1.0.6', 'v1.0.6', 'started', true), 'success',
    'same-version reinstall requires observed worker progress');
assert.equal(classifier(state('v1.0.5.2', 'ready', true), 'v1.0.5.2', 'v1.0.6', 'started', true), 'pending',
    'transient busy status cannot complete operation');
assert.equal(classifier(state('v1.0.6', 'failed'), 'v1.0.5.2', 'v1.0.6', 'started', true), 'failed',
    'failed rollback after observed activity must surface failure');
assert.equal(classifier(state('v1.0.6', 'failed'), 'v1.0.5.2', 'v1.0.6', 'started', false), 'pending',
    'old failed receipt before worker progress must not terminate a new click');
assert.equal(classifier(state('v1.0.5.2', 'ready', false, 'stopped'), 'v1.0.5.2', 'v1.0.6', 'started', true), 'pending',
    'a running original owner must come back started');
assert.equal(classifier(state('v1.0.5.2', 'ready', false, 'stopped'), 'v1.0.5.2', 'v1.0.6', 'stopped', true), 'success',
    'an originally stopped service stays stopped after setup');
assert.equal(classifier(state('v1.0.6', 'ready'), 'v1.0.5.2', 'v1.0.6', 'started', true), 'pending',
    'wrong active release cannot finish successfully');
assert.equal(classifier(null, 'v1.0.5.2', 'v1.0.6', 'started', true), 'pending',
    'unavailable API response cannot claim success');
assert.equal(classifier(state('v1.0.7', 'ready', false, 'stopped'), 'v1.0.7',
    'Not installed', 'error', false), 'success',
    'genuine initial install finishes stopped even without a seen busy pulse');
assert.equal(classifier({installed: false, setup: 'failed', busy: false},
    'v1.0.7', 'Not installed', 'error', true), 'failed',
    'failed first install with no executable must surface a real failure');
assert.equal(classifier({installed: false, setup: 'failed', busy: false},
    'v1.0.7', 'Not installed', 'error', false), 'pending',
    'stale failure without observed progress cannot terminate a new click');
assert.equal(classifier(state('v1.0.7', 'ready', false, 'started'), 'v1.0.7',
    'Not installed', 'error', true), 'pending',
    'initial runtime setup must not auto-start the service');

const script = view.slice(view.indexOf('<script>'), view.indexOf('</script>'));
const braces = script.replace(/\{\{[\s\S]*?\}\}/g, '"x"');
assert.match(script, /function ensureRuntimePolling\(busy\)/);
assert.match(script, /currentRuntimeInstalled &&[\s\S]{0,120}currentServiceState !== 'started'/);
assert.match(script, /\(releaseApplyPending \|\| busy\) && runtimePoll === null/);
assert.match(script, /runtimeStatusInFlight\) return;/);
assert.match(script, /Date\.now\(\) - releaseApplyStartedAt >= releaseApplyDeadlineMs/);
assert.match(script, /finishReleaseOperation\(true, runtimeText\.applyReview\)/);
assert.match(script, /if \(releaseApplyPending \|\| runtimeWasBusy\)/);
assert.match(script, /ensureRuntimePolling\(false\);[\s\S]{0,100}refreshRuntime\(\);/);
assert(braces.includes('releaseNeedsReview'), 'missing fail-closed retry guard');
console.log('PASS: upstream GUI terminal classifier, missing busy pulse, transient polling, bounded review');

// S05d1: execute the actual fixed-cause consumer in both languages.
const failureStart = view.indexOf('        function releaseInstallFailureMessage(xhr) {');
const failureEnd = view.indexOf('\n        // The runtime worker can finish between polls', failureStart);
assert(failureStart >= 0 && failureEnd > failureStart);
const failureSource = '(' + view.slice(failureStart, failureEnd).trim() + ')';
const known = {status: 500, responseJSON: {errorTitle: 'Zapret2 release error',
    errorMessage: 'No stable bol-van/zapret2 releases could be obtained.'}};
for (const isRussian of [false, true]) {
    const failureMessage = vm.runInNewContext(failureSource,
        {isRussian, runtimeText: {applyReview: 'REVIEW'}});
    assert.equal(failureMessage(known), isRussian
        ? 'Не удалось получить список стабильных версий Zapret2. Обновите страницу и проверьте состояние службы перед повтором.'
        : 'Could not obtain the list of stable Zapret2 releases. Reload and check the service state before retrying.');
    for (const unknown of [null, {}, {status: 0}, {status: 503, responseJSON: known.responseJSON},
        {status: 500, responseJSON: {errorMessage: known.responseJSON.errorMessage}},
        {status: 500, responseJSON: {errorTitle: 'x', errorMessage: 'untrusted backend text'}},
        {status: 500, responseJSON: {errorTitle: 'x', errorMessage: known.responseJSON.errorMessage + ' extra'}}]) {
        assert.equal(failureMessage(unknown), 'REVIEW', 'unknown cause must retain review guidance');
    }
}
assert.match(view, /finishReleaseOperation\(true, releaseInstallFailureMessage\(xhr\)\);/);
console.log('PASS: S05d1 known release-list refusal RU/EN, unknown transport review unchanged');
