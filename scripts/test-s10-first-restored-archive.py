import fcntl
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from auto_detect_aborted_first import Slot, ArchiveRefused, archive_original_zero_directories

class Cut(Exception): pass

class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.uid = os.geteuid()
        self.live = self.base/'live'; self.live.mkdir()
        self.hist = self.base/'history'; self.hist.mkdir()
        self.slots = tuple(Slot(self.live/n, self.hist/n) for n in ('work','epoch','producer'))
        for s in self.slots: s.source.mkdir()
        (self.slots[0].source/'root.json').write_bytes(b'original immutable root\n')
        (self.slots[1].source/'pretraffic.json').write_bytes(b'original pinned seed\n')
        for n in ('worker.lock','inbox.txt','debug.log','learning.txt'):
            (self.slots[2].source/n).touch()
        self.lock = os.open(self.slots[2].source/'worker.lock',os.O_RDWR)
        self.addCleanup(os.close,self.lock)
        fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.scope_ok = True
        self.proof = self.evidence(tuple(s.source for s in self.slots), original=True)
    def scope(self): return self.scope_ok
    def evidence(self, paths, original=False):
        selected = paths[2]/'worker.lock'
        st=selected.lstat(); held=os.fstat(self.lock)
        if (st.st_dev,st.st_ino)!=(held.st_dev,held.st_ino): raise ArchiveRefused('not same P2a inode')
        fd=os.open(selected,os.O_RDWR|os.O_NOFOLLOW)
        try:
            try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: pass
            else: raise ArchiveRefused('not held')
        finally: os.close(fd)
        rows=[]
        for p,names in zip(paths, (('root.json',),('pretraffic.json',),('worker.lock','inbox.txt','debug.log','learning.txt'))):
            if set(os.listdir(p))!=set(names): raise ArchiveRefused('foreign entry')
            for n in names:
                path=p/n; st=path.lstat(); raw=path.read_bytes()
                if not path.is_file() or path.is_symlink() or st.st_nlink!=1: raise ArchiveRefused('unsafe file')
                if n in ('inbox.txt','debug.log','learning.txt') and raw: raise ArchiveRefused('nonempty producer')
                rows.append((n,st.st_dev,st.st_ino,hashlib.sha256(raw).digest()))
        result=tuple(rows)
        if not original and result!=self.proof: raise ArchiveRefused('original evidence changed')
        return result
    def run_move(self,**kw):
        return archive_original_zero_directories(self.slots, uid=self.uid, attest=self.evidence,scope=self.scope,**kw)
    def assert_complete(self):
        self.assertEqual(self.evidence(tuple(s.archived for s in self.slots)),self.proof)
        self.assertTrue(all(not s.source.exists() for s in self.slots))
    def test_complete_and_repeat(self):
        self.assertEqual(self.run_move(), self.proof); self.assert_complete()
        self.assertEqual(self.run_move(), self.proof); self.assert_complete()
    def cut(self,index):
        def inject(i):
            if i==index: raise Cut()
        with self.assertRaises(Cut): self.run_move(after_move=inject)
        self.assertEqual([s.archived.exists() for s in self.slots],[i<=index for i in range(3)])
        self.assertEqual(self.run_move(),self.proof); self.assert_complete()
    def test_cut_after_work(self): self.cut(0)
    def test_cut_after_epoch(self): self.cut(1)
    def test_cut_after_producer(self): self.cut(2)
    def test_duplicate_destination(self):
        self.slots[1].archived.mkdir()
        with self.assertRaises(ArchiveRefused): self.run_move()
        self.assertTrue(all(s.source.exists() for s in self.slots))
    def test_out_of_order(self):
        self.slots[1].source.rename(self.slots[1].archived)
        with self.assertRaises(ArchiveRefused): self.run_move()
        self.assertTrue(self.slots[0].source.exists())
    def test_missing_source(self):
        self.slots[1].source.rename(self.base/'unaccounted')
        with self.assertRaises(ArchiveRefused): self.run_move()
        self.assertTrue(self.slots[0].source.exists())
    def test_symlink_destination(self):
        self.slots[1].archived.symlink_to(self.slots[1].source)
        with self.assertRaises(ArchiveRefused): self.run_move()
        self.assertTrue(self.slots[0].source.exists())
    def test_nonempty(self):
        p=self.slots[2].source/'learning.txt'; p.write_bytes(b'never erase')
        with self.assertRaises(ArchiveRefused): self.run_move()
        self.assertEqual(p.read_bytes(),b'never erase')
    def test_replaced_equal_inode(self):
        p=self.slots[1].source/'pretraffic.json'; p.rename(self.base/'old-seed'); p.write_bytes(b'original pinned seed\n')
        with self.assertRaises(ArchiveRefused): self.run_move()
        self.assertTrue(self.slots[0].source.exists())
    def test_scope_changed(self):
        self.scope_ok=False
        with self.assertRaises(ArchiveRefused): self.run_move()
        self.assertTrue(all(s.source.exists() for s in self.slots))
    def test_data_after_move(self):
        def mutate(i):
            if i==0: (self.slots[2].source/'debug.log').write_bytes(b'late')
        with self.assertRaises(ArchiveRefused): self.run_move(after_move=mutate)
        self.assertEqual((self.slots[2].source/'debug.log').read_bytes(),b'late')
        self.assertTrue(self.slots[1].source.exists())
    def test_cross_device(self):
        import auto_detect_aborted_first as archive_move
        real=archive_move._stat_dir
        def different(path,uid):
            st=real(path,uid)
            if path==self.hist:
                row=list(st);row[2]+=1;return os.stat_result(row)
            return st
        with patch.object(archive_move,'_stat_dir',side_effect=different),self.assertRaisesRegex(ArchiveRefused,'cross_device'):
            self.run_move()
        self.assertTrue(all(s.source.exists() for s in self.slots))
    def test_real_child_exit_and_reacquire_every_cut(self):
        # The fixture owns the original lock; child gets its OFD by fork.
        # No finally runs in the child. Parent releases and reacquires the
        # same lock at the selected producer path before resuming.
        for index in range(3):
            with self.subTest(index=index):
                if index:
                    for slot in reversed(self.slots): slot.archived.rename(slot.source)
                pid=os.fork()
                if pid==0:
                    def crash(i):
                        if i==index: os._exit(91)
                    try: self.run_move(after_move=crash)
                    except BaseException: os._exit(92)
                    os._exit(93)
                _,status=os.waitpid(pid,0)
                self.assertEqual(os.waitstatus_to_exitcode(status),91)
                path=(self.slots[2].archived if self.slots[2].archived.exists() else self.slots[2].source)/'worker.lock'
                old=os.fstat(self.lock)
                fcntl.flock(self.lock,fcntl.LOCK_UN)
                fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW)
                try:
                    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    self.assertEqual((os.fstat(fd).st_dev,os.fstat(fd).st_ino),(old.st_dev,old.st_ino))
                    # Keep the original registered fd number for cleanup.
                    os.dup2(fd,self.lock)
                finally: os.close(fd)
                self.assertEqual(self.run_move(),self.proof)
                self.assert_complete()
    def test_real_cross_device_when_available(self):
        if not Path('/dev/shm').is_dir() or Path('/dev/shm').stat().st_dev==self.base.stat().st_dev:
            self.skipTest('second filesystem unavailable')
        with tempfile.TemporaryDirectory(dir='/dev/shm') as folder:
            slots=(Slot(self.slots[0].source,Path(folder)/'work'),*self.slots[1:])
            with self.assertRaisesRegex(ArchiveRefused,'cross_device'):
                archive_original_zero_directories(slots,uid=self.uid,attest=self.evidence,scope=self.scope)
            self.assertTrue(all(s.source.exists() for s in self.slots))
    def test_boolean_evidence_not_authority(self):
        with self.assertRaises(ArchiveRefused):
            archive_original_zero_directories(self.slots,uid=self.uid,attest=lambda p:True,scope=self.scope)


