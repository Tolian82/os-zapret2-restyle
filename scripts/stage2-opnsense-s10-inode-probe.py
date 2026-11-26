#!/usr/bin/env python3
"""Disposable filesystem experiment; not an Apply or a G03 acceptance gate."""
import argparse
import ast
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


def load_writer(mode):
    source = (BACKEND / "auto_detect_destination_commit.py").read_text()
    boundary = "        os.replace(temp, path)\n        _sync(path.parent)\n"
    if source.count(boundary) != 1:
        raise RuntimeError("unexpected writer boundary")
    if mode == "file-after-dir":
        source = source.replace(boundary, boundary + "        os.fsync(fd)\n")
    elif mode == "file-dir-file":
        source = source.replace(boundary, "        os.replace(temp, path)\n        os.fsync(fd)\n        _sync(path.parent)\n        os.fsync(fd)\n")
    elif mode != "original":
        raise RuntimeError("unknown experiment")
    names = {"_target", "_file_identity", "_target_identity", "_native_list_modification_visible", "_replace"}
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in names]
    receipts = ast.parse((BACKEND / "auto_detect_epoch_receipts.py").read_text())
    nodes += [n for n in receipts.body if isinstance(n, ast.FunctionDef) and n.name == "_sync"]
    if {n.name for n in nodes} != names | {"_sync"}:
        raise RuntimeError("missing original helper")
    scope = dict(Path=Path, os=os, stat=stat, secrets=secrets, MAX_TARGET=4 * 1024 * 1024,
                 DestinationRefused=RuntimeError)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<original-writer>", "exec"), scope)
    return scope


def run_probe(base, count, waits):
    modes = ("original", "file-after-dir", "file-dir-file")
    report = {m: dict(samples=0, ctime_drift=0, other_drift=0, refused=0, first_drift={}) for m in modes}
    samples = []
    def observe(sample, label):
        mode, target, after, original, scope, observed = sample
        try:
            raw, info = scope["_target"](target, os.geteuid())
            actual = scope["_target_identity"](info)
            ctime = actual[2] != original[2]
            other = raw != after or actual[:2] != original[:2] or actual[3:] != original[3:]
        except (OSError, RuntimeError, ValueError):
            ctime, other = False, True
        for changed, key in ((ctime, "ctime_drift"), (other, "other_drift")):
            if changed and key not in observed:
                report[mode][key] += 1
                timings = report[mode]["first_drift"].setdefault(key, {})
                timings[label] = timings.get(label, 0) + 1
                observed.add(key)

    with tempfile.TemporaryDirectory(prefix="g03-inode-probe-", dir=base) as tmp:
        root = Path(tmp)
        wal = root / "wal"
        wal.mkdir()
        for mode in modes:
            scope = load_writer(mode)
            for index in range(count):
                target = root / f"{mode}-{index}.txt"
                before, after = b"before.example\n", b"after-long.example\n"
                target.write_bytes(before)
                pinned = []
                def stage(phase, item, data, info):
                    if phase == "installed":
                        pinned.append(scope["_target_identity"](info))
                    # Emulate the existing separate durable WAL checkpoint, not its authorization.
                    pending = wal / ".pending"
                    with pending.open("wb") as stream:
                        stream.write(hashlib.sha256(data).hexdigest().encode())
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(pending, wal / "record")
                    scope["_sync"](wal)
                try:
                    scope["_replace"](target, before, after, os.geteuid(), stage_fn=stage,
                                      expected_identity=scope["_target_identity"](target.lstat()))
                    if len(pinned) != 1:
                        raise RuntimeError("missing installed pin")
                    report[mode]["samples"] += 1
                    sample = (mode, target, after, pinned[0], scope, set())
                    samples.append(sample)
                    observe(sample, "writer-return")
                except (OSError, RuntimeError, ValueError):
                    report[mode]["refused"] += 1
        for delay, label in waits:
            time.sleep(delay)
            for sample in samples:
                observe(sample, label)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portable", action="store_true")
    args = parser.parse_args()
    if args.portable:
        base, count, waits = None, 2, [(0, "batch-complete"), (0.01, "short")]
        filesystem = "portable"
    else:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                os.environ.get("GITHUB_ACTIONS") != "true" or
                os.environ.get("ZAPRET2_G03_DISPOSABLE_NATIVE") != "1"):
            raise SystemExit("G03_INODE_PROBE_NATIVE_SCOPE_REQUIRED")
        base = "/usr/local/etc"
        df = subprocess.run(["/bin/df", "-T", base], capture_output=True, text=True, timeout=5, check=True)
        fields = df.stdout.splitlines()[-1].split()
        filesystem = fields[1] if len(fields) > 1 and fields[1] in ("ufs", "zfs") else "unknown"
        count, waits = 8, [(0, "batch-complete"), (1, "1s"), (3, "4s"), (4, "8s")]
    result = run_probe(base, count, waits)
    print("G03_INODE_PROBE=" + json.dumps({"filesystem": filesystem, "variants": result,
          "g03_acceptance": False}, sort_keys=True), flush=True)
    if any(row["samples"] + row["refused"] != count for row in result.values()):
        raise SystemExit("G03_INODE_PROBE_INCOMPLETE")
    if any(not row["samples"] for row in result.values()):
        raise SystemExit("G03_INODE_PROBE_NO_SAMPLE")
    if args.portable and any(row["refused"] or row["other_drift"] or row["ctime_drift"] for row in result.values()):
        raise SystemExit("G03_INODE_PROBE_PORTABLE_REFUSED")


if __name__ == "__main__":
    main()
