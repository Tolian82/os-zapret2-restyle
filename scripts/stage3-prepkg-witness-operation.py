#!/usr/bin/env python3
"""CI-only idempotent witness operation reservation / terminal status protocol.

NEVER a supported pkg gateway. SAME disposable VM, no owner-approved signer,
external durable high-watermark, server, or cross-store transaction. All
input identities are CI fixtures, not real owner authorization.
"""
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "stage3_ci_monotonic_witness",HERE/"stage3-prepkg-monotonic-witness.py")
monotonic=importlib.util.module_from_spec(spec)
spec.loader.exec_module(monotonic)
ledger=monotonic.ledger
checkpoint=monotonic.checkpoint

PREFIX="ZAPRET2_STAGE3_OPERATION_ADMISSION="
SCHEMA="zapret2-ci-witness-operation-event-v1"
ENTRY=re.compile(r"operation-([0-9]{12})-([0-9a-f]{64})\.json\Z")
FIELDS=frozenset(("schema","repository","event_number","operation_id",
                  "payload_sha256","checkpoint_sha256",
                  "checkpoint_sequence","action","previous_entry_sha256"))
MAX_EVENTS=512
LIMIT=2048
ACTIONS=("RESERVE","CONSUME","ABORT")


class Refusal(Exception):
    pass


def need(ok,reason):
    if not ok:
        raise Refusal(reason)


def identities(operation_id,payload_sha):
    need(checkpoint.digest_valid(operation_id) and
         checkpoint.digest_valid(payload_sha),
         "OPERATION_ID_OR_PAYLOAD_SHA_INVALID")


def event_chain(fd):
    # Same trusted directory, lock and immutable-file checks as _117.
    names=os.listdir(fd)
    need(monotonic.LOCK in names,"OPERATION_LOCK_MISSING")
    names.remove(monotonic.LOCK)
    need(len(names)<=MAX_EVENTS,"OPERATION_EVENT_LIMIT_EXCEEDED")
    need(all(ENTRY.fullmatch(n) is not None for n in names),
         "OPERATION_UNKNOWN_OR_PARTIAL_ENTRY")
    previous="0"*64
    events=[]
    by_id={}
    for idx,name in enumerate(sorted(names),1):
        raw=ledger.private_file(fd,name,LIMIT)
        try:
            event=ledger.strict_json(raw)
        except ledger.Refusal as exc:
            raise Refusal("OPERATION_"+str(exc)) from None
        basename=ENTRY.fullmatch(name)
        need(isinstance(event,dict) and set(event)==FIELDS and
             event["schema"]==SCHEMA and event["repository"]==ledger.REPO and
             type(event["event_number"]) is int and
             event["event_number"]==idx and
             int(basename.group(1))==idx and
             type(event["checkpoint_sequence"]) is int and
             1<=event["checkpoint_sequence"]<=ledger.MAX_ENTRIES and
             event["action"] in ACTIONS and
             isinstance(event["operation_id"],str) and
             event["operation_id"]==basename.group(2),
             "OPERATION_RECORD_SCHEMA_OR_SEQUENCE")
        for field in ("operation_id","payload_sha256","checkpoint_sha256"):
            need(checkpoint.digest_valid(event[field]),
                 "OPERATION_RECORD_BAD_IDENTITY:"+field)
        need(isinstance(event["previous_entry_sha256"],str) and
             checkpoint.SHA.fullmatch(event["previous_entry_sha256"]) is not None and
             hmac.compare_digest(event["previous_entry_sha256"],previous),
             "OPERATION_EVENT_CHAIN_BROKEN")
        op=event["operation_id"]
        prior=by_id.get(op)
        if prior is None:
            need(event["action"]=="RESERVE","OPERATION_EVENT_WITHOUT_RESERVATION")
        else:
            need(prior["action"]=="RESERVE" and
                 event["action"] in ("CONSUME","ABORT") and
                 all(event[field]==prior[field] for field in
                     ("payload_sha256","checkpoint_sha256",
                      "checkpoint_sequence")),
                 "OPERATION_REPLAY_OR_ILLEGAL_TRANSITION")
        by_id[op]=event
        previous=hashlib.sha256(raw).hexdigest()
        events.append(event)
    return events,by_id,previous


def append(fd,events,op,payload,sha,sequence,action,previous):
    need(len(events)<MAX_EVENTS,"OPERATION_CAPACITY_EXHAUSTED")
    index=len(events)+1
    record={"schema":SCHEMA,"repository":ledger.REPO,
            "event_number":index,"operation_id":op,
            "payload_sha256":payload,"checkpoint_sha256":sha,
            "checkpoint_sequence":sequence,"action":action,
            "previous_entry_sha256":previous}
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    need(len(raw)<=LIMIT,"OPERATION_EVENT_OVERSIZE")
    name="operation-"+f"{index:012d}"+"-"+op+".json"
    opened=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                   0o600,dir_fd=fd)
    try:
        position=0
        while position<len(raw):
            written=os.write(opened,raw[position:])
            need(written>0,"OPERATION_POISONED_SHORT_WRITE")
            position+=written
        os.fsync(opened)
    finally:
        os.close(opened)
    os.fsync(fd)
    return record


