#!/usr/bin/env python3
"""S07 bounded OPNsense native Config -> pure neutral in-memory projection.

No executable entry point: importing this adapter never runs a command, writes
Config, creates a journal, or resolves WAN by guessing a device. Only original
WAN preflight may classify an assigned OPT/TUN interface for real operations.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True  # Must be set before imports in this module.

from neutral_config_model import SourceId, ConfigModelError, project

CONFIG = Path("/conf/config.xml")
REGISTRY_SOURCE = Path(__file__).with_name("registry.sh")
MAX_CONFIG = 16 * 1024 * 1024
MAX_REGISTRY = 128 * 1024


class NativeProjectionError(ConfigModelError):
    pass


def _nodes(node: ET.Element | None, permitted: tuple[str, ...], *, leaf: bool = True) -> dict[str, ET.Element]:
    if node is None:
        return {}
    result: dict[str, ET.Element] = {}
    for child in node:
        if (child.tag not in permitted or child.tag in result or (leaf and len(child)) or
                child.attrib or (child.tail or "").strip()):
            raise NativeProjectionError("INVALID_OR_DUPLICATE_XML_NODE")
        result[child.tag] = child
    return result


def _branch(node: ET.Element | None, allowed: tuple[str, ...]) -> dict[str, str]:
    nodes = _nodes(node, allowed)
    return {key: "" if el.text is None else el.text for key, el in nodes.items()}


def xml_snapshot(raw: bytes) -> dict[str, object]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_CONFIG or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise NativeProjectionError("INVALID_XML_INPUT")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise NativeProjectionError("INVALID_XML") from exc
    if root.tag != "opnsense":
        raise NativeProjectionError("INVALID_XML_ROOT")
    parents = root.findall("OPNsense")
    if len(parents) != 1:
        raise NativeProjectionError("OPNSENSE_MODEL_MISSING_OR_DUPLICATE")
    models = parents[0].findall("Zapret")
    if len(models) != 1:
        raise NativeProjectionError("ZAPRET_MODEL_MISSING_OR_DUPLICATE")
    model = models[0]
    # The native OPNsense Model stores an optional version attribute, e.g.
    # <Zapret version="2.0.0">. It is metadata, never a second config source.
    version = model.attrib.get("version")
    if set(model.attrib) - {"version"} or (version is not None and
            not re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,3}){0,2}", version)):
        raise NativeProjectionError("INVALID_MODEL_ATTRIBUTES")
    top: dict[str, ET.Element] = {}
    allowed_top = ("general", "hostlist", "voice", "strategy", "strategylab")
    for el in model:
        if el.tag not in allowed_top or el.tag in top or el.attrib:
            raise NativeProjectionError("INVALID_MODEL_BRANCH")
        top[el.tag] = el
    # Preserve legacy fields only as presence metadata: never treat them as
    # authoritative file-backed HOSTLIST/IPSET or as S08 compiled profile args.
    lab = _branch(top.get("strategylab"), ("enablequic",))
    voice = _nodes(top.get("voice"), ("waninterface", "telegram", "discord", "x", "sip", "custom"), leaf=False)
    for name, el in voice.items():
        if name == "waninterface":
            if len(el) or el.attrib:
                raise NativeProjectionError("INVALID_LEGACY_VOICE_WAN")
        elif el.attrib:
            raise NativeProjectionError("INVALID_VOICE_MODEL")
    return {
        "general": _branch(top.get("general"), ("enabled", "waninterface", "divertport", "ports", "autorestart")),
        "hostlist": _branch(top.get("hostlist"), ("mode", "domains", "youtubedomains", "userdomains", "excludedomains", "excludeipset", "telegramips", "discordips", "xips", "sipips", "customips")),
        "strategy": _branch(top.get("strategy"), ("httpargs", "httpsargs", "trafficargs", "extraargs")),
        "strategylab": lab,
        "voice": {name: _branch(voice.get(name), ("enabled", "args")) for name in ("telegram", "discord", "x", "sip", "custom")},
    }


def registered_ids(source: bytes) -> tuple[SourceId, ...]:
    """Read registry_build()'s current static rows, not a second registry.

    This parser intentionally refuses a dynamic/changed declaration layout;
    a new registry generator must be qualified as a separate source change.
    """
    if type(source) is not bytes or not source or len(source) > MAX_REGISTRY:
        raise NativeProjectionError("INVALID_REGISTRY_SOURCE")
    try:
        text = source.decode("utf-8")
        block = text.split("registry_build()\n{", 1)[1].split("registry_validate()\n{", 1)[0]
    except (UnicodeDecodeError, IndexError) as exc:
        raise NativeProjectionError("INVALID_REGISTRY_SOURCE") from exc
    items: list[SourceId] = []
    for line in block.splitlines():
        if not re.match(r"^\s*printf ", line):
            continue
        match = re.fullmatch(r"\s*printf '((?:HOSTLIST|IPSET)\\t[a-z][a-z0-9_-]*\\t--(?:hostlist|ipset)\\t[a-z][a-z0-9_.-]*\\t[01])\\n'", line)
        if match is None:
            raise NativeProjectionError("UNKNOWN_REGISTRY_DECLARATION")
        parts = match.group(1).split(r"\t")
        kind, name, opt, storage, required = parts
        if opt != ("--hostlist" if kind == "HOSTLIST" else "--ipset"):
            raise NativeProjectionError("INVALID_REGISTRY_OPTION")
        if not storage.startswith(kind.lower() + "."):
            raise NativeProjectionError("INVALID_REGISTRY_STORAGE")
        items.append(SourceId(kind, name, storage, required == "1"))
    if not items or len(items) > 128 or len({(i.kind, i.name) for i in items}) != len(items):
        raise NativeProjectionError("INVALID_REGISTRY_MEMBERS")
    return tuple(items)


def read_saved(*, config: Path = CONFIG, registry: Path = REGISTRY_SOURCE,
               reader=None, config_owner: int | None = None):
    """Read only fixed trusted source files. No XML model writer or shell calls."""
    if reader is None:
        import pwd
        from component_inventory_opnsense import _read_fixed
        try:
            config_owner = pwd.getpwnam("wwwonly").pw_uid
        except (KeyError, OSError) as exc:
            raise NativeProjectionError("UNQUALIFIED_CONFIG_OWNER") from exc
        if config_owner <= 0:
            raise NativeProjectionError("UNQUALIFIED_CONFIG_OWNER")
        reader = _read_fixed
    elif config_owner is None:
        raise NativeProjectionError("UNQUALIFIED_CONFIG_OWNER")
    try:
        raw = reader(config, MAX_CONFIG, config_owner)
        registry_raw = reader(registry, MAX_REGISTRY, 0)
        return project(xml_snapshot(raw), registered_ids(registry_raw))
    except (OSError, ValueError, ET.ParseError) as exc:
        raise NativeProjectionError("UNQUALIFIED_SAVED_CONFIG") from exc
