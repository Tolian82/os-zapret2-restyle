#!/usr/bin/env python3
"""Offline restore stage tests: NO live config, process, firewall or router calls."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_cutover_backup as backup
import voice_cutover_restore_stage as restorer


class RestoreStageTests(unittest.TestCase):
    def setup(self, root):
        root=Path(root)
        current_config=root/"config.xml"
        current_config.write_bytes(b"<opnsense>old config</opnsense>\n")
        current_config.chmod(0o600)
        current_runtime=root/"runtime-v2"
        current_runtime.mkdir()
        (current_runtime/"dvtws.args").write_bytes(b"--port=989\n")
        (current_runtime/"dvtws.args").chmod(0o644)
        (current_runtime/"managed").mkdir()
        (current_runtime/"managed"/"telegram.txt").write_bytes(b"91.108.0.0/16\n")
        private=root/"private"
        private.mkdir(mode=0o700)
        saved=private/"previous"
        backup.capture_previous(current_config, current_runtime, saved)
        previous=backup.bound_resource_fingerprints(saved)
        return saved,private/"ready",previous,current_config,current_runtime

    def test_prepared_stage_is_independent_and_restart_verifiable(self):
        with tempfile.TemporaryDirectory() as d:
            saved,destination,digests,config,runtime=self.setup(d)
            live_config=config.read_bytes()
            live_args=(runtime/"dvtws.args").read_bytes()
            result=restorer.prepare_restore_stage(saved,destination,digests)
            self.assertEqual("staged-only",result["state"])
            self.assertIs(result["activation_authorized"],False)
            self.assertEqual(digests,result["previous"])
            self.assertEqual(backup.inspect_previous(saved),backup.inspect_previous(destination))
            self.assertEqual(digests,backup.bound_resource_fingerprints(destination))
            self.assertEqual(2,result["manifest"]["schema"])
            self.assertEqual(runtime.stat().st_mode & 0o7777,
                             result["manifest"]["runtime_root_mode"])
            self.assertEqual(0o700,(destination/"runtime").stat().st_mode & 0o777)
            self.assertEqual(0o600,(destination/"runtime"/"dvtws.args").stat().st_mode & 0o777,
                             "stage bytes must remain private despite source mode 0644")
            self.assertEqual(0o700,destination.stat().st_mode & 0o777)
            self.assertEqual(0o700,(destination/"runtime/managed").stat().st_mode & 0o777)
            self.assertEqual(0o644,result["manifest"]["runtime"]["dvtws.args"]["mode"],
                             "original mode is retained only as checked metadata")
            self.assertEqual(live_config,config.read_bytes())
            self.assertEqual(live_args,(runtime/"dvtws.args").read_bytes())
            self.assertEqual(live_args,(saved/"runtime/dvtws.args").read_bytes())
            # A second runner must not overwrite even a valid staged previous.
            with self.assertRaises(backup.VoiceBackupError):
                restorer.prepare_restore_stage(saved,destination,digests)

    def test_wrong_journal_or_existing_target_refused_without_changes(self):
        for case in ("mismatched", "existing", "symlink", "foreign-file"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                saved,target,digests,config,runtime=self.setup(d)
                foreign=Path(d)/"foreign"
                foreign.mkdir()
                (foreign/"marker").write_text("untouched")
                if case=="existing":
                    target.mkdir()
                    (target/"marker").write_text("untouched")
                if case=="symlink":
                    target.symlink_to(foreign, target_is_directory=True)
                if case=="foreign-file":
                    target.write_text("untouched")
                if case=="mismatched":
                    digests={**digests,"config":"f"*64}
                with self.assertRaises((backup.VoiceBackupError,OSError)):
                    restorer.prepare_restore_stage(saved,target,digests)
                self.assertEqual("untouched",(foreign/"marker").read_text())
                self.assertEqual(b"<opnsense>old config</opnsense>\n",config.read_bytes())
                self.assertEqual(b"--port=989\n",(runtime/"dvtws.args").read_bytes())
                if case in ("existing","foreign-file"):
                    self.assertEqual("untouched",(target if case=="foreign-file"
                                            else target/"marker").read_text())

    def test_corrupt_or_linked_snapshot_never_publishes_stage(self):
        for case in ("tamper", "symlink", "missing", "extra"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                saved,target,digests,config,runtime=self.setup(d)
                file=saved/"runtime/dvtws.args"
                if case=="tamper":
                    file.write_bytes(b"edited")
                elif case=="symlink":
                    file.unlink()
                    file.symlink_to(config)
                elif case=="missing":
                    file.unlink()
                else:
                    (saved/"runtime/unexpected").write_text("unknown")
                with self.assertRaises((backup.VoiceBackupError,OSError)):
                    restorer.prepare_restore_stage(saved,target,digests)
                self.assertFalse(target.exists())
                self.assertEqual(b"--port=989\n",(runtime/"dvtws.args").read_bytes())

    def test_copy_failure_and_mid_stage_source_change_leave_no_target(self):
        for case in ("copy-exception", "mutate-snapshot"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                saved,target,digests,config,runtime=self.setup(d)
                real=restorer._copy_checked
                def injected(source, dest, row):
                    if source.name=="dvtws.args":
                        if case=="copy-exception":
                            raise OSError("simulated interrupted copy")
                        source.write_bytes(b"different contents")
                    return real(source,dest,row)
                with patch.object(restorer,"_copy_checked",side_effect=injected):
                    with self.assertRaises((OSError,backup.VoiceBackupError)):
                        restorer.prepare_restore_stage(saved,target,digests)
                self.assertFalse(target.exists())
                self.assertEqual(b"--port=989\n",(runtime/"dvtws.args").read_bytes())
                self.assertFalse(list(target.parent.glob(".voice-restore-stage-*")))

    def test_failure_before_final_rename_preserves_previous_and_live(self):
        with tempfile.TemporaryDirectory() as d:
            saved,target,digests,config,runtime=self.setup(d)
            with patch.object(restorer,"_sync_stage",side_effect=OSError("simulated fsync failure")):
                with self.assertRaises(OSError):
                    restorer.prepare_restore_stage(saved,target,digests)
            self.assertFalse(target.exists())
            self.assertEqual(digests,backup.bound_resource_fingerprints(saved))
            self.assertEqual(b"--port=989\n",(runtime/"dvtws.args").read_bytes())
            self.assertFalse(list(target.parent.glob(".voice-restore-stage-*")))


if __name__=="__main__":
    unittest.main(verbosity=2)
