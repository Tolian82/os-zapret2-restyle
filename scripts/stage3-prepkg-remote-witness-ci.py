#!/usr/bin/env python3
"""Stage 3 CI-only mTLS localhost witness, durable SQLite and RSA replies.

NOT a production witness: no owner-approved client identity or real independent host,
owner-approved key, trusted clock, external monotonic authority or pkg support.
The signer and journal belong to the same disposable CI host. All mutating
server functions require an explicit CI opt-in and bind only to 127.0.0.1.
"""
import base64
import hashlib
import hmac
import importlib.util
from pathlib import Path
import json
import os
import re
import socket
import socketserver
import ssl
import sqlite3
import subprocess
import sys
import time

SCHEMA = "zapret2-ci-signed-operation-status-v1"
ISSUER = "CI_SIMULATED_WITNESS_NOT_OWNER_APPROVED"
REPO = "Tolian82/os-zapret2-restyle"
SHA = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset(("action", "operation_id", "payload_sha256",
                    "checkpoint_sha256", "checkpoint_sequence",
                    "challenge_sha256"))
ACTIONS = ("RESERVE", "CONSUME", "ABORT", "STATUS")
MAX_REQUEST = 2048
MAX_ENVELOPE = 8192
TIMEOUT = 4

# Policy is an independent signed CI artifact; never silently skip admission.
_spec = importlib.util.spec_from_file_location(
    "stage3_ci_signed_operator_grant",
    Path(__file__).resolve().parent / "stage3-prepkg-operator-operation-grant-ci.py")
grant = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grant)


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def unique_json(raw):
    def unique(pairs):
        answer = {}
        for k, v in pairs:
            need(k not in answer, "REQUEST_DUPLICATE_JSON_KEY")
            answer[k] = v
        return answer
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              Refusal("REQUEST_NONFINITE_NUMBER")))
    except (UnicodeError, ValueError, TypeError):
        raise Refusal("REQUEST_INVALID_JSON") from None


def inspect(req):
    need(isinstance(req, dict) and set(req) in (FIELDS, FIELDS | {"drop_after_commit"}),
         "REQUEST_FIELDS_INVALID")
    need(isinstance(req["action"], str) and req["action"] in ACTIONS,
         "REQUEST_ACTION_INVALID")
    for key in ("operation_id", "payload_sha256", "checkpoint_sha256",
                "challenge_sha256"):
        value = req[key]
        need(isinstance(value, str) and SHA.fullmatch(value) is not None and
             value != "0" * 64, "REQUEST_SHA_INVALID:" + key)
    need(type(req["checkpoint_sequence"]) is int and
         1 <= req["checkpoint_sequence"] <= 1000000,
         "REQUEST_CHECKPOINT_SEQUENCE_INVALID")
    need("drop_after_commit" not in req or
         type(req["drop_after_commit"]) is bool,
         "REQUEST_DROP_FLAG_INVALID")
    return req


def open_existing(path):
    need(os.path.isabs(path) and os.path.realpath(path) == path and
         "\x00" not in path, "WITNESS_DB_ABSOLUTE_REGULAR_REQUIRED")
    need(os.path.isfile(path) and not os.path.islink(path),
         "WITNESS_DB_MISSING_OR_UNSAFE")
    connection = sqlite3.connect("file:" + path + "?mode=rw",
                                 uri=True, timeout=TIMEOUT,
                                 isolation_level=None)
    connection.execute("PRAGMA busy_timeout=4000")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def initialize(path):
    need(os.path.isabs(path) and not os.path.lexists(path),
         "WITNESS_DB_EXCLUSIVE_INIT_REQUIRED")
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), serial INTEGER NOT NULL)")
        conn.execute("INSERT INTO metadata VALUES (1,0)")
        conn.execute("CREATE TABLE challenges (value TEXT PRIMARY KEY)")
        conn.execute("""CREATE TABLE operations (
                        op TEXT PRIMARY KEY, payload TEXT NOT NULL,
                        checkpoint TEXT NOT NULL, cpseq INTEGER NOT NULL,
                        state TEXT NOT NULL CHECK(state IN ('RESERVED','CONSUMED','ABORTED')),
                        witness_seq INTEGER NOT NULL)""")
        conn.execute("""CREATE UNIQUE INDEX active_checkpoint ON operations(checkpoint)
                        WHERE state != 'ABORTED'""")
        conn.execute("COMMIT")
    finally:
        conn.close()
    os.chmod(path, 0o600)


