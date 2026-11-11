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
console.log('PASS P4b: genuine renderer shows cached native files without optional bundle; unknown stays unknown');
