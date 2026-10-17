#!/usr/bin/env python3
"""GUI native saved-OFF Voice preview: real FD9/Config-fd, zero stages."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import voice_native_draft_preview_route as route
import voice_native_saved_draft_candidate as draft


def previous_config() -> bytes:
    voice = "".join(
        f'<{s}><enabled>0</enabled><args>--filter-udp=*\n--filter-l7=stun\n--payload=stun</args></{s}>'
        for s in draft.SERVICES
    )
    targets = "".join(
        f'<{s}ips>91.108.0.0/16</{s}ips>' for s in draft.SERVICES
    )
    return ('<opnsense><system><password>keep-private</password></system>'
            '<OPNsense><Zapret><general><enabled>1</enabled></general>'
            '<voice>' + voice + '</voice><hostlist>' + targets +
            '</hostlist></Zapret></OPNsense></opnsense>').encode()


class VoiceDraftPreviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="voice-draft-preview-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = self.root / "config.xml"
        self.original = previous_config()
        self.config.write_bytes(self.original)
        self.config.chmod(0o600)
        self.sha = hashlib.sha256(self.original).hexdigest()
        self.hits = 0
        # Linux CI has no wwwonly account; simulate native owner separately.
        patch_owner = patch.object(route, "native_config_owner",
                                   return_value=(os.geteuid(), os.getegid()))
        patch_owner.start()
        self.addCleanup(patch_owner.stop)

    def test_preview_reuses_exact_saved_draft_parser_without_writes(self):
        with patch.object(route, "CONFIG", self.config), \
             patch.object(route, "require_lifecycle_lock",
                          side_effect=lambda: setattr(self, "hits", self.hits + 1)):
            result = route.preview("10001", self.sha)
        self.assertEqual("native-voice-saved-draft-preview", result["state"])
        self.assertEqual(2, result["selected_profiles"])
        self.assertEqual(64, len(result["saved_xml_sha256"]))
        self.assertFalse(result["safe_to_enable_voice"])
        self.assertFalse(result["public_voice_apply"])
        self.assertEqual(self.original, self.config.read_bytes())
        self.assertEqual(["config.xml"], sorted(p.name for p in self.root.iterdir()))
        self.assertGreaterEqual(self.hits, 3)
        route.native_config_owner.assert_called_once_with()

    def test_fail_closed_for_stale_input_without_publishing(self):
        with patch.object(route, "CONFIG", self.config), \
             patch.object(route, "require_lifecycle_lock", return_value=None):
            with self.assertRaises(draft.NativeDraftCandidateError):
                route.preview("10000", "0" * 64)
            with self.assertRaises(draft.NativeDraftCandidateError):
                route.preview("00000", self.sha)
        self.assertEqual(["config.xml"], sorted(p.name for p in self.root.iterdir()))
        self.assertEqual(self.original, self.config.read_bytes())

    def test_invalid_argv_does_not_access_native_backend(self):
        for args in ([], ["preview-draft"], ["wrong", "10000", self.sha],
                     ["preview-draft", "10000", self.sha, "foreign"]):
            with patch.object(route, "preview") as fn:
                self.assertEqual(64, route.main(args))
                fn.assert_not_called()

    def test_native_preview_command_is_configd_only_no_prepared(self):
        actions=(ROOT/"src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
        shell=(ROOT/"src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        api=(ROOT/"src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceController.php").read_text()
        self.assertIn("[voice_preview_draft]", actions)
        self.assertIn("parameters:%s %s", actions[actions.index("[voice_preview_draft]"):])
        self.assertIn("native-voice-preview-draft)", shell)
        self.assertIn("native_voice_preview_draft_service", shell)
        self.assertIn("voice_preview_draft", api)
        self.assertIn("configdpRun(", api)
        self.assertNotIn("[voice_prepare_draft]", actions)
        self.assertNotIn("native-voice-prepare-draft", actions)
        self.assertNotIn("native-voice-apply-prepared", actions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
