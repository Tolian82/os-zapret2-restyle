#!/usr/bin/env python3
"""Official OPNsense Zapret template isolated rendering contract (mock modules)."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0,str(BACKEND))
from shared_apply_render import render_detached,NativeDetachedRenderError,TARGETS


class Config:
    def __init__(self, filename):
        self.path=Path(filename)
    def get(self):
        return {"detached":self.path.read_text()}


class Template:
    def __init__(self,target_root_directory):
        self.root=Path(target_root_directory)
        self.settings=None
        self.bad_targets=False
    def list_module(self, module):
        assert module=="OPNsense/Zapret"
        return {"+TARGETS":TARGETS}
    def set_config(self,settings):
        self.settings=settings
    def generate(self,module):
        assert module=="OPNsense/Zapret"
        result=[]
        for name,rel in TARGETS.items():
            path=self.root/rel.lstrip("/")
            path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            path.write_text(name+":"+self.settings["detached"])
            path.chmod(0o600)
            result.append(str(path))
        return result


CANDIDATE="<opnsense><system><hostname>unchanged</hostname></system>" \
          "<OPNsense><Zapret><voice><telegram><enabled>1</enabled>" \
          "</telegram></voice></Zapret></OPNsense></opnsense>"


class RenderTests(unittest.TestCase):
    def build(self,d):
        root=Path(d)
        job=root/"1"*0 if False else root/("1"*32)
        job.mkdir(mode=0o700)
        candidate=job/"candidate.xml"
        candidate.write_text(CANDIDATE)
        candidate.chmod(0o600)
        return job,candidate

    def test_detached_native_template_outputs_do_not_touch_live_paths(self):
        with tempfile.TemporaryDirectory() as d:
            job,candidate=self.build(d)
            live=job/"live.conf"
            live.write_text("LIVE-UNCHANGED")
            result=render_detached(candidate,job/"templates",
                                   template_factory=Template,config_factory=Config)
            self.assertEqual(3,len(result))
            rendered=job/"templates/usr/local/etc/zapret2/zapret.conf"
            self.assertIn("<enabled>1</enabled>",rendered.read_text())
            self.assertEqual("LIVE-UNCHANGED",live.read_text())
            self.assertEqual(CANDIDATE,candidate.read_text())
            self.assertEqual(0o600,rendered.stat().st_mode & 0o777)
            with self.assertRaisesRegex(NativeDetachedRenderError,"not empty"):
                render_detached(candidate,job/"templates",
                                template_factory=Template,config_factory=Config)

    def test_untrusted_xml_or_mount_cannot_generate_release(self):
        for bad in ("", "<opnsense/>",
                    CANDIDATE.replace("<opnsense>","<!DOCTYPE opnsense><opnsense>"),
                    CANDIDATE.replace("<Zapret>","<Unboundplus>").replace("</Zapret>","</Unboundplus>")):
            with self.subTest(bad=bad[:35]),tempfile.TemporaryDirectory() as d:
                job,candidate=self.build(d)
                candidate.write_text(bad)
                with self.assertRaises(NativeDetachedRenderError):
                    render_detached(candidate,job/"templates",
                                    template_factory=Template,config_factory=Config)
                self.assertFalse((job/"templates").exists())

    def test_wrong_template_targets_and_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            job,candidate=self.build(d)
            class MutatedTemplate(Template):
                def list_module(self,module):
                    return {"+TARGETS":{"zapret.conf":"/etc/rc.conf"}}
            with self.assertRaisesRegex(NativeDetachedRenderError,"targets"):
                render_detached(candidate,job/"templates",
                                template_factory=MutatedTemplate,config_factory=Config)
        with tempfile.TemporaryDirectory() as d:
            job,candidate=self.build(d)
            victim=job/"foreign"
            victim.write_text("foreign")
            candidate.unlink()
            candidate.symlink_to(victim)
            with self.assertRaisesRegex(NativeDetachedRenderError,"unsafe"):
                render_detached(candidate,job/"templates",
                                template_factory=Template,config_factory=Config)

    def test_refuses_arbitrary_path_or_missing_fd9(self):
        script=BACKEND/"shared_apply_render.py"
        self.assertEqual(64,subprocess.run([sys.executable,str(script),
                                            "render","/tmp/evil"],
                                            capture_output=True).returncode)
        self.assertEqual(69,subprocess.run([sys.executable,str(script),
                                            "render","1"*32],
                                            capture_output=True).returncode)


if __name__=="__main__":
    unittest.main(verbosity=2)
