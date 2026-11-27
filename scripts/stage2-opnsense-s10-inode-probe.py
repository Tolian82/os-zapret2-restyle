#!/usr/bin/env python3
"""Disposable filesystem experiment; not an Apply or a G03 acceptance gate."""
import argparse
import ast
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"


def load_writer():
    names = {"_target", "_file_identity", "_target_identity", "_native_list_modification_visible", "_replace"}
    source = ast.parse((BACKEND / "auto_detect_destination_commit.py").read_text())
    nodes = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names]
    receipts = ast.parse((BACKEND / "auto_detect_epoch_receipts.py").read_text())
    nodes += [n for n in receipts.body if isinstance(n, ast.FunctionDef) and n.name == "_sync"]
    if {n.name for n in nodes} != names | {"_sync"}:
        raise RuntimeError("missing original helper")
    scope = dict(Path=Path, os=os, stat=stat, secrets=secrets, MAX_TARGET=4 * 1024 * 1024,
                 DestinationRefused=RuntimeError)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<original-writer>", "exec"), scope)
    return scope


def run_probe(base, count, waits, *, wal_base=None, focused=False):
    modes = ("original", "late-pinned", "wal-file-barrier", "wal-dir-barrier",
             "wal-rewrite-barrier", "local-rewrite-barrier", "no-rename-control")
    if focused:
        modes = ("original", "wal-rewrite-barrier", "local-rewrite-barrier", "no-rename-control")
    report = {m: dict(samples=0, ctime_drift=0, other_drift=0, refused=0,
                      first_drift={}, early_ctime_drift={}) for m in modes}
    scope = load_writer()
    identity = scope["_target_identity"]
    samples = []

    def same_except_ctime(a, b):
        return a[:2] == b[:2] and a[3:] == b[3:]

    def snapshot(target, data, anchor=None):
        raw, info = scope["_target"](target, os.geteuid())
        actual = identity(info)
        if raw != data or anchor is not None and identity(os.fstat(anchor)) != actual:
            raise RuntimeError("physical image changed")
        return actual

    def note_early(row, original, actual, label):
        if not same_except_ctime(original, actual):
            raise RuntimeError("non-ctime identity changed")
        if original[2] != actual[2]:
            counts = row["early_ctime_drift"]
            counts[label] = counts.get(label, 0) + 1

    def observe(sample, label):
        mode, target, after, pinned, seen = sample
        try:
            actual = snapshot(target, after)
            ctime = actual[2] != pinned[2]
            other = not same_except_ctime(actual, pinned)
        except (OSError, RuntimeError, ValueError):
            ctime, other = False, True
        for changed, key in ((ctime, "ctime_drift"), (other, "other_drift")):
            if changed and key not in seen:
                seen[key] = label

    with ExitStack() as stack:
        root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="g03-inode-probe-", dir=base)))
        wal_root = root if wal_base is None else Path(stack.enter_context(
            tempfile.TemporaryDirectory(prefix="g03-wal-probe-", dir=wal_base)))
        wal = wal_root / "wal"
        wal.mkdir()
        local = root / "local-barrier"
        local.mkdir()

        def checkpoint(data, sample=None, *, directory=wal):
            def step(label):
                if sample is not None:
                    observe(sample, label)
            pending = directory / ".pending"
            with pending.open("wb") as stream:
                step("wal-open")
                stream.write(hashlib.sha256(data).hexdigest().encode())
                stream.flush()
                step("wal-flush")
                os.fsync(stream.fileno())
                step("wal-file-fsync")
            step("wal-close")
            os.replace(pending, directory / "record")
            step("wal-rename")
            scope["_sync"](directory)
            step("wal-dir-fsync")

        for index in range(count):
            for mode in modes:
                row = report[mode]
                target = root / f"{mode}-{index}.txt"
                before, after = b"before.example\n", b"after-long.example\n"
                target.write_bytes(before)
                early, pinned, anchor = None, None, None
                sample = None

                def stage(phase, item, data, info):
                    nonlocal early, pinned, anchor, sample
                    if phase == "ready":
                        checkpoint(data)
                        return
                    early = identity(info)
                    if mode != "original":
                        # Anchor the exact renamed inode while the original writer
                        # is still open. Do not persist an installed pin yet.
                        anchor = os.open(item, os.O_RDONLY | os.O_NOFOLLOW)
                        if snapshot(item, data, anchor) != early:
                            raise RuntimeError("installed anchor mismatch")
                    else:
                        pinned = early
                        sample = (mode, target, after, pinned, {})
                        checkpoint(data, sample)
                        observe(sample, "after-installed-wal")

                try:
                    if mode == "no-rename-control":
                        # Control only: fresh bytes in a file, no active-list rename.
                        # Never use in-place writes as a production replacement.
                        with target.open("wb") as stream:
                            stream.write(after)
                            stream.flush()
                            os.fsync(stream.fileno())
                        scope["_sync"](root)
                        checkpoint(after)
                        stage("installed", target, after, target.lstat())
                    else:
                        scope["_replace"](target, before, after, os.geteuid(), stage_fn=stage,
                                          expected_identity=identity(target.lstat()))
                    if early is None:
                        raise RuntimeError("missing installed observation")
                    if mode != "original":
                        if anchor is None:
                            raise RuntimeError("missing anchor")
                        returned = snapshot(target, after, anchor)
                        note_early(row, early, returned, "writer-return")
                        if mode == "wal-file-barrier":
                            fd = os.open(wal / "record", os.O_RDONLY | os.O_NOFOLLOW)
                            try:
                                os.fsync(fd)
                            finally:
                                os.close(fd)
                        elif mode == "wal-dir-barrier":
                            scope["_sync"](wal)
                        elif mode == "wal-rewrite-barrier":
                            # Synthetic extra WAL cycle, not a new production phase.
                            checkpoint(after)
                        elif mode == "local-rewrite-barrier":
                            # Test-only same-filesystem I/O, not a product journal.
                            checkpoint(after, directory=local)
                        pinned = snapshot(target, after, anchor)
                        note_early(row, returned, pinned, "before-final-pin")
                        sample = (mode, target, after, pinned, {})
                        checkpoint(after, sample)
                        observe(sample, "after-installed-wal")
                        if not same_except_ctime(pinned, identity(os.fstat(anchor))):
                            raise RuntimeError("anchor drift")
                    if sample is None:
                        raise RuntimeError("missing sample")
                    observe(sample, "writer-return")
                except (OSError, RuntimeError, ValueError):
                    row["refused"] += 1
                    sample = None
                finally:
                    if anchor is not None:
                        os.close(anchor)
                if sample is not None:
                    row["samples"] += 1
                    samples.append(sample)
                    observe(sample, "anchor-closed")
        for delay, label in waits:
            time.sleep(delay)
            for sample in samples:
                observe(sample, label)
        for mode, _, _, _, seen in samples:
            row = report[mode]
            for key, label in seen.items():
                row[key] += 1
                timings = row["first_drift"].setdefault(key, {})
                timings[label] = timings.get(label, 0) + 1
    return report


