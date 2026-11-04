#!/usr/bin/env python3
"""Disposable OPNsense-only signed-grant proof using TWO REAL archive byte streams.

Called only from the existing Stage 3 isolated native bootstrap after official
Mk builds a source-only candidate. This script never invokes pkg or changes
the installed predecessor, Config, IPFW or any real archive.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
SCHEMA = "zapret2-ci-operator-operation-grant-v1"
REPO = "Tolian82/os-zapret2-restyle"


def load():
    spec = importlib.util.spec_from_file_location(
        "ci_measured_grant_native", HERE / "stage3-prepkg-operator-operation-grant-ci.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Refusal(Exception):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def command(*args, data=None):
    result = subprocess.run(["/usr/bin/openssl", *map(str, args)],
                            input=data, capture_output=True, timeout=15)
    need(result.returncode == 0, "NATIVE_GRANT_OPENSSL_FAILED")
    return result.stdout


def version(path, rules):
    name = path.name
    need(name.startswith(rules.PKG_NAME + "-") and name.endswith(".pkg"),
         "NATIVE_GRANT_PACKAGE_FILENAME_INVALID")
    value = name[len(rules.PKG_NAME) + 1:-4]
    need(rules.VERSION.fullmatch(value) is not None,
         "NATIVE_GRANT_PACKAGE_VERSION_INVALID")
    return value


def write_private(path, data):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600)
    try:
        while data:
            n = os.write(fd, data)
            need(n > 0, "NATIVE_GRANT_WRITE_FAILED")
            data = data[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def evaluate(old_path, incoming_path, old_sha, incoming_sha, commit):
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         os.getenv("GITHUB_ACTIONS") == "true" and
         os.getenv("ZAPRET2_STAGE3_PREPKG_ARCHIVE_BOOTSTRAP") == "1" and
         os.getenv("ZAPRET2_NATIVE_PROJECT_SHA") == commit,
         "NATIVE_GRANT_DISPOSABLE_TARGET_AND_EXACT_HEAD_REQUIRED")
    need(re.fullmatch("[0-9a-f]{40}", commit) is not None and
         all(re.fullmatch("[0-9a-f]{64}", x) is not None and x != "0" * 64
             for x in (old_sha, incoming_sha)),
         "NATIVE_GRANT_DIGEST_IDENTITY_INVALID")
    rules = load()
    old = Path(old_path)
    new = Path(incoming_path)
    old_ver = version(old, rules)
    new_ver = version(new, rules)
    old_size = rules.measured_archive(str(old), old_ver, old_sha)
    new_size = rules.measured_archive(str(new), new_ver, incoming_sha)
    need(old != new and old_ver != new_ver and
         old_size > 100000 and new_size > 100000,
         "NATIVE_GRANT_TWO_REAL_DISTINCT_ARCHIVES_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="ci-measured-archive-grant-", dir="/root") as tmp:
        root = Path(tmp)
        signing_key = root / "operator-private.pem"
        operator_pem = root / "operator-public.pem"
        status_key = root / "witness-private.pem"
        status_pem = root / "witness-public.pem"
        for private, public in ((signing_key, operator_pem),
                                (status_key, status_pem)):
            command("genpkey", "-algorithm", "RSA", "-pkeyopt",
                    "rsa_keygen_bits:2048", "-out", private)
            write_private(public, command("pkey", "-in", private, "-pubout"))
        operator_sha = hashlib.sha256(operator_pem.read_bytes()).hexdigest()
        witness_sha = hashlib.sha256(status_pem.read_bytes()).hexdigest()
        client_sha = "a" * 64  # Synthetic client binding: no live TLS in this helper.
        op = hashlib.sha256(("operation:" + commit).encode()).hexdigest()
        payload = hashlib.sha256(("payload:" + commit).encode()).hexdigest()
        cp = hashlib.sha256(("checkpoint:" + commit).encode()).hexdigest()
        grant = {
            "schema": SCHEMA, "repository": REPO,
            "issuer": "CI_EPHEMERAL_OPERATOR_NOT_OWNER_APPROVED",
            "sequence": 1, "operator_authority_sha256": operator_sha,
            "status_signer_sha256": witness_sha,
            "client_leaf_sha256": client_sha,
            "source_commit": commit,
            "old_pkg_sha256": old_sha, "new_pkg_sha256": incoming_sha,
            "old_pkg_version": old_ver, "new_pkg_version": new_ver,
            "not_before": int(time.time()) - 30,
            "not_after": int(time.time()) + 300,
            "actions": ["RESERVE"],
            "entries": [{"operation_id": op,
                         "payload_sha256": payload,
                         "checkpoint_sha256": cp,
                         "checkpoint_sequence": 1}]
        }
        grant_file = root / "signed-grant.json"
        sig_file = root / "signed-grant.sig"

        def seal(value):
            data = (json.dumps(value, sort_keys=True,
                               separators=(",", ":")) + "\n").encode()
            for target in (grant_file, sig_file):
                if target.exists():
                    target.unlink()
            write_private(grant_file, data)
            write_private(sig_file, command(
                "dgst", "-sha256", "-sign", signing_key, data=data))

        def admitted(expected_commit=commit):
            return rules.load(
                str(grant_file), str(sig_file), str(operator_pem),
                operator_sha, witness_sha, client_sha, expected_commit,
                str(old), str(new))

        seal(grant)
        policy = admitted()
        request = {"action": "RESERVE", "operation_id": op,
                   "payload_sha256": payload,
                   "checkpoint_sha256": cp,
                   "checkpoint_sequence": 1}
        need(rules.authorize(policy, request), "NATIVE_GRANT_REAL_PAIR_NOT_AUTHORIZED")
        try:
            rules.authorize(policy, {**request, "action": "ABORT"})
        except rules.Refusal as error:
            need(str(error) == "GRANT_ACTION_NOT_AUTHORIZED",
                 "NATIVE_GRANT_WRONG_ACTION_REFUSAL")
        else:
            raise Refusal("NATIVE_GRANT_WRONG_ACTION_ACCEPTED")

        # A properly RESIGNED grant still cannot rewrite measured original
        # archive bytes through false SHA claims or an alternate source head.
        grant["old_pkg_sha256"] = "f" * 64
        seal(grant)
        try:
            admitted()
        except rules.Refusal as error:
            need(str(error) == "GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST",
                 "NATIVE_GRANT_OLD_SHA_MISMATCH_INCORRECT_REFUSAL")
        else:
            raise Refusal("NATIVE_GRANT_RESIGNED_WRONG_OLD_ARCHIVE_ACCEPTED")
        grant["old_pkg_sha256"] = old_sha
        grant["new_pkg_sha256"] = "f" * 64
        seal(grant)
        try:
            admitted()
        except rules.Refusal as error:
            need(str(error) == "GRANT_ARCHIVE_BYTES_NOT_SIGNED_DIGEST",
                 "NATIVE_GRANT_NEW_SHA_MISMATCH_INCORRECT_REFUSAL")
        else:
            raise Refusal("NATIVE_GRANT_RESIGNED_WRONG_NEW_ARCHIVE_ACCEPTED")
        grant["new_pkg_sha256"] = incoming_sha
        grant["source_commit"] = "f" * 40
        seal(grant)
        try:
            admitted()
        except rules.Refusal as error:
            need(str(error) == "GRANT_SOURCE_COMMIT_NOT_EXPECTED",
                 "NATIVE_GRANT_HEAD_MISMATCH_INCORRECT_REFUSAL")
        else:
            raise Refusal("NATIVE_GRANT_RESIGNED_WRONG_SOURCE_ACCEPTED")
    return {"status": "PASS_NATIVE_REAL_OLD_AND_OFFICIAL_MK_CANDIDATE_SIGNED_GRANT",
            "actual_old_archive_sha256": old_sha,
            "actual_incoming_archive_sha256": incoming_sha,
            "old_version": old_ver, "incoming_version": new_ver,
            "old_bytes_measured": old_size, "incoming_bytes_measured": new_size,
            "source_commit": commit, "signed_scope_verified": True,
            "resigned_false_archive_and_head_refused": True,
            "operator_approval_owner_authenticated": False,
            "archive_signature_owner_authenticated": False,
            "independent_remote_witness_deployed": False,
            "installed_pkg_mutation": False,
            "pkg_invoked_by_this_step": False,
            "supported_updater_implemented": False,
            "lh08_ac11_accepted": False}


def main(args):
    try:
        need(len(args) == 5, "NATIVE_GRANT_EXACT_ARCHIVE_ARGS_REQUIRED")
        result = evaluate(*args)
        print("STAGE3_MEASURED_GRANT=" + json.dumps(result, sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print("STAGE3_MEASURED_GRANT=REFUSED:" + str(exc), file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
