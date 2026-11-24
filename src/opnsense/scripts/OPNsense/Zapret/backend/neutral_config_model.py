#!/usr/bin/env python3
"""S07 pure requested-settings projection. No XML, filesystem, process or FD9.

The output is not a runtime configuration, authority, or user-facing JSON.
Absent nodes remain absent; no defaulting or implicit Start is permitted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Mapping

_MISSING = object()
_WAN = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,31}\Z")
_ID = re.compile(r"[a-z][a-z0-9_-]*\Z")
_AUTORESTART = frozenset(("off", "hourly", "daily", "weekly", "monthly"))
_MODES = frozenset(("all", "list", "auto"))
_VOICES = ("telegram", "discord", "x", "sip", "custom")
_LISTS = ("youtubedomains", "userdomains", "excludedomains", "excludeipset",
          "telegramips", "discordips", "xips", "sipips", "customips")
_STRATEGY = ("httpargs", "httpsargs", "trafficargs", "extraargs")


class ConfigModelError(ValueError):
    """Unqualified input: do not use the projected candidate."""


@dataclass(frozen=True)
class SourceId:
    kind: str
    name: str
    storage_key: str
    content_required: bool


@dataclass(frozen=True)
class TextPresence:
    key: str
    present: bool
    empty: bool | None
    size: int | None


@dataclass(frozen=True)
class VoiceRequest:
    service: str
    enabled: bool | None
    args_present: bool
    args: str | None = field(repr=False)


@dataclass(frozen=True)
class RequestedConfig:
    enabled: bool | None
    saved_wan: str | None
    wan_state: str
    divert_port: int | None
    ports: tuple[int, ...] | None
    autorestart: str | None
    target_mode: str | None
    lab_enablequic: bool | None
    voice: tuple[VoiceRequest, ...]
    list_fields: tuple[TextPresence, ...]
    legacy_strategy: tuple[TextPresence, ...]
    registered_sources: tuple[SourceId, ...]
    schema: int = 1
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def _section(value: object, allowed: frozenset[str]) -> Mapping[str, str]:
    if type(value) is not dict or not set(value).issubset(allowed):
        raise ConfigModelError("INVALID_MODEL_SECTION")
    for name, text in value.items():
        if type(name) is not str or type(text) is not str or len(text) > 262144:
            raise ConfigModelError("INVALID_MODEL_SCALAR")
    return value


def _bool(values: Mapping[str, str], key: str) -> bool | None:
    v = values.get(key, _MISSING)
    if v is _MISSING:
        return None
    if v not in ("0", "1"):
        raise ConfigModelError("INVALID_BOOLEAN")
    return v == "1"


def _option(values: Mapping[str, str], key: str, allowed: frozenset[str]) -> str | None:
    v = values.get(key, _MISSING)
    if v is _MISSING:
        return None
    if v not in allowed:
        raise ConfigModelError("INVALID_ENUM")
    return v


def _port(v: str) -> int:
    if not re.fullmatch(r"[0-9]{1,5}", v, re.ASCII):
        raise ConfigModelError("INVALID_PORT")
    n = int(v)
    if not 1 <= n <= 65535:
        raise ConfigModelError("INVALID_PORT")
    return n


def _text_presence(values: Mapping[str, str], keys: tuple[str, ...]) -> tuple[TextPresence, ...]:
    return tuple(TextPresence(name, name in values,
                              values[name] == "" if name in values else None,
                              len(values[name].encode("utf-8")) if name in values else None)
                 for name in keys)


def project(tree: Mapping[str, object], sources: tuple[SourceId, ...]) -> RequestedConfig:
    """Validate a detached OPNsense scalar snapshot; never resolve or execute WAN.

    The sources argument is supplied only by the OPNsense adapter's existing
    registry read, not a second hardcoded registry. The caller retains
    responsibility for original WAN preflight and original FD9 attestation.
    """
    if type(tree) is not dict or set(tree) != {"general", "hostlist", "voice", "strategy", "strategylab"}:
        raise ConfigModelError("INVALID_MODEL_KEYS")
    g = _section(tree["general"], frozenset(("enabled", "waninterface", "divertport", "ports", "autorestart")))
    h = _section(tree["hostlist"], frozenset(("mode", "domains", *_LISTS)))
    s = _section(tree["strategy"], frozenset(_STRATEGY))
    lab = _section(tree["strategylab"], frozenset(("enablequic",)))
    raw_voice = tree["voice"]
    if type(raw_voice) is not dict or set(raw_voice) != set(_VOICES):
        raise ConfigModelError("INVALID_VOICE_KEYS")
    voice = []
    for name in _VOICES:
        fields = _section(raw_voice[name], frozenset(("enabled", "args")))
        voice.append(VoiceRequest(name, _bool(fields, "enabled"),
                                  "args" in fields, fields.get("args")))

    if type(sources) is not tuple or not sources:
        raise ConfigModelError("INVALID_REGISTRY")
    seen = set()
    storage = set()
    for source in sources:
        if (type(source) is not SourceId or source.kind not in ("HOSTLIST", "IPSET") or
                type(source.name) is not str or not _ID.fullmatch(source.name) or
                type(source.storage_key) is not str or
                not re.fullmatch(r"(?:hostlist|ipset)\.[a-z][a-z0-9_-]*", source.storage_key) or
                not source.storage_key.startswith(source.kind.lower() + ".") or
                type(source.content_required) is not bool or
                (source.kind, source.name) in seen or source.storage_key in storage):
            raise ConfigModelError("INVALID_REGISTRY")
        seen.add((source.kind, source.name))
        storage.add(source.storage_key)
    wan = g.get("waninterface")
    if wan is not None and wan != "" and not _WAN.fullmatch(wan):
        raise ConfigModelError("INVALID_WAN_SELECTION")
    if wan is None:
        wan_state = "MISSING"
    elif wan == "":
        wan_state = "EMPTY"
    else:
        wan_state = "NEEDS_NATIVE_RESOLUTION"  # Includes opt/TUN; never infer device.
    dp = _port(g["divertport"]) if "divertport" in g else None
    ports = None
    if "ports" in g:
        parts = g["ports"].split(",")
        if len(parts) > 128 or len(parts) == 0:
            raise ConfigModelError("INVALID_PORTS")
        ports = tuple(_port(v) for v in parts)
        if len(set(ports)) != len(ports):
            raise ConfigModelError("INVALID_PORTS")
    return RequestedConfig(enabled=_bool(g, "enabled"), saved_wan=wan,
                           wan_state=wan_state, divert_port=dp, ports=ports,
                           autorestart=_option(g, "autorestart", _AUTORESTART),
                           target_mode=_option(h, "mode", _MODES),
                           lab_enablequic=_bool(lab, "enablequic"),
                           voice=tuple(voice), list_fields=_text_presence(h, _LISTS),
                           legacy_strategy=_text_presence(s, _STRATEGY),
                           registered_sources=sources)
