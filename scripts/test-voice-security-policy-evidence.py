#!/usr/bin/env python3
"""Offline schema-3 Voice security evidence and full cutover fail-closed tests."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_cutover_journal as journal
import voice_cutover_full_recovery as full
import voice_firewall_ledger as firewall
import voice_process_recovery_evidence as processes
import voice_security_policy_evidence as security
from voice_freebsd_process_security import FIELDS
from voice_cutover_guard import check_pending

SCRIPTS={"engine":"/usr/local/etc/zapret2/binaries/my/dvtws2",
         "daemon":"/usr/sbin/daemon",
         "monitor":"/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"}
IMAGES={**SCRIPTS,"monitor":"/bin/sh"}
CREDS={"engine":dict.fromkeys(FIELDS,65534),
       "daemon":dict.fromkeys(FIELDS,0),
       "monitor":dict.fromkeys(FIELDS,0)}
IPFW={"rule_base":19000,"rule_max":19010,"rules":{},"tables":{}}
PROOF={k:"f"*64 for k in journal.PROOF_NAMES}


class Probe:
    def __init__(self, value):
        self.value=value
    def probe(self):
        return copy.deepcopy(self.value)


class Observe:
    def __init__(self, previous):
        self.previous=previous
    def observe(self):
        return dict(self.previous)


class SecurityReader:
    def __init__(self, previous):
        self.expected_scripts=dict(SCRIPTS)
        self.kernel_images=dict(IMAGES)
        self.credentials=copy.deepcopy(CREDS)
        self.calls=0
        self.previous=previous
        self.bad=None

    def inspect_twice(self):
        self.calls+=1
        result={"state":"review-required","can_activate":False,
                "can_recover_automatically":False,"safe_to_mutate":False,
                "roles":{}}
        for role,pid in (("engine",101),("daemon",102),("monitor",103)):
            result["roles"][role]={
                "pid":pid,"start_ns":pid*1000000000,
                "image":self.kernel_images[role],
                "credentials":copy.deepcopy(self.credentials[role]),
            }
        if self.bad=="pid":
            result["roles"]["engine"]["pid"]+=1
        elif self.bad=="creds":
            result["roles"]["monitor"]["credentials"]["euid"]=65534
        elif self.bad=="image":
            result["roles"]["engine"]["image"]="/bin/echo"
        elif self.bad=="status":
            result["state"]="ready"
        elif self.bad=="race" and self.calls >= 2:
            result["roles"]["engine"]["start_ns"]+=1
        return result


class SecurityPolicyTests(unittest.TestCase):
    def setup(self, root):
        base=Path(root)
        xml=base/"config.xml"
        xml.write_text("<opnsense/>")
        xml.chmod(0o600)
        runtime=base/"runtime"
        runtime.mkdir()
        (runtime/"dvtws.args").write_text("--port=989\n")
        private=base/"private"
        private.mkdir(mode=0o700)
        for name in ("whole","ipfw"):
            (private/name).mkdir(mode=0o700)
        previous_backup=private/"previous"
        manifest=backup.capture_previous(xml,runtime,previous_backup)
        def instance(role,pid):
            return {"pid":pid,"start_ns":pid*1000000000,
                    "executable":SCRIPTS[role]}
        old={"engine":{"state":"running","process":instance("engine",101),
                       "runtime_args_sha256":manifest["runtime"]["dvtws.args"]["sha256"]},
             "supervisor":{"state":"running",
                           "daemon":instance("daemon",102),
                           "monitor":instance("monitor",103)}}
        process_dir=private/"process"
        fingerprints=processes.capture_process_evidence(
            Probe(old),previous_backup,process_dir,SCRIPTS)
        ipfw=firewall.VoiceOwnershipStore(private/"ipfw")
        ipfw.seed(IPFW)
        prior={**backup.bound_resource_fingerprints(previous_backup),
               **fingerprints,
               "firewall":firewall.fingerprint(firewall.canonical_manifest(IPFW))}
        policy_dir=private/"security"
        digest=security.capture_security_policy(
            previous_backup,process_dir,policy_dir,prior,
            SCRIPTS,IMAGES,CREDS)
        whole=journal.VoiceCutoverJournal(private/"whole")
        return (whole,ipfw,previous_backup,process_dir,policy_dir,prior,digest)

    def start(self, setup):
        whole,ipfw,saved,process_dir,policy_dir,prior,digest=setup
        whole.begin_security_bound(prior,PROOF,IPFW,policy_dir,saved,process_dir,SCRIPTS)
        return whole.read()

    def inspect(self, setup, reader=None, *, policy_dir=None):
        whole,ipfw,saved,process_dir,default,prior,digest=setup
        return full.inspect_full_recovery(
            whole,ipfw,saved,process_dir,SCRIPTS,Observe(prior),
            security_evidence=default if policy_dir is None else policy_dir,
            security_reader=reader,
        )

    def assert_denied(self, value):
        for key in ("can_activate","can_recover_automatically","safe_to_mutate",
                    "safe_to_finish_intent"):
            self.assertIs(value[key],False)

    def test_private_policy_reopens_and_schema_three_journal_binds_it(self):
        with tempfile.TemporaryDirectory() as root:
            setup=self.setup(root)
            whole,ipfw,saved,process_dir,policy_dir,prior,digest=setup
            self.assertEqual(0o700,policy_dir.stat().st_mode & 0o777)
            self.assertEqual(0o600,(policy_dir/"policy.json").stat().st_mode & 0o777)
            self.assertEqual(digest,security.inspect_security_policy(
                policy_dir,saved,process_dir,expected_scripts=SCRIPTS)["policy_sha256"])
            record=self.start(setup)
            self.assertEqual(journal.SECURITY_BOUND_SCHEMA,record["schema"])
            self.assertEqual(digest,record["candidate"][journal.SECURITY_FIELD])
            self.assertEqual(digest,security.inspect_security_policy(
                policy_dir,saved,process_dir,journal_record=record)["policy_sha256"])
            self.assertEqual("blocked",check_pending(whole.directory,ipfw.directory)["state"])
            reader=SecurityReader(prior)
            report=self.inspect(setup,reader)
            self.assertEqual("review-required",report["state"])
            self.assertEqual("all-previous-fingerprints-observed",report["reason"])
            self.assertEqual(2,reader.calls)
            self.assert_denied(report)
            self.assertEqual("blocked",self.inspect(setup)["state"])
            self.assertEqual("missing-native-security-attestation",
                             self.inspect(setup)["reason"])

    def test_existing_schema_one_and_two_remain_readable(self):
        with tempfile.TemporaryDirectory() as root:
            setup=self.setup(root)
            whole,ipfw,saved,process_dir,policy_dir,prior,digest=setup
            record=journal.new_record(prior,PROOF)
            self.assertEqual(journal.SCHEMA,record["schema"])
            bounded=journal.new_bound_record(prior,PROOF,IPFW)
            self.assertEqual(journal.BOUND_SCHEMA,bounded["schema"])
            with self.assertRaises(journal.CutoverJournalError):
                journal.new_security_bound_record(prior,PROOF,IPFW,"invalid")

    def test_foreign_policy_or_live_security_refused(self):
        for variant in ("foreign-reader","live-credentials","live-image",
                        "live-pid","live-status","race"):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as root:
                setup=self.setup(root)
                self.start(setup)
                reader=SecurityReader(setup[5])
                if variant=="foreign-reader":
                    reader.kernel_images["engine"]="/bin/echo"
                else:
                    reader.bad={"live-credentials":"creds",
                                "live-image":"image","live-pid":"pid",
                                "live-status":"status","race":"race"}[variant]
                report=self.inspect(setup,reader)
                self.assertEqual("blocked",report["state"])
                self.assert_denied(report)

    def test_modified_sealed_policy_and_cross_cutover_swap_refused(self):
        for variant in ("file-corrupt","mode","symlink","extra",
                        "journal-mismatch","wrong-previous"):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as root:
                setup=self.setup(root)
                whole,ipfw,saved,process_dir,policy_dir,prior,digest=setup
                record=self.start(setup)
                policy=policy_dir/"policy.json"
                if variant=="file-corrupt":
                    policy.write_text('{"schema":1,"check":"bad"}')
                elif variant=="mode":
                    policy.chmod(0o644)
                elif variant=="symlink":
                    policy.unlink()
                    policy.symlink_to(saved/"manifest.json")
                elif variant=="extra":
                    (policy_dir/"intruder").write_text("no")
                elif variant=="journal-mismatch":
                    body={k:v for k,v in record.items() if k!="check"}
                    body["candidate"][journal.SECURITY_FIELD]="f"*64
                    body["check"]=journal._digest(body)
                    whole._target().write_text(__import__("json").dumps(body))
                else:
                    (saved/"config/config.xml").write_text("modified")
                report=self.inspect(setup,SecurityReader(prior))
                self.assertEqual("blocked",report["state"])
                self.assert_denied(report)

    def test_policy_capture_rejects_wrong_roles_uid_and_duplicate_destination(self):
        for variant in ("wrong-previous","missing-role","invalid-uid",
                        "foreign-image","duplicate","stale-backup"):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as root:
                setup=self.setup(root)
                whole,ipfw,saved,process_dir,policy_dir,prior,digest=setup
                new_dir=policy_dir.parent/"new-security"
                prev=copy.deepcopy(prior)
                images=dict(IMAGES)
                creds=copy.deepcopy(CREDS)
                if variant=="wrong-previous":
                    prev["engine"]="f"*64
                elif variant=="missing-role":
                    del images["monitor"]
                elif variant=="invalid-uid":
                    creds["engine"]["euid"]=True
                elif variant=="foreign-image":
                    images["engine"]="../bad"
                elif variant=="duplicate":
                    new_dir=policy_dir
                elif variant=="stale-backup":
                    (saved/"config/config.xml").write_text("modified")
                with self.assertRaises((security.SecurityPolicyError,ValueError,OSError)):
                    security.capture_security_policy(
                        saved,process_dir,new_dir,prev,SCRIPTS,images,creds)
                if variant!="duplicate":
                    self.assertFalse(new_dir.exists())

    def test_unbound_old_or_corrupt_journal_refuses_security_commit(self):
        with tempfile.TemporaryDirectory() as root:
            setup=self.setup(root)
            whole,ipfw,saved,process_dir,policy_dir,prior,digest=setup
            different={**prior,"firewall":"f"*64}
            with self.assertRaises((journal.CutoverJournalError,security.SecurityPolicyError)):
                whole.begin_security_bound(different,PROOF,IPFW,policy_dir,
                                           saved,process_dir,SCRIPTS)
            self.assertIsNone(whole.read())
            self.start(setup)
            with self.assertRaises(journal.CutoverJournalError):
                self.start(setup)


if __name__=="__main__":
    unittest.main(verbosity=2)
