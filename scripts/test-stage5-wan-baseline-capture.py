#!/usr/bin/env python3
"""All tests are offline; no capture, curl, IPFW or installed OPNsense."""
from __future__ import annotations
import contextlib
import importlib.util
import io
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("stage5_baseline", HERE / "stage5-wan-baseline-capture.py")
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
generator = m.module("stage5_test_plan", HERE / "stage5-wan-acquisition-plan.py")


def candidate(v6=False):
    if v6:
        return generator.plan("yt3.ggpht.com","2001:4860:4860::8888","2001:db8::10",54111,"vtnet1")
    return generator.plan("yt3.ggpht.com","142.251.127.198","192.168.80.251",54111,"vtnet1")


def sample_pcap():
    # Minimal Ethernet IPv4/TCP with 5 byte payload and linktype 1.
    ip = bytes((0x45,0,0,45,0,0,0,0,64,6,0,0,192,168,80,251,142,251,127,198))
    tcp = struct.pack("!HHIIHHHH",54111,443,100,0,0x5018,4096,0,0) + b"hello"
    frame = b"\x22"*6 + b"\x33"*6 + struct.pack("!H",0x0800) + ip+tcp
    return (b"\xd4\xc3\xb2\xa1" + struct.pack("<HHiIII",2,4,0,0,65535,1) +
            struct.pack("<IIII",0,0,len(frame),len(frame)) + frame)


class FakeProcess:
    def __init__(self, capture):
        self.capture = capture
        self.pid = 999999 if capture else 999998
        self.returncode = None if capture else 0
        self.stderr = io.BytesIO(b"tcpdump: listening on vtnet1") if capture else None

    def poll(self):
        return None if self.capture else 0

    def wait(self, timeout=None):
        self.returncode = 0
        return 0


