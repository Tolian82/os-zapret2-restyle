import os, tempfile, pathlib, stat, unittest
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from managed_inode_barrier import seed, finish, recover, ManagedBarrierRefused, _payload, _name

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name); self.managed=self.root/'active'/'managed'; self.managed.mkdir(parents=True)
        self.uid=os.getuid(); self.token='.auto-detect-'+'a'*32+'.tmp'
        self.kw=(self.root,self.managed,self.token,self.uid)
        self.scratch=self.root/_name(self.token)
    def test_seed_finish(self):
        pin=seed(*self.kw);self.assertEqual((self.scratch/'record').read_bytes(),_payload(self.token))
        finish(*self.kw,pin);self.assertFalse(self.scratch.exists()); recover(*self.kw,pin)
    def test_recovery_before_finish(self):
        pin=seed(*self.kw);recover(*self.kw,pin);recover(*self.kw,pin);self.assertFalse(self.scratch.exists())
    def test_unbound_residue_refused(self):
        pin=seed(*self.kw)
        with self.assertRaisesRegex(ManagedBarrierRefused,'unbound'):recover(*self.kw,None)
        self.assertTrue(self.scratch.exists());recover(*self.kw,pin)
    def test_recovery_replays_exact_fsync_barrier(self):
        from unittest.mock import patch
        import managed_inode_barrier

        pin = seed(*self.kw)
        with patch.object(managed_inode_barrier, "finish", wraps=finish) as finish_witness:
            recover(*self.kw, pin)
        finish_witness.assert_called_once_with(*self.kw, pin)
        self.assertFalse(self.scratch.exists())

    def test_foreign_same_bytes_inode(self):
        pin=seed(*self.kw);original=self.scratch/'record';original.rename(self.scratch/'foreign');original.write_bytes(_payload(self.token));original.chmod(0o600)
        (self.scratch/'foreign').unlink()
        with self.assertRaises(ManagedBarrierRefused):finish(*self.kw,pin)
        with self.assertRaises(ManagedBarrierRefused):recover(*self.kw,pin)
    def test_symlink_refused(self):
        pin=seed(*self.kw);(self.scratch/'record').unlink();(self.scratch/'record').symlink_to(self.managed)
        with self.assertRaises(ManagedBarrierRefused):recover(*self.kw,pin)
    def test_data_changed_refused(self):
        pin=seed(*self.kw);(self.scratch/'record').write_bytes(b'b'*64)
        with self.assertRaises(ManagedBarrierRefused):recover(*self.kw,pin)
    def test_after_unlink_recovery(self):
        pin=seed(*self.kw);(self.scratch/'record').unlink()
        recover(*self.kw,pin);self.assertFalse(self.scratch.exists())
    def test_partial_rewrite_refused(self):
        pin=seed(*self.kw);(self.scratch/'record').write_bytes(_payload(self.token))
        with self.assertRaises(ManagedBarrierRefused):recover(*self.kw,pin)
    def test_foreign_dir_refused(self):
        pin=seed(*self.kw);self.scratch.rename(self.root/'old');self.scratch.mkdir(mode=0o700)
        with self.assertRaises(ManagedBarrierRefused):recover(*self.kw,pin)
    def test_link_and_mode_refused(self):
        pin=seed(*self.kw);os.link(self.scratch/'record',self.root/'link')
        with self.assertRaises(ManagedBarrierRefused):recover(*self.kw,pin)
if __name__=='__main__':unittest.main()
