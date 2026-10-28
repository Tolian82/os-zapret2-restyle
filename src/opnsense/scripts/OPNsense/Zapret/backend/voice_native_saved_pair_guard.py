#!/usr/bin/env python3
"""Read-only pair guard for saved Voice XML and OPNsense-rendered zapret.conf.

The ordinary OPNsense template remains the ONLY generator. This module does
not render, persist, execute or modify either input. It refuses a torn pair:
all fields consumed by the existing orchestrator must agree with the same
saved XML snapshot before the detached compiler is called.

The caller has original lifecycle FD9, original Config inode flock and
verified 0600 root-private inputs; root-only publication is elsewhere.
"""
from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

SCALARS = (
    ("ZAPRET_ENABLED", "general/enabled", True),
    ("WAN_IF", "general/waninterface", True),
    ("DIVERT_PORT", "general/divertport", True),
    ("EXTRA_ARGS", "strategy/extraargs", False),
    ("HOSTLIST_MODE", "hostlist/mode", False),
)
BLOCKS = (
    ("TRAFFIC_ARGS", "strategy/trafficargs"),
    ("YOUTUBE_DOMAINS", "hostlist/youtubedomains"),
    ("TELEGRAM_IPS", "hostlist/telegramips"),
    ("DISCORD_IPS", "hostlist/discordips"),
    ("X_IPS", "hostlist/xips"),
    ("SIP_IPS", "hostlist/sipips"),
    ("CUSTOM_IPS", "hostlist/customips"),
    ("USER_DOMAINS", "hostlist/userdomains"),
    ("EXCLUDE_DOMAINS", "hostlist/excludedomains"),
    ("EXCLUDE_IPSET", "hostlist/excludeipset"),
)
SERVICES = ("telegram", "discord", "x", "sip", "custom")
MAX_XML = 4 * 1024 * 1024
MAX_RENDERED = 4 * 1024 * 1024


class SavedPairError(ValueError):
    pass


def _single(root: ET.Element, path: str, *, required: bool = False) -> str:
    nodes = root.findall("./OPNsense/Zapret/" + path)
    if len(nodes) > 1 or (required and len(nodes) != 1):
        raise SavedPairError("ambiguous or absent native Voice settings")
    if not nodes:
        return ""
    if list(nodes[0]):
        raise SavedPairError("nested field in saved Voice XML")
    return nodes[0].text or ""


def _scalar(text: str, name: str) -> str:
    rows = re.findall(r"^" + re.escape(name) + r'="([^\r\n]*)"$',
                      text, flags=re.MULTILINE)
    if len(rows) != 1:
        raise SavedPairError("missing or repeated saved config scalar")
    return rows[0]


def _block(text: str, name: str) -> str:
    marker = "__ZAPRET_" + name + "__"
    expr = (r"^" + re.escape(name) + r"=\$\(cat <<'" + re.escape(marker) +
            r"'\n(.*?)\n" + re.escape(marker) + r"\n\)$")
    rows = re.findall(expr, text, flags=re.MULTILINE | re.DOTALL)
    if len(rows) != 1:
        raise SavedPairError("missing or repeated saved config heredoc")
    return rows[0]


def require_saved_pair(source_xml: Path, rendered_conf: Path) -> None:
    """Refuse mismatch BEFORE invoking original orchestrator or writing stage."""
    source_xml, rendered_conf = Path(source_xml), Path(rendered_conf)
    xml_bytes, rendered_bytes = source_xml.read_bytes(), rendered_conf.read_bytes()
    if len(xml_bytes) > MAX_XML or len(rendered_bytes) > MAX_RENDERED or (
        b"<!DOCTYPE" in xml_bytes.upper() or b"<!ENTITY" in xml_bytes.upper()
    ):
        raise SavedPairError("unsafe candidate config size or DTD")
    try:
        xml = ET.fromstring(xml_bytes)
        rendered = rendered_bytes.decode("utf-8")
    except (ET.ParseError, UnicodeError) as exc:
        raise SavedPairError("invalid native saved pair encoding") from exc
    if xml.tag != "opnsense" or "\r" in rendered:
        raise SavedPairError("invalid native saved Config root/newlines")
    for name, path, required in SCALARS:
        expected = _single(xml, path, required=required)
        if _scalar(rendered, name) != expected:
            raise SavedPairError("saved XML and generated config disagree on " + name)
    if _single(xml, "general/enabled", required=True) != "1":
        raise SavedPairError("native candidate requires global ON")
    for name, path in BLOCKS:
        if _block(rendered, name) != _single(xml, path):
            raise SavedPairError("saved XML and generated heredoc disagree on " + name)
    for service in SERVICES:
        saved = _single(xml, "voice/" + service + "/enabled")
        if not saved:
            saved = "0"
        if saved not in ("0", "1") or _scalar(
            rendered, "VOICE_" + service.upper() + "_REQUESTED"
        ) != saved:
            raise SavedPairError("saved XML and generated Voice enable disagree")