class CaptureTests(unittest.TestCase):
    def test_exact_pinned_plan_roundtrip_no_execution(self):
        for v6 in (False, True):
            with self.subTest(v6=v6), tempfile.TemporaryDirectory() as d:
                p = Path(d,"plan.json")
                plan = candidate(v6)
                p.write_text(json.dumps(plan))
                self.assertEqual(plan,m.safe_plan(p))
                self.assertFalse(plan["executed"])

    def test_modified_plan_rejected_before_any_process(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,"plan.json")
            for key,value in (("executed",True),("owner_live_authorization",True),("installed_a07","PASS")):
                obj=candidate()
                obj[key]=value
                p.write_text(json.dumps(obj))
                with self.subTest(key=key), self.assertRaises(m.CaptureError):
                    m.safe_plan(p)

    def test_symlink_hardlink_and_bad_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,"real.json");p.write_text(json.dumps(candidate()))
            q=Path(d,"link.json");q.symlink_to(p)
            with self.assertRaises(m.CaptureError): m.safe_plan(q)
            link=Path(d,"hard.json");os.link(p,link)
            with self.assertRaises(m.CaptureError):m.safe_plan(p)
            link.unlink()
            p.write_text("{")
            with self.assertRaises(m.CaptureError):m.safe_plan(p)

    def test_linux_or_unapproved_gates_refuse(self):
        with patch.object(m.platform,"system",return_value="Linux"):
            with self.assertRaises(m.CaptureError):m.live_gate()
        with patch.object(m.platform,"system",return_value="FreeBSD"), \
             patch.object(m.os,"geteuid",return_value=0), \
             patch.object(m.Path,"is_file",return_value=True), \
             patch.object(m.Path,"is_dir",return_value=True), \
             patch.dict(m.os.environ,{m.OPT_IN:"not-approved"}):
            with self.assertRaises(m.CaptureError):m.live_gate()

    def test_check_cli_prints_offline_only_json_without_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,"safe.json");p.write_text(json.dumps(candidate()))
            with patch.object(m,"live_gate") as gate, patch.object(m,"execute_one") as exec1:
                with patch("sys.stdout",new_callable=io.StringIO) as stream:
                    self.assertEqual(0,m.main(["--check","--plan",str(p)]))
                value=json.loads(stream.getvalue())
                self.assertEqual("PLAN_VALIDATED_ONLY",value["status"])
                self.assertFalse(value["executed"])
                gate.assert_not_called(); exec1.assert_not_called()

    def test_run_requires_one_mode_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,"plan.json");p.write_text(json.dumps(candidate()))
            for args in (["--plan",str(p)],["--check","--execute","--plan",str(p)]):
                with self.assertRaises(m.CaptureError):m.main(args)

    def test_preflight_requires_actual_ip_route_and_ethernet(self):
        plan=candidate()
        replies=iter(["vtnet1: flags\n inet 192.168.80.251 netmask ...\n",
                      "route to: 142.251.127.198\n interface: vtnet1\n",
                      "Data link types for vtnet1: EN10MB (Ethernet)\n"])
        class FakeSocket:
            def __enter__(self): return self
            def __exit__(self,*_): pass
            def bind(self,*args): self.bound=args
        with patch.object(m,"checked",side_effect=lambda *_args,**_:next(replies)) as command, \
             patch.object(m.socket,"socket",return_value=FakeSocket()) as sk:
            m.preflight(plan)
            self.assertEqual(3,command.call_count)
            sk.assert_called_once()

    def test_preflight_blocks_other_wan_and_no_linktype(self):
        for replies in (
            ["inet 192.168.80.251 ","interface: vtnet2","EN10MB"],
            ["inet 192.168.80.251 ","interface: vtnet1","RAW"],
            ["inet 10.0.0.1 ","interface: vtnet1","EN10MB"]
        ):
            with self.subTest(replies=replies),patch.object(m,"checked",side_effect=replies):
                with self.assertRaises(m.CaptureError):m.preflight(candidate())

    def test_ipv6_route_family_and_interface_owned(self):
        plan=candidate(True)
        replies=iter(["inet6 2001:db8::10 prefixlen 64\n",
                      "route to: 2001:4860:4860::8888\n interface: vtnet1\n","EN10MB"])
        class FakeSocket:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def setsockopt(self,*_):pass
            def bind(self,*_):pass
        with patch.object(m,"checked",side_effect=lambda *_a,**_:next(replies)) as checked, \
             patch.object(m.socket,"socket",return_value=FakeSocket()):
            m.preflight(plan)
        self.assertEqual("-6",checked.call_args_list[1][0][0][1])

    def test_bounded_simulated_success_requires_owner_compare(self):
        plan=candidate()
        spawned=[]
        created=[]
        def popen(argv,**kwargs):
            capture="/usr/sbin/tcpdump" in argv[0]
            if capture:
                path=Path(argv[argv.index("-w")+1])
                created.append(path)
                path.write_bytes(sample_pcap())
            obj=FakeProcess(capture)
            spawned.append((argv,obj,kwargs))
            return obj
        bridge=types.SimpleNamespace(compare=Mock())
        analyzer=types.SimpleNamespace(summarize=lambda *_: {
            "capture_correlated":True,"family":"ipv4","outgoing_packets":1,
            "payload_packets":1,"source_port":54111})
        with patch.object(m,"terminate",side_effect=lambda *args,**kw:None), \
             patch.object(m,"inspect") as native:
            result=m.execute_one(plan,popen=popen,process_identity=lambda: ("stable",),readiness=lambda *_a,**_kw:None,
                                 owner_inspection=lambda _:{"config_digest":"a"*64},
                                 network_preflight=lambda _:None,bridge=bridge,analyzer=analyzer)
            native.assert_not_called()
        self.assertEqual("BASELINE_CAPTURE_OBSERVED_ONLY",result["status"])
        self.assertFalse(result["exclude_effect_proven"])
        self.assertFalse(result["wan_origin_proven"])
        self.assertEqual(2,len(spawned))
        self.assertEqual("-U",spawned[0][0][1])
        self.assertTrue(spawned[0][2]["start_new_session"])
        self.assertTrue(created[0].is_file())
        bridge.compare.assert_called_once()
        shutil.rmtree(created[0].parent)

    def test_simulated_failed_probe_cleans_temp_and_never_claims_pass(self):
        plan=candidate()
        paths=[]
        def popen(argv,**kwargs):
            capture=argv[0]=="/usr/sbin/tcpdump"
            if capture:
                path=Path(argv[argv.index("-w")+1]); paths.append(path);path.write_bytes(sample_pcap())
            proc=FakeProcess(capture)
            if not capture:proc.returncode=7
            return proc
        with patch.object(m,"terminate",side_effect=lambda *args,**kw:None):
            with self.assertRaises(m.CaptureError):
                m.execute_one(plan,popen=popen,process_identity=lambda: ("stable",),readiness=lambda *_a,**_kw:None,
                              owner_inspection=lambda _:{"config_digest":"a"*64},
                              network_preflight=lambda _:None,bridge=types.SimpleNamespace(),
                              analyzer=types.SimpleNamespace())
        self.assertFalse(paths[0].parent.exists())

    def test_changed_native_owner_refuses_and_cleans(self):
        paths=[]
        def popen(argv,**kwargs):
            capture=argv[0]=="/usr/sbin/tcpdump"
            if capture:
                path=Path(argv[argv.index("-w")+1]);paths.append(path);path.write_bytes(sample_pcap())
            return FakeProcess(capture)
        bridge=types.SimpleNamespace(compare=Mock(side_effect=m.CaptureError("CONFIG_CHANGE")))
        analyzer=types.SimpleNamespace(summarize=lambda *_:{
             "capture_correlated":True,"family":"ipv4","outgoing_packets":1,
             "payload_packets":1,"source_port":54111})
        with patch.object(m,"terminate",side_effect=lambda *args,**kw:None):
            with self.assertRaises(m.CaptureError):
                m.execute_one(candidate(),popen=popen,process_identity=lambda: ("stable",),
                              readiness=lambda *_a,**_kw:None,owner_inspection=lambda _:{"config_digest":"a"*64},
                              network_preflight=lambda _:None,bridge=bridge,analyzer=analyzer)
        bridge.compare.assert_called_once()
        self.assertFalse(paths[0].parent.exists())

    def test_delayed_bpf_delivery_is_waited_for_but_never_extends_deadline(self):
        # Reproduces the owner-live regression: curl exits before FreeBSD BPF
        # delivers the first packet; old code stopped tcpdump immediately.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "baseline.pcap")
            path.write_bytes(sample_pcap()[:24])
            clock = [0.0]
            def tick(seconds):
                clock[0] += seconds
                if clock[0] >= .3:
                    path.write_bytes(sample_pcap())
            live = types.SimpleNamespace(poll=lambda: None)
            self.assertTrue(m.wait_for_packet_flush(
                live, path, deadline=1.0, now=lambda: clock[0], pause=tick))
            self.assertGreaterEqual(clock[0], .3)
            self.assertLessEqual(clock[0], 1.0)

            path.write_bytes(sample_pcap()[:24])
            clock[0] = 0.0
            self.assertFalse(m.wait_for_packet_flush(
                live, path, deadline=.2, now=lambda: clock[0], pause=tick))
            self.assertLessEqual(clock[0], .2)

    def test_missing_header_only_and_invalid_capture_reasons_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "baseline.pcap")
            with self.assertRaisesRegex(m.CaptureError, "no PCAP file"):
                m.read_ethernet_capture(path)
            raw = sample_pcap()
            path.write_bytes(raw[:24])
            with self.assertRaisesRegex(m.CaptureError, "header only: zero packet records"):
                m.read_ethernet_capture(path)
            path.write_bytes(b"broken")
            with self.assertRaisesRegex(m.CaptureError, "incomplete or oversized PCAP"):
                m.read_ethernet_capture(path)
            path.write_bytes(raw)
            self.assertEqual(raw, m.read_ethernet_capture(path))

    def test_tcpdump_readiness_marker_is_required(self):
        read_fd,write_fd=os.pipe()
        try:
            os.write(write_fd,b"tcpdump: listening on vtnet1, link-type EN10MB\n")
            with os.fdopen(read_fd,"rb",buffering=0) as p:
                fake=types.SimpleNamespace(stderr=p,poll=lambda:None)
                m.tcpdump_ready(fake,deadline=m.time.monotonic()+1)
        finally:os.close(write_fd)


    def test_native_pid_and_start_witness_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp, "dvtws2.pid")
            monitor = Path(tmp, "zapret2-supervisor-monitor.pid")
            engine.write_text("4242\n")
            monitor.write_text("4343\n")
            with patch.object(m, "checked", return_value="Thu Oct 29 20:00:00 2026\n") as check:
                witness = m.process_witness(pid_files=(engine, monitor))
                self.assertEqual((4242, 4343), (witness[0][1], witness[1][1]))
                self.assertEqual(2, check.call_count)
                self.assertEqual(["/bin/ps", "-p", "4242", "-o", "lstart="],
                                 check.call_args_list[0][0][0])
            for value in ("", "x", "0", "-1", "4242\n4343", "99999999999"):
                engine.write_text(value)
                with self.subTest(pid=value), self.assertRaises(m.CaptureError):
                    m.process_witness(pid_files=(engine, monitor))
            engine.write_text("4242")
            link = Path(tmp, "symlink.pid")
            link.symlink_to(engine)
            with self.assertRaises(m.CaptureError):
                m.process_witness(pid_files=(link, monitor))
            link.unlink()
            os.link(engine, link)
            with self.assertRaises(m.CaptureError):
                m.process_witness(pid_files=(engine, monitor))
            link.unlink()
            monitor.write_text("4242")
            with patch.object(m, "checked", return_value="Thu Oct 29 20:00:00 2026"):
                with self.assertRaises(m.CaptureError):
                    m.process_witness(pid_files=(engine, monitor))
            monitor.write_text("4343")
            with patch.object(m, "checked", return_value=""):
                with self.assertRaises(m.CaptureError):
                    m.process_witness(pid_files=(engine, monitor))

    def test_restart_during_native_inspection_prevents_any_probe(self):
        witnessed = iter(("old-process", "new-process"))
        never = Mock()
        def owner(_):
            return {"config_digest": "a"*64}
        with self.assertRaisesRegex(m.CaptureError, "changed during initial"):
            m.execute_one(candidate(), popen=never, bridge=types.SimpleNamespace(),
                          owner_inspection=owner,
                          process_identity=lambda: next(witnessed),
                          network_preflight=lambda _: None,
                          analyzer=types.SimpleNamespace())
        never.assert_not_called()

    def test_restart_after_capture_refuses_result_and_removes_pcap(self):
        paths = []
        def popen(argv, **kwargs):
            capture = argv[0] == "/usr/sbin/tcpdump"
            if capture:
                path = Path(argv[argv.index("-w") + 1])
                paths.append(path)
                path.write_bytes(sample_pcap())
            return FakeProcess(capture)
        bridge = types.SimpleNamespace(compare=Mock())
        analyzer = types.SimpleNamespace(summarize=lambda *_: {
            "capture_correlated": True, "family": "ipv4",
            "outgoing_packets": 1, "payload_packets": 1, "source_port": 54111})
        seen = iter(("old-instance", "old-instance", "new-instance"))
        with patch.object(m, "terminate", side_effect=lambda *_a, **_k: None):
            with self.assertRaisesRegex(m.CaptureError, "restarted during baseline"):
                m.execute_one(candidate(), popen=popen, readiness=lambda *_a, **_k: None,
                              process_identity=lambda: next(seen),
                              owner_inspection=lambda _: {"config_digest": "a"*64},
                              network_preflight=lambda _: None, bridge=bridge, analyzer=analyzer)
        bridge.compare.assert_called_once()
        self.assertFalse(paths[0].parent.exists())

    def test_nothing_auto_applies_exclude(self):
        s=(HERE/"stage5-wan-baseline-capture.py").read_text()
        self.assertNotIn("configctl",s)
        self.assertNotIn("ipfw add",s)
        self.assertNotIn("pkg add",s)
        self.assertIn("one baseline",s.lower())
        self.assertNotIn("excluded.pcap",s)


if __name__=="__main__":
    unittest.main(verbosity=2)
