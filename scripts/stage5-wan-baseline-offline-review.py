#!/usr/bin/env python3
"""Read an existing owner-approved Stage 5 baseline PCAP; never send packets.

Checks the original generated plan and exact TCP five-tuple using the existing
strict Ethernet-PCAP parser. No system inspection, network, IPFW, GUI or Config
access. A successful output is NOT proof of live DPI modification or Exclude.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
DIRECTORY = Path(__file__).resolve().parent
PLAN_TOOL = DIRECTORY / 'stage5-wan-acquisition-plan.py'
CONTROLLER = DIRECTORY / 'stage5-wan-baseline-capture.py'
ATTRIBUTION = DIRECTORY / 'stage5-wan-pcap-attribution.py'


class ReviewError(ValueError):
    pass


def companion(name: str, file: Path):
    try:
        mode = file.lstat()
    except OSError as exc:
        raise ReviewError('missing trusted companion: ' + file.name) from exc
    if not stat.S_ISREG(mode.st_mode) or mode.st_nlink != 1:
        raise ReviewError('unsafe trusted companion: ' + file.name)
    spec = importlib.util.spec_from_file_location(name, file)
    if spec is None or spec.loader is None:
        raise ReviewError('cannot load trusted companion: ' + file.name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def report(observation: dict, capture_sha256: str, manifest: dict) -> dict:
    """Classify observed packets only; never promote them to mutation proof."""
    if observation['same_sequence_conflicts']:
        condition = 'AMBIGUOUS_SAME_SEQUENCE_TCP_PAYLOAD'
    elif observation['capture_correlated']:
        condition = 'CORRELATED_TCP_PAYLOAD_OBSERVED_ONLY'
    else:
        condition = 'INCONCLUSIVE_NO_UNAMBIGUOUS_TCP_PAYLOAD'
    return {
        'status': 'BASELINE_OFFLINE_REVIEW_ONLY',
        'condition': condition,
        'capture_sha256': capture_sha256,
        'declared_wan_interface': manifest['wan_interface'],
        'declared_domain_unverified': manifest['domain'],
        'baseline_observation': observation,
        'wan_origin_proven': False,
        'tls_sni_proven': False,
        'engine_strategy_modification_proven': False,
        'exclude_effect_proven': False,
        'installed_a07': 'OPEN',
        'installed_a08': 'OPEN',
        'note': 'Read-only classification of one existing five-tuple PCAP; neither a comparison phase nor Lua/Exclude proof. No capture bytes or requests exported.'
    }


def inspect(plan_path: Path, capture_path: Path) -> dict:
    # The controller's existing generator check rejects altered plans without
    # any live execution. The attribution parser rejects unsafe/bad PCAPs.
    companion('stage5_review_generator', PLAN_TOOL)
    ctl = companion('stage5_review_controller', CONTROLLER)
    parser = companion('stage5_review_attribution', ATTRIBUTION)
    plan = ctl.safe_plan(plan_path)
    manifest = parser.parse_manifest(json.dumps(plan['analysis_manifest']).encode())
    raw = parser.read_file(capture_path, parser.MAX_PCAP)
    observed = parser.summarize(raw, manifest, 'baseline')
    return report(observed, hashlib.sha256(raw).hexdigest(), manifest)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True, type=Path)
    p.add_argument('--baseline', required=True, type=Path)
    args = p.parse_args(argv)
    if args.plan.resolve() == args.baseline.resolve():
        raise ReviewError('plan and capture must be distinct')
    result = inspect(args.plan, args.baseline)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ReviewError, ValueError, OSError, KeyError, TypeError) as exc:
        print('BASELINE_OFFLINE_REVIEW=UNVERIFIED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
