#!/usr/bin/env python3
"""Private immutable previous Config+runtime backup, corruption and race tests."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT/"src/opnsense/scripts/OPNsense/Zapret/backend"
spec=importlib.util.spec_from_file_location("voice_cutover_backup", BACKEND/"voice_cutover_backup.py")
backup=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class SnapshotTests(unittest.TestCase):
    def fixture(self, root):
        root=Path(root)
        config=root/"config.xml"
        config.write_text("<opnsense><OPNsense><Zapret/></OPNsense></opnsense>\n")
        config.chmod(0o600)
        active=root/"runtime"
        active.mkdir()
        (active/"dvtws.args").write_text("--port=989\n--filter-tcp=443\n")
        managed=active/"managed"
        managed.mkdir()
        (managed/"ipset-telegram.txt").write_text("91.108.0.0/16\n")
        parent=root/"private"
        parent.mkdir(mode=0o700)
        return config,active,parent/"previous"

    def test_capture_restore_material_survives_restart_without_live_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            config,active,target=self.fixture(d)
            source_config=config.read_bytes()
            source_args=(active/"dvtws.args").read_bytes()
            manifest=backup.capture_previous(config,active,target)
            self.assertEqual(1,manifest["schema"])
            self.assertEqual(
                hashlib.sha256(source_config).hexdigest(),
                manifest["config"]["sha256"],
            )
            self.assertEqual("file",manifest["runtime"]["dvtws.args"]["type"])
            self.assertEqual("dir",manifest["runtime"]["managed/"]["type"])
            self.assertTrue((target/"manifest.sha256").is_file())
            self.assertEqual(0o700,target.stat().st_mode & 0o777)
            self.assertEqual(0o600,(target/"config/config.xml").stat().st_mode & 0o777)
            self.assertEqual(manifest,backup.inspect_previous(target))
            self.assertEqual(source_config,config.read_bytes())
            self.assertEqual(source_args,(active/"dvtws.args").read_bytes())
            self.assertEqual(source_config,(target/"config/config.xml").read_bytes())
            self.assertEqual(source_args,(target/"runtime/dvtws.args").read_bytes())
            with self.assertRaises(backup.VoiceBackupError):
                backup.capture_previous(config,active,target)
            self.assertEqual(manifest,backup.inspect_previous(target))

    def test_snapshot_fingerprints_bind_to_durable_cutover_intent(self):
        # Existing full transaction journal records five resource hashes.
        # The byte snapshot attests exactly Config and runtime, not kernel
        # IPFW or process state; those three require independent adapters.
        journal_spec=importlib.util.spec_from_file_location(
            "voice_cutover_journal", BACKEND/"voice_cutover_journal.py"
        )
        journal=importlib.util.module_from_spec(journal_spec)
        journal_spec.loader.exec_module(journal)
        with tempfile.TemporaryDirectory() as d:
            config,active,target=self.fixture(d)
            snapshot=backup.capture_previous(config,active,target)
            digests=backup.bound_resource_fingerprints(target)
            self.assertEqual(snapshot["config"]["sha256"],digests["config"])
            self.assertEqual(64,len(digests["runtime"]))
            before={**digests,
                    "engine":"1"*64, "firewall":"2"*64,
                    "supervisor":"3"*64}
            proof={"saved_xml_sha256":"4"*64,
                   "merged_sha256":"5"*64,
                   "native_argv_sha256":"6"*64}
            record=journal.new_record(before,proof)
            self.assertEqual(before,record["previous"])
            self.assertEqual(digests,backup.bound_resource_fingerprints(target,before))
            bad={**before,"runtime":"f"*64}
            with self.assertRaisesRegex(backup.VoiceBackupError,"fingerprint mismatch"):
                backup.bound_resource_fingerprints(target,bad)
            (target/"runtime/dvtws.args").write_text("--port=990\n")
            with self.assertRaises(backup.VoiceBackupError):
                backup.bound_resource_fingerprints(target,before)

    def test_invalid_input_and_parent_permissions_never_publish(self):
        for variant in ("config-symlink","runtime-symlink","parent-mode","runtime-special"):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as d:
                config,active,target=self.fixture(d)
                if variant=="config-symlink":
                    ref=Path(d)/"other.xml"
                    config.rename(ref)
                    config.symlink_to(ref)
                elif variant=="runtime-symlink":
                    ref=Path(d)/"other-runtime"
                    active.rename(ref)
                    active.symlink_to(ref, target_is_directory=True)
                elif variant=="parent-mode":
                    target.parent.chmod(0o755)
                else:
                    (active/"unsafe").symlink_to("/etc/passwd")
                with self.assertRaises((backup.VoiceBackupError,OSError)):
                    backup.capture_previous(config,active,target)
                self.assertFalse(target.exists())

    def test_corruption_extra_payload_and_unsafe_manifest_fail_readonly(self):
        for case in ("config-content","runtime-content","manifest","manifest-seal",
                     "extra-file","symlink-file","mode","missing-runtime"):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                config,active,target=self.fixture(d)
                backup.capture_previous(config,active,target)
                if case=="config-content":
                    (target/"config/config.xml").write_text("bad")
                elif case=="runtime-content":
                    (target/"runtime/dvtws.args").write_text("fake")
                elif case=="manifest":
                    (target/"manifest.json").write_text('{"broken":true}')
                elif case=="manifest-seal":
                    (target/"manifest.sha256").write_text("0"*64+"\n")
                elif case=="extra-file":
                    (target/"runtime/foreign").write_text("foreign")
                elif case=="symlink-file":
                    p=target/"runtime/dvtws.args"
                    p.unlink()
                    p.symlink_to(config)
                elif case=="mode":
                    (target/"manifest.json").chmod(0o644)
                elif case=="missing-runtime":
                    (target/"runtime/managed/ipset-telegram.txt").unlink()
                with self.assertRaises((backup.VoiceBackupError,OSError,KeyError,TypeError)):
                    backup.inspect_previous(target)
                self.assertTrue(config.is_file())
                self.assertTrue(active.is_dir())

    def test_mid_copy_source_replacement_refuses_snapshot_without_touching_original(self):
        with tempfile.TemporaryDirectory() as d:
            config,active,target=self.fixture(d)
            real=backup._tree
            def race(source,dest):
                result=real(source,dest)
                config.write_text("<opnsense><changed/></opnsense>\n")
                return result
            # A concurrent model change between copy and publishing must
            # reject the snapshot rather than accepting torn pre-cutover data.
            with patch.object(backup,"_tree",side_effect=race):
                with self.assertRaisesRegex(backup.VoiceBackupError,"Config changed"):
                    backup.capture_previous(config,active,target)
            self.assertFalse(target.exists(),
                             "inconsistent previous snapshot was published")

    def test_mid_copy_runtime_change_is_rejected_without_publishing(self):
        with tempfile.TemporaryDirectory() as d:
            config,active,target=self.fixture(d)
            original=backup._tree
            def edit_after_runtime_capture(source,dest):
                result=original(source,dest)
                (active/"managed/ipset-telegram.txt").write_text("203.0.113.10\n")
                return result
            with patch.object(backup,"_tree",side_effect=edit_after_runtime_capture):
                with self.assertRaisesRegex(backup.VoiceBackupError,"runtime file changed"):
                    backup.capture_previous(config,active,target)
            self.assertFalse(target.exists())
            self.assertEqual("203.0.113.10\n",
                             (active/"managed/ipset-telegram.txt").read_text())

if __name__=="__main__":
    unittest.main(verbosity=2)
