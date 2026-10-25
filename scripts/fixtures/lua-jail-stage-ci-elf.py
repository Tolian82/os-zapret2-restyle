#!/usr/bin/env python3
"""CI-only FreeBSD ELF library staging for a pinned *CI-built* upstream engine.

Never run an ELF here. Reuse the project's bounded ELF metadata parsers.
The executable trial requires independent kernel jail confinement and MUST
NOT be used to approve deletion or claim installed-engine Lua compatibility.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_engine_abi import _needed_libraries  # noqa: E402
from extra_resources_jail_loader import _elf_interpreter, STANDARD_INTERPRETER  # noqa: E402
from extra_resources_jail_libraries import SONAME  # noqa: E402

DIRECTORIES = (Path("/usr/local/lib"), Path("/usr/lib"), Path("/lib"))
LIMIT = 32 * 1024 * 1024
MAX_COUNT = 48
MAX_TOTAL = 96 * 1024 * 1024


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_source(path: Path) -> tuple[Path, bytes]:
    if not path.is_absolute():
        raise ValueError("absolute CI ELF path required")
    resolved = path.resolve(strict=True)
    if not any(resolved == root or root in resolved.parents for root in (*DIRECTORIES, Path("/libexec"))):
        raise ValueError("CI ELF dependency escaped explicit FreeBSD library namespace")
    info = resolved.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or info.st_mode & 0o022 or info.st_size < 64 or info.st_size > LIMIT):
        raise ValueError("unsafe CI source ELF inode or size")
    data = resolved.read_bytes()
    if len(data) != info.st_size or sha(data) != sha(resolved.read_bytes()):
        raise ValueError("CI ELF source raced during read")
    return resolved, data


def find_library(name: str) -> tuple[Path, Path, bytes]:
    if not SONAME.fullmatch(name) or ".." in name:
        raise ValueError("unsafe DT_NEEDED name")
    for directory in DIRECTORIES:
        path = directory / name
        if path.exists() or path.is_symlink():
            origin, data = safe_source(path)
            return path, origin, data
    raise ValueError("missing real FreeBSD DT_NEEDED library: " + name)


def write(root: Path, rel: str, data: bytes) -> None:
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        raise ValueError("duplicate staged CI ELF path")
    with dest.open("xb") as output:
        output.write(data)
    dest.chmod(0o555)


def stage(root: Path, engine: Path, shim: Path, evidence: Path) -> None:
    if not root.is_dir() or root.is_symlink() or evidence.exists():
        raise ValueError("CI jail staging root or evidence path invalid")
    original = engine.read_bytes()
    if _elf_interpreter(original, dependency=False) != STANDARD_INTERPRETER:
        raise ValueError("real CI upstream dvtws2 lacks canonical FreeBSD interpreter")
    if not _needed_libraries(original):
        raise ValueError("CI upstream engine is not dynamically linked")
    shim_data = shim.read_bytes()
    _elf_interpreter(shim_data, dependency=True)
    current = [*_needed_libraries(original), *_needed_libraries(shim_data)]
    names = set()
    entries = []
    total = 0
    while current:
        name = current.pop(0)
        if name in names:
            continue
        if len(names) >= MAX_COUNT:
            raise ValueError("too many CI ELF dependencies")
        candidate, resolved, data = find_library(name)
        # CI-only: genuine FreeBSD base/pkg system DSOs may use native
        # DT_FILTER/RUNPATH directives that the deliberately stricter
        # *installed-engine removal* attestor cannot model. We never
        # authorize removal from this experiment. Parse recursive DT_NEEDED
        # with the SAME structural ELF reader, pin exact bytes, then require
        # the real ld-elf.so.1 to resolve them inside a kernel no-IP jail.
        # No system library, Config or host directory is mounted into jail.
        nested = _needed_libraries(data)
        relative = candidate.relative_to("/")
        write(root, str(relative), data)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError("CI ELF dependency graph exceeds byte limit")
        names.add(name)
        entries.append({"source": str(candidate), "resolved": str(resolved),
                        "dest": str(relative), "sha256": sha(data)})
        for child in nested:
            if child not in names and child not in current:
                current.append(child)
    loader, loader_data = safe_source(Path(STANDARD_INTERPRETER))
    _elf_interpreter(loader_data, dependency=True)
    write(root, STANDARD_INTERPRETER.lstrip("/"), loader_data)
    entries.append({"source": STANDARD_INTERPRETER, "resolved": str(loader),
                    "dest": STANDARD_INTERPRETER.lstrip("/"), "sha256": sha(loader_data)})
    # Source and destination engine/shim are also pinned on either side of
    # the actual isolated execution; no host file is mapped into the jail.
    for source, dest in ((engine, "ci-engine"), (shim, "no-net.so")):
        entries.append({"source": str(source), "resolved": str(source.resolve()),
                        "dest": dest, "sha256": sha(source.read_bytes())})
    evidence.write_text(json.dumps(entries, sort_keys=True) + "\n")
    verify(root, evidence)
    print("PASS: pinned CI-built upstream ELF and exact recursive FreeBSD library bytes; NOT installed engine")


def verify(root: Path, evidence: Path) -> None:
    rows = json.loads(evidence.read_text())
    if not isinstance(rows, list) or not 2 <= len(rows) <= MAX_COUNT + 3:
        raise ValueError("invalid CI ELF library pin ledger")
    for row in rows:
        dest = root / row["dest"]
        source = Path(row["source"])
        if source.resolve(strict=True) != Path(row["resolved"]):
            raise ValueError("CI ELF source path identity drift")
        for item in (source, dest):
            if item == dest and (item.is_symlink() or item.stat().st_mode & 0o022):
                raise ValueError("staged CI ELF path changed")
            if sha(item.read_bytes()) != row["sha256"]:
                raise ValueError("CI ELF source/staged digest drift")
    print("PASS: CI ELF source/staged digest reattestation")


def main() -> None:
    if len(sys.argv) < 4 or os.geteuid() != 0:
        raise SystemExit("root CI only: stage|verify JAIL_ROOT EVIDENCE [ENGINE SHIM]")
    operation = sys.argv[1]
    root = Path(sys.argv[2])
    evidence = Path(sys.argv[3])
    try:
        if operation == "stage" and len(sys.argv) == 6:
            stage(root, Path(sys.argv[4]), Path(sys.argv[5]), evidence)
        elif operation == "verify" and len(sys.argv) == 4:
            verify(root, evidence)
        else:
            raise ValueError("unsupported CI staging operation")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise SystemExit("FAIL: CI-only ELF staging: " + str(exc)) from exc


if __name__ == "__main__":
    main()
