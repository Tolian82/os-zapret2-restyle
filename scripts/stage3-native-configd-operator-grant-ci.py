#!/usr/bin/env python3
"""Disposable CI-only operator-signed archive grant for the real configd FD9 worker.

Controller signs BEFORE configd/SCM_RIGHTS transfer; the worker verifies
BEFORE the existing authentic native pkg dispatch in its OWN retained FD9.
No production owner signer, live mTLS witness, remote ledger or pkg API here.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

HERE = Path(__file__).resolve().parent
SCOPE = "stage3-prepkg-operator-operation-grant-ci.py"
ROOT_NAME = "ci-operator-grant"
SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
NAME = "os-zapret2-restyle"
FILES = ("operator-public.pem", "status-public.pem", "signed-grant.json",
         "signed-grant.sig", "wrong-old.json", "wrong-old.sig",
         "wrong-new.json", "wrong-new.sig", "wrong-head.json", "wrong-head.sig")


class Refusal(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Refusal(why)


def policy_module():
    s = importlib.util.spec_from_file_location("ci_native_fd9_approval_scope", HERE / SCOPE)
    obj = importlib.util.module_from_spec(s)
    s.loader.exec_module(obj)
    return obj


def create(root, name, payload):
    path = root / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        while payload:
            n = os.write(fd, payload)
            need(n > 0, "FD9_GRANT_SHORT_WRITE")
            payload = payload[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def openssl(*args, data=None):
    p = subprocess.run(["/usr/bin/openssl", *map(str, args)], input=data,
                       capture_output=True, check=False, timeout=15)
    need(p.returncode == 0, "FD9_GRANT_OPENSSL_FAILED")
    return p.stdout


def exact_private_root(root):
    need(root.is_dir() and not root.is_symlink() and
         stat.S_ISDIR(root.lstat().st_mode) and
         root.lstat().st_uid == os.geteuid() and
         stat.S_IMODE(root.lstat().st_mode) == 0o700,
         "FD9_GRANT_PRIVATE_ROOT_UNTRUSTED")


def expected_identity(head, old_sha, new_sha):
    need(type(head) is str and COMMIT.fullmatch(head) is not None and
         all(type(d) is str and SHA.fullmatch(d) is not None and d != "0"*64
             for d in (old_sha, new_sha)),
         "FD9_GRANT_INVALID_EXPECTED_HEAD_OR_PACKAGE_DIGEST")
    return {
        "operation_id": hashlib.sha256(
            ("fd9-operation|" + head + "|" + old_sha + "|" + new_sha).encode()).hexdigest(),
        "payload_sha256": new_sha,
        "checkpoint_sha256": old_sha,
        "checkpoint_sequence": 1,
    }


def issue(root_dir, head, old_archive, candidate_archive, old_sha, new_sha, revision):
    """Create a signed CI grant before the true configd worker can run pkg."""
    root = Path(root_dir)
    exact_private_root(root)
    identity = expected_identity(head, old_sha, new_sha)
    need(type(revision) is str and revision.isdecimal() and int(revision) > 0,
         "FD9_GRANT_REVISION_INVALID")
    grant = policy_module()
    grant.measured_archive(str(old_archive), "0.6.2_1", old_sha)
    grant.measured_archive(str(candidate_archive), "0.6.2_" + revision, new_sha)
    folder = root / ROOT_NAME
    folder.mkdir(mode=0o700)
    exact_private_root(folder)
    operator_secret = folder / "operator-private.pem"
    status_secret = folder / "status-private.pem"
    try:
        for secret, public in ((operator_secret, "operator-public.pem"),
                               (status_secret, "status-public.pem")):
            openssl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
                    "-out", secret)
            create(folder, public, openssl("pkey", "-in", secret, "-pubout"))
        authority_sha = hashlib.sha256((folder / "operator-public.pem").read_bytes()).hexdigest()
        status_sha = hashlib.sha256((folder / "status-public.pem").read_bytes()).hexdigest()
        # Deliberately synthetic role digest: NO mTLS session or remote witness.
        client_sha = hashlib.sha256(("CI_NO_TLS_PEER|" + head).encode()).hexdigest()
        now = int(time.time())
        record = {
            "schema": grant.SCHEMA, "repository": grant.REPO, "issuer": grant.ISSUER,
            "sequence": 1, "operator_authority_sha256": authority_sha,
            "status_signer_sha256": status_sha,
            "client_leaf_sha256": client_sha,
            "source_commit": head, "old_pkg_sha256": old_sha,
            "new_pkg_sha256": new_sha,
            "old_pkg_version": "0.6.2_1",
            "new_pkg_version": "0.6.2_" + revision,
            "not_before": now - 30, "not_after": now + 1800,
            "actions": ["RESERVE"], "entries": [identity],
        }
        for stem, change in (("signed-grant", {}),
                             ("wrong-old", {"old_pkg_sha256": "f"*64}),
                             ("wrong-new", {"new_pkg_sha256": "f"*64}),
                             ("wrong-head", {"source_commit": "f"*40})):
            value = {**record, **change}
            raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
            create(folder, stem + ".json", raw)
            create(folder, stem + ".sig",
                   openssl("dgst", "-sha256", "-sign", operator_secret, data=raw))
    finally:
        # Worker never receives signing private keys. This is CI custody only;
        # root of the runner could still replace authority PEM and expected pin.
        for secret in (operator_secret, status_secret):
            if secret.exists() and not secret.is_symlink():
                secret.unlink()
    return {
        "operator_sha256": authority_sha, "status_sha256": status_sha,
        "client_sha256": client_sha, **identity,
        "ci_signer_destroyed_before_configd_dispatch": True,
        "owner_operator_approved": False,
    }


def verify(root_dir, ticket, head, old_archive, candidate_archive, old_sha, new_sha,
           revision, fd9_check):
    """Fail closed on signed scope + archive bytes under a *real* old FD9 checker."""
    need(callable(fd9_check), "FD9_GRANT_CHECKER_REQUIRED")
    folder = Path(root_dir) / ROOT_NAME
    exact_private_root(folder)
    expected = expected_identity(head, old_sha, new_sha)
    need(type(ticket) is dict and set(ticket) == {
        "operator_sha256", "status_sha256", "client_sha256",
        "operation_id", "payload_sha256", "checkpoint_sha256",
        "checkpoint_sequence", "ci_signer_destroyed_before_configd_dispatch",
        "owner_operator_approved"} and
        all(ticket.get(k) == v for k,v in expected.items()) and
        ticket.get("ci_signer_destroyed_before_configd_dispatch") is True and
        ticket.get("owner_operator_approved") is False and
        all(SHA.fullmatch(ticket.get(k, "")) is not None
            for k in ("operator_sha256", "status_sha256", "client_sha256")),
        "FD9_GRANT_ROOT_TICKET_ROLE_OR_OPERATION_UNTRUSTED")
    need(not (folder / "operator-private.pem").exists() and
         not (folder / "status-private.pem").exists(),
         "FD9_GRANT_SIGNING_PRIVATE_KEY_PRESENT_IN_WORKER")
    grant = policy_module()

    def signed(stem):
        return grant.load(
            str(folder / (stem + ".json")), str(folder / (stem + ".sig")),
            str(folder / "operator-public.pem"),
            ticket["operator_sha256"], ticket["status_sha256"],
            ticket["client_sha256"], head, str(old_archive),
            str(candidate_archive))

    fd9_check()
    policy = signed("signed-grant")
    need(grant.authorize(policy, {"action": "RESERVE", **expected}),
         "FD9_GRANT_OPERATION_NOT_AUTHORIZED")
    # Correctly re-signed false SHA/head must fail the same real-byte policy.
    negatives = {"wrong-old": "GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST",
                 "wrong-new": "GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST",
                 "wrong-head": "GRANT_SOURCE_COMMIT_NOT_EXPECTED"}
    for stem, reason in negatives.items():
        fd9_check()
        try:
            signed(stem)
        except grant.Refusal as exc:
            need(str(exc) == reason, "FD9_GRANT_NEGATIVE_WRONG_REFUSAL:" + stem)
        else:
            raise Refusal("FD9_GRANT_RESIGNED_FALSE_SCOPE_ACCEPTED:" + stem)
    fd9_check()
    # This is not a durable reserve or one-use external witness: merely a
    # signed scope check inside original FD9 before an actual pkg dispatcher.
    return {"ci_operator_signature_verified": True,
            "ci_real_old_and_new_archives_measured": True,
            "ci_resigned_false_old_new_head_denied": True,
            "ci_original_fd9_held_during_grant_admission": True,
            "ci_remote_witness_deployed": False,
            "ci_owner_approval_authenticated": False,
            "ci_pkg_one_use_commit_proven": False,
            "lh08_ac11_accepted": False}


def cleanup(root_dir):
    folder = Path(root_dir) / ROOT_NAME
    exact_private_root(folder)
    need(set(p.name for p in folder.iterdir()) == set(FILES),
         "FD9_GRANT_CLEANUP_FOREIGN_OR_MISSING_FILE")
    for name in FILES:
        p = folder / name
        need(p.is_file() and not p.is_symlink() and p.stat().st_uid == os.geteuid() and
             stat.S_IMODE(p.stat().st_mode) == 0o600,
             "FD9_GRANT_CLEANUP_FILE_CHANGED:" + name)
    for name in FILES:
        (folder / name).unlink()
    folder.rmdir()
