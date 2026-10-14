#!/usr/bin/env python3
"""Common Apply durable phases and existing lifecycle guard, without kernel changes."""
import sys
from contextlib import ExitStack
import subprocess
from unittest.mock import patch
import tempfile
from pathlib import Path
import unittest

BACKEND=Path(__file__).resolve().parents[1]/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from shared_apply_operation import SharedApplyOperation,SharedOperationError,committed_owner
from voice_cutover_guard import check_pending

def detail(ident="1"*32):
    return {"id":ident,"page":"voice","base":"a"*64,
            "candidate":"b"*64,"changed_fields":[
                "voice.telegram.enabled","hostlist.telegramips"]}

class TestJournal(unittest.TestCase):
    def test_legacy_prepared_is_one_durable_blocking_common_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            record=store.prepare_legacy_predecessor(detail(), lambda: "f"*64)
            self.assertEqual("prepared",record["phase"])
            self.assertEqual("f"*64,record["legacy_predecessor"])
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            reloaded=SharedApplyOperation(store.root)
            self.assertEqual(record,reloaded.read())
            with self.assertRaisesRegex(SharedOperationError,"reviewed executor"):
                reloaded.advance("activating",detail())
            with self.assertRaisesRegex(SharedOperationError,"reviewed executor"):
                reloaded.advance("restored",detail())
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                reloaded.recover_prepared(detail()["id"], lambda: True)
            with self.assertRaises(SharedOperationError):
                reloaded.prepare_legacy_predecessor(detail("2"*32),lambda: "b"*64)
            self.assertEqual(record,reloaded.read())

    def test_legacy_arm_attestation_failure_never_writes_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            with self.assertRaisesRegex(SharedOperationError,"fingerprint"):
                store.prepare_legacy_predecessor(detail(),lambda: "unsafe")
            self.assertFalse(store.root.exists())
            with self.assertRaises(SharedOperationError):
                store.prepare_legacy_predecessor(detail(),lambda: "")
            self.assertFalse(store.root.exists())
            with self.assertRaises(SharedOperationError):
                store.prepare_legacy_predecessor(detail("2"*32),lambda: None)
            self.assertFalse(store.root.exists())
            with self.assertRaises(SharedOperationError):
                store.prepare_legacy_predecessor(
                    {**detail(),"page":"strategies"},lambda: "f"*64)
            self.assertFalse(store.root.exists())

    def test_legacy_arm_cli_refuses_missing_root_fd9(self):
        result=subprocess.run([sys.executable,
            str(BACKEND/"shared_apply_operation.py"),"arm-legacy",
            "1"*32,"a"*64,"b"*64,"-"],capture_output=True,text=True)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_operator_can_only_cancel_completely_unchanged_live_predecessor(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            armed=store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            for observed in ("a"*64, "", None, True):
                with self.subTest(observed=observed):
                    with self.assertRaises(SharedOperationError):
                        store.cancel_pristine_legacy(detail()["id"],lambda:observed)
                    self.assertEqual(armed,store.read())
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy("2"*32,lambda:"f"*64)
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            restored=store.cancel_pristine_legacy(detail()["id"],lambda:"f"*64)
            self.assertEqual("restored",restored["phase"])
            self.assertNotIn("legacy_predecessor",restored)
            self.assertIsNone(committed_owner(restored))
            self.assertTrue(check_pending(
                root/"voice-cutover",root/"voice-ipfw")["safe_to_mutate"])
            self.assertEqual(restored,SharedApplyOperation(store.root).read())
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())

    def test_cancellation_rejects_changed_journal_after_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            armed=store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            def bad_witness():
                # Simulate a foreign/nonterminal journal swap during observer.
                target=store.root/"operation.json"
                # Replace a single valid field in-place, preserving schema
                # and the persistent armed phase so the observer can detect
                # a different but still parseable journal record.
                content=target.read_text().replace('"id":"'+"1"*32+'"','"id":"'+"2"*32+'"')
                target.write_text(content)
                return "f"*64
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],bad_witness)
            self.assertEqual("2"*32,store.read()["detail"]["id"])
            self.assertEqual("prepared",store.read()["phase"])
            # Never accepted a changed durable identity as cancel authority.

    def test_legacy_cancel_cli_is_not_generic_freebsd_bypass(self):
        result=subprocess.run([sys.executable,
            str(BACKEND/"voice_native_legacy_predecessor_route.py"),"cancel-common",
            "1"*32],capture_output=True,text=True)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_durable_legacy_quiescing_boundary_preserves_old_proof_and_can_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            initial=store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_quiesce(detail()["id"],lambda:"a"*64)
            self.assertEqual(initial,store.read())
            record=store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            self.assertEqual("legacy-quiescing",record["phase"])
            self.assertEqual(initial["legacy_predecessor"],record["legacy_predecessor"])
            self.assertEqual(record,SharedApplyOperation(store.root).read())
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())
            with self.assertRaises(SharedOperationError):
                store.recover_prepared(detail()["id"],lambda:True)
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],lambda:"a"*64)
            self.assertEqual(record,store.read())
            done=store.cancel_pristine_legacy(detail()["id"],lambda:"f"*64)
            self.assertEqual("restored",done["phase"])
            self.assertNotIn("legacy_predecessor",done)
            self.assertTrue(store.advisory()["safe_to_mutate"])

    def test_old_legacy_quiescing_cannot_close_after_identity_swap(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            saved=store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            reloaded=SharedApplyOperation(store.root)
            with self.assertRaises(SharedOperationError):
                reloaded.cancel_pristine_legacy("2"*32,lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                reloaded.cancel_pristine_legacy(detail()["id"],lambda:None)
            self.assertEqual(saved,reloaded.read())

    def test_private_old_process_stop_reuses_fixed_actuator_and_one_journal(self):
        import os
        from types import SimpleNamespace
        from voice_native_legacy_predecessor_route import stop_armed_common_predecessor
        from voice_native_process_probe import FreeBSDVoiceProcessProbe
        from voice_native_kernel_argv import FreeBSDKernelArgvReader
        from voice_ipfw_adapter import FreeBSDIPFWAdapter
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            marker=root/"old-marker"
            marker.write_bytes(b"enabled\n")
            os.chmod(marker,0o600)
            store=SharedApplyOperation(root/"shared-apply")
            store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            probe=object.__new__(FreeBSDVoiceProcessProbe)
            kernel=object.__new__(FreeBSDKernelArgvReader)
            ipfw=object.__new__(FreeBSDIPFWAdapter)
            ipfw.allow_mutations=False
            ipfw.rule_base=19000
            ipfw.rule_max=19010
            stopped=[False]
            invoked=[]
            ipfw_snapshot={"rules":{"19000":["divert"]},
                           "targets":["91.108.0.0/16"],"wan":"igb0","port":"9876"}
            old={"legacy_ipfw_previous":ipfw_snapshot,
                 "legacy_ipfw_structure_sha256":"1"*64,
                 "marker":{"mode":0o600}}
            def runner(argv,**kwargs):
                self.assertEqual(["/bin/sh",str(__import__(
                    "voice_native_process_actions").SCRIPT),"stop"],argv)
                self.assertEqual((9,),kwargs["pass_fds"])
                invoked.append("stop")
                stopped[0]=True
                return SimpleNamespace(returncode=0,stdout="",stderr="")
            def inventory(_):
                return {"engine":{"state":"stopped" if stopped[0] else "running"},
                        "supervisor":{"state":"stopped" if stopped[0] else "running"}}
            with patch("voice_native_legacy_predecessor_route._locked_config"), \
                 patch("voice_native_legacy_predecessor_route.cancel_unchanged_common_predecessor",
                       return_value="f"*64), \
                 patch("voice_native_process_actions._secure_script"), \
                 patch("voice_native_legacy_predecessor_route.inspect_legacy_previous_live_identity",
                       return_value=old), \
                 patch("shared_apply_operation.fingerprint_legacy_predecessor",
                       return_value="f"*64), \
                 patch("voice_native_legacy_predecessor_route.inspect_previous",
                       return_value={}), \
                 patch("voice_native_legacy_predecessor_route._verify_sources"), \
                 patch("voice_native_legacy_predecessor_route._legacy_read",
                       return_value=b"enabled\n"), \
                 patch("voice_native_legacy_predecessor_route._read_private_file",
                       return_value=b"enabled\n"), \
                 patch("voice_native_live_preflight._current_engine_args",
                       return_value=(["dvtws2"],"e"*64)), \
                 patch("voice_native_live_ipfw.observe_legacy_poc_ipfw",
                       return_value={"structure_sha256":"1"*64,
                                     "previous_ipfw":ipfw_snapshot}), \
                 patch.object(FreeBSDVoiceProcessProbe,"observe_processes",
                              new=lambda _:inventory(None)):
                record=stop_armed_common_predecessor(
                    identity=detail()["id"],store=store,
                    work=root/detail()["id"],config_path=root/"config.xml",
                    config_fd=4,config_owner=(0,0),active_runtime=root/"active",
                    marker_path=marker,ledger_root=root/"ledger",
                    process_probe=probe,kernel_reader=kernel,
                    readonly_ipfw=ipfw,
                    require_lifecycle_owner=lambda:None,runner=runner)
            self.assertEqual(["stop"],invoked)
            self.assertEqual("legacy-processes-stopped",record["phase"])
            self.assertEqual(record,store.read())
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],lambda:"f"*64)

    def test_stopped_legacy_ipfw_retirement_is_one_durable_shared_wal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            digest="f"*64
            store.prepare_legacy_predecessor(detail(),lambda:digest)
            store.begin_legacy_quiesce(detail()["id"],lambda:digest)
            store.mark_legacy_processes_stopped(detail()["id"],lambda:digest)
            stopped=store.read()
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_ipfw_retire(detail()["id"],lambda:digest)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_ipfw_retire(detail()["id"],lambda:"a"*64)
            self.assertEqual(stopped,store.read())
            pending=store.begin_legacy_ipfw_retire(detail()["id"],lambda:digest)
            self.assertEqual("legacy-ipfw-retiring",pending["phase"])
            self.assertEqual(digest,pending["legacy_predecessor"])
            self.assertEqual(pending,SharedApplyOperation(store.root).read())
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_ipfw_retire(detail()["id"],lambda:digest)
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_ipfw_retire(detail()["id"],lambda:"a"*64)
            self.assertEqual(pending,store.read())
            done=store.finish_legacy_ipfw_retire(detail()["id"],lambda:digest)
            self.assertEqual("legacy-ipfw-retired",done["phase"])
            self.assertEqual(digest,done["legacy_predecessor"])
            self.assertEqual(done,SharedApplyOperation(store.root).read())
            self.assertFalse(store.advisory()["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],lambda:digest)
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())

    def test_private_legacy_ipfw_retirement_deletes_only_sealed_old_objects(self):
        import os
        from voice_native_legacy_predecessor_route import retire_stopped_common_legacy_ipfw
        from voice_native_process_probe import FreeBSDVoiceProcessProbe
        from voice_ipfw_adapter import FreeBSDIPFWAdapter
        marker_bytes=b"enabled\n"
        for fail_after in (None, 1, "foreign"):
            with self.subTest(fail_after=fail_after), tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                work=root/detail()["id"]
                work.mkdir()
                marker=root/"marker"
                marker.write_bytes(marker_bytes)
                os.chmod(marker,0o600)
                store=SharedApplyOperation(root/"shared-apply")
                store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
                store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
                store.mark_legacy_processes_stopped(detail()["id"],lambda:"f"*64)
                probe=object.__new__(FreeBSDVoiceProcessProbe)
                reader=object.__new__(FreeBSDIPFWAdapter)
                reader.allow_mutations=False
                reader.rule_base=19000; reader.rule_max=19010
                writer=object.__new__(FreeBSDIPFWAdapter)
                writer.allow_mutations=True
                writer.rule_base=19000; writer.rule_max=19010
                prior={"rules":{"19000":["divert","9000","udp"],
                                "19001":["divert","9000","tcp"]},
                       "targets":["91.108.0.0/16"]}
                kernel={"rules":dict(prior["rules"]),"targets":list(prior["targets"])}
                issued=[]
                baseline={"legacy_ipfw_previous":prior,"marker":{"mode":0o600}}
                summary={"previous_five":"d"*64}
                plan={"previous_five":"d"*64}
                def snapshot(_):
                    return {"rules":dict(kernel["rules"]),
                            "targets":None if kernel["targets"] is None else list(kernel["targets"])}
                def delete(_, number):
                    issued.append("delete:"+str(number))
                    if fail_after == 1 and len(issued) == 1:
                        raise OSError("simulated ipfw failure after durable intent")
                    kernel["rules"].pop(str(number))
                    if fail_after == "foreign" and len(issued) == 1:
                        kernel["rules"]["19009"]=["foreign"]
                def command(_, *args, **kwargs):
                    self.assertEqual(("table","zapret2_tgvoice","destroy"),args)
                    self.assertTrue(kwargs["modifying"])
                    issued.append("destroy")
                    kernel["targets"]=None
                with patch("voice_native_legacy_predecessor_route._locked_config"), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous_live_identity",
                           return_value=baseline), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_restore_plan",
                           return_value=plan), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous",
                           return_value=summary), \
                     patch("voice_native_legacy_predecessor_route.inspect_previous",
                           return_value={}), \
                     patch("voice_native_legacy_predecessor_route._verify_sources"), \
                     patch("voice_native_legacy_predecessor_route._read_private_file",
                           return_value=marker_bytes), \
                     patch("voice_native_legacy_predecessor_route._legacy_read",
                           return_value=marker_bytes), \
                     patch("shared_apply_operation.fingerprint_legacy_predecessor",
                           return_value="f"*64), \
                     patch("voice_native_legacy_reverse_wal._stopped",
                           return_value="exact-three-role-absence"), \
                     patch("voice_native_legacy_ipfw_replay._strict_snapshot",
                           side_effect=snapshot), \
                     patch.object(FreeBSDIPFWAdapter,"delete_rule",new=delete), \
                     patch.object(FreeBSDIPFWAdapter,"_run",new=command):
                    if fail_after is None:
                        result=retire_stopped_common_legacy_ipfw(
                            identity=detail()["id"],store=store,work=work,
                            config_path=root/"config.xml",config_fd=4,
                            config_owner=(0,0),active_runtime=root/"active",
                            marker_path=marker,process_probe=probe,
                            readonly_ipfw=reader,mutating_ipfw=writer,
                            require_lifecycle_owner=lambda:None)
                        self.assertEqual("legacy-ipfw-retired",result["phase"])
                        self.assertEqual(["delete:19001","delete:19000","destroy"],issued)
                        self.assertEqual({"rules":{},"targets":None},snapshot(reader))
                    else:
                        with self.assertRaises((OSError,RuntimeError)):
                            retire_stopped_common_legacy_ipfw(
                                identity=detail()["id"],store=store,work=work,
                                config_path=root/"config.xml",config_fd=4,
                                config_owner=(0,0),active_runtime=root/"active",
                                marker_path=marker,process_probe=probe,
                                readonly_ipfw=reader,mutating_ipfw=writer,
                                require_lifecycle_owner=lambda:None)
                        self.assertEqual("legacy-ipfw-retiring",store.read()["phase"])
                        self.assertNotIn("destroy",issued)
                        with self.assertRaises(RuntimeError):
                            retire_stopped_common_legacy_ipfw(
                                identity=detail()["id"],store=store,work=work,
                                config_path=root/"config.xml",config_fd=4,
                                config_owner=(0,0),active_runtime=root/"active",
                                marker_path=marker,process_probe=probe,
                                readonly_ipfw=reader,mutating_ipfw=writer,
                                require_lifecycle_owner=lambda:None)
                self.assertEqual(marker_bytes,marker.read_bytes())
                self.assertEqual("shared-apply-pending",check_pending(
                    root/"voice-cutover",root/"voice-ipfw")["reason"])

    def test_legacy_marker_retirement_requires_empty_ipfw_and_same_shared_journal(self):
        with tempfile.TemporaryDirectory() as root:
            store=SharedApplyOperation(Path(root)/"shared-apply")
            old="f"*64
            store.prepare_legacy_predecessor(detail(),lambda:old)
            store.begin_legacy_quiesce(detail()["id"],lambda:old)
            store.mark_legacy_processes_stopped(detail()["id"],lambda:old)
            store.begin_legacy_ipfw_retire(detail()["id"],lambda:old)
            store.finish_legacy_ipfw_retire(detail()["id"],lambda:old)
            before=store.read()
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_marker_retire(detail()["id"],lambda:old)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_marker_retire(detail()["id"],lambda:"e"*64)
            self.assertEqual(before,store.read())
            pending=store.begin_legacy_marker_retire(detail()["id"],lambda:old)
            self.assertEqual("legacy-marker-retiring",pending["phase"])
            self.assertEqual(old,pending["legacy_predecessor"])
            self.assertEqual(pending,SharedApplyOperation(store.root).read())
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_marker_retire(detail()["id"],lambda:old)
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_marker_retire(detail()["id"],lambda:"e"*64)
            self.assertEqual(pending,store.read())
            final=store.finish_legacy_marker_retire(detail()["id"],lambda:old)
            self.assertEqual("legacy-marker-retired",final["phase"])
            self.assertEqual(final,SharedApplyOperation(store.root).read())
            guard=check_pending(Path(root)/"voice-cutover",Path(root)/"voice-ipfw")
            self.assertEqual("shared-apply-pending",guard["reason"])
            self.assertEqual("legacy-marker-retired",guard["phase"])
            with self.assertRaises(SharedOperationError):
                store.cancel_pristine_legacy(detail()["id"],lambda:old)
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())

    def test_private_old_marker_retirement_pins_exact_bytes_and_refuses_replay(self):
        import os
        from voice_native_legacy_predecessor_route import (
            retire_stopped_common_legacy_marker,
        )
        from voice_native_process_probe import FreeBSDVoiceProcessProbe
        from voice_ipfw_adapter import FreeBSDIPFWAdapter
        raw=b"enabled\n"
        for fault in (None,"ipfw","unlink","finish"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                folder=Path(temp)
                work=folder/detail()["id"]
                work.mkdir()
                marker=folder/"legacy-marker"
                marker.write_bytes(raw)
                os.chmod(marker,0o600)
                store=SharedApplyOperation(folder/"shared-apply")
                store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
                store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
                store.mark_legacy_processes_stopped(detail()["id"],lambda:"f"*64)
                store.begin_legacy_ipfw_retire(detail()["id"],lambda:"f"*64)
                store.finish_legacy_ipfw_retire(detail()["id"],lambda:"f"*64)
                reader=object.__new__(FreeBSDIPFWAdapter)
                reader.rule_base=19000
                reader.rule_max=19010
                reader.allow_mutations=False
                probe=object.__new__(FreeBSDVoiceProcessProbe)
                info={"previous_five":"c"*64}
                manifest={"legacy_ipfw_previous":{}, "marker":{
                    "mode":0o600,"bytes":len(raw),
                    "sha256":__import__("hashlib").sha256(raw).hexdigest(),
                }}
                plan={"previous_five":"c"*64,"marker_target":str(marker)}
                def kernel(_):
                    return ({"rules":{"19000":["foreign"]},"targets":None}
                            if fault=="ipfw" else {"rules":{},"targets":None})
                def invoke():
                    return retire_stopped_common_legacy_marker(
                        identity=detail()["id"],store=store,work=work,
                        config_path=folder/"config.xml",config_fd=4,
                        config_owner=(os.geteuid(),0),
                        active_runtime=folder/"runtime",marker_path=marker,
                        process_probe=probe,readonly_ipfw=reader,
                        require_lifecycle_owner=lambda:None,
                    )
                with patch("voice_native_legacy_predecessor_route._locked_config"), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous_live_identity",
                           return_value=manifest), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_restore_plan",
                           return_value=plan), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous",
                           return_value=info), \
                     patch("voice_native_legacy_predecessor_route.inspect_previous",
                           return_value={}), \
                     patch("voice_native_legacy_predecessor_route._verify_sources"), \
                     patch("voice_native_legacy_predecessor_route._read_private_file",
                           return_value=raw), \
                     patch("shared_apply_operation.fingerprint_legacy_predecessor",
                           return_value="f"*64), \
                     patch("voice_native_legacy_reverse_wal._stopped",
                           return_value="exact-three-role-absence"), \
                     patch("voice_native_legacy_ipfw_replay._strict_snapshot",
                           side_effect=kernel):
                    if fault in ("unlink","finish"):
                        target=("voice_native_legacy_predecessor_route.os.unlink"
                                if fault=="unlink" else
                                "shared_apply_operation.SharedApplyOperation.finish_legacy_marker_retire")
                        with patch(target,side_effect=OSError("injected crash")):
                            with self.assertRaises(OSError):
                                invoke()
                        self.assertEqual("legacy-marker-retiring",store.read()["phase"])
                        self.assertEqual(marker.exists(),fault=="unlink")
                    elif fault=="ipfw":
                        with self.assertRaises(RuntimeError):
                            invoke()
                        self.assertEqual("legacy-ipfw-retired",store.read()["phase"])
                        self.assertEqual(raw,marker.read_bytes())
                    else:
                        done=invoke()
                        self.assertEqual("legacy-marker-retired",done["phase"])
                        self.assertFalse(marker.exists())
                    with self.assertRaises(RuntimeError):
                        invoke()

    def test_native_common_forward_inherits_original_fd9_and_config_fd(self):
        import os
        from types import SimpleNamespace
        from voice_native_legacy_predecessor_route import (
            _invoke_existing_native_common, LegacyPredecessorRouteError,
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            service = root / "zapret_service.sh"
            service.write_text("#!/bin/sh\n", encoding="ascii")
            service.chmod(0o600)
            work = root / detail()["id"]
            work.mkdir()
            called = []
            seen = []
            def runner(argv, **kw):
                self.assertEqual(["/bin/sh", "-c"], argv[:2])
                self.assertEqual("native-common-forward", argv[3])
                self.assertEqual(str(work / "release"), argv[5])
                self.assertEqual(detail()["id"], argv[6])
                self.assertEqual((9, 11), kw["pass_fds"])
                self.assertEqual(90, kw["timeout"])
                self.assertNotIn("ZAPRET_NATIVE_PRIVATE_IMPORT", kw["env"])
                self.assertNotIn(str(work), argv[2])
                called.append(argv[4])
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("voice_native_legacy_predecessor_route.NATIVE_COMMON_SERVICE",
                       service):
                for mode in ("probe", "activate"):
                    self.assertTrue(_invoke_existing_native_common(
                        mode=mode, identity=detail()["id"], work=work,
                        config_fd=11, require_lifecycle_owner=lambda: seen.append("FD9"),
                        runner=runner,
                    ))
                self.assertEqual(["probe", "activate"], called)
                self.assertEqual(["FD9", "FD9"], seen)
                for bad in ("-bad", "", "1" * 31):
                    with self.assertRaises(LegacyPredecessorRouteError):
                        _invoke_existing_native_common(
                            mode="activate", identity=bad, work=work,
                            config_fd=11, require_lifecycle_owner=lambda: None,
                            runner=runner,
                        )
                with self.assertRaises(LegacyPredecessorRouteError):
                    _invoke_existing_native_common(
                        mode="activate", identity=detail()["id"], work=work,
                        config_fd=9, require_lifecycle_owner=lambda: None,
                        runner=runner,
                    )
                service.chmod(0o666)
                with self.assertRaises(LegacyPredecessorRouteError):
                    _invoke_existing_native_common(
                        mode="probe", identity=detail()["id"], work=work,
                        config_fd=11, require_lifecycle_owner=lambda: None,
                        runner=runner,
                    )
                service.chmod(0o600)
                with patch("voice_native_legacy_predecessor_route.subprocess.run",
                           return_value=SimpleNamespace(returncode=70,
                                                        stdout="", stderr="error")):
                    with self.assertRaises(LegacyPredecessorRouteError):
                        _invoke_existing_native_common(
                            mode="activate", identity=detail()["id"], work=work,
                            config_fd=11, require_lifecycle_owner=lambda: None,
                        )

    def test_old_marker_retired_can_enter_private_common_runtime_once(self):
        from voice_native_legacy_predecessor_route import (
            activate_common_after_legacy_retirement,
            rollback_pristine_common_after_interruption, LegacyPredecessorRouteError,
        )
        from voice_native_process_probe import FreeBSDVoiceProcessProbe
        from voice_ipfw_adapter import FreeBSDIPFWAdapter

        for crash in ("none", "actuator", "new-owner-proof",
                      "native-not-running", "native-ipfw-drift", "native-fixed"):
            with self.subTest(crash=crash), tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                work=root/detail()["id"]
                work.mkdir()
                store=SharedApplyOperation(root/"shared-apply")
                owner="f"*64
                store.prepare_legacy_predecessor(detail(),lambda:owner)
                store.begin_legacy_quiesce(detail()["id"],lambda:owner)
                store.mark_legacy_processes_stopped(detail()["id"],lambda:owner)
                store.begin_legacy_ipfw_retire(detail()["id"],lambda:owner)
                store.finish_legacy_ipfw_retire(detail()["id"],lambda:owner)
                store.begin_legacy_marker_retire(detail()["id"],lambda:owner)
                store.finish_legacy_marker_retire(detail()["id"],lambda:owner)
                probe=object.__new__(FreeBSDVoiceProcessProbe)
                ipfw=object.__new__(FreeBSDIPFWAdapter)
                ipfw.rule_base,ipfw.rule_max=19000,19010
                ipfw.allow_mutations=False
                checks=[]
                starts=[]
                def preflight():
                    checks.append("preflight")
                    return True
                def activate():
                    starts.append("common-start")
                    if crash=="actuator":
                        raise OSError("power cut after intent before native start")
                    return True
                def live():
                    checks.append("live")
                    return "0"*64 if crash=="new-owner-proof" else detail()["candidate"]
                def invoke():
                    return activate_common_after_legacy_retirement(
                        identity=detail()["id"],store=store,work=work,
                        config_path=root/"config.xml",config_fd=4,
                        config_owner=(0,0),active_runtime=root/"active",
                        marker_path=root/"old-marker",process_probe=probe,
                        readonly_ipfw=ipfw,require_lifecycle_owner=lambda:None,
                        **({} if crash == "native-fixed" else {
                            "common_preflight": preflight,
                            "common_activate": activate,
                            "common_attest": live,
                        }))
                with ExitStack() as patches:
                    if crash == "native-fixed":
                        def real_common_forward(**args):
                            checks.append("native-" + args["mode"])
                            self.assertEqual(detail()["id"], args["identity"])
                            self.assertEqual(4, args["config_fd"])
                            if args["mode"] == "activate":
                                starts.append("common-start")
                            return True
                        patches.enter_context(patch(
                            "voice_native_legacy_predecessor_route._invoke_existing_native_common",
                            side_effect=real_common_forward))
                    patches.enter_context(patch(
                        "voice_native_legacy_predecessor_route._locked_config"))
                    patches.enter_context(patch(
                        "shared_apply_operation.fingerprint_legacy_predecessor",
                        return_value=owner))
                    patches.enter_context(patch(
                        "shared_apply_seal.verify_seal", return_value={"sealed":True}))
                    patches.enter_context(patch(
                        "voice_ipfw_adapter.shared_release_manifest",
                        return_value={"rule_base":19000,"rule_max":19010,
                                      "rules":{19000:["divert","foo"]},"tables":{}}))
                    patches.enter_context(patch(
                        "voice_live_inspect.inspect_common_runtime",
                        return_value={
                            "state":"stopped" if crash=="native-not-running" else "running",
                            "source_verified":True,"engine_verified":True,
                            "supervisor_verified":True,
                        }))
                    patches.enter_context(patch(
                        "voice_ipfw_adapter.shared_firewall_action",
                        side_effect=(LegacyPredecessorRouteError("foreign native IPFW")
                                     if crash=="native-ipfw-drift" else None)))
                    patches.enter_context(patch(
                        "voice_native_legacy_predecessor_route.inspect_previous",
                        return_value={}))
                    patches.enter_context(patch(
                        "voice_native_legacy_predecessor_route._verify_sources"))
                    patches.enter_context(patch(
                        "voice_native_legacy_predecessor_route.inspect_legacy_previous",
                        return_value={"previous_five":"old"}))
                    patches.enter_context(patch(
                        "voice_native_legacy_predecessor_route.inspect_legacy_restore_plan",
                        return_value={"previous_five":"old",
                                      "marker_target":str(root/"old-marker")}))
                    patches.enter_context(patch(
                        "voice_native_legacy_reverse_wal._stopped",
                        return_value="exact-three-role-absence"))
                    patches.enter_context(patch(
                        "voice_native_legacy_ipfw_replay._strict_snapshot",
                        return_value={"rules":{},"targets":None}))
                    if crash=="actuator":
                        with self.assertRaises(OSError):
                            invoke()
                    elif crash in ("new-owner-proof", "native-not-running",
                                   "native-ipfw-drift"):
                        with self.assertRaises(LegacyPredecessorRouteError):
                            invoke()
                    else:
                        self.assertEqual("legacy-common-activated",invoke()["phase"])
                    self.assertEqual(["common-start"],starts)
                    if crash == "native-fixed":
                        self.assertEqual(
                            ["native-probe", "native-probe", "native-activate",
                             "native-attest"], checks)
                    expected=("legacy-common-activated" if crash in ("none", "native-fixed")
                              else "legacy-common-activating")
                    self.assertEqual(expected,store.read()["phase"])
                    self.assertIsNone(committed_owner(store.read()))
                    self.assertFalse(store.advisory()["safe_to_mutate"])
                    self.assertEqual("shared-apply-pending",check_pending(
                        root/"voice-cutover",root/"voice-ipfw")["reason"])
                    # An interrupted transition may NEVER start a second
                    # candidate engine, including across a fresh process.
                    with self.assertRaises(LegacyPredecessorRouteError):
                        invoke()
                    self.assertEqual(["common-start"],starts)

                    if crash == "actuator":
                        def pristine_rollback(absence=lambda: True):
                            return rollback_pristine_common_after_interruption(
                                identity=detail()["id"], store=store, work=work,
                                config_path=root/"config.xml", config_fd=4,
                                config_owner=(0,0), active_runtime=root/"active",
                                marker_path=root/"old-marker", process_probe=probe,
                                readonly_ipfw=ipfw,
                                require_lifecycle_owner=lambda: None,
                                common_absence=absence,
                            )
                        with self.assertRaises(LegacyPredecessorRouteError):
                            pristine_rollback(lambda: False)
                        self.assertEqual("legacy-common-activating", store.read()["phase"])
                        stage = root / (".active.stage." + detail()["id"])
                        stage.write_text("incomplete native install")
                        with self.assertRaises(LegacyPredecessorRouteError):
                            pristine_rollback()
                        stage.unlink()
                        self.assertEqual("legacy-rollback-ipfw",
                                         pristine_rollback()["phase"])
                        with self.assertRaises(LegacyPredecessorRouteError):
                            pristine_rollback()
                        with self.assertRaises(SharedOperationError):
                            store.begin_legacy_common_activation(detail()["id"], lambda: owner)
                        self.assertEqual(["common-start"], starts)
                    with self.assertRaises(SharedOperationError):
                        store.advance("committed",detail())

    def test_private_common_activation_refuses_early_or_foreign_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            store.prepare_legacy_predecessor(detail(),lambda:"f"*64)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_common_activation(detail()["id"],lambda:"f"*64)
            store.begin_legacy_quiesce(detail()["id"],lambda:"f"*64)
            store.mark_legacy_processes_stopped(detail()["id"],lambda:"f"*64)
            store.begin_legacy_ipfw_retire(detail()["id"],lambda:"f"*64)
            store.finish_legacy_ipfw_retire(detail()["id"],lambda:"f"*64)
            store.begin_legacy_marker_retire(detail()["id"],lambda:"f"*64)
            store.finish_legacy_marker_retire(detail()["id"],lambda:"f"*64)
            old=store.read()
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_common_activation(detail()["id"],lambda:"0"*64)
            self.assertEqual(old,store.read())
            pending=store.begin_legacy_common_activation(detail()["id"],lambda:"f"*64)
            self.assertEqual("legacy-common-activating",pending["phase"])
            for method in (
                lambda:store.finish_legacy_common_activation("2"*32,lambda:"f"*64),
                lambda:store.finish_legacy_common_activation(detail()["id"],lambda:"0"*64),
                lambda:store.begin_legacy_ipfw_rollback(detail()["id"],lambda:"f"*64),
            ):
                with self.assertRaises(SharedOperationError):
                    method()
                self.assertEqual(pending,store.read())
            done=store.finish_legacy_common_activation(detail()["id"],lambda:"f"*64)
            self.assertEqual("legacy-common-activated",done["phase"])
            self.assertIsNone(committed_owner(done))
            self.assertFalse(store.advisory()["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_common_activation(detail()["id"],lambda:"f"*64)

    def test_legacy_rollback_ipfw_uses_same_journal_not_a_second_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            store=SharedApplyOperation(root/"shared-apply")
            seal="f"*64
            store.prepare_legacy_predecessor(detail(), lambda:seal)
            store.begin_legacy_quiesce(detail()["id"], lambda:seal)
            store.mark_legacy_processes_stopped(detail()["id"], lambda:seal)
            store.begin_legacy_ipfw_retire(detail()["id"], lambda:seal)
            store.finish_legacy_ipfw_retire(detail()["id"], lambda:seal)
            store.begin_legacy_marker_retire(detail()["id"], lambda:seal)
            store.finish_legacy_marker_retire(detail()["id"], lambda:seal)
            original=store.read()
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_ipfw_rollback(detail()["id"],lambda:seal)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_ipfw_rollback(detail()["id"],lambda:"b"*64)
            self.assertEqual(original,store.read())
            pending=store.begin_legacy_ipfw_rollback(detail()["id"],lambda:seal)
            self.assertEqual("legacy-rollback-ipfw",pending["phase"])
            self.assertEqual(seal,pending["legacy_predecessor"])
            self.assertEqual(pending,SharedApplyOperation(store.root).read())
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_ipfw_rollback(detail()["id"],lambda:seal)
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_ipfw_rollback(detail()["id"],lambda:"b"*64)
            done=store.finish_legacy_ipfw_rollback(detail()["id"],lambda:seal)
            self.assertEqual("legacy-rollback-ipfw-restored",done["phase"])
            self.assertEqual(done,SharedApplyOperation(store.root).read())
            self.assertFalse(store.advisory()["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())

    def test_private_legacy_ipfw_reverse_resumes_only_verified_prefix(self):
        import os
        from voice_native_legacy_predecessor_route import (
            restore_retired_common_legacy_ipfw,
        )
        from voice_native_process_probe import FreeBSDVoiceProcessProbe
        from voice_ipfw_adapter import FreeBSDIPFWAdapter
        from voice_native_legacy_ipfw_replay import _expected_after
        old={"rules":{"19000":["divert","9900","udp"]},
             "targets":["91.108.13.10","91.108.13.11"]}
        commands=[
            ["/sbin/ipfw","-q","table","zapret2_tgvoice","create","type","addr"],
            ["/sbin/ipfw","-q","table","zapret2_tgvoice","add","91.108.13.10"],
            ["/sbin/ipfw","-q","table","zapret2_tgvoice","add","91.108.13.11"],
            ["/sbin/ipfw","-qf","add","19000",*old["rules"]["19000"]],
        ]
        for scenario in ("complete","power-cut","foreign"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                work=root/detail()["id"]
                work.mkdir()
                marker=root/"legacy-marker"
                store=SharedApplyOperation(root/"shared-apply")
                seal="f"*64
                store.prepare_legacy_predecessor(detail(),lambda:seal)
                store.begin_legacy_quiesce(detail()["id"],lambda:seal)
                store.mark_legacy_processes_stopped(detail()["id"],lambda:seal)
                store.begin_legacy_ipfw_retire(detail()["id"],lambda:seal)
                store.finish_legacy_ipfw_retire(detail()["id"],lambda:seal)
                store.begin_legacy_marker_retire(detail()["id"],lambda:seal)
                store.finish_legacy_marker_retire(detail()["id"],lambda:seal)
                reader=object.__new__(FreeBSDIPFWAdapter)
                reader.allow_mutations=False
                reader.rule_base=19000; reader.rule_max=19010
                writer=object.__new__(FreeBSDIPFWAdapter)
                writer.allow_mutations=True
                writer.rule_base=19000; writer.rule_max=19010
                probe=object.__new__(FreeBSDVoiceProcessProbe)
                plan={"previous_five":"a"*64,
                      "marker_target":str(marker),
                      "legacy_ipfw_commands":commands}
                progress={"index":0,"cut":False,"foreign":False}
                issued=[]
                def actual(_):
                    if progress["foreign"]:
                        return {"rules":{"19009":["foreign"]},"targets":None}
                    return _expected_after(plan,progress["index"])
                def apply(_, *args, **kwargs):
                    self.assertTrue(kwargs["modifying"])
                    self.assertEqual(tuple(commands[progress["index"]][1:]),args)
                    issued.append(args)
                    progress["index"]+=1
                    if scenario=="power-cut" and progress["index"]==2 and not progress["cut"]:
                        progress["cut"]=True
                        raise OSError("simulated power loss after IPFW command")
                    if scenario=="foreign" and progress["index"]==2:
                        progress["foreign"]=True
                def invoke():
                    return restore_retired_common_legacy_ipfw(
                        identity=detail()["id"],store=store,work=work,
                        config_path=root/"config.xml",config_fd=4,
                        config_owner=(os.geteuid(),0),
                        active_runtime=root/"active",marker_path=marker,
                        process_probe=probe,readonly_ipfw=reader,
                        mutating_ipfw=writer,
                        require_lifecycle_owner=lambda:None,
                    )
                with patch("voice_native_legacy_predecessor_route._locked_config"), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous",
                           return_value={"previous_five":"a"*64}), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_restore_plan",
                           return_value=plan), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous_live_identity",
                           return_value={"legacy_ipfw_previous":old}), \
                     patch("voice_native_legacy_predecessor_route.inspect_previous",
                           return_value={}), \
                     patch("voice_native_legacy_predecessor_route._verify_sources"), \
                     patch("shared_apply_operation.fingerprint_legacy_predecessor",
                           return_value=seal), \
                     patch("voice_native_legacy_reverse_wal._stopped",
                           return_value="exact-three-role-absence"), \
                     patch("voice_native_legacy_ipfw_replay._strict_snapshot",
                           side_effect=actual), \
                     patch.object(FreeBSDIPFWAdapter,"_run",new=apply):
                    if scenario=="complete":
                        self.assertEqual("legacy-rollback-ipfw-restored",
                                         invoke()["phase"])
                        self.assertEqual(len(commands),len(issued))
                    else:
                        with self.assertRaises((OSError,RuntimeError)):
                            invoke()
                        self.assertEqual("legacy-rollback-ipfw",
                                         store.read()["phase"])
                        before=len(issued)
                        if scenario=="power-cut":
                            self.assertEqual("legacy-rollback-ipfw-restored",
                                             invoke()["phase"])
                            self.assertEqual(len(commands)-2,len(issued)-before)
                        else:
                            with self.assertRaises(RuntimeError):
                                invoke()
                            self.assertEqual(before,len(issued))
                    self.assertFalse(marker.exists())
                    self.assertEqual("shared-apply-pending",check_pending(
                        root/"voice-cutover",root/"voice-ipfw")["reason"])

    def test_old_marker_rollback_uses_existing_shared_wal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            owner="f"*64
            store.prepare_legacy_predecessor(detail(),lambda:owner)
            store.begin_legacy_quiesce(detail()["id"],lambda:owner)
            store.mark_legacy_processes_stopped(detail()["id"],lambda:owner)
            store.begin_legacy_ipfw_retire(detail()["id"],lambda:owner)
            store.finish_legacy_ipfw_retire(detail()["id"],lambda:owner)
            store.begin_legacy_marker_retire(detail()["id"],lambda:owner)
            store.finish_legacy_marker_retire(detail()["id"],lambda:owner)
            store.begin_legacy_ipfw_rollback(detail()["id"],lambda:owner)
            store.finish_legacy_ipfw_rollback(detail()["id"],lambda:owner)
            baseline=store.read()
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_marker_rollback(detail()["id"],lambda:owner)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_marker_rollback(detail()["id"],lambda:"e"*64)
            self.assertEqual(baseline,store.read())
            armed=store.begin_legacy_marker_rollback(detail()["id"],lambda:owner)
            self.assertEqual("legacy-rollback-marker",armed["phase"])
            self.assertEqual(armed,SharedApplyOperation(store.root).read())
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_marker_rollback(detail()["id"],lambda:owner)
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_marker_rollback(detail()["id"],lambda:"e"*64)
            self.assertEqual(armed,store.read())
            finished=store.finish_legacy_marker_rollback(detail()["id"],lambda:owner)
            self.assertEqual("legacy-rollback-marker-restored",finished["phase"])
            self.assertFalse(store.advisory()["safe_to_mutate"])
            self.assertEqual(finished,SharedApplyOperation(store.root).read())
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())

    def test_exact_old_marker_rollback_resumes_only_owned_staging_inode(self):
        import os
        import hashlib
        from voice_native_legacy_predecessor_route import (
            restore_retired_common_legacy_marker,
        )
        from voice_native_process_probe import FreeBSDVoiceProcessProbe
        from voice_ipfw_adapter import FreeBSDIPFWAdapter
        from voice_native_legacy_ipfw_replay import _expected_after
        marker_bytes=b"enabled\n"
        owner="f"*64
        commands=[
            ["/sbin/ipfw","-q","table","zapret2_tgvoice","create","type","addr"],
            ["/sbin/ipfw","-q","table","zapret2_tgvoice","add","91.108.13.10"],
            ["/sbin/ipfw","-qf","add","19000","divert","9000","udp"],
        ]
        for fault in ("none","link","finish","stage-clean","foreign-kernel",
                      "foreign-marker","foreign-stage"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                work=root/detail()["id"]
                work.mkdir()
                marker=root/"legacy-marker"
                stage=root/("." + marker.name + ".voice-old-" + detail()["id"][:16])
                store=SharedApplyOperation(root/"shared-apply")
                store.prepare_legacy_predecessor(detail(),lambda:owner)
                store.begin_legacy_quiesce(detail()["id"],lambda:owner)
                store.mark_legacy_processes_stopped(detail()["id"],lambda:owner)
                store.begin_legacy_ipfw_retire(detail()["id"],lambda:owner)
                store.finish_legacy_ipfw_retire(detail()["id"],lambda:owner)
                store.begin_legacy_marker_retire(detail()["id"],lambda:owner)
                store.finish_legacy_marker_retire(detail()["id"],lambda:owner)
                store.begin_legacy_ipfw_rollback(detail()["id"],lambda:owner)
                store.finish_legacy_ipfw_rollback(detail()["id"],lambda:owner)
                reader=object.__new__(FreeBSDIPFWAdapter)
                reader.allow_mutations=False
                reader.rule_base=19000; reader.rule_max=19010
                probe=object.__new__(FreeBSDVoiceProcessProbe)
                summary={"previous_five":"a"*64}
                plan={"previous_five":"a"*64,
                      "marker_target":str(marker),"legacy_ipfw_commands":commands}
                saved={"marker":{"mode":0o600,"bytes":len(marker_bytes),
                                 "sha256":hashlib.sha256(marker_bytes).hexdigest()}}
                if fault=="foreign-marker":
                    marker.write_bytes(b"foreign")
                if fault=="foreign-stage":
                    stage.write_bytes(b"foreign")
                def census(_):
                    return ({"rules":{"19009":["foreign"]},"targets":None}
                            if fault=="foreign-kernel" else
                            _expected_after(plan,len(commands)))
                def invoke():
                    return restore_retired_common_legacy_marker(
                        identity=detail()["id"],store=store,work=work,
                        config_path=root/"config.xml",config_fd=4,
                        config_owner=(os.geteuid(),0),active_runtime=root/"active",
                        marker_path=marker,process_probe=probe,readonly_ipfw=reader,
                        require_lifecycle_owner=lambda:None,
                    )
                with patch("voice_native_legacy_predecessor_route._locked_config"), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous",
                           return_value=summary), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_restore_plan",
                           return_value=plan), \
                     patch("voice_native_legacy_predecessor_route.inspect_legacy_previous_live_identity",
                           return_value=saved), \
                     patch("voice_native_legacy_predecessor_route._read_private_file",
                           return_value=marker_bytes), \
                     patch("voice_native_legacy_predecessor_route.inspect_previous",
                           return_value={}), \
                     patch("voice_native_legacy_predecessor_route._verify_sources"), \
                     patch("shared_apply_operation.fingerprint_legacy_predecessor",
                           return_value=owner), \
                     patch("voice_native_legacy_reverse_wal._stopped",
                           return_value="exact-three-role-absence"), \
                     patch("voice_native_legacy_ipfw_replay._strict_snapshot",
                           side_effect=census):
                    if fault in ("foreign-kernel","foreign-marker","foreign-stage"):
                        with self.assertRaises(RuntimeError):
                            invoke()
                        self.assertEqual("legacy-rollback-ipfw-restored",
                                         store.read()["phase"])
                        self.assertFalse(fault=="foreign-kernel" and marker.exists())
                        continue
                    if fault in ("link","finish","stage-clean"):
                        hook={
                            "link":"voice_native_legacy_predecessor_route.os.link",
                            "finish":"shared_apply_operation.SharedApplyOperation.finish_legacy_marker_rollback",
                            "stage-clean":"voice_native_legacy_predecessor_route.os.unlink",
                        }[fault]
                        with patch(hook,side_effect=OSError("injected power cut")):
                            with self.assertRaises(OSError):
                                invoke()
                        self.assertEqual(
                            "legacy-rollback-marker-restored" if fault=="stage-clean"
                            else "legacy-rollback-marker",store.read()["phase"])
                        self.assertTrue(stage.exists())
                        self.assertEqual(marker.exists(),fault!="link")
                    self.assertEqual("legacy-rollback-marker-restored",invoke()["phase"])
                    self.assertEqual(marker_bytes,marker.read_bytes())
                    self.assertEqual(0o600,marker.stat().st_mode & 0o777)
                    self.assertEqual(1,marker.stat().st_nlink)
                    self.assertFalse(stage.exists())
                    self.assertEqual("legacy-rollback-marker-restored",invoke()["phase"])
                    self.assertEqual("shared-apply-pending",check_pending(
                        root/"voice-cutover",root/"voice-ipfw")["reason"])

    def test_single_shared_journal_old_process_start_is_one_shot(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            store=SharedApplyOperation(root/"shared-apply")
            owner="f"*64
            store.prepare_legacy_predecessor(detail(),lambda:owner)
            store.begin_legacy_quiesce(detail()["id"],lambda:owner)
            store.mark_legacy_processes_stopped(detail()["id"],lambda:owner)
            store.begin_legacy_ipfw_retire(detail()["id"],lambda:owner)
            store.finish_legacy_ipfw_retire(detail()["id"],lambda:owner)
            store.begin_legacy_marker_retire(detail()["id"],lambda:owner)
            store.finish_legacy_marker_retire(detail()["id"],lambda:owner)
            store.begin_legacy_ipfw_rollback(detail()["id"],lambda:owner)
            store.finish_legacy_ipfw_rollback(detail()["id"],lambda:owner)
            store.begin_legacy_marker_rollback(detail()["id"],lambda:owner)
            store.finish_legacy_marker_rollback(detail()["id"],lambda:owner)
            before=store.read()
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_process_restart(detail()["id"],lambda:owner)
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_process_restart(detail()["id"],lambda:"a"*64)
            self.assertEqual(before,store.read())
            intent=store.begin_legacy_process_restart(detail()["id"],lambda:owner)
            self.assertEqual("legacy-rollback-processes",intent["phase"])
            self.assertEqual(intent,SharedApplyOperation(store.root).read())
            with self.assertRaises(SharedOperationError):
                store.begin_legacy_process_restart(detail()["id"],lambda:owner)
            with self.assertRaises(SharedOperationError):
                store.finish_legacy_process_restart(detail()["id"],lambda:"a"*64)
            self.assertEqual(intent,store.read())
            done=store.finish_legacy_process_restart(detail()["id"],lambda:owner)
            self.assertEqual("legacy-rollback-processes-restored",done["phase"])
            with self.assertRaises(SharedOperationError):
                store.complete_legacy_full_restore(detail()["id"],lambda:"a"*64)
            with self.assertRaises(SharedOperationError):
                store.complete_legacy_full_restore("2"*32,lambda:owner)
            self.assertEqual(done,store.read())
            self.assertEqual("shared-apply-pending",check_pending(
                root/"voice-cutover",root/"voice-ipfw")["reason"])
            completed=store.complete_legacy_full_restore(detail()["id"],lambda:owner)
            self.assertEqual("restored",completed["phase"])
            self.assertNotIn("legacy_predecessor",completed)
            self.assertTrue(store.advisory()["safe_to_mutate"])
            self.assertEqual(completed,SharedApplyOperation(store.root).read())
            self.assertIsNone(committed_owner(completed))
            with self.assertRaises(SharedOperationError):
                store.complete_legacy_full_restore(detail()["id"],lambda:owner)
            with self.assertRaises(SharedOperationError):
                store.advance("activating",detail())

    def test_common_legacy_process_resume_never_issues_second_start(self):
        import os
        from types import SimpleNamespace
        from voice_native_legacy_process_restart import (
            restart_common_legacy_processes, LegacyProcessRestartError,
        )
        from voice_native_process_probe import FreeBSDVoiceProcessProbe
        from voice_freebsd_process_security import FreeBSDProcessSecurityReader
        from voice_freebsd_kernel_argv import FreeBSDKernelArgvReader
        from voice_ipfw_adapter import FreeBSDIPFWAdapter
        from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES
        prior="f"*64
        for interrupted in (False,True,"bad-proof","closure-cut"):
            with self.subTest(interrupted=interrupted), tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                work=root/detail()["id"]
                work.mkdir()
                marker=root/"marker"
                marker.write_bytes(b"enabled\n")
                os.chmod(marker,0o600)
                store=SharedApplyOperation(root/"shared-apply")
                store.prepare_legacy_predecessor(detail(),lambda:prior)
                store.begin_legacy_quiesce(detail()["id"],lambda:prior)
                store.mark_legacy_processes_stopped(detail()["id"],lambda:prior)
                store.begin_legacy_ipfw_retire(detail()["id"],lambda:prior)
                store.finish_legacy_ipfw_retire(detail()["id"],lambda:prior)
                store.begin_legacy_marker_retire(detail()["id"],lambda:prior)
                store.finish_legacy_marker_retire(detail()["id"],lambda:prior)
                store.begin_legacy_ipfw_rollback(detail()["id"],lambda:prior)
                store.finish_legacy_ipfw_rollback(detail()["id"],lambda:prior)
                store.begin_legacy_marker_rollback(detail()["id"],lambda:prior)
                store.finish_legacy_marker_rollback(detail()["id"],lambda:prior)
                probe=object.__new__(FreeBSDVoiceProcessProbe)
                probe.expected=EXPECTED_SCRIPTS; probe.pidfiles=PIDFILES
                reader=object.__new__(FreeBSDIPFWAdapter)
                reader.allow_mutations=False
                reader.rule_base=19000; reader.rule_max=19010
                security=object.__new__(FreeBSDProcessSecurityReader)
                security.probe=probe
                security.expected_scripts=EXPECTED_SCRIPTS
                security.kernel_images={"proof":"image"}
                security.credentials={"proof":"credential"}
                argv=object.__new__(FreeBSDKernelArgvReader)
                argv.process_probe=probe
                argv.expected_paths=EXPECTED_SCRIPTS
                policy={
                    "schema":2,"policy_sha256":"9"*64,
                    "policy":{"previous":{"firewall":"b"*64},
                              "supervisor_argv":{"daemon":["sealed"]},
                              "images":security.kernel_images,
                              "credentials":security.credentials}
                }
                plan={"previous_five":{"firewall":"b"*64},
                      "marker_target":str(marker),"legacy_ipfw_commands":[["ipfw"]]}
                old={"previous_five":plan["previous_five"],
                     "process_security_policy_sha256":policy["policy_sha256"]}
                attempts=[]
                def run(*args,**kwargs):
                    attempts.append(args)
                    self.assertEqual("start",args[0][-1])
                    self.assertEqual((9,),kwargs["pass_fds"])
                    if interrupted in (True,"bad-proof"):
                        raise OSError("power cut after possible old process start")
                    return SimpleNamespace(returncode=0,stdout="",stderr="")
                def attest_old(**kwargs):
                    if interrupted=="bad-proof":
                        raise LegacyProcessRestartError("partial or foreign roles")
                    self.assertEqual(probe,kwargs["process_probe"])
                    self.assertIn(store.read()["phase"],
                        ("legacy-rollback-processes","legacy-rollback-processes-restored"))
                    return {"instances":{"engine":"good","daemon":"good","monitor":"good"}}
                def invoke():
                    return restart_common_legacy_processes(
                        identity=detail()["id"],store=store,work=work,
                        config_path=root/"config.xml",config_fd=4,
                        config_owner=(os.geteuid(),0),
                        active_runtime=root/"active",marker_path=marker,
                        ledger_root=root/"ledger",process_probe=probe,
                        readonly_ipfw=reader,security_reader=security,argv_reader=argv,
                        require_lifecycle_owner=lambda:None,runner=run,
                    )
                with ExitStack() as stack:
                    scopes = (
                        patch("voice_native_legacy_process_restart._locked_config"),
                     patch("voice_native_legacy_process_restart._pinned_regular"),
                     patch("voice_native_legacy_process_restart.inspect_legacy_previous",
                           return_value=old),
                     patch("voice_native_legacy_process_restart.inspect_legacy_restore_plan",
                           return_value=plan),
                     patch("voice_native_legacy_previous_seal.inspect_legacy_previous_live_identity",
                           return_value={"marker":{"mode":0o600}}),
                     patch("voice_native_legacy_process_restart.inspect_previous",
                           return_value={}),
                     patch("voice_native_legacy_process_restart.inspect_security_policy",
                           return_value=policy),
                     patch("voice_native_legacy_process_restart.canonical_supervisor_argv",
                           return_value={"daemon":["sealed"]}),
                     patch("voice_native_legacy_process_restart.inspect_process_evidence",
                           return_value={"observation":{"engine":{"state":"running"}}}),
                     patch("voice_native_legacy_process_restart._read_private_file",
                           return_value=b"enabled\n"),
                     patch("voice_native_legacy_poc_guard._legacy_read",
                           return_value=b"enabled\n"),
                     patch("voice_cutover_backup._verify_sources"),
                     patch("shared_apply_operation.fingerprint_legacy_predecessor",
                           return_value=prior),
                     patch("voice_native_legacy_process_restart._ledger_clear",
                           return_value="no-native-ledger"),
                     patch("voice_native_legacy_process_restart._strict_snapshot",
                           return_value={}),
                     patch("voice_native_legacy_process_restart._expected_after",
                           return_value={}),
                     patch("voice_native_legacy_process_restart._marker_stat",
                           return_value=marker.stat()),
                     patch("voice_native_legacy_process_restart._stopped",
                           return_value="exact-three-role-absence"),
                     patch("voice_native_legacy_process_restart._secure_script"),
                     patch("voice_native_legacy_process_restart.attest_restarted_old_roles",
                           side_effect=attest_old),
                    )
                    for scope in scopes:
                        stack.enter_context(scope)
                    if interrupted in (True,"bad-proof"):
                        with self.assertRaises(OSError):
                            invoke()
                        self.assertEqual("legacy-rollback-processes",store.read()["phase"])
                        if interrupted=="bad-proof":
                            with self.assertRaises(LegacyProcessRestartError):
                                invoke()
                        else:
                            self.assertEqual("restored",invoke()["phase"])
                    elif interrupted=="closure-cut":
                        with patch.object(store,"complete_legacy_full_restore",
                                          side_effect=OSError("power cut after roles verified")):
                            with self.assertRaises(OSError):
                                invoke()
                        self.assertEqual("legacy-rollback-processes-restored",
                                         store.read()["phase"])
                        self.assertEqual("restored",invoke()["phase"])
                    else:
                        self.assertEqual("restored",invoke()["phase"])
                    self.assertEqual(1,len(attempts))
                    if interrupted=="bad-proof":
                        self.assertEqual("legacy-rollback-processes",store.read()["phase"])
                    else:
                        self.assertEqual("restored",store.read()["phase"])
                        self.assertNotIn("legacy_predecessor",store.read())
                    with self.assertRaises(LegacyProcessRestartError):
                        invoke()

    def test_missing_state_stays_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            self.assertTrue(j.advisory()["safe_to_mutate"])
            self.assertFalse(j.root.exists())

    def test_phase_chain_durable_guard_terminal_new_operation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            j=SharedApplyOperation(root/"shared-apply")
            for phase in ("prepared","activating","activated","config-saved"):
                j.advance(phase,detail())
                snapshot=(j.root/"operation.json").read_bytes()
                guard=check_pending(root/"voice-cutover",root/"voice-ipfw")
                self.assertEqual(("blocked","shared-apply-pending",phase),
                                 (guard["state"],guard["reason"],guard["phase"]))
                self.assertEqual(snapshot,(j.root/"operation.json").read_bytes())
                self.assertEqual(0o700,j.root.stat().st_mode & 0o777)
                self.assertEqual(0o600,(j.root/"operation.json").stat().st_mode & 0o777)
            j.advance("committed",detail())
            self.assertTrue(j.advisory()["safe_to_mutate"])
            self.assertEqual("shared-runtime-owned",
                             check_pending(root/"voice-cutover",root/"voice-ipfw")["reason"])
            self.assertTrue(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                          native_scope=True)["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                j.advance("prepared",detail())
            j.advance("prepared",detail("2"*32))
            self.assertFalse(j.advisory()["safe_to_mutate"])

    def test_rollback_uncertainty_and_replay_refusal(self):
        samples=(
            ("prepared","activating","activated","restored"),
            ("prepared","activating","requires-review"),
            ("prepared","activating","activated","restore-failed"),
            ("prepared","activating","activated","config-saved","requires-review"),
        )
        for phases in samples:
            with self.subTest(phases=phases),tempfile.TemporaryDirectory() as d:
                j=SharedApplyOperation(Path(d)/"shared-apply")
                for p in phases:j.advance(p,detail())
                self.assertEqual(phases[-1]=="restored",j.advisory()["safe_to_mutate"])
                with self.assertRaises(SharedOperationError):
                    j.advance("activated",detail())

    def test_inspect_cli_has_no_root_override_and_requires_freebsd_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"inspect"],
                              text=True,capture_output=True,check=False)
        self.assertEqual(69,result.returncode)
        invalid=subprocess.run([sys.executable,str(cli),"inspect","/tmp/other"],
                               capture_output=True,check=False)
        self.assertEqual(64,invalid.returncode)
        safe_recovery=subprocess.run(
            [sys.executable,str(cli),"recover-prepared","1"*32],
            capture_output=True,text=True,check=False,
        )
        self.assertEqual(69,safe_recovery.returncode,
                         "recovery must refuse missing FreeBSD FD9 instead of crashing")
        self.assertNotIn("Traceback",safe_recovery.stderr)

    def test_prepared_only_recovery_attests_before_terminal_record(self):
        with tempfile.TemporaryDirectory() as folder:
            journal=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            journal.advance("prepared",d)
            attempts=[]
            def witness():
                attempts.append("verified")
                return True
            journal.recover_prepared(d["id"],witness)
            self.assertEqual(["verified"],attempts)
            self.assertEqual("restored",journal.read()["phase"])
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                journal.recover_prepared(d["id"],witness)
        with tempfile.TemporaryDirectory() as folder:
            journal=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            journal.advance("prepared",d)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                journal.recover_prepared(d["id"],lambda: False)
            self.assertEqual("prepared",journal.read()["phase"])
            journal.advance("activating",d)
            with self.assertRaisesRegex(SharedOperationError,"prepared-only"):
                journal.recover_prepared(d["id"],lambda: True)
            self.assertEqual("activating",journal.read()["phase"])

    def test_previous_committed_owner_survives_prepared_power_cut_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            store=SharedApplyOperation(root/"shared-apply")
            initial=detail("a"*32)
            next_owner=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,initial)
            self.assertEqual(initial,committed_owner(store.read()))
            prepared=store.advance("prepared",next_owner)
            self.assertEqual(initial,prepared["previous"])
            self.assertEqual("shared-apply-pending",
                             check_pending(root/"voice-cutover",root/"voice-ipfw")["reason"])
            restored=store.recover_prepared(next_owner["id"],lambda: True)
            self.assertEqual(initial,restored["previous"])
            self.assertEqual(initial,committed_owner(store.read()))
            old=check_pending(root/"voice-cutover",root/"voice-ipfw")
            self.assertEqual("shared-runtime-owned",old["reason"])
            self.assertFalse(old["safe_to_mutate"])
            self.assertTrue(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                          native_scope=True)["safe_to_mutate"])
            with self.assertRaisesRegex(SharedOperationError,"predecessor ID"):
                store.advance("prepared",initial)
            third=detail("c"*32)
            carry=store.advance("prepared",third)
            self.assertEqual(initial,carry["previous"])

    def test_previous_common_owner_remains_during_safe_pre_save_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            store=SharedApplyOperation(Path(temp)/"shared-apply")
            first=detail("a"*32)
            second=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,first)
            for phase in ("prepared","activating","activated","restored"):
                store.advance(phase,second)
            self.assertEqual(first,committed_owner(store.read()))
            self.assertEqual(first,store.read()["previous"])
            self.assertTrue(store.advisory()["safe_to_mutate"])

    def test_untrusted_predecessor_proof_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            store=SharedApplyOperation(root/"shared-apply")
            store.advance("prepared",detail("b"*32))
            import json
            path=store.root/"operation.json"
            record=json.loads(path.read_text())
            record["previous"]=detail("b"*32)
            path.write_text(json.dumps(record))
            self.assertEqual("invalid-or-untrusted-journal",
                check_pending(root/"voice-cutover",root/"voice-ipfw")["reason"])

    def test_pristine_activating_recovery_requires_previous_owner_and_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            previous=detail("a"*32)
            candidate=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                j.advance(phase,previous)
            j.advance("prepared",candidate)
            j.advance("activating",candidate)
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(candidate["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                j.recover_activating_pristine(candidate["id"],previous["id"],lambda: False)
            self.assertEqual("activating",j.read()["phase"])
            restored=j.recover_activating_pristine(
                candidate["id"],previous["id"],lambda: True)
            self.assertEqual(previous,restored["previous"])
            self.assertEqual(previous,committed_owner(restored))
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(candidate["id"],previous["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail("c"*32)
            j.advance("prepared",d)
            j.advance("activating",d)
            with self.assertRaisesRegex(SharedOperationError,"pristine"):
                j.recover_activating_pristine(d["id"],"a"*32,lambda: True)
            self.assertEqual("activating",j.read()["phase"])

    def test_cold_activated_completion_requires_predecessor_and_attestation(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            old=detail("a"*32); new=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,old)
            for phase in ("prepared","activating","activated"):
                store.advance(phase,new)
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(new["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                store.finish_activated_restore(new["id"],old["id"],lambda: False)
            self.assertEqual("activated",store.read()["phase"])
            restored=store.finish_activated_restore(new["id"],old["id"],lambda: True)
            self.assertEqual("restored",restored["phase"])
            self.assertEqual(old,committed_owner(restored))
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(new["id"],old["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            for phase in ("prepared","activating","activated"):
                store.advance(phase,d)
            with self.assertRaisesRegex(SharedOperationError,"activated rollback"):
                store.finish_activated_restore(d["id"],"a"*32,lambda: True)

    def test_installed_activating_completion_requires_exact_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SharedApplyOperation(Path(folder)/"shared-apply")
            previous=detail("a"*32)
            new=detail("b"*32)
            for phase in ("prepared","activating","activated","config-saved","committed"):
                store.advance(phase,previous)
            store.advance("prepared",new)
            store.advance("activating",new)
            with self.assertRaisesRegex(SharedOperationError,"activating rollback"):
                store.finish_activating_installed_restore(new["id"],"c"*32,lambda: True)
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                store.finish_activating_installed_restore(new["id"],previous["id"],lambda: False)
            self.assertEqual("activating",store.read()["phase"])
            restored=store.finish_activating_installed_restore(new["id"],previous["id"],lambda: True)
            self.assertEqual(previous,committed_owner(restored))
            self.assertEqual("restored",restored["phase"])
            with self.assertRaisesRegex(SharedOperationError,"activating rollback"):
                store.finish_activating_installed_restore(new["id"],previous["id"],lambda: True)

    def test_installed_activating_cli_refuses_missing_freebsd_fd9(self):
        result=subprocess.run(
            [sys.executable,str(BACKEND/"shared_apply_operation.py"),
             "finish-activating","a"*32,"b"*32],
            capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_activated_cli_refuses_missing_freebsd_fd9(self):
        result=subprocess.run([sys.executable,str(BACKEND/"shared_apply_operation.py"),
                               "finish-activated","a"*32,"b"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_post_save_recovery_only_after_attested_runtime_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            j=SharedApplyOperation(root/"shared-apply")
            d=detail("4"*32)
            for phase in ("prepared","activating","activated","config-saved"):
                j.advance(phase,d)
            self.assertFalse(check_pending(root/"voice-cutover",root/"voice-ipfw")["safe_to_mutate"])
            self.assertFalse(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                           native_scope=True)["safe_to_mutate"])
            self.assertTrue(check_pending(root/"voice-cutover",root/"voice-ipfw",
                                         native_scope=True,recover_saved=True)["safe_to_mutate"])
            with self.assertRaisesRegex(SharedOperationError,"attestation"):
                j.finish_saved(d["id"],lambda: False)
            self.assertEqual("config-saved",j.read()["phase"])
            completed=j.finish_saved(d["id"],lambda: True)
            self.assertEqual("committed",completed["phase"])
            with self.assertRaisesRegex(SharedOperationError,"saved-only"):
                j.finish_saved(d["id"],lambda: True)
        with tempfile.TemporaryDirectory() as folder:
            j=SharedApplyOperation(Path(folder)/"shared-apply")
            d=detail()
            for phase in ("prepared","activating","activated"):
                j.advance(phase,d)
            with self.assertRaisesRegex(SharedOperationError,"saved-only"):
                j.finish_saved(d["id"],lambda: True)
            self.assertEqual("activated",j.read()["phase"])

    def test_activating_cli_refuses_unprivileged_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"recover-activating",
                               "a"*32,"b"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_saved_finish_cli_refuses_unprivileged_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        result=subprocess.run([sys.executable,str(cli),"finish-saved","4"*32],
                              capture_output=True,text=True,check=False)
        self.assertEqual(69,result.returncode)
        self.assertNotIn("Traceback",result.stderr)

    def test_invalid_identity_fields_and_reordered_phase(self):
        with tempfile.TemporaryDirectory() as d:
            j=SharedApplyOperation(Path(d)/"shared-apply")
            good=detail()
            for bad in (
                {**good,"id":"wrong"},
                {**good,"page":"unknown"},
                {**good,"base":"bad"},
                {**good,"changed_fields":["hostlist.telegramips"]*2},
                {**good,"changed_fields":["../../etc/passwd"]},
            ):
                with self.assertRaises(SharedOperationError):
                    j.advance("prepared",bad)
            self.assertFalse(j.root.exists())
            j.advance("prepared",good)
            for phase,values in (("committed",good),
                                 ("activated",good),
                                 ("activating",detail("3"*32))):
                with self.assertRaises(SharedOperationError):
                    j.advance(phase,values)
            self.assertEqual("prepared",j.read()["phase"])

    def test_symlink_orphan_corruption_and_foreign_file_block(self):
        for issue in ("orphan","root-link","file-link","bad-json","extra","bad-mode"):
            with self.subTest(issue=issue),tempfile.TemporaryDirectory() as d:
                root=Path(d); j=SharedApplyOperation(root/"shared-apply")
                if issue=="root-link":
                    target=root/"other"; target.mkdir()
                    j.root.symlink_to(target)
                else:
                    # The writer itself creates the trusted root. Creating
                    # an empty root first intentionally represents a crash.
                    if issue in ("file-link","extra","bad-mode"):
                        j.advance("prepared",detail())
                    else:
                        j.root.mkdir(mode=0o700)
                    if issue=="file-link":
                        (j.root/"operation.json").unlink()
                        (j.root/"operation.json").symlink_to(root/"unknown")
                    elif issue=="bad-json":
                        (j.root/"operation.json").write_text("{bad")
                    elif issue=="extra":
                        (j.root/"tmp").write_text("unexpected")
                    elif issue=="bad-mode":
                        j.root.chmod(0o755)
                status=check_pending(root/"voice-cutover",root/"voice-ipfw")
                self.assertEqual("invalid-or-untrusted-journal",status["reason"])
                self.assertFalse(status["safe_to_mutate"])

    def test_cli_refuses_nonfreebsd_or_missing_fd9(self):
        cli=BACKEND/"shared_apply_operation.py"
        p=subprocess.run([sys.executable,str(cli),"record","prepared",
                          "1"*32,"voice","a"*64,"b"*64,"hostlist.telegramips"],
                         text=True,capture_output=True,check=False)
        self.assertEqual(69,p.returncode)

    def test_existing_service_routes_record_under_fd9(self):
        service=(BACKEND.parent/"zapret_service.sh").read_text()
        self.assertIn("shared_apply_record_service()",service)
        self.assertIn("shared-apply-record)",service)
        self.assertIn("service_with_lifecycle_lock",service)
        guard=service.split("if ! ",1)[0] if False else service.split(
            "# Do not permit ANY legacy lifecycle action",1)[1].split(
            'service_dispatch "$@"',1)[0]
        self.assertNotIn("shared-apply-record",guard)

if __name__=="__main__":
    unittest.main(verbosity=2)
