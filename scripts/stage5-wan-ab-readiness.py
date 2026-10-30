#!/usr/bin/env python3
"""Offline Stage 5 A07 A/B/restoration evidence review; NEVER runs WAN probes or Apply.

This reviewer cannot establish a selected Lua strategy, TLS SNI, actual WAN
origin, operator consent, or DPI modification. It never authorizes phase B.
"""
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
ROOT = Path(__file__).resolve().parent
COMPANIONS = {
    'controller': 'stage5-wan-baseline-capture.py',
    'pcap': 'stage5-wan-pcap-attribution.py',
    'owner': 'stage5-installed-evidence.py',
}
MAX_LIST = 65536


class ReadinessError(ValueError):
    pass


def companion(name):
    path = ROOT / COMPANIONS[name]
    try:
        info = path.lstat()
    except OSError as exc:
        raise ReadinessError('missing reviewed companion: ' + name) from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ReadinessError('unsafe reviewed companion: ' + name)
    spec = importlib.util.spec_from_file_location('a07_' + name, path)
    if spec is None or spec.loader is None:
        raise ReadinessError('cannot load reviewed companion: ' + name)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def networks(raw):
    """Independent *read-only* witness of managed CIDRs, never an Apply parser."""
    result = []
    try:
        lines = raw.decode('ascii').splitlines()
        if len(lines) > 4096:
            raise ReadinessError('oversized managed exclusion list')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            net = ipaddress.ip_network(line, strict=True)
            if net.prefixlen == 0:
                raise ReadinessError('unbounded exclusion list witness')
            result.append(net)
    except (UnicodeError, ValueError) as exc:
        raise ReadinessError('invalid managed exclusion witness') from exc
    return result


def contains(raw, target):
    return any(target in net for net in networks(raw) if net.version == target.version)