def latest_match(remote,local,key_sha,key_path,snapshot,sig):
    # No caller-chosen "expected latest". The simulated _117 store
    # determines the SHA and _116 verifies real signed checkpoint bytes.
    try:
        return monotonic.compare(remote,local,key_sha,key_path,snapshot,sig)
    except (monotonic.Refusal,ledger.Refusal,checkpoint.Refusal) as exc:
        raise Refusal("OPERATION_WITNESS_UNAVAILABLE_OR_SPLIT:"+str(exc)) from None


def result(event,repeat=False):
    return {"status":"CI_OPERATION_"+event["action"]+"_NOT_PKG_AUTHORIZATION",
            "operation_id":event["operation_id"],
            "payload_sha256":event["payload_sha256"],
            "checkpoint_sha256":event["checkpoint_sha256"],
            "checkpoint_sequence":event["checkpoint_sequence"],
            "idempotent_replay":repeat,
            "owner_approved_transaction":False,
            "external_witness_deployed":False,
            "witness_and_local_spend_atomic":False,
            "production_pkg_authorized":False,
            "pkg_invoked":False}


def initialize(store):
    ledger.qualify_runtime()
    with monotonic.directory(store) as fd:
        need(not os.listdir(fd),"OPERATION_STORE_ALREADY_INITIALIZED")
        lock=os.open(monotonic.LOCK,
                     os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                     0o600,dir_fd=fd)
        try:
            os.fsync(lock)
        finally:
            os.close(lock)
        os.fsync(fd)
    return {"status":"CI_OPERATION_STORE_UNTRUSTED_BOOTSTRAP",
            "owner_approved_transaction":False,"pkg_invoked":False}


def transition(action,store,remote,local,key_sha,key_path,
               snapshot,sig,operation_id,payload_sha):
    ledger.qualify_runtime()
    identities(operation_id,payload_sha)
    need(action in ACTIONS,"OPERATION_UNKNOWN_ACTION")
    with monotonic.directory(store) as fd,monotonic.exclusive(fd):
        events,by_id,previous=event_chain(fd)
        old=by_id.get(operation_id)
        if old is not None:
            need(old["payload_sha256"]==payload_sha,
                 "OPERATION_ID_REUSED_FOR_DIFFERENT_PAYLOAD")
        if action=="RESERVE":
            if old is not None:
                return result(old,True)  # Never writes another reservation.
            need(not any(ev["action"]=="RESERVE" for ev in by_id.values()),
                 "OPERATION_PENDING_ALREADY_EXISTS")
        else:
            need(old is not None,"OPERATION_NOT_RESERVED")
            if old["action"]==action:
                return result(old,True)  # Lost reply: immutable status lookup.
            need(old["action"]=="RESERVE",
                 "OPERATION_TERMINAL_STATUS_CONFLICT")
        # Verify actual latest while own lock held. This does NOT make
        # local ledger/witness/operation store a cross-store transaction.
        proof=latest_match(remote,local,key_sha,key_path,snapshot,sig)
        sha=proof["checkpoint_sha256"]
        sequence=proof["sequence"]
        if old is not None:
            need(old["checkpoint_sequence"]==sequence and
                 hmac.compare_digest(old["checkpoint_sha256"],sha),
                 "OPERATION_WITNESS_CHANGED_DURING_PENDING")
        else:
            need(not any(ev["action"]=="CONSUME" and
                         ev["checkpoint_sha256"]==sha
                         for ev in by_id.values()),
                 "OPERATION_CHECKPOINT_ALREADY_CONSUMED")
        event=append(fd,events,operation_id,payload_sha,sha,sequence,
                     action,previous)
    return result(event)


def status(store,op):
    ledger.qualify_runtime()
    need(checkpoint.digest_valid(op),"OPERATION_ID_INVALID")
    with monotonic.directory(store) as fd,monotonic.exclusive(fd):
        _,by_id,_=event_chain(fd)
        need(op in by_id,"OPERATION_NOT_FOUND")
        return result(by_id[op])


def main(args):
    try:
        ledger.qualify_runtime()
        need(args and args[0] in ("initialize","reserve","consume",
                                 "abort","status"),
             "OPERATION_COMMAND_REQUIRED")
        if args[0]=="initialize" and len(args)==2:
            value=initialize(args[1])
        elif args[0]=="status" and len(args)==3:
            value=status(args[1],args[2])
        elif args[0] in ("reserve","consume","abort") and len(args)==10:
            value=transition(args[0].upper(),*args[1:])
        else:
            raise Refusal("OPERATION_EXACT_ARGUMENTS_REQUIRED")
    except (Refusal,monotonic.Refusal,checkpoint.Refusal,ledger.Refusal,
            OSError,ValueError,UnicodeError,TypeError) as exc:
        print(PREFIX+"REFUSED:"+str(exc),file=sys.stderr)
        return 78
    print(PREFIX+json.dumps(value,sort_keys=True))
    return 0


if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