def transition(path, data):
    req = inspect(data)
    con = open_existing(path)
    try:
        con.execute("BEGIN IMMEDIATE")
        # Every request challenge is consumed DURABLY even for read-only status
        # and exact idempotent re-reads. A lost reply needs a NEW challenge.
        con.execute("INSERT INTO challenges VALUES (?)", (req["challenge_sha256"],))
        op = req["operation_id"]
        old = con.execute("SELECT payload, checkpoint, cpseq, state, witness_seq "
                          "FROM operations WHERE op=?", (op,)).fetchone()
        action = req["action"]
        if action == "STATUS":
            need(old is not None, "WITNESS_OPERATION_UNKNOWN")
        if old is not None:
            need((old[0], old[1], old[2]) ==
                 (req["payload_sha256"], req["checkpoint_sha256"],
                  req["checkpoint_sequence"]),
                 "WITNESS_OPERATION_IDENTITY_CHANGED")
            if action == "RESERVE":
                need(old[3] == "RESERVED", "WITNESS_ALREADY_TERMINAL")
            elif action in ("CONSUME", "ABORT"):
                need(old[3] in ("RESERVED", "ABORTED" if action == "ABORT" else "CONSUMED"),
                     "WITNESS_TERMINAL_CONFLICT")
            if action == "CONSUME" and old[3] == "RESERVED":
                new_state = "CONSUMED"
            elif action == "ABORT" and old[3] == "RESERVED":
                new_state = "ABORTED"
            else:
                new_state = None
            if new_state is not None:
                serial = max(con.execute("SELECT serial FROM metadata WHERE id=1").fetchone()[0] + 1,
                             req["checkpoint_sequence"] + 1)
                con.execute("UPDATE metadata SET serial=? WHERE id=1", (serial,))
                con.execute("UPDATE operations SET state=?, witness_seq=? WHERE op=?",
                            (new_state, serial, op))
        else:
            need(action == "RESERVE", "WITNESS_RESERVE_REQUIRED")
            need(con.execute("SELECT count(*) FROM operations WHERE state='RESERVED'").fetchone()[0] == 0,
                 "WITNESS_OTHER_PENDING_OPERATION")
            serial = max(con.execute("SELECT serial FROM metadata WHERE id=1").fetchone()[0] + 1,
                             req["checkpoint_sequence"] + 1)
            con.execute("UPDATE metadata SET serial=? WHERE id=1", (serial,))
            con.execute("INSERT INTO operations VALUES (?,?,?,?,?,?)",
                        (op, req["payload_sha256"], req["checkpoint_sha256"],
                         req["checkpoint_sequence"], "RESERVED",
                         serial))
        row = con.execute("SELECT state, witness_seq FROM operations WHERE op=?", (op,)).fetchone()
        need(row is not None, "WITNESS_OPERATION_NOT_FOUND_AFTER_TX")
        con.execute("COMMIT")
        now = int(time.time())
        reply = {"schema": SCHEMA, "repository": REPO, "issuer": ISSUER,
                 "operation_id": op, "payload_sha256": req["payload_sha256"],
                 "checkpoint_sha256": req["checkpoint_sha256"],
                 "checkpoint_sequence": req["checkpoint_sequence"],
                 "witness_sequence": row[1], "challenge_sha256": req["challenge_sha256"],
                 "action": row[0], "issued_at": now, "expires_at": now + 60}
        return (json.dumps(reply, sort_keys=True, separators=(",", ":")) + "\n").encode()
    except Exception:
        try:
            con.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()


def seal(raw, key):
    try:
        result = subprocess.run(["/usr/bin/openssl", "dgst", "-sha256",
                                 "-sign", key], input=raw, capture_output=True,
                                timeout=TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("WITNESS_RSA_UNAVAILABLE") from None
    need(result.returncode == 0 and 0 < len(result.stdout) <= 1024,
         "WITNESS_SIGNING_FAILED")
    return result.stdout


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(TIMEOUT)
        try:
            frame = bytearray()
            while len(frame) <= MAX_REQUEST:
                byte = self.request.recv(1)
                if byte == b"\n":
                    break
                need(byte, "REQUEST_TRUNCATED")
                frame.extend(byte)
            else:
                raise Refusal("REQUEST_TOO_LARGE")
            request = inspect(unique_json(bytes(frame).decode("utf-8")))
            # Signed operator scope is checked before taking a SQLite lock.
            grant.authorize(self.server.operator_policy, request)
            raw = transition(self.server.database, request)
            if request.get("drop_after_commit", False):
                return  # Deliberate CI lost-reply injection AFTER SQLite commit.
            signed = seal(raw, self.server.key)
            envelope = {"message": base64.b64encode(raw).decode("ascii"),
                        "signature": base64.b64encode(signed).decode("ascii")}
            self.request.sendall((json.dumps(envelope, separators=(",", ":")) + "\n").encode())
        except (Refusal, grant.Refusal, sqlite3.Error, OSError, ValueError, UnicodeError) as exc:
            try:
                self.request.sendall((json.dumps({"refused": type(exc).__name__ + ":" + str(exc)}) + "\n").encode())
            except OSError:
                pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, handler, tls_context, approved_client_sha):
        self.tls_context = tls_context
        self.approved_client_sha = approved_client_sha
        super().__init__(address, handler)

    def get_request(self):
        sock, addr = super().get_request()
        try:
            sock.settimeout(TIMEOUT)
            secure = self.tls_context.wrap_socket(sock, server_side=True)
            identity = hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
            if not hmac.compare_digest(identity, self.approved_client_sha):
                secure.close()
                raise ssl.SSLError("WITNESS_CLIENT_CERT_PIN_MISMATCH")
            return secure, addr
        except (ssl.SSLError, OSError):
            sock.close()
            raise