class RetryPreparedTest(unittest.TestCase):
    """Real original WAL, fixture native authority only; no actual native IO."""
    def setUp(self):
        from shared_apply_operation import SharedApplyOperation, _config_observation_witness
        import auto_detect_aborted_first as a
        self.a = a
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SharedApplyOperation(Path(self.temp.name) / 'wal', owner=os.geteuid())
        self.old_id = 'a' * 32
        self.new_id = 'b' * 32
        self.old = dict(schema=1, phase='restored',
            detail=dict(id=self.old_id, page='strategies', base='c'*64,
                candidate='d'*64, changed_fields=['general.enabled']),
            manifest=dict(schema=2,generation=self.old_id,root_sha256='e'*64,
                seal_sha256='f'*64,candidate_sha256='d'*64),
            first_running_sha256='1'*64,first_pretraffic_sha256='2'*64)
        self.store._persist_record(self.old)
        self.wal = self.store.root / 'operation.json'
        self.raw = self.wal.read_bytes()
        self.detail = dict(id=self.new_id,page='strategies',base='c'*64,
            candidate='3'*64,changed_fields=['general.enabled'])
        self.seal = {'sha256':{'plan.json':'4'*64}}
        self.witness = _config_observation_witness(self.detail,'4'*64,'c'*64)
        self.paths = tuple(Path(self.temp.name)/name for name in ('work','epoch','producer'))
        self.proof = (b'root',b'seed',((1,2,3),))
        for name,value in (
            ('SharedApplyOperation',lambda **kw:self.store),
            ('require_lifecycle_lock',lambda:None),
            ('assert_inherited_config_fd',lambda *args,**kw:None),
            ('_zero_processes',lambda *args:None),
            ('_first_retry_paths',lambda *args:self.paths),
            ('_first_retry_candidate',lambda *args:(self.detail,self.seal)),
            ('_empty_kernel',lambda path:'native-managed-kernel-empty'),
            ('_source_evidence',lambda *args,**kw:self.proof),
        ):
            p=patch.object(a,name,value);p.start();self.addCleanup(p.stop)
        p=patch.object(a.sys,'platform','freebsd14');p.start();self.addCleanup(p.stop)
        p=patch.object(a.os,'geteuid',return_value=0);p.start();self.addCleanup(p.stop)

    def prepare(self, **kw):
        return self.a.prepare_first_retry_locked(self.new_id,
            kw.get('witness',self.witness),config_fd=kw.get('config_fd',4),
            queue_fd=kw.get('queue_fd',3))

    def assert_old(self):
        self.assertEqual(self.wal.read_bytes(),self.raw)
        self.assertEqual(self.store.read(),self.old)

    def test_new_prepared_no_false_predecessor(self):
        self.assertEqual(self.prepare(),{'result':'original-first-retry-prepared','id':self.new_id})
        self.assertEqual(self.store.read(),{'schema':1,'phase':'prepared','detail':self.detail})

    def test_config_and_descriptor_refusal(self):
        for kw in ({'witness':'0'*64},{'queue_fd':5},{'config_fd':6}):
            with self.subTest(kw=kw),self.assertRaises(ArchiveRefused): self.prepare(**kw)
            self.assert_old()

    def test_archive_drift_or_writer_refusal(self):
        for name in ('_first_retry_paths','_first_retry_candidate','_source_evidence','_empty_kernel'):
            with self.subTest(name=name),patch.object(self.a,name,side_effect=ArchiveRefused('fixture drift')):
                with self.assertRaises(ArchiveRefused): self.prepare()
                self.assert_old()

    def test_proof_changed_between_reads(self):
        with patch.object(self.a,'_source_evidence',side_effect=[self.proof,(b'other',)]):
            with self.assertRaisesRegex(ArchiveRefused,'PREIMAGE_CHANGED'): self.prepare()
        self.assert_old()

    def test_generic_prepared_still_refuses(self):
        from shared_apply_operation import SharedOperationError
        with self.assertRaises(SharedOperationError): self.store.advance('prepared',self.detail)
        self.assert_old()


if __name__=='__main__': unittest.main(verbosity=2)
