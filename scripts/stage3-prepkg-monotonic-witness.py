#!/usr/bin/env python3
"""Disposable same-VM *simulation* of an independent monotonic witness.

An external, independently administered owner-approved witness is NOT present.
This local fixture proves compare-and-append, fail-closed denial, races, and
split-state handling; it cannot defend against a root attacker rolling back
BOTH this store and the original ledger. No pkg/upgrade entrypoint exists.
"""
import contextlib
import fcntl
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "ci_signed_ledger_checkpoint",HERE/"stage3-prepkg-checkpoint-witness.py")
checkpoint=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)
ledger=checkpoint.ledger

PREFIX="ZAPRET2_STAGE3_MONOTONIC_WITNESS="
SCHEMA="zapret2-ci-monotonic-remote-state-v1"
ROOT_NAME="witness-store"
LOCK="witness.lock"
STATE=re.compile(r"state-([0-9]{12})\.json\Z")
FIELDS=frozenset(("schema","repository","generation","checkpoint_sequence",
                 "checkpoint_sha256","head_sha256","witness_key_sha256",
                 "previous_record_sha256"))
MAX_BYTES=2048
MAX_EVENTS=512


class Refusal(Exception):
    pass


def need(yes, reason):
    if not yes:
        raise Refusal(reason)


def canonical_root(path):
    need(isinstance(path,str) and path.startswith("/root/") and
         os.path.normpath(path)==path and os.path.basename(path)==ROOT_NAME and
         "\x00" not in path,"REMOTE_WITNESS_PRIVATE_DIRECTORY_REQUIRED")
    current=path
    while True:
        st=os.lstat(current)
        need(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and
             (stat.S_IMODE(st.st_mode)&0o022)==0,
             "REMOTE_WITNESS_UNTRUSTED_ANCESTOR")
        if current==path:
            need(stat.S_IMODE(st.st_mode)==0o700,
                 "REMOTE_WITNESS_DIRECTORY_0700_REQUIRED")
        if current=="/root":
            break
        parent=os.path.dirname(current)
        need(parent!=current,"REMOTE_WITNESS_PATH_ESCAPE")
        current=parent


@contextlib.contextmanager
def directory(path):
    ledger.qualify_runtime()  # Four CI-only guards; never production.
    canonical_root(path)
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        original=os.fstat(fd)
        named=os.lstat(path)
        need(stat.S_ISDIR(original.st_mode) and original.st_uid==0 and
             stat.S_IMODE(original.st_mode)==0o700 and
             (original.st_dev,original.st_ino)==(named.st_dev,named.st_ino),
             "REMOTE_WITNESS_DIRECTORY_RACED")
        yield fd
        later=os.fstat(fd)
        need((original.st_dev,original.st_ino)==(later.st_dev,later.st_ino),
             "REMOTE_WITNESS_DIRECTORY_CHANGED")
    finally:
        os.close(fd)


