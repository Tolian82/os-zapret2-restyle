#!/usr/bin/env node
// P4b: exercise the actual Strategies Full Help renderer with a minimal DOM.
// No browser backend is mocked in native installed-CI acceptance; this test
// only probes the pure presentation boundary for cached API response shapes.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const page = readFileSync(new URL('../src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt',
                                  import.meta.url), 'utf8');
const begin = 'function renderResourceHelpInventory(data) {';
const end = 'function requestResourceHelpInventory(force) {';
assert.equal(page.split(begin).length, 2, 'single real help renderer required');
assert.equal(page.split(end).length, 2, 'single real cache-only request required');
const original = page.slice(page.indexOf(begin), page.indexOf(end)).trim();
assert.ok(original.endsWith('}'), 'unexpected renderer boundary');
assert.ok(!/(?:fetch\s*\(|git\s|\.html\s*\(|eval\s*\()/i.test(original),
          'resource inventory help must use text-only rendering');

class Element {
  constructor(tag, attributes = {}) {
    this.tag = tag;
    this.attributes = attributes;
    this.nodes = [];
    this.content = '';
    this.classes = new Set((attributes.class || '').split(' ').filter(Boolean));
  }
  empty() { this.nodes = []; this.content = ''; return this; }
  text(value) {
    if (arguments.length === 0) return this.content + this.nodes.map(x => x.text()).join(' ');
    this.nodes = [];
    this.content = String(value);
    return this;
  }
  append(child) { assert.ok(child instanceof Element); this.nodes.push(child); return this; }
  appendTo(parent) { parent.append(this); return this; }
  addClass(value) { this.classes.add(value); return this; }
  children() { return this.nodes; }
  descendants(tag) {
    return this.nodes.flatMap(x => [...(x.tag === tag ? [x] : []), ...x.descendants(tag)]);
  }
}

const translations = {
  installHelp: 'Optional bundle NOT installed; extra files may be added.',
  listUnavailable: 'Inventory cache UNKNOWN.',
  native: 'Installed Zapret2',
  other: 'Other',
  lua: 'Lua',
  bin: 'BIN',
  none: 'No installed files',
};

function fixture(data) {
  const panel = new Element('panel');
  const $ = (selector, attrs = {}) => {
    if (selector === '#zapretExtraResourceHelp') return panel;
    const m = /^<([a-z]+)\/>$/.exec(selector);
    assert.ok(m, 'unexpected DOM selector: ' + selector);
    return new Element(m[1], attrs);
  };
  // Evaluate exactly the function extracted from production general.volt,
  // not a second implementation or a regex-only source assertion.
  const render = new Function('$', 'extrasText', 'let helpInventoryLastInstalled = false;\n' +
                              original + '\nreturn renderResourceHelpInventory;')($, translations);
  render(data);
  return panel;
}

const upstream = {name: 'native.lua', origin: 'upstream'};
const nativeBin = {name: 'native.bin', origin: 'upstream'};
const additional = {name: 'additional.lua', origin: 'other'};

const noBundle = fixture({status: 'ok', installed: false,
                          lua: [upstream], bin: [nativeBin]});
assert.match(noBundle.text(), /Optional bundle NOT installed/);
assert.deepEqual(noBundle.descendants('li').map(x => x.text()),
                 ['native.lua', 'native.bin'],
                 'installed=false must NOT hide upstream Lua/BIN');
assert.ok(noBundle.descendants('li').every(x => x.classes.has('text-success')));

const withBundle = fixture({status: 'ok', installed: true,
                            lua: [upstream, additional], bin: [nativeBin]});
assert.doesNotMatch(withBundle.text(), /Optional bundle NOT installed/);
assert.deepEqual(withBundle.descendants('li').map(x => x.text()),
                 ['native.lua', 'additional.lua', 'native.bin']);
assert.ok(withBundle.descendants('li')[1].classes.has('text-info'));

const empty = fixture({status: 'ok', installed: false, lua: [], bin: []});
assert.match(empty.text(), /Optional bundle NOT installed/);
assert.equal(empty.descendants('li').filter(x => x.text() === 'No installed files').length, 2);

for (const bad of [null, {status: 'unavailable'},
                   {status: 'ok', installed: false},
                   {status: 'ok', installed: 'false', lua: [], bin: []},
                   {status: 'ok', installed: false, lua: {}, bin: []}]) {
  const panel = fixture(bad);
  assert.match(panel.text(), /Inventory cache UNKNOWN/);
  assert.equal(panel.descendants('li').length, 0);
  assert.doesNotMatch(panel.text(), /Optional bundle NOT installed/);
}
const malicious = fixture({status: 'ok', installed: false,
                           lua: [{name: '<script>bad</script>.lua', origin: 'other'}], bin: []});
assert.ok(!malicious.text().includes('<script>'), 'malformed names must not render as HTML');
// Native OPNsense full-help preset may reapply with toggleClass(), changing
// icon class while real field help is still visible. Read the *production*
// isResourceHelpEnabled function; do not substitute a second implementation.
const helpStart = 'function isResourceHelpEnabled() {';
assert.equal(page.split(helpStart).length, 2, 'single real native Help state helper');
const helpBody = page.slice(page.indexOf(helpStart), page.indexOf(begin)).trim();
const isEnabled = (iconOn, preset, helpShown, helpHidden = false) => {
  const nativeHelp = {
    length: 1,
    hasClass(c) { return c === 'show' ? helpShown : c === 'hidden' ? helpHidden : false; },
  };
  const icon = { hasClass(c) { return c === 'fa-toggle-on' && iconOn; } };
  const jquery = selector => selector.startsWith('#show_all_help_') ? icon : nativeHelp;
  const fakeWindow = { sessionStorage: { getItem(k) {
    assert.equal(k, 'all_help_preset'); return preset ? '1' : '0';
  }}};
  return new Function('$', 'window', helpBody +
    '\nreturn isResourceHelpEnabled;')(jquery, fakeWindow)();
};
assert.equal(isEnabled(true, false, false), true, 'native icon ON is authoritative');
assert.equal(isEnabled(false, true, true), true, 'native preset+help shown survives icon reinit');
assert.equal(isEnabled(false, true, false), false, 'preset alone is insufficient');
assert.equal(isEnabled(false, true, true, true), false, 'hidden native help does not qualify');
assert.equal(isEnabled(false, false, true), false, 'popup alone cannot open whole catalog');
assert.equal(isEnabled(false, false, false), false, 'native Help OFF must stay OFF');

// Regression for the real native OPNsense 26.7 initialization order: the
// icon mutates first; the stored preset then marks native field help 'show'.
// Verify the actual source observes the later transition, not only the icon.
const observerStart = "const resourceHelpNativeSource = document.querySelector(";
const observerEnd = "        updateResourceHelpVisibility();";
assert.equal(page.split(observerStart).length, 2, "single native source observer");
const startAt = page.indexOf(observerStart);
const stopAt = page.indexOf(observerEnd, startAt);
assert.ok(stopAt > startAt, "native source observer must precede final visibility sync");
const observerCode = page.slice(startAt, stopAt).trim();
let nativeUpdates = 0;
const observed = [];
class RecordingObserver {
  constructor(callback) { this.callback = callback; }
  observe(target, options) {
    assert.deepEqual(options.attributeFilter, ["class"]);
    observed.push({target, callback: this.callback});
  }
}
const nativeSource = { classes: new Set(["hidden"]) };
const registerObserver = new Function(
  "document", "window", "MutationObserver", "updateResourceHelpVisibility",
  observerCode + "\nreturn resourceHelpNativeSource;"
);
const result = registerObserver(
  { querySelector(selector) {
    assert.match(selector, /help_for_zapret\.strategy\.trafficargs/);
    return nativeSource;
  }},
  { MutationObserver: RecordingObserver }, RecordingObserver,
  () => nativeUpdates++
);
assert.equal(result, nativeSource);
assert.equal(observed.length, 1, "must subscribe to actual native help class");
assert.equal(observed[0].target, nativeSource);
assert.equal(isEnabled(false, true, false, true), false);
nativeSource.classes.delete("hidden");
nativeSource.classes.add("show");
observed[0].callback([{attributeName: "class", target: nativeSource}]);
assert.equal(nativeUpdates, 1, "native help class change must refresh cache Help");
assert.equal(isEnabled(false, true, true, false), true,
             "native preset and visible help must make catalog eligible");
const missing = registerObserver(
  { querySelector() { return null; } },
  { MutationObserver: RecordingObserver }, RecordingObserver,
  () => { throw new Error("no native help element must mean no callback"); }
);
assert.equal(missing, null);
assert.equal(observed.length, 1, "unknown native source must not create observer");

console.log('PASS P4b: genuine renderer shows cached native files without optional bundle; unknown stays unknown');
