#!/usr/bin/env python3
"""Genuine old STOPPED -> source-built official native successor, disposable OPNsense only.

This characterizes pkg behavior, NOT an atomic root-pkg admission mechanism.
Never execute on an owner appliance; no RUNNING or rollback qualification.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OPTIN = 'ZAPRET2_STAGE2_REAL_STOPPED_UPGRADE'
REVISION = '74'
OLD_VERSION = '0.6.2_1'


def load(filename):
    spec = importlib.util.spec_from_file_location(filename.replace('-', '_').replace('.', '_'),
                                                  HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load actual repository siblings in the CI checkout, not temporary fake drivers.
clean = load('stage2-opnsense-real-native-clean-install.py')
old = clean.prior
native = clean.native


class Refusal(Exception):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def normalized_config(raw):
    """Preserve all configured values except the native register.php revision metadata."""
    try:
        root = copy.deepcopy(ET.fromstring(raw))
    except ET.ParseError:
        raise Refusal('CONFIG_XML_INVALID') from None
    need(root.tag == 'opnsense' and len(root.findall('revision')) <= 1,
         'CONFIG_ROOT_OR_REVISION_AMBIGUOUS')
    for revision in root.findall('revision'):
        root.remove(revision)

    def strip_whitespace(node):
        if not (node.text or '').strip():
            node.text = None
        node.tail = None
        for child in node:
            strip_whitespace(child)

    strip_whitespace(root)
    return ET.tostring(root, encoding='utf-8')



def redacted_config_delta(before, after):
    """Expose only tags/structural counts, never any Config user values."""
    try:
        a = ET.fromstring(before)
        b = ET.fromstring(after)
    except ET.ParseError:
        return {'xml_readable': False}
    known_root = {'system', 'OPNsense', 'installedpackages', 'version',
                  'lastchange', 'interfaces', 'filter', 'nat', 'widgets'}
    known_system = {'firmware', 'hostname', 'webgui', 'ssh', 'timezone'}
    known_firmware = {'plugins', 'type'}

    def tag_label(tag, allowed):
        return tag if tag in allowed else 'other_tag_sha256_' + hashlib.sha256(
            tag.encode('utf-8')).hexdigest()[:12]

    def changed(parent_a, parent_b, allowed):
        aa = {e.tag: e for e in parent_a} if parent_a is not None else {}
        bb = {e.tag: e for e in parent_b} if parent_b is not None else {}
        return [tag_label(k, allowed) for k in sorted(set(aa) | set(bb))
                if k not in aa or k not in bb or
                ET.tostring(aa[k]) != ET.tostring(bb[k])]

    return {'xml_readable': True,
            'root_changed_tags': changed(a, b, known_root),
            'system_changed_tags': changed(a.find('system'), b.find('system'),
                                           known_system),
            'firmware_changed_tags': changed(a.find('system/firmware'),
                                             b.find('system/firmware'),
                                             known_firmware),
            'opnsense_node_changed': ET.tostring(a.find('OPNsense')) !=
                                     ET.tostring(b.find('OPNsense')) if
                                     a.find('OPNsense') is not None and
                                     b.find('OPNsense') is not None else
                                     a.find('OPNsense') is not b.find('OPNsense')}



def prove_preserved_config(before, after):
    """Allow solely OPNsense's plugin registration and revision metadata.

    No unrelated Config field, sibling, plugin entry or foreign value may move.
    """
    try:
        a = ET.fromstring(before)
        b = ET.fromstring(after)
    except ET.ParseError:
        raise Refusal('REPLACEMENT_CONFIG_XML_INVALID') from None
    need(a.tag == 'opnsense' and b.tag == 'opnsense',
         'REPLACEMENT_CONFIG_ROOT_WRONG')
    fa = a.find('system/firmware')
    fb = b.find('system/firmware')
    need(fa is not None and fb is not None,
         'REPLACEMENT_EXISTING_FIRMWARE_MISSING')
    pa, pb = fa.findall('plugins'), fb.findall('plugins')
    need(len(pa) <= 1 and len(pb) == 1,
         'REPLACEMENT_PLUGIN_REGISTRY_AMBIGUOUS')

    def names(nodes):
        raw = (nodes[0].text or '') if nodes else ''
        entries = [x for x in raw.split(',') if x]
        need(len(entries) == len(set(entries)) and
             all(x.strip() == x and x for x in entries),
             'REPLACEMENT_DUPLICATE_OR_MALFORMED_PLUGIN_LIST')
        return entries

    before_names = names(pa)
    after_names = names(pb)
    expected = set(before_names) | {native.NAME}
    need(set(after_names) == expected and native.NAME in after_names and
         (after_names == before_names or after_names == sorted(expected)),
         'REPLACEMENT_FOREIGN_PLUGIN_REGISTRY_MODIFIED')

    aa, bb = copy.deepcopy(a), copy.deepcopy(b)
    for root in (aa, bb):
        for revision in root.findall('revision'):
            root.remove(revision)
        firmware = root.find('system/firmware')
        for node in firmware.findall('plugins'):
            firmware.remove(node)

    def strip_formatting(node):
        if not (node.text or '').strip():
            node.text = None
        node.tail = None
        for child in node:
            strip_formatting(child)

    strip_formatting(aa)
    strip_formatting(bb)
    need(ET.tostring(aa, encoding='utf-8') == ET.tostring(bb, encoding='utf-8'),
         'REPLACEMENT_CONFIG_CHANGED_BEYOND_OFFICIAL_METADATA:' +
         json.dumps(redacted_config_delta(before, after), sort_keys=True))
    return {'plugin_names_preserved': True,
            'plugin_registry_count': len(after_names),
            'plugin_name_registered': True,
            'all_non_registry_config_preserved': True,
            'only_normal_revision_metadata_exempted': True}


def check_old_archive(path):
    need(path.is_file() and not path.is_symlink(), 'OLD_ARCHIVE_NOT_REGULAR')
    archive, _service = old.archive_data(path)  # immutable published SHA
    need(archive.get('name') == old.NAME and
         archive.get('version') == OLD_VERSION and
         archive.get('abi') == old.ABI, 'OLD_ARCHIVE_IDENTITY_WRONG')
    return archive


def replace_with_actual_pkg(path):
    # Version-distinct native pkg replacement; do NOT disable original scripts.
    # The -f allows a locally supplied archive to supersede installed pkgdb.
    # Do not hold an outer FD9 over native pkg; genuine hooks lock internally.
    result = clean.run(['pkg', '-o', 'REPO_AUTOUPDATE=false', 'add', '-f', str(path)],
                       timeout=230)
    need(result.returncode == 0 and
         'os-zapret2-restyle was installed.' in result.stdout,
         'GENUINE_STOPPED_REPLACEMENT_POSTINSTALL_NOT_PROVEN:rc=' +
         str(result.returncode) + ':' + (result.stdout + result.stderr)[-450:])
    return {'native_pkg_exit': result.returncode,
            'original_postinstall_success_observed': True,
            'version_distinct_local_archive_replacement': True}


def verify_cold_runtime():
    inspector = load('stage0-opnsense-prepkg-readonly.py')
    inspector.check_no_owners((inspector.JOURNAL, *inspector.MARKERS,
                               *inspector.PIDFILES, inspector.PENDING_EXTRA))
    inspector.check_process_census(inspector.checked_process_census())
    ipfw = inspector.command(['/sbin/ipfw', '-q', 'list'])
    inspector.check_kernel_cold(
        inspector.command(['/sbin/kldstat', '-q', '-m', 'ipfw']).returncode,
        inspector.command(['/sbin/kldstat', '-q', '-m', 'ipdivert']).returncode,
        ipfw.returncode, ipfw.stdout + ipfw.stderr)
    return {'no_plugin_processes_or_markers': True,
            'no_ipfw_or_ipdivert_kernel_ownership': True}


def execute(archive):
    need(os.environ.get(OPTIN) == '1' and
         os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_NATIVE_BUILD_CI') == '1',
         'DISPOSABLE_STOPPED_UPGRADE_OPTIN_REQUIRED')
    native.gate()  # strict actual disposable OPNsense 26.7 KVM and target ABI
    need(native.REVISION == REVISION and clean.REVISION == REVISION,
         'CURRENT_OFFICIAL_NATIVE_SOURCE_REVISION_MISMATCH')
    clean.plugin_absent()
    check_old_archive(archive)
    package = native.build()  # build while no old package is installed
    need(package['status'] == 'PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY' and
         package['project_sha'] == os.environ.get('ZAPRET2_NATIVE_PROJECT_SHA'),
         'NATIVE_SOURCE_BUILD_NOT_PROVEN')
    successor = native.ROOT / package['output']
    expected_sha = package['real_native_pkg']['sha256']
    need(successor.is_file() and not successor.is_symlink() and
         clean.digest(successor) == expected_sha, 'SUCCESSOR_ARCHIVE_DIGEST_WRONG')
    installer = load('stage0-opnsense-installed-predecessor.py')
    provenance = installer.install_and_verify(archive)
    need(provenance['status'] == 'PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE',
         'ACTUAL_OLD_INSTALLED_PROVENANCE_REFUSED')
    inspector = load('stage0-opnsense-prepkg-readonly.py')
    baseline = inspector.snapshot(archive)
    need(baseline['status'] == 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY' and
         baseline['real_old_status'] == 'STOPPED' and
         baseline['safe_pkg_transaction_authorized'] is False,
         'ORIGINAL_INSTALLED_STOPPED_FD9_IPFW_NOT_PROVEN')
    config_before = Path('/conf/config.xml').read_bytes()
    proof = replace_with_actual_pkg(successor)
    need(clean.digest(successor) == expected_sha, 'SUCCESSOR_ARCHIVE_CHANGED_DURING_PKG')
    manifest, pkgdb = clean.installed_pkg_manifest(successor)
    files = clean.verify_installed_files(successor, manifest)
    status = clean.cold_status()
    runtime = verify_cold_runtime()
    config_after = Path('/conf/config.xml').read_bytes()
    registration = prove_preserved_config(config_before, config_after)
    return {'schema': 1, 'status': 'PASS_REAL_NATIVE_STOPPED_VERSION_REPLACEMENT',
            'tested_exact_project_sha': package['project_sha'],
            'native_source_package_sha256': expected_sha,
            'old_published_archive_sha256': old.ARCHIVE_SHA,
            'old_installed_package': old.NAME + '-' + OLD_VERSION,
            'new_installed_package': native.NAME + '-' + native.VERSION + '_' + REVISION,
            'old_preflight': baseline['status'], 'actual_pkg': proof,
            'installed_files': files, 'installed_hook_bodies_verified': True,
            'installed_native_deps': pkgdb['deps'], 'new_service': status,
            'new_runtime': runtime, 'config_registry_and_other_fields_verified': registration,
            'original_old_predeinstall_execution_proven': False,
            'fd9_held_across_pkg_operation': False,
            'direct_privileged_pkg_bypass_prevented': False,
            'running_replacement_tested': False,
            'forced_same_version_reinstall_tested': False,
            'failure_rollback_tested': False, 'configctl_lifecycle_tested': False,
            'owner_appliance_modified': False, 'stage0_closed': False,
            'publication_approved': False}


def main():
    if len(sys.argv) != 2:
        print('STAGE2_STOPPED_UPGRADE=REFUSED:EXACT_ARCHIVED_PACKAGE_PATH_REQUIRED',
              file=sys.stderr)
        return 2
    try:
        result = execute(Path(sys.argv[1]))
    except (Refusal, clean.Refusal, old.Refusal, native.Refusal,
            OSError, ValueError, KeyError, TypeError) as exc:
        print('STAGE2_STOPPED_UPGRADE=REFUSED:' + str(exc), file=sys.stderr)
        return 2
    print('STAGE2_STOPPED_UPGRADE=' + json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
