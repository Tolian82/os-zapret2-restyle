"""Canonical immutable Strategy Lab candidate representation and exact rendering."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .resources import BUILTIN_BLOBS, ResourceInventory

CANDIDATE_SPEC_SCHEMA = 1
CANDIDATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
RESOURCE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
DEFAULT_LUA_DEPENDENCIES = ("zapret-lib.lua", "zapret-antidpi.lua")


class CandidateSpecError(ValueError):
    """A candidate cannot be normalized or rendered exactly."""


@dataclass(frozen=True)
class LuaArgument:
    name: str
    value: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True)
class LuaInstance:
    function: str
    arguments: tuple[LuaArgument, ...]
    raw: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "function": self.function,
            "arguments": [argument.to_dict() for argument in self.arguments],
            "raw": self.raw,
        }


@dataclass(frozen=True)
class BlobRequirement:
    name: str
    resource_class: str
    value: str
    filename: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "resource_class": self.resource_class,
            "value": self.value,
            "filename": self.filename,
        }


def _split_escaped(value: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for character in value:
        if escaped:
            current.extend(("\\", character))
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == delimiter:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    parts.append("".join(current))
    return parts


def _lua_instance(line: str) -> LuaInstance:
    raw = line.removeprefix("--lua-desync=")
    parts = _split_escaped(raw, ":")
    function = parts[0]
    if not function:
        raise CandidateSpecError("Lua desynchronization function is empty")
    arguments: list[LuaArgument] = []
    for item in parts[1:]:
        if not item:
            raise CandidateSpecError("Lua desynchronization argument is empty")
        name, separator, value = item.partition("=")
        if not name:
            raise CandidateSpecError("Lua desynchronization argument name is empty")
        arguments.append(LuaArgument(name=name, value=value if separator else None))
    return LuaInstance(function=function, arguments=tuple(arguments), raw=line)


def _blob_reference(
    value: str,
    declarations: dict[str, BlobRequirement],
) -> BlobRequirement:
    if value in BUILTIN_BLOBS:
        return BlobRequirement(name=value, resource_class="builtin", value=value)
    if value.lower().startswith("0x"):
        if len(value) <= 2 or any(character not in "0123456789abcdefABCDEF" for character in value[2:]):
            raise CandidateSpecError(f"inline BLOB value is invalid: {value}")
        return BlobRequirement(name=value, resource_class="inline", value=value)
    if value in declarations:
        return declarations[value]
    raise CandidateSpecError(f"named BLOB dependency has no installed-resource declaration: {value}")


def _deduplicate(values: Iterable[BlobRequirement]) -> tuple[BlobRequirement, ...]:
    result: list[BlobRequirement] = []
    seen: set[tuple[str, str, str, str | None]] = set()
    for value in values:
        key = (value.name, value.resource_class, value.value, value.filename)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return tuple(result)


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    family: str
    protocol: str
    l3: str
    transport: str
    port: int
    l7: str | None
    target_binding: bool
    strategy_lines: tuple[str, ...]
    lua_instances: tuple[LuaInstance, ...]
    lua_dependencies: tuple[str, ...]
    blob_requirements: tuple[BlobRequirement, ...]
    in_range: str | None
    out_range: str | None
    provenance: str
    search_cost: int
    complexity: int
    render_mode: str = "fragment"
    target_selector: str | None = None

    def __post_init__(self) -> None:
        if not CANDIDATE_ID_RE.fullmatch(self.candidate_id):
            raise CandidateSpecError("candidate id is invalid")
        if not self.family or not self.protocol or self.l3 not in {"ipv4", "ipv6"}:
            raise CandidateSpecError("candidate classification is invalid")
        if self.transport not in {"tcp", "udp"} or isinstance(self.port, bool) or not 1 <= self.port <= 65535:
            raise CandidateSpecError("candidate transport or port is invalid")
        if self.l7 is not None and (not self.l7 or "\n" in self.l7):
            raise CandidateSpecError("candidate L7 filter is invalid")
        if not self.strategy_lines or any(not line or "\n" in line or "\r" in line for line in self.strategy_lines):
            raise CandidateSpecError("candidate strategy lines are invalid")
        if not self.lua_instances:
            raise CandidateSpecError("bypass candidate contains no Lua action")
        if (
            not self.lua_dependencies
            or len(set(self.lua_dependencies)) != len(self.lua_dependencies)
            or any(
                not RESOURCE_NAME_RE.fullmatch(name) or not name.endswith(".lua")
                for name in self.lua_dependencies
            )
        ):
            raise CandidateSpecError("candidate Lua dependencies are invalid")
        if self.render_mode not in {"fragment", "profile"}:
            raise CandidateSpecError("candidate render mode is invalid")
        if self.render_mode == "profile" and self.target_binding:
            if not self.target_selector or self.target_selector not in self.strategy_lines:
                raise CandidateSpecError("exact profile target selector is unavailable")
        if self.search_cost <= 0 or self.complexity <= 0 or not self.provenance:
            raise CandidateSpecError("candidate search metadata is invalid")
        for value in (self.in_range, self.out_range):
            if value is not None and (not value or any(character.isspace() for character in value)):
                raise CandidateSpecError("candidate range is invalid")

    @classmethod
    def from_strategy(
        cls,
        *,
        candidate_id: str,
        family: str,
        protocol: str,
        transport: str,
        port: int,
        l7: str | None,
        strategy: str,
        target_binding: bool,
        l3: str = "ipv4",
        in_range: str | None = None,
        out_range: str | None = None,
        provenance: str = "legacy-catalog",
        search_cost: int = 1,
        complexity: int = 1,
        render_mode: str = "fragment",
        target_selector: str | None = None,
        lua_dependencies: tuple[str, ...] = DEFAULT_LUA_DEPENDENCIES,
    ) -> "CandidateSpec":
        lines = tuple(line for line in strategy.splitlines() if line)
        if not lines:
            raise CandidateSpecError("candidate strategy is empty")
        declarations: dict[str, BlobRequirement] = {}
        requirements: list[BlobRequirement] = []
        for line in lines:
            if not line.startswith("--blob="):
                continue
            value = line.removeprefix("--blob=")
            name, separator, source = value.partition(":")
            if not RESOURCE_NAME_RE.fullmatch(name):
                raise CandidateSpecError(f"BLOB name is invalid: {name}")
            if name in BUILTIN_BLOBS:
                raise CandidateSpecError(f"BLOB declaration shadows a built-in name: {name}")
            if name in declarations:
                raise CandidateSpecError(f"BLOB name is declared more than once: {name}")
            if not separator:
                declaration = BlobRequirement(
                    name=name,
                    resource_class="external",
                    value=name,
                    filename=name if name.endswith(".bin") else f"{name}.bin",
                )
                declarations[name] = declaration
                requirements.append(declaration)
            elif source.lower().startswith("0x"):
                inline = _blob_reference(source, {})
                declaration = BlobRequirement(
                    name=name,
                    resource_class=inline.resource_class,
                    value=inline.value,
                )
                declarations[name] = declaration
                requirements.append(declaration)
            else:
                raise CandidateSpecError("candidate external BLOB must use installed-resource shorthand")
        instances = tuple(_lua_instance(line) for line in lines if line.startswith("--lua-desync="))
        for instance in instances:
            for argument in instance.arguments:
                if argument.value is None:
                    continue
                if argument.name == "blob" or argument.name.endswith("_pattern"):
                    requirements.append(_blob_reference(argument.value, declarations))
        line_in_ranges = [line.removeprefix("--in-range=") for line in lines if line.startswith("--in-range=")]
        line_out_ranges = [line.removeprefix("--out-range=") for line in lines if line.startswith("--out-range=")]
        if len(line_in_ranges) > 1 or len(line_out_ranges) > 1:
            raise CandidateSpecError("candidate contains duplicate range arguments")
        if line_in_ranges:
            if in_range is not None and in_range != line_in_ranges[0]:
                raise CandidateSpecError("candidate input range conflicts with strategy")
            in_range = line_in_ranges[0]
        if line_out_ranges:
            if out_range is not None and out_range != line_out_ranges[0]:
                raise CandidateSpecError("candidate output range conflicts with strategy")
            out_range = line_out_ranges[0]
        return cls(
            candidate_id=candidate_id,
            family=family,
            protocol=protocol,
            l3=l3,
            transport=transport,
            port=port,
            l7=l7,
            target_binding=target_binding,
            strategy_lines=lines,
            lua_instances=instances,
            lua_dependencies=lua_dependencies,
            blob_requirements=_deduplicate(requirements),
            in_range=in_range,
            out_range=out_range,
            provenance=provenance,
            search_cost=search_cost,
            complexity=complexity,
            render_mode=render_mode,
            target_selector=target_selector,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": CANDIDATE_SPEC_SCHEMA,
            "candidate_id": self.candidate_id,
            "family": self.family,
            "protocol": self.protocol,
            "l3": self.l3,
            "transport": self.transport,
            "port": self.port,
            "l7": self.l7,
            "target_binding": self.target_binding,
            "strategy_lines": list(self.strategy_lines),
            "payload_filters": [
                line.removeprefix("--payload=")
                for line in self.strategy_lines
                if line.startswith("--payload=")
            ],
            "lua_instances": [instance.to_dict() for instance in self.lua_instances],
            "lua_dependencies": list(self.lua_dependencies),
            "blob_requirements": [requirement.to_dict() for requirement in self.blob_requirements],
            "resource_classes": (
                ["blob-free"]
                if not self.blob_requirements
                else list(dict.fromkeys(requirement.resource_class for requirement in self.blob_requirements))
            ),
            "ranges": {"in": self.in_range, "out": self.out_range},
            "provenance": self.provenance,
            "search": {"cost": self.search_cost, "complexity": self.complexity},
            "render_mode": self.render_mode,
            "target_selector": self.target_selector,
        }

    @property
    def spec_id(self) -> str:
        encoded = json.dumps(
            self._identity_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "cs1-" + hashlib.blake2b(encoded, digest_size=16).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        value = self._identity_payload()
        value["spec_id"] = self.spec_id
        return value

    def _map_external_blob(self, line: str, inventory: ResourceInventory) -> str:
        if not line.startswith("--blob="):
            return line
        value = line.removeprefix("--blob=")
        if ":" in value:
            return line
        path = inventory.external_blob_path(value)
        return f"--blob={value}:@{path}"

    def render_runtime_arguments(
        self,
        inventory: ResourceInventory,
        *,
        divert_port: int,
        hostlist_path: Path | None,
    ) -> tuple[str, ...]:
        if isinstance(divert_port, bool) or not 1 <= divert_port <= 65535:
            raise CandidateSpecError("candidate divert port is invalid")
        if self.target_binding and hostlist_path is None:
            raise CandidateSpecError("candidate target binding is unavailable")
        arguments = [f"--port={divert_port}"]
        arguments.extend(f"--lua-init=@{inventory.lua_path(name)}" for name in self.lua_dependencies)
        if self.render_mode == "profile":
            body: list[str] = []
            for line in self.strategy_lines:
                if self.target_binding and line == self.target_selector:
                    assert hostlist_path is not None
                    body.append(f"--hostlist={hostlist_path}")
                else:
                    body.append(self._map_external_blob(line, inventory))
            arguments.extend(body)
            return tuple(arguments)
        arguments.append(f"--filter-{self.transport}={self.port}")
        if self.l7:
            arguments.append(f"--filter-l7={self.l7}")
        if self.target_binding:
            assert hostlist_path is not None
            arguments.append(f"--hostlist={hostlist_path}")
        if self.in_range is not None:
            arguments.append(f"--in-range={self.in_range}")
        if self.out_range is not None:
            arguments.append(f"--out-range={self.out_range}")
        for line in self.strategy_lines:
            if line.startswith("--in-range=") or line.startswith("--out-range="):
                continue
            arguments.append(self._map_external_blob(line, inventory))
        return tuple(arguments)
