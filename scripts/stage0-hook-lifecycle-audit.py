#!/usr/bin/env python3
"""Exact-HEAD Stage 0.13 package hook/lifecycle evidence, never executes hooks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HOOKS = ('pkg/+PRE_INSTALL', 'pkg/+PRE_DEINSTALL', 'pkg/+POST_DEINSTALL', 'pkg/+POST_INSTALL')
SERVICE = 'src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh'
PATHS = HOOKS + (SERVICE,)
PATTERNS = {
    'service_status': r'\$\{SERVICE_SCRIPT\}.*\bstatus\b',
    'service_stop': r'\$\{SERVICE_SCRIPT\}.*\bstop\b',
    'restart_marker': r'(?:REPLACEMENT_RESTART_MARKER|UPGRADE_RESTART_MARKER)',
    'lockf_fd9': r'LOCKF_BIN.*\b9\b|\$LOCKF_BIN.*\b9\b|\) 9>',
    'python_minor_pin': r'(?:python3\.13|python313)',
    'configd_signal': r'KILL_BIN.*-TERM',
    'configd_reload': r'\bconfigd_old_worker\b|\bconfigd_new_worker\b',
    'configctl': r'\bCONFIGCTL\b',
    'foreign_or_incomplete_refusal': r'(?:incomplete zapret lifecycle|unknown owner|foreign-or-modified-rules|never stop unverified)',
    'ipfw': r'\bIPFW_BIN\b|\bipfw\b',
    'shared_journal': r'(?:SHARED_APPLY_JOURNAL|shared_apply_operation\.py)',
    'native_stop_status': r'\b(?:stop|status)\)',
}

def cmd(root, *args):
    return subprocess.check_output(('git', '-C', str(root), *args), stderr=subprocess.PIPE).decode().strip()


def inventory(root, expected_head):
    head = cmd(root, 'rev-parse', 'HEAD')
    if not re.fullmatch('[a-f0-9]{40}', head) or head != expected_head:
        raise ValueError('exact HEAD mismatch')
    tree = cmd(root, 'ls-tree', '-r', 'HEAD').splitlines()
    index = {}
    for row in tree:
        meta, sep, path = row.partition('\t')
        if not sep:
            raise ValueError('invalid git tree entry')
        mode, kind, blob = meta.split()
        index[path] = (mode, kind, blob)
    evidence = {}
    for path in PATHS:
        if path not in index or index[path][1] != 'blob':
            raise ValueError('missing authoritative tracked hook/entrypoint: ' + path)
        mode, _, blob = index[path]
        payload = subprocess.check_output(('git', '-C', str(root), 'show', f'HEAD:{path}'))
        if hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest() != blob:
            raise ValueError('Git blob digest mismatch: ' + path)
        content = payload.decode('utf-8')
        matched = {name: [i for i, line in enumerate(content.splitlines(), 1)
                          if re.search(pattern, line, re.IGNORECASE)]
                   for name, pattern in PATTERNS.items()}
        evidence[path] = {'mode': mode, 'blob': blob, 'line_count': len(content.splitlines()),
                          'matches': {k: v for k, v in matched.items() if v}}
    return {'schema': 1, 'head': head, 'paths': evidence,
            'hook_order_documented_not_target_observed': list(HOOKS),
            'observations': classify(evidence),
            'runtime_fd9_signal_process_ownership_tested': False,
            'target_pkg_hook_execution_order_tested': False,
            'python_loss_native_stop_tested': False,
            'foreign_ipfw_cleanup_tested': False,
            'signed_target_provider_qualified': False,
            'stage0_closed': False}


def classify(rows):
    pre, pre_de, post_de, post, service = (rows[p]['matches'] for p in PATHS)
    return {
        'incoming_preinstall_reads_old_service': bool(pre.get('service_status') and pre.get('service_stop')),
        'incoming_preinstall_fd9_cold_inspection': bool(pre.get('lockf_fd9') and pre.get('shared_journal')),
        'incoming_preinstall_requires_python_for_cold_path': bool(pre.get('python_minor_pin')),
        'old_predeinstall_unknown_owner_refusal': bool(pre_de.get('foreign_or_incomplete_refusal')),
        'old_predeinstall_stop_has_no_hook_fd9': bool(pre_de.get('service_stop') and not pre_de.get('lockf_fd9')),
        'postdeinstall_no_service_action': not bool(post_de.get('service_stop') or post_de.get('configctl')),
        'postinstall_restarts_only_on_marker': bool(post.get('restart_marker') and post.get('configctl')),
        'postinstall_configd_worker_signal': bool(post.get('configd_signal') and post.get('configd_reload')),
        'postinstall_version_pinned_optional_cache': bool(post.get('python_minor_pin')),
        'service_has_shared_journal_and_ipfw': bool(service.get('shared_journal') and service.get('ipfw')),
        'source_service_is_nonexecutable': rows[SERVICE]['mode'] == '100644',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args()
    report = inventory(args.root, args.expected_head)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print('STAGE0_HOOK_LIFECYCLE=READ_ONLY ' + json.dumps({'head': report['head'],
          'observations': report['observations'], 'stage0_closed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
