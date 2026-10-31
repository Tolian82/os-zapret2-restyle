#!/usr/bin/env python3
"""Read-only official OPNsense 26.7 repository trust *source-shape* audit.

A pinned Git source template is not an installed repository configuration,
a trusted fingerprint, or proof of a cryptographically verified pkg catalog.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

OFFICIAL_CORE_REF = 'ac08367416c1d66dea87df0ef0de24c315b5d5bc'
FINGERPRINT_PATH = '/usr/local/etc/pkg/fingerprints/OPNsense'
SOURCE_URL = '%%CORE_PACKAGESITE%%/${ABI}/%%CORE_ABI%%'


def inspect_template(data, name, channel, enabled):
    """Reject unexpected directives or duplicates, even if expected tokens exist."""
    if len(data) > 16_384:
        raise ValueError('oversized repository source template')
    text = data.decode('utf-8')
    lines = [x.strip() for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]
    if len(lines) != 7 or lines[0] != name + ': {' or lines[-1] != '}':
        raise ValueError('unexpected repository block shape or identity: ' + name)
    values = {}
    for line in lines[1:-1]:
        match = re.fullmatch(r'([a-z_]+):\s*(?:"([^"\\\r\n]+)"|([0-9]+|yes|no))\s*,?', line)
        if match is None:
            raise ValueError('invalid repository directive syntax: ' + name)
        key, quoted, bare = match.groups()
        if key in values:
            raise ValueError('duplicate repository directive: ' + key)
        values[key] = quoted if quoted is not None else bare
    expected = {
        'fingerprints': FINGERPRINT_PATH,
        'url': SOURCE_URL + '/' + channel,
        'signature_type': 'fingerprints',
        'priority': '11',
        'enabled': enabled,
    }
    if values != expected:
        raise ValueError('repository trust source mismatch: ' + name)
    return {'repo_name': name, 'channel': channel,
            'expected_fingerprint_directory': FINGERPRINT_PATH,
            'enabled_by_default': enabled == 'yes',
            'signature_type': 'fingerprints',
            'source_sha256': hashlib.sha256(data).hexdigest()}


def audit(main_path, aux_path):
    main = inspect_template(Path(main_path).read_bytes(), 'OPNsense', 'latest', 'yes')
    aux = inspect_template(Path(aux_path).read_bytes(), 'OPNsense-aux', 'aux', 'no')
    return {
        'schema': 1,
        'proof': 'pinned-official-core-source-template-only',
        'official_opnsense_core_ref': OFFICIAL_CORE_REF,
        'official_main': main,
        'official_aux': aux,
        'main_official_source_contract_valid': True,
        'aux_official_source_contract_valid': True,
        'installed_repository_configuration_qualified': False,
        'installed_trusted_fingerprint_qualified': False,
        'signed_pkg_catalog_cryptographically_verified': False,
        'owner_appliance_software_state_modified': False,
        'stage0_closed': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-repo', type=Path, required=True)
    parser.add_argument('--aux-repo', type=Path, required=True)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.main_repo, args.aux_repo)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('STAGE0_OFFICIAL_REPO_TRUST_SOURCE=' + json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