def review(plan, baseline=None, completed=None):
    ctl = companion('controller')
    pcap = companion('pcap')
    trusted = ctl.safe_plan(plan)
    manifest = pcap.parse_manifest(json.dumps(trusted['analysis_manifest']).encode())
    if manifest['baseline'] != manifest['excluded']:
        raise ReadinessError('phase identity differs')
    result = {
        'status': 'A07_PLAN_REVIEW_ONLY',
        'family': 'ipv' + str(ipaddress.ip_address(manifest['remote_ip']).version),
        'identity': {'domain': manifest['domain'], 'remote_ip': manifest['remote_ip'],
                     'wan_interface_declared_only': manifest['wan_interface'],
                     'source_port': manifest['baseline']['source_port']},
        'phase_b_permitted': False, 'owner_live_authorized': False,
        'baseline_strategy_modification_proven': False,
        'wan_origin_proven': False, 'tls_sni_proven': False,
        'exclude_effect_proven': False, 'process_continuity_proven': False,
        'installed_a07': 'OPEN', 'installed_a08': 'OPEN',
        'next_gate': 'INDEPENDENT_BASELINE_STRATEGY_MODIFICATION_AND_EXPLICIT_OWNER_APPROVAL',
    }
    if baseline is None:
        if completed is not None:
            raise ReadinessError('no baseline for complete review')
        return result
    raw = pcap.read_file(baseline, pcap.MAX_PCAP)
    observation = pcap.summarize(raw, manifest, 'baseline')
    result['baseline'] = {
        'capture_sha256': hashlib.sha256(raw).hexdigest(),
        'five_tuple_correlated': observation['capture_correlated'],
        'outgoing_packets': observation['outgoing_packets'],
        'payload_packets': observation['payload_packets'],
        'same_sequence_conflicts': observation['same_sequence_conflicts'],
    }
    result['status'] = 'A07_BASELINE_CAPTURE_REVIEW_ONLY'
    if not observation['capture_correlated'] or observation['same_sequence_conflicts']:
        result['next_gate'] = 'AMBIGUOUS_BASELINE_CAPTURE_STOP'
    if completed is None:
        return result
    if not observation['capture_correlated'] or observation['same_sequence_conflicts']:
        raise ReadinessError('baseline capture is not unambiguous')
    excluded = pcap.read_file(completed['excluded'], pcap.MAX_PCAP)
    comparison = pcap.compare(manifest, raw, excluded)
    if not comparison['five_tuple_capture_correlated']:
        raise ReadinessError('A/B captures do not contain matching attributed flows')
    owner = companion('owner')
    snapshots = {key: owner._parse_snapshot(
        pcap.read_file(completed[key + '_owner'], owner.MAX_SNAPSHOT), key)
        for key in ('original', 'excluded', 'restored')}
    # The native owner comparison checks the real installed inspector's
    # Config/engine/rule scopes, but not PID lifetime or WAN provenance.
    first, middle, last = (snapshots[k] for k in ('original', 'excluded', 'restored'))
    if middle['config_digest'] == first['config_digest']:
        raise ReadinessError('excluded phase has no changed native Config witness')
    if last['config_digest'] != first['config_digest']:
        raise ReadinessError('native Config digest not restored')
    if (last['rule_count'], last['table_count'], owner._scope(last)) != (
            first['rule_count'], first['table_count'], owner._scope(first)):
        raise ReadinessError('native IPFW/Voice owner scope not restored')
    snapshots_raw = {key: pcap.read_file(completed[key + '_exclude'], MAX_LIST)
                     for key in ('original', 'excluded', 'restored')}
    target = ipaddress.ip_address(manifest['remote_ip'])
    if (contains(snapshots_raw['original'], target) or
            not contains(snapshots_raw['excluded'], target)):
        raise ReadinessError('pinned endpoint has no verified A/B exclusion transition')
    if snapshots_raw['restored'] != snapshots_raw['original']:
        raise ReadinessError('original managed Exclude bytes not restored')
    if snapshots_raw['excluded'] == snapshots_raw['original']:
        raise ReadinessError('excluded managed Exclude did not change')
    result['status'] = 'A07_OFFLINE_AB_RESTORATION_REVIEW_ONLY'
    result['pair'] = {
        'same_pinned_five_tuple': comparison['same_remote_endpoint'] and
                                  comparison['same_source_port'],
        'payload_comparison': comparison['payload_comparison'],
        'excluded_capture_sha256': hashlib.sha256(excluded).hexdigest(),
    }
    result['restoration'] = {
        'original_exclude_sha256': hashlib.sha256(snapshots_raw['original']).hexdigest(),
        'managed_exclude_bytes_equal': True,
        'native_config_digest_equal': True,
        'native_owner_scope_equal': True,
        'owner_process_continuity_unverified': True,
    }
    result['next_gate'] = 'INDEPENDENT_WAN_STRATEGY_ATTRIBUTION_AND_OWNER_REVIEW_REQUIRED'
    return result


def main(argv=None):
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--plan', required=True, type=Path)
    args.add_argument('--baseline', type=Path)
    args.add_argument('--excluded', type=Path)
    for phase in ('original', 'excluded', 'restored'):
        args.add_argument('--' + phase + '-owner', type=Path)
        args.add_argument('--' + phase + '-exclude', type=Path)
    a = args.parse_args(argv)
    keys = ('excluded',) + tuple(phase + '_' + kind for phase in
                                 ('original', 'excluded', 'restored') for kind in ('owner', 'exclude'))
    present = {key: getattr(a, key) for key in keys if getattr(a, key) is not None}
    if present and (a.baseline is None or len(present) != len(keys)):
        raise ReadinessError('full A/B review requires all phase files and baseline')
    paths = [a.plan] + ([a.baseline] if a.baseline else []) + list(present.values())
    if len({str(p.resolve()) for p in paths}) != len(paths):
        raise ReadinessError('evidence input paths must be distinct')
    print(json.dumps(review(a.plan, a.baseline, present or None), sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ReadinessError, ValueError, OSError, KeyError, TypeError) as exc:
        print('A07_OFFLINE_REVIEW=BLOCKED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
