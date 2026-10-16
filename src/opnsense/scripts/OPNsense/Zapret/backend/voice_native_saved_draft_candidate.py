#!/usr/bin/env python3
"""Produce native Voice ON candidate from SAVED OFF GUI drafts under one FD9.

Import-only. This does NOT accept browser XML or a variable filesystem path.
The GUI can eventually request a bounded five-bit ON mask plus a 64-char
current-Config digest. An original lifecycle FD9 owner, and an original Config
inode flock, read that exact source and privately stage an independent XML.

No Config.save, configctl reload, service restart, IPFW or engine activation.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
from xml.dom import minidom

from voice_native_lifecycle_router import _locked_config

SERVICES = ("telegram", "discord", "x", "sip", "custom")
MAX_CONFIG = 4 * 1048576


class NativeDraftCandidateError(RuntimeError):
    pass


def _unique(parent, tag: str):
    children = [
        n for n in parent.childNodes
        if n.nodeType == n.ELEMENT_NODE and n.nodeName == tag
    ]
    if len(children) != 1:
        raise NativeDraftCandidateError("missing or repeated saved Voice model field")
    return children[0]


def _leaf(parent, name: str) -> tuple[object, str]:
    node = _unique(parent, name)
    if node.attributes.length:
        raise NativeDraftCandidateError("foreign attributes in Voice model field")
    if any(n.nodeType not in (n.TEXT_NODE, n.CDATA_SECTION_NODE)
           for n in node.childNodes):
        raise NativeDraftCandidateError("nested or foreign Voice model field")
    text = "".join(n.data for n in node.childNodes)
    return node, text


def _check_mask(mask: str, expected_sha: str) -> None:
    if not isinstance(mask, str) or not re.fullmatch(r"[01]{5}", mask) or (
        mask == "00000" or not isinstance(expected_sha, str)
        or not re.fullmatch(r"[a-f0-9]{64}", expected_sha)
    ):
        raise NativeDraftCandidateError("invalid Voice profile mask or Config baseline")


def render_saved_draft_candidate(
    *, config_path, mask, expected_sha, config_fd,
    config_owner, require_lifecycle_owner,
) -> bytes:
    """ONE authoritative, read-only saved-draft parser under FD9 + Config flock.

    This exact parser is shared by GUI preflight and the persistent candidate
    publisher. Never read a browser-supplied XML or install running resources.
    """
    _check_mask(mask, expected_sha)
    config_path = Path(config_path)
    if not config_path.is_absolute() or not callable(require_lifecycle_owner):
        raise NativeDraftCandidateError("foreign native Voice Config or missing lifecycle owner")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)

    active = os.fstat(config_fd)
    if not stat.S_ISREG(active.st_mode) or active.st_size > MAX_CONFIG:
        raise NativeDraftCandidateError("current Config size or inode is invalid")
    current_xml = os.pread(config_fd, MAX_CONFIG + 1, 0)
    if len(current_xml) > MAX_CONFIG or (
        hashlib.sha256(current_xml).hexdigest() != expected_sha
    ) or any(marker in current_xml.upper() for marker in (b"<!DOCTYPE", b"<!ENTITY")):
        raise NativeDraftCandidateError("saved Voice Config generation changed or unsafe")
    try:
        doc = minidom.parseString(current_xml)
    except Exception as exc:
        raise NativeDraftCandidateError("original Config XML is malformed") from exc
    if doc.doctype is not None or doc.documentElement.tagName != "opnsense":
        raise NativeDraftCandidateError("foreign original Config XML root")
    zapret = _unique(_unique(doc.documentElement, "OPNsense"), "Zapret")
    general = _unique(zapret, "general")
    if _leaf(general, "enabled")[1] != "1":
        raise NativeDraftCandidateError("Zapret must be enabled for native Voice")
    voice = _unique(zapret, "voice")
    hostlist = _unique(zapret, "hostlist")
    for index, service in enumerate(SERVICES):
        profile = _unique(voice, service)
        enabled, previous = _leaf(profile, "enabled")
        if previous != "0":
            raise NativeDraftCandidateError("saved GUI Voice draft must be all OFF")
        if mask[index] != "1":
            continue
        if not _leaf(profile, "args")[1].strip() or (
            not _leaf(hostlist, service + "ips")[1].strip()
        ):
            raise NativeDraftCandidateError("enabled Voice needs previously saved args/IPSET")
        for node in tuple(enabled.childNodes):
            enabled.removeChild(node)
            node.unlink()
        enabled.appendChild(doc.createTextNode("1"))
    candidate_xml = doc.toxml(encoding="utf-8")
    if len(candidate_xml) > MAX_CONFIG:
        raise NativeDraftCandidateError("Voice candidate XML exceeds Config limit")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if hashlib.sha256(os.pread(config_fd, MAX_CONFIG + 1, 0)).hexdigest() != expected_sha:
        raise NativeDraftCandidateError("current Config changed during candidate rendering")
    return candidate_xml


def preview_saved_draft_candidate(
    *, config_path, mask, expected_sha, config_fd,
    config_owner, require_lifecycle_owner,
) -> dict:
    """No filesystem writes, status only; no PREPARED journal."""
    candidate_xml = render_saved_draft_candidate(
        config_path=config_path, mask=mask, expected_sha=expected_sha,
        config_fd=config_fd, config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    return {
        "state": "native-voice-saved-draft-preview",
        "selected_profiles": sum(ch == "1" for ch in mask),
        "saved_xml_sha256": hashlib.sha256(candidate_xml).hexdigest(),
        "safe_to_enable_voice": False,
        "public_voice_apply": False,
    }