@contextlib.contextmanager
def exclusive(fd):
    opened=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        st=os.fstat(opened)
        named=os.stat(LOCK,dir_fd=fd,follow_symlinks=False)
        need(stat.S_ISREG(st.st_mode) and st.st_uid==0 and
             st.st_nlink==1 and st.st_size==0 and
             stat.S_IMODE(st.st_mode)==0o600 and
             (st.st_dev,st.st_ino)==(named.st_dev,named.st_ino),
             "REMOTE_WITNESS_LOCK_UNTRUSTED")
        try:
            fcntl.flock(opened,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (BlockingIOError,OSError):
            raise Refusal("REMOTE_WITNESS_BUSY_FAIL_CLOSED") from None
        now=os.stat(LOCK,dir_fd=fd,follow_symlinks=False)
        need((st.st_dev,st.st_ino)==(now.st_dev,now.st_ino),
             "REMOTE_WITNESS_LOCK_REPLACED")
        yield
    finally:
        os.close(opened)


def records(fd):
    names=os.listdir(fd)
    need(LOCK in names,"REMOTE_WITNESS_LOCK_MISSING")
    names.remove(LOCK)
    need(0<len(names)<=MAX_EVENTS,"REMOTE_WITNESS_UNINITIALIZED_OR_TOO_MANY")
    need(all(STATE.fullmatch(x) is not None for x in names),
         "REMOTE_WITNESS_UNKNOWN_OR_PARTIAL_FILE")
    previous="0"*64
    last_seq=0
    last_key=None
    used=set()
    entries=[]
    for generation,name in enumerate(sorted(names),1):
        raw=ledger.private_file(fd,name,MAX_BYTES)
        try:
            item=ledger.strict_json(raw)
        except ledger.Refusal as exc:
            raise Refusal("REMOTE_WITNESS_"+str(exc)) from None
        need(isinstance(item,dict) and set(item)==FIELDS and
             item["schema"]==SCHEMA and item["repository"]==ledger.REPO and
             type(item["generation"]) is int and item["generation"]==generation and
             int(STATE.fullmatch(name).group(1))==generation and
             type(item["checkpoint_sequence"]) is int and
             1<=item["checkpoint_sequence"]<=ledger.MAX_ENTRIES,
             "REMOTE_WITNESS_RECORD_SCHEMA_OR_GENERATION")
        for field in ("checkpoint_sha256","head_sha256","witness_key_sha256",
                      "previous_record_sha256"):
            need(isinstance(item[field],str) and
                 checkpoint.SHA.fullmatch(item[field]) is not None,
                 "REMOTE_WITNESS_BAD_RECORD_HASH:"+field)
        need(checkpoint.digest_valid(item["checkpoint_sha256"]) and
             checkpoint.digest_valid(item["head_sha256"]) and
             checkpoint.digest_valid(item["witness_key_sha256"]) and
             hmac.compare_digest(item["previous_record_sha256"],previous) and
             item["checkpoint_sha256"] not in used and
             (last_key is None or item["witness_key_sha256"]==last_key) and
             (last_seq==0 or item["checkpoint_sequence"]==last_seq+1),
             "REMOTE_WITNESS_CHAIN_OR_SEQUENCE_DIVERGED")
        entries.append(item)
        previous=hashlib.sha256(raw).hexdigest()
        last_seq=item["checkpoint_sequence"]
        last_key=item["witness_key_sha256"]
        used.add(item["checkpoint_sha256"])
    return entries,previous


def write_record(fd,generation,sequence,checkpoint_sha,head,key_sha,previous,
                 fail_after_create=False):
    need(1<=generation<=MAX_EVENTS,"REMOTE_WITNESS_CAPACITY")
    item={"schema":SCHEMA,"repository":ledger.REPO,
          "generation":generation,"checkpoint_sequence":sequence,
          "checkpoint_sha256":checkpoint_sha,"head_sha256":head,
          "witness_key_sha256":key_sha,"previous_record_sha256":previous}
    raw=(json.dumps(item,sort_keys=True,separators=(",",":"))+"\n").encode()
    need(len(raw)<=MAX_BYTES,"REMOTE_WITNESS_RECORD_OVERSIZE")
    name="state-"+f"{generation:012d}"+".json"
    output=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                   0o600,dir_fd=fd)
    try:
        if fail_after_create:
            raise Refusal("REMOTE_WITNESS_INJECTED_INTERRUPTED_APPEND")
        position=0
        while position<len(raw):
            copied=os.write(output,raw[position:])
            need(copied>0,"REMOTE_WITNESS_POISONED_SHORT_WRITE")
            position+=copied
        os.fsync(output)
    finally:
        os.close(output)
    os.fsync(fd)
    return item


def trusted_local_match(ledger_path,key_sha,key_path,checkpoint_sha,
                        checkpoint_path,sig_path):
    # A real RSA signature is verified, but signer identity/expected latest
    # SHA are caller-chosen CI values unless independently owner provisioned.
    try:
        return checkpoint.verify(ledger_path,key_sha,key_path,checkpoint_sha,
                                 checkpoint_path,sig_path)
    except checkpoint.Refusal as exc:
        raise Refusal("REMOTE_WITNESS_SIGNED_CHECKPOINT_"+str(exc)) from None
    except ledger.Refusal as exc:
        raise Refusal("REMOTE_WITNESS_LOCAL_"+str(exc)) from None


def bootstrap(store,ledger_path,key_sha,key_path,sha,source,sig):
    ledger.qualify_runtime()
    with directory(store) as fd:
        need(not os.listdir(fd),"REMOTE_WITNESS_ALREADY_BOOTSTRAPPED")
        # A local bootstrap is explicitly NOT an out-of-band approved genesis.
        proof=trusted_local_match(ledger_path,key_sha,key_path,sha,source,sig)
        lock=os.open(LOCK,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                     0o600,dir_fd=fd)
        try:
            os.fsync(lock)
        finally:
            os.close(lock)
        os.fsync(fd)
        with exclusive(fd):
            write_record(fd,1,proof["checkpoint_sequence"],
                         sha,proof["ledger_head_sha256"],key_sha,"0"*64)
    return {"status":"CI_WITNESS_BOOTSTRAP_UNTRUSTED_LOCAL_ONLY",
            "sequence":proof["checkpoint_sequence"],
            "production_external_witness":False,"pkg_invoked":False}


