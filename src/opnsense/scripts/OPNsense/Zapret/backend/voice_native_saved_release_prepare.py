#!/usr/bin/env python3
"""Stage-3 saved Voice GUI + native generator -> existing five-resource PREPARED.

PRIVATE import-only composition, no second compiler/engine/IPFW implementation,
no GUI/configd/boot activation. The caller must already own the ORIGINAL FD9
lifecycle and original Config inode flock throughout this call. No user-provided
proof or manifest is trusted. Live Config/runtime/kernel are never changed.
"""
from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

from voice_cutover_backup import _private_dir
from voice_handoff_preflight import build_runtime_handoff
from voice_firewall_ledger import decode_manifest
from voice_native_forward_stage_prepare import prepare_staged_forward_voice_intent
from voice_native_recovery_quiescence import _locked_config
from voice_release_stage import compile_bundle, file_sha256

FILES = ("voice.conf", "traffic.conf", "metadata.json",
         "profile-plan.json", "capture-plan.json")
# Native IPSET paths are fixed at the installed generator root; staged or
# simulated previous runtime paths must never alter the compiled argv.
MANAGED_ACTIVE_ROOT = Path("/usr/local/etc/zapret2/runtime-v2")


class SavedReleasePrepareError(RuntimeError):
    pass


def _require_global_on(config_source: Path) -> None:
    """Candidate is a complete saved XML generation, not a bare Voice profile."""
    raw = config_source.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise SavedReleasePrepareError("DTD forbidden in candidate Config")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SavedReleasePrepareError("invalid candidate Config XML") from exc
    if root.tag != "opnsense":
        raise SavedReleasePrepareError("invalid OPNsense root")
    general = root.findall("./OPNsense/Zapret/general")
    if len(general) != 1:
        raise SavedReleasePrepareError("missing or ambiguous saved global service")
    nodes = general[0].findall("enabled")
    if len(nodes) != 1 or list(nodes[0]) or (
        nodes[0].text or ""
    ).strip() != "1":
        raise SavedReleasePrepareError("native Voice requires saved global service ON")


def prepare_saved_release_forward_intent(
    *, release_dir, managed_source, ordinary_source, tcp_ports, udp_ports,
    physical_wan, divert_port, source_config, source_runtime,
    journal, ledger, previous_backup, process_evidence, security_evidence,
    previous_observer, config_path, active_runtime, expected_scripts,
    ipfw_adapter, config_fd, config_owner, require_lifecycle_owner,
) -> dict:
    """Rebuild Voice from GUI XML, verify real generator, seal native PREPARED.

    source_config is a detached candidate Config (NOT the locked old inode).
    source_runtime is a detached already-generated native runtime tree.
    release_dir is the write-once output of the existing Voice release stage.
    This routine creates no intermediate competing runtime or Config authority.
    """
    if not callable(require_lifecycle_owner):
        raise SavedReleasePrepareError("missing original lifecycle owner")
    config_path, active_runtime = Path(config_path), Path(active_runtime)
    source_config, source_runtime = Path(source_config), Path(source_runtime)
    release_dir, managed_source = Path(release_dir), Path(managed_source)
    ordinary_source = Path(ordinary_source)
    tcp_ports, udp_ports = Path(tcp_ports), Path(udp_ports)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    _private_dir(release_dir)
    if set(p.name for p in release_dir.iterdir()) != set(FILES):
        raise SavedReleasePrepareError("native Voice release artifacts incomplete or foreign")
    _require_global_on(source_config)
    # Independently compile the same saved GUI fields and shared managed IPSET
    # through the ORIGINAL compiler. Reject even coherent-looking forged
    # metadata if it does not originate from this XML and ordinary Strategies.
    expected = compile_bundle(
        source_config, managed_source, MANAGED_ACTIVE_ROOT,
        physical_wan, 19000, 19010, divert_port, ordinary_source,
    )
    for name in FILES:
        file = release_dir / name
        if file.is_symlink() or not file.is_file() or (
            file.read_bytes() != expected[name].encode("utf-8")
        ):
            raise SavedReleasePrepareError("compiled release differs from saved GUI")
    # Existing production handoff binds real generator dvtws.args, ordinary
    # port-extractor output, STUN/Strategies merge and exact scoped IPFW.
    manifest, proof = build_runtime_handoff(
        release_dir, source_runtime / "dvtws.args", ordinary_source,
        tcp_ports, udp_ports, source_config,
    )
    desired = decode_manifest(manifest)
    if not proof["enabled_services"] or not desired["tables"] or (
        proof["rule_base"], proof["rule_max"]
    ) != (19000, 19010):
        raise SavedReleasePrepareError("release does not enable native Voice")
    metadata = json.loads(expected["metadata.json"])
    if file_sha256(source_config) != proof["saved_xml_sha256"] or (
        file_sha256(ordinary_source) != metadata["ordinary_sha256"]
    ):
        raise SavedReleasePrepareError("saved XML or ordinary Strategies drifted")
    # A foreign stage with the right checksums is still refused by the
    # underlying write-once stage+journal contract. Recheck FD9/Config first.
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    return prepare_staged_forward_voice_intent(
        journal=journal, ledger=ledger, previous_backup=previous_backup,
        process_evidence=process_evidence, security_evidence=security_evidence,
        previous_observer=previous_observer,
        config_path=config_path, active_runtime=active_runtime,
        source_config=source_config, source_runtime=source_runtime,
        proof=proof, desired_manifest=desired, expected_scripts=expected_scripts,
        ipfw_adapter=ipfw_adapter, config_fd=config_fd,
        config_owner=config_owner, require_lifecycle_owner=require_lifecycle_owner,
    )
