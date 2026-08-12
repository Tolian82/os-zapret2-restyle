"""Job-scoped inventory of installed Zapret2 Lua and fake-file resources."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INVENTORY_SCHEMA = 1
BUILTIN_BLOBS = ("fake_default_tls", "fake_default_http", "fake_default_quic")
RESOURCE_CLASSES = ("blob-free", "builtin", "inline", "external")
DEFAULT_LUA_ROOT = Path("/usr/local/etc/zapret2/lua")
DEFAULT_FAKE_ROOT = Path("/usr/local/etc/zapret2/files/fake")


class ResourceInventoryError(RuntimeError):
    """Installed resource evidence is missing, invalid, or insufficient."""


@dataclass(frozen=True)
class InstalledResource:
    name: str
    path: str
    size: int
    mtime_ns: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "InstalledResource":
        if not isinstance(value, dict):
            raise ResourceInventoryError("resource inventory entry is not an object")
        name = value.get("name")
        path = value.get("path")
        size = value.get("size")
        mtime_ns = value.get("mtime_ns")
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(path, str)
            or not path
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or isinstance(mtime_ns, bool)
            or not isinstance(mtime_ns, int)
            or mtime_ns < 0
        ):
            raise ResourceInventoryError("resource inventory entry is invalid")
        return cls(name=name, path=path, size=size, mtime_ns=mtime_ns)


@dataclass(frozen=True)
class ResourceInventory:
    inventory_id: str
    observed_at: str
    lua_root: str
    fake_root: str
    lua_root_exists: bool
    fake_root_exists: bool
    lua: tuple[InstalledResource, ...]
    external_blobs: tuple[InstalledResource, ...]

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": INVENTORY_SCHEMA,
            "lua_root": self.lua_root,
            "fake_root": self.fake_root,
            "lua_root_exists": self.lua_root_exists,
            "fake_root_exists": self.fake_root_exists,
            "lua": [item.to_dict() for item in self.lua],
            "external_blobs": [item.to_dict() for item in self.external_blobs],
            "builtin_blobs": list(BUILTIN_BLOBS),
            "resource_classes": list(RESOURCE_CLASSES),
            "inline": {"prefix": "0x", "available": True},
        }

    def expected_id(self) -> str:
        encoded = json.dumps(
            self._identity_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "ri1-" + hashlib.blake2b(encoded, digest_size=16).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        value = self._identity_payload()
        value.update(inventory_id=self.inventory_id, observed_at=self.observed_at)
        return value

    def lua_path(self, name: str) -> str:
        for item in self.lua:
            if item.name == name:
                if item.size == 0:
                    raise ResourceInventoryError(f"required installed Lua resource is empty: {name}")
                return item.path
        raise ResourceInventoryError(f"required installed Lua resource is unavailable: {name}")

    def external_blob_path(self, blob_name: str) -> str:
        filename = blob_name if blob_name.endswith(".bin") else f"{blob_name}.bin"
        for item in self.external_blobs:
            if item.name == filename:
                if item.size == 0:
                    raise ResourceInventoryError(
                        f"required installed fake-file resource is empty: {filename}"
                    )
                return item.path
        raise ResourceInventoryError(f"required installed fake-file resource is unavailable: {filename}")

    @classmethod
    def from_dict(cls, value: Any) -> "ResourceInventory":
        if not isinstance(value, dict) or value.get("schema") != INVENTORY_SCHEMA:
            raise ResourceInventoryError("resource inventory schema is invalid")
        inventory_id = value.get("inventory_id")
        observed_at = value.get("observed_at")
        lua_root = value.get("lua_root")
        fake_root = value.get("fake_root")
        lua_root_exists = value.get("lua_root_exists")
        fake_root_exists = value.get("fake_root_exists")
        if (
            not isinstance(inventory_id, str)
            or not inventory_id
            or not isinstance(observed_at, str)
            or not observed_at
            or not isinstance(lua_root, str)
            or not lua_root
            or not isinstance(fake_root, str)
            or not fake_root
            or not isinstance(lua_root_exists, bool)
            or not isinstance(fake_root_exists, bool)
            or value.get("builtin_blobs") != list(BUILTIN_BLOBS)
            or value.get("resource_classes") != list(RESOURCE_CLASSES)
            or value.get("inline") != {"prefix": "0x", "available": True}
        ):
            raise ResourceInventoryError("resource inventory metadata is invalid")
        lua_raw = value.get("lua")
        blob_raw = value.get("external_blobs")
        if not isinstance(lua_raw, list) or not isinstance(blob_raw, list):
            raise ResourceInventoryError("resource inventory lists are invalid")
        inventory = cls(
            inventory_id=inventory_id,
            observed_at=observed_at,
            lua_root=lua_root,
            fake_root=fake_root,
            lua_root_exists=lua_root_exists,
            fake_root_exists=fake_root_exists,
            lua=tuple(InstalledResource.from_dict(item) for item in lua_raw),
            external_blobs=tuple(InstalledResource.from_dict(item) for item in blob_raw),
        )
        if inventory.inventory_id != inventory.expected_id():
            raise ResourceInventoryError("resource inventory identity does not match its contents")
        return inventory


def configured_lua_root() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_LUA_DIR", str(DEFAULT_LUA_ROOT))).resolve(strict=False)


def configured_fake_root() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_FAKE_DIR", str(DEFAULT_FAKE_ROOT))).resolve(strict=False)


def _installed_files(root: Path, suffix: str) -> tuple[bool, tuple[InstalledResource, ...]]:
    if not root.is_dir():
        return False, ()
    items: list[InstalledResource] = []
    try:
        entries = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        raise ResourceInventoryError(f"installed resource directory is unreadable: {root}") from exc
    for entry in entries:
        if entry.suffix != suffix or not entry.is_file():
            continue
        try:
            stat = entry.stat()
        except OSError as exc:
            raise ResourceInventoryError(f"installed resource is unreadable: {entry}") from exc
        items.append(
            InstalledResource(
                name=entry.name,
                path=str(entry.resolve(strict=False)),
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            )
        )
    return True, tuple(items)


def snapshot_inventory(lua_root: Path, fake_root: Path) -> ResourceInventory:
    lua_root = lua_root.resolve(strict=False)
    fake_root = fake_root.resolve(strict=False)
    lua_exists, lua = _installed_files(lua_root, ".lua")
    fake_exists, external_blobs = _installed_files(fake_root, ".bin")
    inventory = ResourceInventory(
        inventory_id="pending",
        observed_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        lua_root=str(lua_root),
        fake_root=str(fake_root),
        lua_root_exists=lua_exists,
        fake_root_exists=fake_exists,
        lua=lua,
        external_blobs=external_blobs,
    )
    return ResourceInventory(
        inventory_id=inventory.expected_id(),
        observed_at=inventory.observed_at,
        lua_root=inventory.lua_root,
        fake_root=inventory.fake_root,
        lua_root_exists=inventory.lua_root_exists,
        fake_root_exists=inventory.fake_root_exists,
        lua=inventory.lua,
        external_blobs=inventory.external_blobs,
    )


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def load_inventory(path: Path) -> ResourceInventory:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResourceInventoryError(f"resource inventory is unreadable: {path}") from exc
    return ResourceInventory.from_dict(value)


def ensure_job_inventory(job: Path) -> ResourceInventory:
    path = job / "resource-inventory.json"
    if path.is_file():
        return load_inventory(path)
    inventory = snapshot_inventory(configured_lua_root(), configured_fake_root())
    _atomic_json(path, inventory.to_dict())
    return inventory
