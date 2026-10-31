#!/usr/bin/env python3
"""Read-only, exact-HEAD inventory of configd's directly invoked sources.

This is an audit, NOT a second compatibility policy and NOT runtime qualification.
The installed package can have different file modes from the source Git index.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ACTIONS = 'src/opnsense/service/conf/actions.d/actions_zapret.conf'
CONTROLLERS = 'src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/'
PREFIX = '/usr/local/'
REQUIRED = {'start', 'stop', 'status', 'voice_inspect', 'strategy_lab_start',
            'setup_install', 'extra_resources_install', 'shared_apply'}


def git(*args, root):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def modes(root):
    data = git('ls-files', '--stage', '-z', root=root).decode('utf-8')
    output = {}
    for record in data.split('\0'):
        if record:
            meta, path = record.split('\t', 1)
            mode, _, _ = meta.split(' ', 2)
            output[path] = mode
    return output


def parse_actions(text):
    actions = {}
    current = None
    for number, raw in enumerate(text.splitlines(), 1):
        value = raw.strip()
        if not value or value.startswith(('#', ';')):
            continue
        m = re.fullmatch(r'\[([a-z][a-z0-9_]*)\]', value)
        if m:
            current = m.group(1)
            if current in actions:
                raise ValueError(f'duplicate action {current} line {number}')
            actions[current] = {'section_line': number}
        elif value.startswith('command:'):
            if current is None or 'command' in actions[current]:
                raise ValueError(f'command outside/duplicate section line {number}')
            actions[current].update(command=value.split(':', 1)[1].strip(), command_line=number)
        elif value.startswith('type:') and current is not None:
            actions[current]['type'] = value.split(':', 1)[1].strip()
    missing = sorted(REQUIRED - actions.keys())
    if missing:
        raise ValueError(f'missing required configd actions: {missing}')
    for name, action in actions.items():
        if not action.get('command') or not action.get('type'):
            raise ValueError(f'configd action {name} has incomplete command/type')
    return actions


def parse_controllers(root, index):
    out = []
    for path in sorted(p for p in index if p.startswith(CONTROLLERS) and p.endswith('.php')):
        body = (root / path).read_text(encoding='utf-8')
        for match in re.finditer(r'configdRun\s*\(', body):
            # Restrict the attribution to the immediate literal first argument.
            tail = body[match.end():match.end()+160]
            direct = re.match(r'\s*[\'"]zapret\s+([a-z][a-z0-9_]*)[\'"]', tail)
            out.append({'source': path, 'line': body.count('\n', 0, match.start()) + 1,
                        'action': direct.group(1) if direct else None,
                        'binding': 'literal' if direct else 'dynamic-or-nonliteral'})
    return out


def audit(root, expected_head=None):
    root = Path(root).resolve()
    head = git('rev-parse', 'HEAD', root=root).decode().strip()
    if expected_head and expected_head != head:
        raise ValueError(f'wrong exact HEAD: {head} != {expected_head}')
    index = modes(root)
    if ACTIONS not in index:
        raise ValueError('configd action registry untracked')
    records = parse_actions((root / ACTIONS).read_text(encoding='utf-8'))
    direct = []
    issues = []
    for name, obj in records.items():
        command = obj['command']
        parts = command.split()
        first = parts[0] if parts else ''
        if not first.startswith(PREFIX):
            issues.append(f'{name}: command executable is not an absolute /usr/local/ path')
            continue
        interpreter = first.startswith('/usr/local/bin/python3')
        if interpreter:
            sources = [p.rstrip(';') for p in parts[1:] if p.startswith(PREFIX)]
            if not sources:
                issues.append(f'{name}: direct Python invocation has no absolute script path')
                continue
            installed = sources[0]
            kind = 'explicit-python'
        else:
            installed = first.rstrip(';')
            kind = 'direct-script'
        if not installed.startswith(PREFIX):
            issues.append(f'{name}: unsupported entrypoint: {installed}')
            continue
        source = 'src/' + installed[len(PREFIX):]
        mode = index.get(source)
        if mode is None:
            issues.append(f'{name}: missing tracked source {source}')
        direct.append({'action': name, 'registry_line': obj['section_line'],
                       'command_line': obj['command_line'], 'command': command,
                       'configd_type': obj['type'], 'kind': kind,
                       'interpreter': first if interpreter else None,
                       'installed_entrypoint': installed, 'source': source,
                       'git_mode': mode,
                       'direct_executable_mode': kind == 'direct-script' and mode == '100755',
                       'requires_native_mode_review': kind == 'direct-script' and mode != '100755'})
    controls = parse_controllers(root, index)
    for ref in controls:
        if ref['action'] is not None and ref['action'] not in records:
            issues.append(f"{ref['source']}:{ref['line']}: unknown configd action {ref['action']}")
    return {'schema': 1, 'proof': 'source-git-configd-callpath-not-installed-runtime',
            'head': head, 'registered_actions': len(records),
            'direct_actions': direct, 'controller_refs': controls,
            'explicit_python_actions': sorted(x['action'] for x in direct if x['kind']=='explicit-python'),
            'source_mode_review': sorted(x['action'] for x in direct if x['requires_native_mode_review']),
            'unresolved_controller_refs': sum(x['action'] is None for x in controls),
            'errors': sorted(issues), 'owner_target_qualified': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--expected-head')
    p.add_argument('--json', type=Path, required=True)
    p.add_argument('--markdown', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.repo, args.expected_head)
    if result['errors']:
        raise SystemExit('CONFIGD_CALLPATH_ERRORS=' + json.dumps(result['errors']))
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    rows = ['# Stage 0 source configd entrypoints', '', f"Exact HEAD: {result['head']}; {result['registered_actions']} actions.",
            '', '| Action | Config line | Invocation | Source Git mode | Installed path |', '|---|---:|---|---|---|']
    for x in result['direct_actions']:
        rows.append(f"| {x['action']} | {x['command_line']} | {x['kind']} | {x['git_mode']} | {x['installed_entrypoint']} |")
    rows += ['', f"**Needs native executable mode review:** {', '.join(result['source_mode_review']) or 'none'}.",
             f"**Unresolved PHP configd calls:** {result['unresolved_controller_refs']}; inspect before migration.",
             '', 'This source audit is not an installed-package file/mode, transitively Python-free Stop/Status, or target OPNsense runtime proof.', '']
    args.markdown.write_text('\n'.join(rows), encoding='utf-8')
    print('STAGE0_CONFIGD_CALLPATH=PASS ' + json.dumps({k:result[k] for k in ('head','registered_actions','explicit_python_actions','source_mode_review','unresolved_controller_refs')},sort_keys=True))


if __name__ == '__main__':
    main()