def publish(store,ledger_path,key_sha,key_path,sha,source,sig,
            expected_seq,expected_prior_sha):
    ledger.qualify_runtime()
    need(type(expected_seq) is int and expected_seq>0 and
         checkpoint.digest_valid(expected_prior_sha) and
         checkpoint.digest_valid(sha) and
         checkpoint.digest_valid(key_sha),
         "REMOTE_WITNESS_EXPECTED_CAS_INVALID")
    with directory(store) as fd,exclusive(fd):
        events,previous=records(fd)
        latest=events[-1]
        need(latest["checkpoint_sequence"]==expected_seq and
             hmac.compare_digest(latest["checkpoint_sha256"],expected_prior_sha),
             "REMOTE_WITNESS_CAS_STALE_OR_CONCURRENT")
        need(latest["witness_key_sha256"]==key_sha,
             "REMOTE_WITNESS_SIGNER_ROTATION_UNAPPROVED")
        proof=trusted_local_match(ledger_path,key_sha,key_path,sha,source,sig)
        need(proof["checkpoint_sequence"]==expected_seq+1,
             "REMOTE_WITNESS_SEQUENCE_GAP_OR_ROLLBACK")
        written=write_record(fd,len(events)+1,proof["checkpoint_sequence"],
                             sha,proof["ledger_head_sha256"],key_sha,previous)
    return {"status":"CI_WITNESS_CAS_PUBLISHED_LOCAL_ONLY",
            "sequence":written["checkpoint_sequence"],
            "checkpoint_sha256":written["checkpoint_sha256"],
            "production_external_witness":False,"pkg_invoked":False}


def compare(store,ledger_path,key_sha,key_path,source,sig):
    ledger.qualify_runtime()
    need(checkpoint.digest_valid(key_sha),"REMOTE_WITNESS_KEY_PIN_REQUIRED")
    # Latest comes from the witness store, NEVER a caller-specified
    # "expected latest" SHA. The store is *not* truly remote in CI.
    with directory(store) as fd,exclusive(fd):
        events,_=records(fd)
        latest=events[-1]
        need(latest["witness_key_sha256"]==key_sha,
             "REMOTE_WITNESS_KEY_MISMATCH")
        proof=trusted_local_match(ledger_path,key_sha,key_path,
                                  latest["checkpoint_sha256"],source,sig)
        need(proof["checkpoint_sequence"]==latest["checkpoint_sequence"] and
             proof["ledger_head_sha256"]==latest["head_sha256"],
             "REMOTE_WITNESS_MATCHED_DIFFERENT_LOCAL_HISTORY")
    return {"status":"CI_WITNESS_CURRENT_LOCAL_MATCH_NOT_OWNER_APPROVAL",
            "sequence":latest["checkpoint_sequence"],
            "checkpoint_sha256":latest["checkpoint_sha256"],
            "witness_latest_independently_anchored":False,
            "witness_root_rollback_resistant":False,
            "witness_remote_service_deployed":False,
            "cross_store_atomic_transaction_implemented":False,
            "production_pkg_authorized":False,"pkg_invoked":False}


def main(args):
    try:
        ledger.qualify_runtime()
        need(args and args[0] in ("bootstrap","publish","compare"),
             "REMOTE_WITNESS_COMMAND_REQUIRED")
        if len(args)==8 and args[0]=="bootstrap":
            result=bootstrap(*args[1:])
        elif len(args)==10 and args[0]=="publish":
            need(re.fullmatch(r"[1-9][0-9]{0,11}\Z",args[-2]) is not None,
                 "REMOTE_WITNESS_DECIMAL_SEQUENCE_REQUIRED")
            result=publish(*args[1:-2],int(args[-2]),args[-1])
        elif len(args)==7 and args[0]=="compare":
            result=compare(*args[1:])
        else:
            raise Refusal("REMOTE_WITNESS_EXACT_ARGUMENTS_REQUIRED")
    except (Refusal,ledger.Refusal,checkpoint.Refusal,OSError,ValueError,
            UnicodeError,TypeError) as exc:
        print(PREFIX+"REFUSED:"+str(exc),file=sys.stderr)
        return 78
    print(PREFIX+json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
