#!/usr/bin/env python3
"""Source-only sealed ORIGINAL FD9 schema-2 test fixture (never installed).

Only injected witness is a future P2c running process. Native producer bytes,
real original P2a queue flock, shared release seal, nofollow snapshot,
pretraffic/epoch immutable fsync and per-minute chain remain physical files.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox
from auto_detect_epoch_receipts import EpochReceipts
from shared_apply_seal import create_seal

CANDIDATE = "c" * 64


def sealed_shared_release(base: Path, proof: GenerationProof) -> tuple[Path, GenerationProof]:
    """Create a *real hashed/sealed* candidate, not a live P2c attestation."""
    folder = base / "shared-work"
    folder.mkdir(mode=0o700)
    work = folder / proof.generation
    work.mkdir(mode=0o700)
    release = work / "release"
    release.mkdir(mode=0o700)
    (work / "candidate.xml").write_text("<opnsense/>")
    (work / "plan.json").write_text('{"page":"strategies"}\n')
    argv = (
        "--port=989\n"
        "--hostlist-auto-debug=" + proof.debug_path + "\n"
        "--filter-tcp=80,443\n"
        "--filter-l7=http,tls\n"
        "--hostlist=" + str(base / "youtube-hostlist.txt") + "\n"
        "--new\n"
        "--filter-tcp=80\n"
        "--filter-l7=http,tls\n"
        "--hostlist-auto=" + proof.raw_path + "\n"
        "--hostlist-auto-retrans-reset=0\n"
    ).encode()
    (release / "dvtws.args").write_bytes(argv)
    final_digest = hashlib.sha256(argv).hexdigest()
    mapping = {
        "schema": 2,
        "evidence": "ORIGINAL_SHARED_GENERATOR_CAPTURE",
        "generation": proof.generation,
        "owner_operation_id": proof.operation_id,
        "owner_candidate_sha256": CANDIDATE,
        "final_args_sha256": final_digest,
        "mode": "auto",
        "raw_path": proof.raw_path,
        "debug_path": proof.debug_path,
        "observer_native_number": proof.observer_native_number,
        "profiles": [
            {"native_number": no, "status": status, "hostlist": hostlist}
            for no, status, hostlist in proof.profiles
        ],
    }
    (release / "auto-detect-generation.json").write_text(
        json.dumps(mapping, sort_keys=True, separators=(",", ":")) + "\n")
    create_seal(work, owner=os.geteuid())
    return work, replace(proof, final_args_sha256=final_digest)


def sealed_original_epoch(base: Path, proof: GenerationProof,
                          queue: DurableInbox, receipts: EpochReceipts) -> GenerationProof:
    """Source-only two-phase record, physically before/after launch boundary.

    An injected real-owner P2c witness is limited to postlaunch completion.
    The live native product still lacks schema-2 release authorization.
    """
    work, proof = sealed_shared_release(base, proof)
    with queue.exclusive():
        receipts.seal_pretraffic(
            queue, workspace=work, candidate_sha256=CANDIDATE)
    with queue.exclusive():
        receipts.finish_running(proof, queue, attest=lambda: proof)
    return proof