def filesystem_type(path):
    df = subprocess.run(["/bin/df", "-T", str(path)], capture_output=True, text=True, timeout=5, check=True)
    fields = df.stdout.splitlines()[-1].split()
    return fields[1] if len(fields) > 1 and fields[1] in ("ufs", "zfs") else "unknown"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portable", action="store_true")
    parser.add_argument("--base", type=Path)
    parser.add_argument("--wal-base", type=Path)
    parser.add_argument("--expect-filesystem", choices=("ufs", "zfs"))
    parser.add_argument("--expect-wal-filesystem", choices=("ufs", "zfs"))
    parser.add_argument("--focused", action="store_true")
    args = parser.parse_args()
    if args.portable:
        if any((args.base, args.wal_base, args.expect_filesystem, args.expect_wal_filesystem)):
            parser.error("native paths and filesystem assertions require native scope")
        base, count, waits = None, 2, [(0, "batch-complete"), (0.01, "short")]
        filesystem = wal_filesystem = "portable"
        same_device = True
    else:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                os.environ.get("GITHUB_ACTIONS") != "true" or
                os.environ.get("ZAPRET2_G03_DISPOSABLE_NATIVE") != "1"):
            raise SystemExit("G03_INODE_PROBE_NATIVE_SCOPE_REQUIRED")
        base = args.base or Path("/usr/local/etc")
        wal_base = args.wal_base or base
        filesystem, wal_filesystem = filesystem_type(base), filesystem_type(wal_base)
        if (filesystem == "unknown" or wal_filesystem == "unknown" or
                args.expect_filesystem not in (None, filesystem) or
                args.expect_wal_filesystem not in (None, wal_filesystem)):
            raise SystemExit("G03_INODE_PROBE_FILESYSTEM_MISMATCH")
        same_device = base.stat().st_dev == wal_base.stat().st_dev
        count, waits = 8, [(0, "batch-complete"), (1, "1s"), (3, "4s"), (4, "8s")]
    result = run_probe(base, count, waits, wal_base=args.wal_base, focused=args.focused)
    print("G03_INODE_PROBE=" + json.dumps({"filesystem": filesystem, "wal_filesystem": wal_filesystem,
          "same_device": same_device, "variants": result,
          "g03_acceptance": False}, sort_keys=True), flush=True)
    if any(row["samples"] + row["refused"] != count for row in result.values()):
        raise SystemExit("G03_INODE_PROBE_INCOMPLETE")
    if any(not row["samples"] for row in result.values()):
        raise SystemExit("G03_INODE_PROBE_NO_SAMPLE")
    if args.portable and any(row["refused"] or row["other_drift"] or row["ctime_drift"] for row in result.values()):
        raise SystemExit("G03_INODE_PROBE_PORTABLE_REFUSED")


if __name__ == "__main__":
    main()