def server_tls_context(ca_file, certificate, private_key):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=ca_file)
    context.load_cert_chain(certfile=certificate, keyfile=private_key)
    context.options |= ssl.OP_NO_COMPRESSION
    return context


def client_tls_context(ca_file, certificate, private_key):
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True  # Server certificate must match 127.0.0.1 SAN.
    context.load_cert_chain(certfile=certificate, keyfile=private_key)
    context.options |= ssl.OP_NO_COMPRESSION
    return context


def request(port, values, ca_file, client_certificate, client_private_key,
            expected_server_der_sha):
    need(type(port) is int and 0 < port < 65536, "CLIENT_PORT_INVALID")
    need(isinstance(expected_server_der_sha, str) and
         SHA.fullmatch(expected_server_der_sha) is not None and
         expected_server_der_sha != "0" * 64, "CLIENT_SERVER_CERT_PIN_REQUIRED")
    context = client_tls_context(ca_file, client_certificate, client_private_key)
    with socket.create_connection(("127.0.0.1", port), timeout=TIMEOUT) as channel:
      with context.wrap_socket(channel, server_hostname="127.0.0.1") as sock:
        sock.settimeout(TIMEOUT)
        server_sha = hashlib.sha256(sock.getpeercert(binary_form=True)).hexdigest()
        need(hmac.compare_digest(server_sha, expected_server_der_sha),
             "CLIENT_SERVER_CERT_PIN_MISMATCH")
        sock.sendall((json.dumps(values, separators=(",", ":")) + "\n").encode())
        chunks = bytearray()
        while len(chunks) <= MAX_ENVELOPE:
            part = sock.recv(4096)
            if not part:
                break
            chunks.extend(part)
            if b"\n" in chunks:
                break
        need(chunks and len(chunks) <= MAX_ENVELOPE and chunks.endswith(b"\n"),
             "CLIENT_REPLY_MISSING_OR_OVERSIZE")
    answer = unique_json(bytes(chunks).decode())
    need(isinstance(answer, dict), "CLIENT_ENVELOPE_INVALID")
    need("refused" not in answer and set(answer) == {"message", "signature"},
         "CLIENT_REFUSED_OR_BAD_ENVELOPE")
    try:
        return (base64.b64decode(answer["message"], validate=True),
                base64.b64decode(answer["signature"], validate=True))
    except (ValueError, TypeError):
        raise Refusal("CLIENT_ENVELOPE_BASE64_INVALID") from None


def main(args):
    try:
        need(os.environ.get("ZAPRET2_CI_REMOTE_WITNESS_ONLY") == "1",
             "WITNESS_DISPOSABLE_CI_OPTIN_REQUIRED")
        need(len(args) in (2, 14), "WITNESS_CLI_INVALID")
        if len(args) == 2 and args[0] == "init":
            initialize(args[1])
            print("CI_WITNESS_DB_INITIALIZED", flush=True)
        elif len(args) == 14 and args[0] == "serve":
            (path, key, ca, certificate, tls_key, client_sha,
             grant_path, grant_sig, operator_pem, operator_key_sha,
             source_commit, old_archive, new_archive) = args[1:]
            need(isinstance(client_sha, str) and SHA.fullmatch(client_sha) is not None and
                 client_sha != "0" * 64, "WITNESS_CLIENT_CERT_PIN_REQUIRED")
            need(os.path.exists(key) and os.path.isfile(key), "WITNESS_PRIVATE_SIGNER_MISSING")
            # The signed status key is derived from the actual private key,
            # never an unauthenticated caller-supplied matching digest.
            operator_policy = grant.load(
                grant_path, grant_sig, operator_pem, operator_key_sha,
                grant.signer_sha(key), client_sha, source_commit,
                old_archive, new_archive)
            tls = server_tls_context(ca, certificate, tls_key)
            with open_existing(path):
                pass
            with Server(("127.0.0.1", 0), Handler, tls, client_sha) as service:
                service.database = path
                service.key = key
                service.operator_policy = operator_policy
                print("CI_WITNESS_PORT=" + str(service.server_address[1]), flush=True)
                service.serve_forever(poll_interval=0.2)
        else:
            raise Refusal("WITNESS_CLI_INVALID")
        return 0
    except (Refusal, grant.Refusal, OSError, ssl.SSLError, sqlite3.Error, ValueError) as exc:
        print("CI_WITNESS_REFUSED:" + str(exc), file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
