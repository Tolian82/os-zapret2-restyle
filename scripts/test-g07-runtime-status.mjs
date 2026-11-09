#!/usr/bin/env node
// LC-09 G07: execute the ACTUAL general.volt native status classifier,
// without simulating a browser or claiming installed-native verification.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const view = fs.readFileSync(
    new URL('../src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt', import.meta.url),
    'utf8'
);
const controller = fs.readFileSync(
    new URL('../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php',
        import.meta.url),
    'utf8'
);
const start = view.indexOf('        function classifyRuntimeStatus(data) {');
const end = view.indexOf('\n        function renderRuntime(data) {', start);
assert(start >= 0 && end > start, 'missing real LC-09 classification function');
const classify = vm.runInNewContext('(' + view.slice(start, end).trim() + ')');

const base = {status: 'ok', installed: false, busy: false,
              setup: 'unknown', service: 'error', version: ''};
const check = (data, expected, reason) =>
    assert.equal(classify(data), expected, reason);

check(base, 'not-installed', 'empty native installation has its own category');
check({...base, setup: 'installing', busy: true}, 'installing',
      'actual setup lock holder is Installing');
check({...base, installed: true, setup: 'ready', service: 'stopped',
       version: 'v1.0.7'}, 'stopped', 'verified installed stopped state');
check({...base, installed: true, setup: 'ready', service: 'started',
       version: 'v1.0.7'}, 'started', 'verified installed real PID state');
check({...base, installed: true, setup: 'unknown', service: 'started',
       version: 'v1.0.7'}, 'started',
      'installed real service can have no setup status on a direct expert install');
check({...base, setup: 'failed'}, 'error', 'failed initial installation is Error');

const reject = [
    null, undefined, {}, {status: 'failed'}, {...base, status: 'unavailable'},
    {...base, installed: null}, {...base, installed: '0'},
    {...base, busy: null}, {...base, busy: '1'},
    {...base, service: 'started'}, {...base, version: 'v1.0.7'},
    {...base, version: undefined}, {...base, setup: 'ready'},
    {...base, installed: true, service: 'error', version: 'v1.0.7'},
    {...base, installed: true, service: 'started', version: ''},
    {...base, installed: true, service: 'started', version: 'v1x0x7'},
    {...base, installed: true, service: 'stopped', version: 'not-a-release'},
    {...base, installed: true, setup: 'garbage', service: 'started', version: 'v1.0.7'},
    {...base, installed: true, setup: undefined, service: 'started', version: 'v1.0.7'},
    {...base, installed: true, service: 'wat', version: 'v1.0.7'},
    {...base, setup: 'installing', busy: false},
    {...base, setup: 'unknown', busy: true}
];
for (const bad of reject) {
    check(bad, 'error', 'unverified status must be Error, never Not installed');
}

assert.match(view, /notInstalled: isRussian \? 'Не установлен' : 'Not installed'/);
assert.match(view, /installing: isRussian \? 'Установка…' : 'Installing…'/);
assert.match(view, /category === 'not-installed'/);
assert.match(view, /category === 'installing'/);
assert.match(view, /badge\.addClass\('label-default'\)\.text\(runtimeText\.notInstalled\)/);
assert.match(view, /releaseNeedsReview = true;/);
assert.match(controller, /'installed' => null/);
assert.match(controller, /'reason' => 'status-unavailable'/);
assert.match(controller, /count\(\$seen\) !== 5/);
assert.match(controller, /isset\(\$seen\[\$field\]\)/);
assert.match(controller, /isset\(\$runtime\['reason'\]\)/);
assert.match(controller, /\$status = isset\(\$state\['reason'\]\) \? 'unavailable' : 'ok'/);
console.log('PASS: G07 LC-09 exactly five status categories, RU/EN and malformed native output fail closed');
