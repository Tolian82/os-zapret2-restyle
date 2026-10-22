#!/usr/local/bin/python3.13
"""Read-only immutable-revision preflight for manually installed Zapret2 extras.

No files are installed by this program. This is the first safety increment
before adding a privileged transaction/restart entrypoint.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
from urllib.request import Request, urlopen

SOURCE = "Tolian82/zapret2-extra-resources"
SOURCE_REF_URL = f"https://api.github.com/repos/{SOURCE}/git/ref/heads/main"
RUNTIME_ROOT = Path("/usr/local/etc/zapret2")
MANAGED_METADATA = Path("/var/db/zapret2-restyle/extra-resources/installed.json")
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_FILE = 2 * 1024 * 1024
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
FILE_PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")


class PreflightError(RuntimeError):
    pass


def resource_path(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split("/")
    if any(not FILE_PART.fullmatch(part) or part in {".", ".."} for part in parts):
        return False
    path = PurePosixPath(value)
    return (len(parts) == 2 and parts[0] == "lua" and path.suffix == ".lua") or (
        len(parts) == 3 and parts[:2] == ["files", "fake"] and path.suffix == ".bin"
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def obtain_revision() -> str:
    req = Request(SOURCE_REF_URL, headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "os-zapret2-restyle"})
    with urlopen(req, timeout=20) as response:
        raw = response.read(8193)
    if len(raw) > 8192:
        raise PreflightError("GitHub revision response exceeds the supported size")
    try:
        revision = json.loads(raw)["object"]["sha"]
    except (ValueError, TypeError, KeyError) as exc:
        raise PreflightError("GitHub returned an invalid source revision") from exc
    if not isinstance(revision, str) or not SHA_PATTERN.fullmatch(revision):
        raise PreflightError("GitHub returned an invalid commit SHA")
    return revision


def obtain_archive(revision: str) -> bytes:
    if not SHA_PATTERN.fullmatch(revision):
        raise PreflightError("source revision is not an immutable commit SHA")
    url = f"https://codeload.github.com/{SOURCE}/tar.gz/{revision}"
    with urlopen(Request(url, headers={"User-Agent": "os-zapret2-restyle"}), timeout=60) as response:
        result = response.read(MAX_ARCHIVE + 1)
    if len(result) > MAX_ARCHIVE:
        raise PreflightError("source archive exceeds the size limit")
    return result


def unpack_verified_archive(data: bytes, revision: str) -> dict[str, bytes]:
    """Read allowed members in memory, never extract or follow tar links."""
    if not SHA_PATTERN.fullmatch(revision):
        raise PreflightError("invalid source revision")
    prefix = f"zapret2-extra-resources-{revision}/"
    files: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile() or member.issym() or member.islnk():
                    raise PreflightError(f"archive contains a non-regular member: {member.name}")
                if not member.name.startswith(prefix):
                    raise PreflightError("archive contains a path outside its pinned root")
                rel = member.name[len(prefix):]
                if (not rel or rel.startswith("/") or "\\" in rel
                        or any(part in {"", ".", ".."} for part in rel.split("/"))):
                    raise PreflightError(f"archive contains an invalid path: {rel}")
                if rel in files:
                    raise PreflightError(f"archive contains a duplicate path: {rel}")
                if member.size < 0 or member.size > MAX_FILE:
                    raise PreflightError(f"archive member exceeds limit: {rel}")
                total += member.size
                if total > MAX_ARCHIVE:
                    raise PreflightError("unpacked archive exceeds size limit")
                f = archive.extractfile(member)
                if f is None:
                    raise PreflightError(f"archive member unreadable: {rel}")
                body = f.read(MAX_FILE + 1)
                if len(body) != member.size:
                    raise PreflightError(f"archive member size mismatch: {rel}")
                files[rel] = body
    except (tarfile.TarError, OSError) as exc:
        raise PreflightError(f"source archive is damaged: {exc}") from exc
    return files


def parse_json(files: dict[str, bytes], path: str) -> dict:
    try:
        result = json.loads(files[path].decode("utf-8"))
    except (KeyError, ValueError, UnicodeError) as exc:
        raise PreflightError(f"catalog metadata is invalid: {path}") from exc
    if not isinstance(result, dict):
        raise PreflightError(f"catalog metadata is not an object: {path}")
    return result


def verified_resources(files: dict[str, bytes]) -> tuple[dict[str, bytes], int]:
    manifest = parse_json(files, "inventory/sources.json")
    if manifest.get("schema") != 1 or not isinstance(manifest.get("resources"), list):
        raise PreflightError("source inventory schema is invalid")
    payloads: dict[str, bytes] = {}
    known_sha: set[str] = set()
    for record in manifest["resources"]:
        if not isinstance(record, dict) or not resource_path(record.get("target")):
            raise PreflightError("source inventory contains an unsafe resource path")
        target = record["target"]
        if target in payloads or target not in files:
            raise PreflightError(f"missing or duplicate source entry: {target}")
        data = files[target]
        if not data or len(data) > MAX_FILE:
            raise PreflightError(f"resource is empty or oversized: {target}")
        if record.get("size") != len(data) or record.get("sha") != git_blob_sha(data):
            raise PreflightError(f"source checksum/size mismatch: {target}")
        if record["sha"] in known_sha:
            raise PreflightError("source inventory contains duplicate resource bytes")
        known_sha.add(record["sha"])
        payloads[target] = data
    actual = {name for name in files if resource_path(name)}
    if actual != set(payloads):
        raise PreflightError("actual Lua/BIN files do not match the source inventory")
    lua = sum(name.startswith("lua/") for name in payloads)
    bin_count = len(payloads) - lua
    if manifest.get("counts") != {"lua": lua, "bin": bin_count} or manifest.get("total") != len(payloads):
        raise PreflightError("source inventory totals are inconsistent")
    capabilities = parse_json(files, "inventory/capabilities.json")
    if capabilities.get("schema") != 1 or not isinstance(capabilities.get("resources"), list):
        raise PreflightError("capability metadata schema is invalid")
    seen: set[str] = set()
    for descriptor in capabilities["resources"]:
        if not isinstance(descriptor, dict):
            raise PreflightError("capability entry is not an object")
        target = descriptor.get("target")
        if target not in payloads or target in seen:
            raise PreflightError(f"capability references absent or duplicate resource: {target}")
        seen.add(target)
        kind = "lua" if target.startswith("lua/") else "blob"
        if descriptor.get("kind") != kind:
            raise PreflightError(f"resource capability type mismatch: {target}")
        if kind == "lua":
            export = descriptor.get("export")
            if not isinstance(export, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", export):
                raise PreflightError(f"invalid Lua export descriptor: {target}")
            pattern = rb"(?m)^\s*function\s+" + re.escape(export.encode("ascii")) + rb"\s*\("
            if not re.search(pattern, payloads[target]):
                raise PreflightError(f"Lua export is absent: {target}")
        elif descriptor.get("format") == "tls-clienthello":
            body = payloads[target]
            if len(body) < 6 or body[0] != 0x16 or body[1] != 0x03 or body[5] != 0x01:
                raise PreflightError(f"declared TLS ClientHello signature missing: {target}")
    return payloads, len(seen)


def validate_runtime_path(root: Path, path: str) -> Path:
    if not resource_path(path):
        raise PreflightError(f"unsafe installation path: {path}")
    if root.is_symlink() or not root.is_dir():
        raise PreflightError("installed Zapret2 runtime is unavailable or symlinked")
    current = root
    for part in path.split("/")[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            raise PreflightError(f"installed resource directory is absent or unsafe: {current}")
    dest = root / path
    if dest.is_symlink():
        raise PreflightError(f"installed resource is a symlink: {path}")
    if dest.exists() and not dest.is_file():
        raise PreflightError(f"installed resource is not a regular file: {path}")
    return dest


def inspect_collisions(payloads: dict[str, bytes], runtime: Path, managed: Path) -> dict:
    previous = {}
    if managed.is_symlink():
        raise PreflightError("managed resource metadata is a symlink")
    if managed.exists():
        try:
            metadata = json.loads(managed.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PreflightError("managed resource metadata is unreadable") from exc
        if not isinstance(metadata, dict) or metadata.get("schema") != 1 or not isinstance(metadata.get("files"), dict):
            raise PreflightError("managed resource metadata is invalid")
        previous = metadata["files"]
        if any(not resource_path(name) or not isinstance(digest, str)
               or not re.fullmatch(r"[0-9a-f]{64}", digest) for name, digest in previous.items()):
            raise PreflightError("managed metadata contains invalid file identities")
    for name, digest in previous.items():
        path = validate_runtime_path(runtime, name)
        if not path.exists() or sha256(path.read_bytes()) != digest:
            raise PreflightError(f"previously managed resource changed or missing: {name}")
    additions = 0
    updates = 0
    identical = 0
    for name, data in payloads.items():
        dest = validate_runtime_path(runtime, name)
        if dest.exists() and name not in previous:
            raise PreflightError(f"resource name conflicts with upstream/user file: {name}")
        if not dest.exists():
            additions += 1
        elif sha256(data) == previous[name]:
            identical += 1
        else:
            updates += 1
    return {"new": additions, "updated": updates, "unchanged": identical,
            "previously_managed": len(previous)}


def preflight(archive: bytes, revision: str, runtime: Path, managed: Path) -> dict:
    files = unpack_verified_archive(archive, revision)
    payloads, eligible_descriptors = verified_resources(files)
    plan = inspect_collisions(payloads, runtime, managed)
    return {"status": "preflight_only", "source_commit": revision,
            "lua": sum(p.startswith("lua/") for p in payloads),
            "bin": sum(p.startswith("files/fake/") for p in payloads),
            "described_capabilities": eligible_descriptors, **plan,
            "installed": False, "restarted": False}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "preflight":
        print("usage: extra_resources_preflight.py preflight", file=sys.stderr)
        return 64
    try:
        revision = obtain_revision()
        archive = obtain_archive(revision)
        print(json.dumps(preflight(archive, revision, RUNTIME_ROOT, MANAGED_METADATA),
                         sort_keys=True))
        return 0
    except (PreflightError, OSError, ValueError) as exc:
        print(f"EXTRA_RESOURCES_PREFLIGHT_FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
