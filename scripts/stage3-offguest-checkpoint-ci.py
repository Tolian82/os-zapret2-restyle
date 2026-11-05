#!/usr/bin/env python3
"""CI-only host/OPNsense network separation probe, NEVER a pkg authorization.

Host owns the ephemeral TLS/status private keys and SQLite, outside the synced
checkout. Guest receives only server.crt, status-public.pem and test pins.
The test host is still controlled by the same GitHub runner, NOT by the owner.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import sqlite3
import ssl
import stat
import subprocess
import sys
import time

SCHEMA = 'zapret2-ci-offguest-checkpoint-v1'
HEAD = re.compile(r'[a-f0-9]{40}\Z')
HEX = re.compile(r'[a-f0-9]{64}\Z')
MAX_FRAME = 4096
HOST_ALIAS = '10.0.2.2'


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def qualify():
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('ZAPRET2_STAGE3_OFFGUEST_CI') == '1',
         'CI_OFFGUEST_EXPLICIT_OPTIN_REQUIRED')


def strict_json(raw):
    def unique(pairs):
        output = {}
        for key, value in pairs:
            need(key not in output, 'CI_OFFGUEST_DUPLICATE_KEY')
            output[key] = value
        return output
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                          parse_constant=lambda x: (_ for _ in ()).throw(Refusal('CI_OFFGUEST_NONFINITE')))
    except (ValueError, UnicodeError, TypeError):
        raise Refusal('CI_OFFGUEST_INVALID_JSON') from None


def exact_private(path, kind):
    path = Path(path)
    st = path.lstat()
    need(st.st_uid == os.geteuid() and not path.is_symlink() and
         (stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o700 if kind == 'dir'
          else stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
               stat.S_IMODE(st.st_mode) == 0o600),
         'CI_OFFGUEST_PRIVATE_' + kind.upper() + '_INVALID')
    return path


def external_root(root, public):
    root = exact_private(root, 'dir')
    public = exact_private(public, 'dir')
    need(root.resolve() != public.resolve() and
         not public.resolve().is_relative_to(root.resolve()) and
         not root.resolve().is_relative_to(public.resolve()),
         'CI_OFFGUEST_HOST_AND_PUBLIC_OVERLAP')
    workspace = os.environ.get('GITHUB_WORKSPACE')
    if workspace:
        need(not root.resolve().is_relative_to(Path(workspace).resolve()),
             'CI_OFFGUEST_HOST_PRIVATE_KEY_IN_SHARED_WORKSPACE')
        need(public.resolve().is_relative_to(Path(workspace).resolve()),
             'CI_OFFGUEST_PUBLIC_FIXTURE_NOT_SHARED')
    return root, public


def openssl(*args, payload=None):
    cmd = ['/usr/bin/openssl', *map(str, args)]
    result = subprocess.run(cmd, input=payload, capture_output=True, timeout=15, check=False)
    need(result.returncode == 0, 'CI_OFFGUEST_OPENSSL_FAILURE:' + str(args[0]))
    return result.stdout


def write_owned(path, raw):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def setup(root, public, head):
    qualify()
    root, public = external_root(root, public)
    need(HEAD.fullmatch(head) is not None and head != '0'*40,
         'CI_OFFGUEST_HEAD_REQUIRED')
    need(not tuple(root.iterdir()) and not tuple(public.iterdir()),
         'CI_OFFGUEST_FIXTURE_ALREADY_EXISTS')
    key = root / 'tls.key'
    certificate = root / 'tls.crt'
    signer = root / 'status.key'
    openssl('req','-x509','-newkey','rsa:2048','-nodes','-sha256','-days','1',
            '-keyout',key,'-out',certificate,'-subj','/CN=CI-Offguest-Not-Owner',
            '-addext','subjectAltName=IP:10.0.2.2,IP:127.0.0.1')
    openssl('genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048', '-out',signer)
    for file in (key,certificate,signer):
        os.chmod(file, 0o600)
        exact_private(file, 'file')
    key_pub = openssl('pkey','-in',signer,'-pubout')
    cert = certificate.read_bytes()
    write_owned(public/'server.crt',cert)
    write_owned(public/'status-public.pem',key_pub)
    db = root/'checkpoint.sqlite'
    with sqlite3.connect(db) as connection:
        connection.execute('PRAGMA journal_mode=DELETE')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('CREATE TABLE checkpoint(id INTEGER PRIMARY KEY CHECK(id=1), seq INTEGER NOT NULL, head TEXT NOT NULL)')
        connection.execute('CREATE TABLE challenges(challenge TEXT PRIMARY KEY)')
        connection.execute('INSERT INTO checkpoint VALUES(1,7,?)',(head,))
    os.chmod(db,0o600)
    exact_private(db,'file')
    return {'key':key,'cert':certificate,'signer':signer,'db':db,
            'public':public,'tls_der':hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.decode())).hexdigest(),
            'status_sha':hashlib.sha256(key_pub).hexdigest(),'head':head}


def handle_status(database, signer, request, expected_head):
    need(type(request) is dict and set(request) == {'action','challenge','head'} and
         request['action']=='STATUS' and type(request['challenge']) is str and
         HEX.fullmatch(request['challenge']) is not None and
         request['head']==expected_head,'CI_OFFGUEST_REQUEST_SCOPE_INVALID')
    with sqlite3.connect(database, isolation_level=None, timeout=5) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        try:
            sequence, head = db.execute('SELECT seq,head FROM checkpoint WHERE id=1').fetchone()
            need(head==expected_head and sequence==7,'CI_OFFGUEST_CHECKPOINT_CHANGED')
            need(db.execute('SELECT COUNT(*) FROM checkpoint').fetchone()[0]==1,
                 'CI_OFFGUEST_MULTIPLE_CHECKPOINTS')
            try:
                db.execute('INSERT INTO challenges VALUES(?)',(request['challenge'],))
            except sqlite3.IntegrityError:
                raise Refusal('CI_OFFGUEST_CHALLENGE_REPLAY') from None
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK')
            raise
    raw=(json.dumps({'schema':SCHEMA,'head':head,'challenge':request['challenge'],
                     'sequence':sequence,'status':'CI_HOST_CHECKPOINT_ONLY',
                     'production_pkg_authorized':False},sort_keys=True,separators=(',',':'))+'\n').encode()
    signature=openssl('dgst','-sha256','-sign',signer,payload=raw)
    return (json.dumps({'raw':base64.b64encode(raw).decode(),
                        'sig':base64.b64encode(signature).decode()},
                       sort_keys=True,separators=(',',':'))+'\n').encode()


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(8)
        try:
            frame=bytearray()
            while len(frame) < MAX_FRAME:
                byte=self.request.recv(1)
                need(byte,'CI_OFFGUEST_REQUEST_EOF')
                if byte==b'\n':break
                frame.extend(byte)
            else:raise Refusal('CI_OFFGUEST_REQUEST_OVERSIZE')
            result=handle_status(self.server.database,self.server.signer,
                                 strict_json(bytes(frame)),self.server.head)
        except (Refusal,sqlite3.Error,OSError,ValueError) as exc:
            result=(json.dumps({'refused':str(exc)})+'\n').encode()
        try:self.request.sendall(result)
        except OSError:pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=False
    daemon_threads=True
    def __init__(self,address,context):
        self.context=context
        super().__init__(address,Handler)
    def get_request(self):
        sock,addr=super().get_request()
        try:
            return self.context.wrap_socket(sock,server_side=True),addr
        except BaseException:
            sock.close()
            raise


def serve(root,public,head):
    state=setup(root,public,head)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(state['cert'],state['key'])
    with Server(('127.0.0.1',0),context) as server:
        server.database=state['db'];server.signer=state['signer'];server.head=head
        endpoint={'schema':SCHEMA,'head':head,'host':HOST_ALIAS,
                  'port':server.server_address[1],
                  'tls_der_sha256':state['tls_der'],
                  'status_pub_sha256':state['status_sha'],
                  'production_pkg_authorized':False}
        write_owned(state['public']/'endpoint.json',
                    (json.dumps(endpoint,sort_keys=True)+'\n').encode())
        print('CI_OFFGUEST_HOST_READY='+str(server.server_address[1]),flush=True)
        server.serve_forever(poll_interval=.2)


def read_public(public):
    public=exact_private(public,'dir')
    need({p.name for p in public.iterdir()}=={'server.crt','status-public.pem','endpoint.json'},
         'CI_OFFGUEST_UNEXPECTED_PUBLIC_FILES')
    raw={p.name:exact_private(p,'file').read_bytes() for p in public.iterdir()}
    need(all(0<len(x)<8192 for x in raw.values()),'CI_OFFGUEST_BAD_PUBLIC_SIZE')
    ep=strict_json(raw['endpoint.json'])
    need(type(ep) is dict and set(ep)=={'schema','head','host','port',
              'tls_der_sha256','status_pub_sha256','production_pkg_authorized'} and
         ep['schema']==SCHEMA and ep['host']==HOST_ALIAS and
         HEAD.fullmatch(ep['head']) and type(ep['port']) is int and 0<ep['port']<65536 and
         type(ep['production_pkg_authorized']) is bool and not ep['production_pkg_authorized'],
         'CI_OFFGUEST_ENDPOINT_SCOPE_INVALID')
    cert_der=ssl.PEM_cert_to_DER_cert(raw['server.crt'].decode())
    need(hashlib.sha256(cert_der).hexdigest()==ep['tls_der_sha256'] and
         hashlib.sha256(raw['status-public.pem']).hexdigest()==ep['status_pub_sha256'],
         'CI_OFFGUEST_PUBLIC_PINS_INCONSISTENT')
    return ep,raw


def status_request(public,head,challenge,host=HOST_ALIAS):
    qualify()
    ep,files=read_public(public)
    need(ep['head']==head and HEX.fullmatch(challenge) is not None and
         host in (HOST_ALIAS,'127.0.0.1'),'CI_OFFGUEST_CLIENT_SCOPE_INVALID')
    context=ssl.create_default_context(cadata=files['server.crt'].decode())
    context.check_hostname=True
    with socket.create_connection((host,ep['port']),timeout=8) as channel:
        with context.wrap_socket(channel,server_hostname=host) as conn:
            der=conn.getpeercert(binary_form=True)
            need(hashlib.sha256(der).hexdigest()==ep['tls_der_sha256'],
                 'CI_OFFGUEST_SERVER_CERT_CHANGED')
            conn.sendall((json.dumps({'action':'STATUS','head':head,
                                      'challenge':challenge})+'\n').encode())
            answer=bytearray()
            while len(answer)<MAX_FRAME:
                chunk=conn.recv(1024)
                need(chunk,'CI_OFFGUEST_REPLY_EOF')
                answer.extend(chunk)
                if b'\n' in answer:break
            else:raise Refusal('CI_OFFGUEST_REPLY_OVERSIZE')
    response=strict_json(bytes(answer))
    need(isinstance(response,dict) and set(response)=={'raw','sig'},
         'CI_OFFGUEST_REMOTE_REFUSED_OR_BAD_ENVELOPE')
    try:
        payload=base64.b64decode(response['raw'],validate=True)
        signature=base64.b64decode(response['sig'],validate=True)
    except (TypeError,ValueError):
        raise Refusal('CI_OFFGUEST_BAD_SIGNATURE_ENCODING') from None
    need(0<len(payload)<=MAX_FRAME and 0<len(signature)<=1024,
         'CI_OFFGUEST_SIGNED_REPLY_SIZE_INVALID')
    public_key=Path(public)/'status-public.pem'
    sigfile=Path(public)/'tmp-response.sig'
    # Test-only disposable guest can create an exclusive temporary signature.
    write_owned(sigfile,signature)
    try:
        result=subprocess.run(['/usr/bin/openssl','dgst','-sha256','-verify',
                               str(public_key),'-signature',str(sigfile)],
                              input=payload,capture_output=True,timeout=8,check=False)
        need(result.returncode==0 and result.stdout.strip()==b'Verified OK',
             'CI_OFFGUEST_STATUS_SIGNATURE_INVALID')
    finally:
        sigfile.unlink()
    decoded=strict_json(payload)
    need(type(decoded) is dict and set(decoded)=={'schema','head','challenge','sequence',
          'status','production_pkg_authorized'} and decoded['schema']==SCHEMA and
         decoded['head']==head and decoded['challenge']==challenge and
         type(decoded['sequence']) is int and decoded['sequence']==7 and
         decoded['status']=='CI_HOST_CHECKPOINT_ONLY' and
         decoded['production_pkg_authorized'] is False,
         'CI_OFFGUEST_SIGNED_STATUS_NOT_BOUND')
    return decoded


def scenario(public,head,host=HOST_ALIAS):
    import secrets
    first=secrets.token_hex(32)
    result=status_request(public,head,first,host)
    need(result['sequence']==7,'CI_OFFGUEST_MISSING_HOST_HIGHWATER')
    second=secrets.token_hex(32)
    latest=status_request(public,head,second,host)
    need(latest['sequence']==7 and second!=first,
         'CI_OFFGUEST_HOST_SEQUENCE_NOT_STABLE')
    try:
        status_request(public,head,first,host)
    except Refusal as exc:
        need(str(exc)=='CI_OFFGUEST_REMOTE_REFUSED_OR_BAD_ENVELOPE',
             'CI_OFFGUEST_WRONG_REPLAY_REFUSAL')
    else:
        raise Refusal('CI_OFFGUEST_CHALLENGE_REPLAY_ACCEPTED')
    return {'status':'PASS_CI_OFFGUEST_CHECKPOINT_TRANSPORT_ONLY',
            'verified_status_responses':2,'replay_refused':True,
            'host_sequence':7,'host_private_key_on_guest':False,
            'owner_approved_authority':False,'production_pkg_authorized':False}


def audit_host(root,public,head):
    qualify()
    root,public=external_root(root,public)
    names={p.name for p in root.iterdir()}
    need(names=={'tls.key','tls.crt','status.key','checkpoint.sqlite'},
         'CI_OFFGUEST_HOST_PRIVATE_RESOURCE_DRIFT')
    for p in root.iterdir():exact_private(p,'file')
    ep,_=read_public(public)
    need(ep['head']==head and not any(n.endswith('.key') or 'sqlite' in n for n in
         (p.name for p in public.iterdir())), 'CI_OFFGUEST_SECRETS_EXPORTED')
    with sqlite3.connect(root/'checkpoint.sqlite') as db:
        need(db.execute('SELECT seq,head FROM checkpoint').fetchall()==[(7,head)] and
             db.execute('SELECT count(*) FROM challenges').fetchone()[0]==2,
             'CI_OFFGUEST_HOST_PERSISTENCE_NOT_PROVEN')
    return {'status':'PASS_CI_HOST_KEY_AND_SQLITE_NOT_SYNCED',
            'external_operator_enrolled':False,'pkg_invoked':False}


def main(argv):
    try:
        qualify()
        need(len(argv)>=1,'CI_OFFGUEST_CLI_MISSING')
        if len(argv)==4 and argv[0]=='serve':
            serve(Path(argv[1]),Path(argv[2]),argv[3]);return 0
        if len(argv)==3 and argv[0]=='client':
            print('CI_OFFGUEST='+json.dumps(scenario(Path(argv[1]),argv[2]),sort_keys=True));return 0
        if len(argv)==4 and argv[0]=='audit':
            print('CI_OFFGUEST='+json.dumps(audit_host(Path(argv[1]),Path(argv[2]),argv[3]),sort_keys=True));return 0
        raise Refusal('CI_OFFGUEST_CLI_INVALID')
    except (Refusal,OSError,ssl.SSLError,sqlite3.Error,subprocess.SubprocessError) as exc:
        print('CI_OFFGUEST=REFUSED:'+type(exc).__name__+':'+str(exc),file=sys.stderr)
        return 78


if __name__=='__main__':
    sys.exit(main(sys.argv[1:]))
