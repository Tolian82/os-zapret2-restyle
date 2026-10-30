#!/usr/bin/env python3
"""Offline Stage 5 TLS profile eligibility binding; NEVER proves execution or A07."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import ipaddress
import json
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / 'src/opnsense/scripts/OPNsense/Zapret/backend'
FILES = {
    'owner': ('owner.json', 262144),
    'argv': ('dvtws.args', 262144),
    'witness': ('dvtws.args.global-policy.json', 65536),
    'user': ('hostlist-user.txt', 12 * 1024 * 1024),
    'youtube': ('hostlist-youtube.txt', 12 * 1024 * 1024),
    'exclude': ('ipset-exclude.txt', 262144),
    **{x: (f'ipset-{x}.txt', 262144) for x in ('telegram', 'discord', 'x', 'sip', 'custom')},
}


class PhaseAError(ValueError):
    pass


def require_file(file: Path, max_size: int) -> bytes:
    try:
        info = file.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 <= info.st_size <= max_size:
            raise PhaseAError('unsafe or oversized input: ' + file.name)
        raw = file.read_bytes()
        if len(raw) != info.st_size or b'\x00' in raw:
            raise PhaseAError('inconsistent or binary input: ' + file.name)
        return raw
    except OSError as exc:
        raise PhaseAError('unreadable input: ' + file.name) from exc


def companion(name: str, path: Path):
    require_file(path, 300000)
    if path == NATIVE / 'global_exclusions.py' and str(NATIVE) not in sys.path:
        sys.path.insert(0, str(NATIVE))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PhaseAError('unavailable verified companion: ' + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect(bundle: Path, plan_file: Path, baseline: Path | None = None) -> dict:
    if not bundle.is_dir() or bundle.is_symlink():
        raise PhaseAError('unsafe evidence bundle directory')
    ctl = companion('phase_a_controller', HERE / 'stage5-wan-baseline-capture.py')
    target = companion('phase_a_selector', HERE / 'stage5-wan-target-preflight.py')
    owner = companion('phase_a_owner', HERE / 'stage5-installed-evidence.py')
    native = companion('phase_a_native', NATIVE / 'global_exclusions.py')
    signature = companion('phase_a_signature', HERE / 'stage5-tls-profile-signature.py')
    plan = ctl.safe_plan(plan_file)
    manifest = plan['analysis_manifest']
    ip = ipaddress.ip_address(manifest['remote_ip'])
    family = 'ipv' + str(ip.version)
    domain = manifest['domain']
    raw = {key: require_file(bundle / filename, limit)
           for key, (filename, limit) in FILES.items()}
    snapshot = owner._parse_snapshot(raw['owner'], 'Phase A')
    if snapshot['installed_plugin_version'] != '0.6.1_12':
        raise PhaseAError('unrecognized installed candidate')
    argv = raw['argv'].decode('utf-8')
    policy = json.loads(raw['witness'].decode('utf-8'))
    rows = native.segments(argv)
    digest = hashlib.sha256(raw['argv']).hexdigest()
    if (not isinstance(policy, dict) or policy.get('schema') != 1 or
        policy.get('argv_sha256') != digest or type(policy.get('profiles')) is not int or
        policy['profiles'] != len(rows)):
        raise PhaseAError('final argv differs from native release policy witness')
    profiles = target.profile_summary(argv, (
        native.segments, native.templates_and_imports, native.inherited, native.visible))
    lists = {name: raw[key].decode('utf-8') for key, name in
             (('user', 'hostlist-user.txt'), ('youtube', 'hostlist-youtube.txt'))}
    excluded = target.parse_networks(raw['exclude'].decode('utf-8'), 'exclude')
    voices = {service: target.parse_networks(raw[service].decode('utf-8'), service)
              for service in ('telegram', 'discord', 'x', 'sip', 'custom')}
    hits = {str(target.MANAGED / name) for name, content in lists.items()
            if target.hostlist_hits(content, domain)}
    blocked = bool(target.matches(ip, excluded) or any(
        target.matches(ip, net) for net in voices.values()))
    eligible = [] if blocked else [p['index'] for p in profiles
        if p['ordinary'] and p['tls_443'] and family in p['families']
        and hits.intersection(p['hostlists'])]
    result = {
        'status': 'PHASE_A_REVIEW_ONLY',
        'identity': {'family': family, 'domain_declared_only': domain,
                     'remote_ip': str(ip), 'source_port': manifest['baseline']['source_port'],
                     'wan_declared_only': manifest['wan_interface']},
        'native_owner_snapshot_validated': True,
        'native_config_digest': snapshot['config_digest'],
        'final_argv_sha256': digest,
        'managed_inputs_sha256': hashlib.sha256(b''.join(
            key.encode() + b'\x00' + raw[key] for key in sorted(FILES)
            if key not in ('owner', 'argv', 'witness'))).hexdigest(),
        'final_profile_count': len(profiles),
        'eligible_profile_indexes': eligible,
        'eligible_profile_action_signatures': signature.candidate_signatures(
            argv, native, eligible, len(profiles)),
        'action_signatures_are_runtime_proof': False,
        'candidate_classification': ('TARGET_EXCLUDED_OR_VOICE_OVERLAP' if blocked else
                                     'NO_ELIGIBLE_TLS_PROFILE' if not eligible else
                                     'MULTIPLE_ELIGIBLE_PROFILES' if len(eligible) > 1 else
                                     'ONE_ELIGIBLE_PROFILE'),
        'runtime_profile_selected': 'UNVERIFIED',
        'runtime_process_continuity': 'UNVERIFIED',
        'wan_packet_provenance': 'UNVERIFIED',
        'tls_clienthello_sni_on_wire': 'UNVERIFIED',
        'baseline_strategy_mutation': 'UNVERIFIED',
        'owner_live_authorized': False, 'phase_b_permitted': False,
        'exclude_effect_proven': False, 'installed_a07': 'OPEN', 'installed_a08': 'OPEN',
    }
    if baseline is not None:
        pcap = companion('phase_a_pcap', HERE / 'stage5-wan-pcap-attribution.py')
        data = pcap.read_file(baseline, pcap.MAX_PCAP)
        observed = pcap.summarize(data, pcap.parse_manifest(
            json.dumps(manifest).encode('utf-8')), 'baseline')
        result['retained_baseline'] = {
            'sha256': hashlib.sha256(data).hexdigest(),
            'five_tuple_correlated_in_supplied_pcap': bool(observed['capture_correlated']),
            'same_sequence_conflicts': observed['same_sequence_conflicts'],
            'payload_packets': observed['payload_packets'],
        }
        if not observed['capture_correlated'] or observed['same_sequence_conflicts']:
            result['candidate_classification'] = 'AMBIGUOUS_BASELINE_STOP'
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--retained-baseline', type=Path)
    opts = p.parse_args(argv)
    print(json.dumps(inspect(opts.bundle, opts.plan, opts.retained_baseline), sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (PhaseAError, ValueError, OSError, KeyError, TypeError, UnicodeError) as exc:
        print('STAGE5_TLS_PHASE_A=BLOCKED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
