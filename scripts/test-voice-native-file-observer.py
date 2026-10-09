#!/usr/bin/env python3
"""No-appliance live Config/runtime witness tests, Linux and FreeBSD."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_native_file_observer as live


class LiveFileObserverTests(unittest.TestCase):
    def fixture(self, path):
        root=Path(path)
        config=root/"config.xml"
        config.write_bytes(b"<opnsense>previous</opnsense>\n")
        config.chmod(0o600)
        runtime=root/"runtime"
        runtime.mkdir(mode=0o700)
        (runtime/"dvtws.args").write_bytes(b"--port=989\n")
        (runtime/"dvtws.args").chmod(0o644)
        (runtime/"managed").mkdir(mode=0o700)
        (runtime/"managed"/"ipset-telegram.txt").write_bytes(b"91.108.0.0/16\n")
        (runtime/"empty").mkdir(mode=0o700)
        private=root/"private"
        private.mkdir(mode=0o700)
        previous=private/"previous"
        backup.capture_previous(config,runtime,previous)
        return config,runtime,previous

    def test_live_exact_fingerprints_equal_private_previous_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            config,runtime,previous=self.fixture(d)
            old=backup.bound_resource_fingerprints(previous)
            before={name:(runtime/name).read_bytes() for name in (
                "dvtws.args","managed/ipset-telegram.txt"
            )}
            result=live.observe_live_files(config,runtime)
            self.assertEqual(old,result)
            self.assertEqual(old,live.LiveFileObserver(config,runtime).observe())
            self.assertEqual(before,{name:(runtime/name).read_bytes() for name in before})
            self.assertEqual(b"<opnsense>previous</opnsense>\n",config.read_bytes())
            self.assertEqual(old,backup.bound_resource_fingerprints(previous))

    def test_changed_live_files_produce_different_bounded_fingerprints(self):
        with tempfile.TemporaryDirectory() as d:
            config,runtime,previous=self.fixture(d)
            old=backup.bound_resource_fingerprints(previous)
            config.write_text("<opnsense>different</opnsense>\n")
            now=live.observe_live_files(config,runtime)
            self.assertNotEqual(old["config"],now["config"])
            self.assertEqual(old["runtime"],now["runtime"])
            (runtime/"managed"/"ipset-telegram.txt").write_bytes(b"91.108.13.10\n")
            now=live.observe_live_files(config,runtime)
            self.assertNotEqual(old["runtime"],now["runtime"])
            self.assertEqual(old,backup.bound_resource_fingerprints(previous))

    def test_dir_or_file_mode_and_empty_subdir_affect_runtime_fingerprint(self):
        for variant in ("file-mode","directory-mode","extra-empty-dir"):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as d:
                config,runtime,previous=self.fixture(d)
                old=backup.bound_resource_fingerprints(previous)
                if variant=="file-mode":
                    (runtime/"dvtws.args").chmod(0o600)
                elif variant=="directory-mode":
                    (runtime/"empty").chmod(0o750)
                else:
                    (runtime/"other").mkdir()
                self.assertNotEqual(old["runtime"],
                                    live.observe_live_files(config,runtime)["runtime"])

    def test_symlink_special_hardlink_and_untrusted_root_refused(self):
        variants=("config-link","runtime-link","child-link","directory-link",
                  "special-fifo","hardlink","missing-root")
        for variant in variants:
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as d:
                config,runtime,previous=self.fixture(d)
                if variant=="config-link":
                    config.rename(Path(d)/"original.xml")
                    config.symlink_to(Path(d)/"original.xml")
                elif variant=="runtime-link":
                    runtime.rename(Path(d)/"original-runtime")
                    runtime.symlink_to(Path(d)/"original-runtime", target_is_directory=True)
                elif variant=="child-link":
                    (runtime/"managed"/"link").symlink_to("/etc/passwd")
                elif variant=="directory-link":
                    (runtime/"link").symlink_to(runtime/"managed", target_is_directory=True)
                elif variant=="special-fifo":
                    if not hasattr(os,"mkfifo"): self.skipTest("no mkfifo")
                    os.mkfifo(runtime/"fifo")
                elif variant=="hardlink":
                    os.link(runtime/"dvtws.args",runtime/"copy.args")
                else:
                    runtime.rename(Path(d)/"gone")
                with self.assertRaises((live.LiveFileEvidenceError,OSError)):
                    live.observe_live_files(config,runtime)
                backup.bound_resource_fingerprints(previous)

    def test_oversized_and_excessively_deep_tree_refused(self):
        with tempfile.TemporaryDirectory() as d:
            config,runtime,previous=self.fixture(d)
            huge=runtime/"huge"
            with huge.open("wb") as handle:
                handle.truncate(backup.MAX_BYTES+1)
            with self.assertRaises(live.LiveFileEvidenceError):
                live.observe_live_files(config,runtime)
        with tempfile.TemporaryDirectory() as d:
            config,runtime,previous=self.fixture(d)
            path=runtime
            for n in range(live.MAX_DEPTH+2):
                path=path/f"d{n}"
                path.mkdir()
            with self.assertRaises(live.LiveFileEvidenceError):
                live.observe_live_files(config,runtime)

    def test_bound_on_entry_count_prevents_unlimited_read(self):
        with tempfile.TemporaryDirectory() as d:
            config,runtime,previous=self.fixture(d)
            with patch.object(live,"MAX_FILES",2):
                with self.assertRaises(live.LiveFileEvidenceError):
                    live.observe_live_files(config,runtime)

    def test_replaced_file_between_scans_refused(self):
        with tempfile.TemporaryDirectory() as d:
            config,runtime,previous=self.fixture(d)
            original=live._scan
            count=0
            def change_after_first(*args):
                nonlocal count
                result=original(*args)
                count+=1
                if count==1:
                    (runtime/"dvtws.args").write_text("--port=990\n")
                return result
            with patch.object(live,"_scan",side_effect=change_after_first):
                with self.assertRaisesRegex(live.LiveFileEvidenceError,
                                            "changed between observations"):
                    live.observe_live_files(config,runtime)

    def test_absolute_paths_and_file_owner_requirements(self):
        with tempfile.TemporaryDirectory() as d:
            config,runtime,previous=self.fixture(d)
            with self.assertRaises(live.LiveFileEvidenceError):
                live.observe_live_files(Path("config.xml"),runtime)
            with self.assertRaises(live.LiveFileEvidenceError):
                live.observe_live_files(config,Path("runtime"))
            with patch.object(live.os,"geteuid",return_value=os.geteuid()+1):
                with self.assertRaises(live.LiveFileEvidenceError):
                    live.observe_live_files(config,runtime)


if __name__=="__main__":
    unittest.main(verbosity=2)
