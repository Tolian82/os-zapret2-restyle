import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("midextract", Path(__file__).with_name("stage5-native-pkg-midextract.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class WitnessTests(unittest.TestCase):
    def test_partial_is_only_mixed_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            x, y = Path(d)/"x", Path(d)/"y"
            x.write_bytes(b"one")
            y.write_bytes(b"altered two")
            w=[(x,b"one",b"altered one"),(y,b"two",b"altered two")]
            self.assertEqual(module.witness_state(w),(1,1,0,0))
            y.write_bytes(b"half")
            self.assertEqual(module.witness_state(w),(1,0,0,1))
            x.write_bytes(b"altered one")
            y.write_bytes(b"altered two")
            self.assertEqual(module.witness_state(w),(0,2,0,0))
            y.unlink()
            self.assertEqual(module.witness_state(w),(0,1,1,0))
            x.write_bytes(b"one")
            self.assertEqual(module.witness_state(w),(1,0,1,0))

    def test_truss_invocation_uses_supported_freebsd_15_arguments(self):
        command = module.trace_pkg_command(Path("/root/trace"), Path("/root/candidate.pkg"))
        self.assertEqual(command, ["/usr/bin/truss", "-f", "-o", "/root/trace",
                                   "/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                                   "add", "-f", "/root/candidate.pkg"])
        self.assertNotIn("-t", command)

    def test_witness_declares_only_verifiable_installed_files(self):
        self.assertEqual(len(set(module.WITNESS_RELATIVE)),len(module.WITNESS_RELATIVE))
        self.assertGreaterEqual(len(module.WITNESS_RELATIVE),5)
        self.assertTrue(all(p.endswith((".volt", ".xml", ".conf", ".txt", ".sh"))
                            for p in module.WITNESS_RELATIVE))
        self.assertTrue(any(p.startswith("mvc/") for p in module.WITNESS_RELATIVE))
        self.assertTrue(any(p.startswith("service/") for p in module.WITNESS_RELATIVE))
        self.assertTrue(any(p.startswith("share/") for p in module.WITNESS_RELATIVE))

if __name__ == "__main__":
    unittest.main()
