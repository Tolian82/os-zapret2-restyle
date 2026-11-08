#!/usr/bin/env python3
"""Non-destructive, fast G01 contract tests for standalone Zapret purge.

Must not invoke the destructive path on Linux or a real OPNsense host.
Full native purge requires a separately isolated disposable OPNsense guest.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

SCRIPT = Path(__file__).resolve().with_name("purge-os-zapret2-restyle.sh")
source = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
module = {"__name__": "zapret_purge_contract"}
exec(compile(source, str(SCRIPT), "exec"), module)


class PurgeFastTest(unittest.TestCase):
    def fake_run(self, fn):
        class Scope:
            def __enter__(_):
                _.old = module["run"]
                module["run"] = fn
            def __exit__(self_, exc_type, exc, tb):
                module["run"] = self_.old
        return Scope()

    def test_syntax(self):
        p = subprocess.run(["sh", "-n", str(SCRIPT)], capture_output=True)
        self.assertEqual(0, p.returncode, p.stderr.decode())
        compile(source, str(SCRIPT), "exec")

    def test_refuse_linux_purge(self):
        if not sys.platform.startswith("freebsd"):
            p = subprocess.run(["sh", str(SCRIPT), "--purge", "--yes-disposable"],
                               capture_output=True, text=True)
            self.assertEqual(75, p.returncode)
            self.assertIn("FreeBSD", p.stderr)

    def test_only_exact_scoped_owned_paths(self):
        paths = module["OWNED_TREES"] + module["OWNED_FILES"]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(x.startswith(("/usr/local/", "/var/")) for x in paths))
        self.assertFalse(any("*" in x for x in paths))
        self.assertIn("/usr/local/opnsense/service/templates/OPNsense/Zapret", paths)

    def test_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "owned"
            link.symlink_to("/etc")
            with self.assertRaises(module["Refusal"]):
                module["safe_tree"](link)

    def test_upstream_internal_symlinks_are_unlinked_not_followed(self):
        # The original upstream v1.0.7 Makefile emits binary symlinks.
        # Simulate a root-owned dedicated tree on an unprivileged CI runner.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            external = base / "outside"
            external.mkdir()
            sentinel = external / "keep.txt"
            sentinel.write_text("unrelated resource must survive")
            owned = base / "zapret-owned"
            owned.mkdir()
            (owned / "binary-alias").symlink_to(sentinel)
            (owned / "directory-alias").symlink_to(external, target_is_directory=True)
            original = module["node"]

            def root_owned_node(path):
                try:
                    st = os.lstat(path)
                except FileNotFoundError:
                    return None
                values = list(st)
                values[4] = 0  # fake UID 0, preserving the actual file type
                return os.stat_result(values)

            module["node"] = root_owned_node
            try:
                self.assertTrue(module["safe_tree"](owned))
                module["delete_exact"](owned)
            finally:
                module["node"] = original
            self.assertFalse(owned.exists())
            self.assertEqual(sentinel.read_text(), "unrelated resource must survive")

    def test_non_root_owned_object_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "owned"
            path.mkdir()
            if os.geteuid() != 0:
                with self.assertRaises(module["Refusal"]):
                    module["safe_tree"](path)

    def check_xml(self, contents, expected):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.xml"
            path.write_text(contents)
            old_path, old_safe = module["CONFIG"], module["safe_config"]
            module["CONFIG"] = path
            module["safe_config"] = lambda: True
            try:
                self.assertEqual(expected, module["config_state"]())
                self.assertEqual(contents, path.read_text())
            finally:
                module["CONFIG"], module["safe_config"] = old_path, old_safe

    def test_config_inspection_uses_system_policy_not_owned_tree(self):
        self.assertIn("def safe_config():", source)
        self.assertIn('safe_config()\n    try:', source)
        self.assertIn("metadata.st_mode & stat.S_IWOTH", source)
        self.assertIn('metadata.st_uid != 0', source)  # protected ancestors only
        self.assertNotIn('safe_tree(CONFIG)', source)

    def test_native_core_user_wheel_conf_is_allowed(self):
        # Exact OPNsense 26.7 rc.subr.d/php policy, UID from native metadata.
        original = (module["node"], module["CONFIG"], module["opnsense_core_uid"])
        def fixture(path):
            path = Path(path)
            if path == Path("/"):
                return types.SimpleNamespace(st_mode=0o40755, st_uid=0, st_gid=0)
            if path == Path("/conf"):
                return types.SimpleNamespace(st_mode=0o40770, st_uid=789, st_gid=0)
            if path == Path("/conf/config.xml"):
                return types.SimpleNamespace(st_mode=0o100640, st_uid=789, st_gid=0)
            return None
        try:
            module["CONFIG"] = Path("/conf/config.xml")
            module["node"] = fixture
            module["opnsense_core_uid"] = lambda: 789
            self.assertTrue(module["safe_config"]())
        finally:
            module["node"], module["CONFIG"], module["opnsense_core_uid"] = original

    def test_foreign_native_config_ownership_is_refused(self):
        original = (module["node"], module["CONFIG"], module["opnsense_core_uid"])
        def fixture(conf_uid, conf_gid, conf_mode, file_uid=789, file_gid=0):
            def fake_node(path):
                path = Path(path)
                if path == Path("/"):
                    return types.SimpleNamespace(st_mode=0o40755, st_uid=0, st_gid=0)
                if path == Path("/conf"):
                    return types.SimpleNamespace(st_mode=conf_mode, st_uid=conf_uid, st_gid=conf_gid)
                if path == Path("/conf/config.xml"):
                    return types.SimpleNamespace(st_mode=0o100640, st_uid=file_uid, st_gid=file_gid)
                return None
            return fake_node
        try:
            module["CONFIG"] = Path("/conf/config.xml")
            module["opnsense_core_uid"] = lambda: 789
            for params in ((42, 0, 0o40770),
                           (789, 42, 0o40770),
                           (789, 0, 0o40777),
                           (789, 0, 0o40770, 42, 0),
                           (789, 0, 0o40770, 789, 42),
                           (789, 0, 0o120777)):
                module["node"] = fixture(*params)
                with self.subTest(owners=params):
                    with self.assertRaises(module["Refusal"]):
                        module["safe_config"]()
        finally:
            module["node"], module["CONFIG"], module["opnsense_core_uid"] = original

    def test_core_uid_is_queried_from_stock_opnsense_version(self):
        def fake(argv, **kwargs):
            self.assertEqual(["/usr/local/sbin/opnsense-version", "-R",
                              "CORE_GROUP=CORE_GID:CORE_USER=CORE_UID"], argv)
            return types.SimpleNamespace(stdout="www=789:www=789\n")
        with self.fake_run(fake):
            self.assertEqual(789, module["opnsense_core_uid"]())

    def test_unparseable_native_core_uid_is_refused(self):
        def fake(argv, **kwargs):
            return types.SimpleNamespace(stdout="broken UID")
        with self.fake_run(fake), self.assertRaises(module["Refusal"]):
            module["opnsense_core_uid"]()

    def test_config_reports_only_saved_zapret_and_registration(self):
        self.check_xml(
            "<opnsense><system><firmware><plugins>other,os-zapret2-restyle</plugins>"
            "</firmware></system><OPNsense><Zapret><token>PRIVATE</token></Zapret>"
            "<Other/></OPNsense></opnsense>", (True, True))

    def test_other_config_is_not_modified_by_inspection(self):
        self.check_xml(
            "<opnsense><system><firmware><plugins>other</plugins>"
            "</firmware></system><OPNsense><Other/></OPNsense></opnsense>",
            (False, False))

    def test_stop_uses_bounded_graceful_drain_never_killall(self):
        self.assertIn("for _ in range(5):", source)
        self.assertIn("time.sleep(1)", source)
        self.assertNotIn("killall", source)
        self.assertNotIn("os.kill(", source)

    def test_stopped_service_refuses_unattributed_process_before_pkg(self):
        with self.assertRaises(module["Refusal"]):
            module["attest_processes"](True, "stopped", [4321])
        with self.assertRaises(module["Refusal"]):
            module["attest_processes"](False, "missing", [4321])

    def test_running_owner_requires_process_evidence(self):
        with self.assertRaises(module["Refusal"]):
            module["attest_processes"](True, "running", [])
        with self.assertRaises(module["Refusal"]):
            module["attest_processes"](False, "running", [4321])

    def test_native_running_owner_with_pidproof_no_broad_scan_false_negative(self):
        # Canonical native status already verified the actual owner under FD9.
        # The broad ps census is for foreign PIDs, not an extra status oracle.
        from unittest import mock
        original = module["safe_tree"]
        try:
            module["safe_tree"] = lambda p: str(p) == "/var/run/dvtws2.pid"
            with mock.patch.object(Path, "read_text", return_value="6543"):
                module["attest_processes"](True, "running", [])
                module["attest_processes"](True, "running", [6543])
                with self.assertRaises(module["Refusal"]):
                    module["attest_processes"](True, "running", [9999])
        finally:
            module["safe_tree"] = original

    def test_complete_bsd_process_census_no_truncated_command(self):
        def fake(argv, **kwargs):
            self.assertEqual(["/bin/ps", "-A", "-ww", "-o", "pid=",
                              "-o", "command="], argv)
            return types.SimpleNamespace(stdout=(
                " 6543 /usr/local/etc/zapret2/binaries/my/dvtws2 --filter-tcp=65431\n"
                " 7000 /usr/sbin/ntpd\n"))
        with self.fake_run(fake):
            self.assertEqual([6543], module["processes"]())

    def test_freebsd_native_four_process_running_owner_is_valid(self):
        # Exact PID ancestry observed on disposable OPNsense 26.7:
        # daemon 3877 -> dvtws2 4038, supervisor 46369 -> sh 47909.
        from unittest import mock
        expected = {
            "/var/run/dvtws2.pid": "4038",
            "/var/run/zapret2-supervisor-daemon.pid": "46369",
            "/var/run/zapret2-supervisor-monitor.pid": "47909",
        }
        binary = "/usr/local/etc/zapret2/binaries/my/dvtws2"
        def fake_run(argv, **kwargs):
            self.assertEqual(["/bin/ps", "-p"], argv[:2])
            self.assertEqual(["-ww", "-o", "ppid=", "-o", "command="], argv[3:])
            return types.SimpleNamespace(stdout=(
                " 3877 " + binary + " --filter-tcp=65431\n"
                if argv[2] == "4038" else
                " 1 daemon: dvtws2 (FreeBSD daemon wrapper)\n"
                if argv[2] == "3877" else ""))
        original = module["safe_tree"]
        module["safe_tree"] = lambda p: str(p) in expected
        try:
            with mock.patch.object(
                Path, "read_text", autospec=True,
                side_effect=lambda path, **kw: expected[str(path)]
            ), self.fake_run(fake_run):
                module["attest_processes"](True, "running",
                                            [3877, 4038, 46369, 47909])
                with self.assertRaises(module["Refusal"]):
                    module["attest_processes"](True, "running",
                                                [3877, 4038, 46369, 47909, 9000])
                with self.assertRaises(module["Refusal"]):
                    module["attest_processes"](True, "stopped", [3877])
        finally:
            module["safe_tree"] = original

    def test_native_daemon_parent_spoofing_is_refused(self):
        binary = "/usr/local/etc/zapret2/binaries/my/dvtws2"
        test_cases = (
            (" 3877 /usr/local/bin/other --x\n",
             " 1 daemon: " + binary + " --x\n"),
            (" 3877 " + binary + " --x\n",
             " 1 daemon: /usr/local/bin/other --x\n"),
            (" 3877 " + binary + " --x\n",
             " 1 daemon: " + binary + "-foreign --x\n"),
            (" 3877 " + binary + " --x\n",
             " 1 daemon: adversary_dvtws2 --x\n"),
            (" 3877 " + binary + " --x\n",
             " 200 daemon: " + binary + " --x\n"),
            (" 1 " + binary + " --x\n",
             " 1 daemon: " + binary + " --x\n"),
        )
        for child, parent in test_cases:
            def fake_run(argv, **kwargs):
                return types.SimpleNamespace(
                    stdout=child if argv[2] == "4038" else parent)
            with self.subTest(child=child, parent=parent), self.fake_run(fake_run):
                with self.assertRaises(module["Refusal"]):
                    module["verified_engine_daemon_parent"](4038)

    def test_foreign_rule_in_our_numbers_is_refused(self):
        def fake(argv, **kwargs):
            if argv[0].endswith("kldstat"):
                return types.SimpleNamespace(returncode=0, stdout="")
            return types.SimpleNamespace(returncode=0, stdout=(
                "19000 allow ip from any to any\n65535 allow ip from any to any\n"))
        with self.fake_run(fake), self.assertRaises(module["Refusal"]):
            module["owned_rules"]()

    def test_actual_shared_and_lab_divert_ports(self):
        def fake(argv, **kwargs):
            if argv[0].endswith("kldstat"):
                return types.SimpleNamespace(returncode=0, stdout="")
            return types.SimpleNamespace(returncode=0, stdout=(
                "19000 divert 989 tcp from any to any 80,443 out not diverted not sockarg xmit vtnet1\n"
                "19100 divert 9989 udp from any to any 443 out not diverted not sockarg xmit vtnet1\n"
                "65535 allow ip from any to any\n"))
        with self.fake_run(fake):
            self.assertEqual([19000, 19100], module["owned_rules"]())

    def test_wrong_lab_divert_refused(self):
        def fake(argv, **kwargs):
            if argv[0].endswith("kldstat"):
                return types.SimpleNamespace(returncode=0, stdout="")
            return types.SimpleNamespace(returncode=0, stdout=(
                "19100 divert 989 udp from any to any 443 out not diverted not sockarg xmit vtnet1\n"))
        with self.fake_run(fake), self.assertRaises(module["Refusal"]):
            module["owned_rules"]()

    def test_no_kernel_module_load(self):
        def fake(argv, **kwargs):
            return types.SimpleNamespace(returncode=1, stdout="")
        with self.fake_run(fake):
            self.assertEqual([], module["owned_rules"]())
            self.assertEqual([], module["voice_tables"]())

    def test_voice_table_name_allowlist(self):
        names = module["VOICE_TABLES"]
        self.assertEqual(10, len(names))
        self.assertIn("zapret2_voice_telegram_stage", names)
        self.assertIn("zapret2_voice_custom", names)

    def test_foreign_voice_table_type_refused(self):
        def fake(argv, **kwargs):
            if argv[0].endswith("kldstat"):
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")
            return types.SimpleNamespace(returncode=0, stdout="type: number", stderr="")
        with self.fake_run(fake), self.assertRaises(module["Refusal"]):
            module["voice_tables"]()

    def test_missing_voice_tables_are_skipped(self):
        def fake(argv, **kwargs):
            if argv[0].endswith("kldstat"):
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")
            if argv[2] == "zapret2_voice_telegram":
                return types.SimpleNamespace(returncode=0, stdout="type: addr", stderr="")
            return types.SimpleNamespace(returncode=69, stdout="", stderr="No such process")
        with self.fake_run(fake):
            self.assertEqual(["zapret2_voice_telegram"], module["voice_tables"]())

    def test_unexpected_table_error_refused(self):
        def fake(argv, **kwargs):
            if argv[0].endswith("kldstat"):
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")
            return types.SimpleNamespace(returncode=69, stdout="", stderr="Permission denied")
        with self.fake_run(fake), self.assertRaises(module["Refusal"]):
            module["voice_tables"]()

    def test_disposable_ci_requires_three_optins_and_native_vm(self):
        for token in ("ZAPRET2_PURGE_DISPOSABLE_GUEST",
                      "ZAPRET2_G01_DISPOSABLE_NATIVE", "GITHUB_ACTIONS",
                      "kern.vm_guest"):
            self.assertIn(token, source)
        self.assertIn("non-virtual host", source)

    def test_repo_and_firmware_marker_use_explicit_identity(self):
        self.assertIn('data.get("product_id") != PACKAGE', source)
        self.assertIn("zapret2restyle", source)
        self.assertIn("tolian82[.]github[.]io", source)

    def test_confirmation_and_noninteractive_scope(self):
        for token in ('"PURGE OS-ZAPRET2-RESTYLE"',
                      "ZAPRET2_PURGE_DISPOSABLE_GUEST", '"--keep-repo"',
                      '"--purge"', '"--dry-run"'):
            self.assertIn(token, source)

    def test_existing_fd9_status_inventory_never_runs_native_status(self):
        # Even present FD9 cannot be write-opened via native status on dry-run.
        with tempfile.TemporaryDirectory() as tmp:
            service = Path(tmp) / "service"
            lock = Path(tmp) / "lock"
            service.write_text("installed")
            lock.write_text("preserve")
            names = ("SERVICE", "LOCK", "safe_tree", "processes", "run")
            saved = {name: module[name] for name in names}
            try:
                module["SERVICE"] = service
                module["LOCK"] = lock
                module["safe_tree"] = lambda _: True
                module["processes"] = lambda: [1234]
                module["run"] = lambda *a, **k: self.fail(
                    "status inventory must NEVER invoke native status")
                self.assertEqual("process-present-unverified",
                                 module["service_status"](True))
                module["processes"] = lambda: []
                self.assertEqual("stopped-unverified",
                                 module["service_status"](True))
                self.assertEqual(lock.read_text(), "preserve")
            finally:
                module.update(saved)

    def test_native_status_is_only_after_backup_before_pkg_delete(self):
        purge = source.split("def purge(keep_repo, yes_disposable):", 1)[1]
        self.assertLess(purge.index("backup = backup_config()"),
                        purge.index("status = native_service_status()"))
        self.assertLess(purge.index("status = native_service_status()"),
                        purge.index('run(["/usr/sbin/pkg", "delete"'))
        self.assertNotIn('run([str(SERVICE), "status"]',
                         source.split("def service_status(installed):", 1)[1]
                         .split("def native_service_status():", 1)[0])

    def test_dry_run_does_not_create_missing_fd9(self):
        self.assertIn("unverified-lock-absent", source)
        self.assertIn("if not safe_tree(LOCK)", source)


    def test_missing_freebsd_voice_table_errno_71(self):
        def fake(argv, **kwargs):
            if argv[0].endswith("kldstat"):
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")
            return types.SimpleNamespace(
                returncode=71, stdout="", stderr="ipfw: failed to request table info: No such process")
        with self.fake_run(fake):
            self.assertEqual([], module["voice_tables"]())

    def test_original_fd9_inode_is_unlinked_before_unlock(self):
        purge = source.split("def purge(keep_repo, yes_disposable):", 1)[1]
        self.assertIn("os.fstat(lockfd)", purge)
        self.assertIn("current.st_ino != held.st_ino", purge)
        self.assertLess(purge.index("os.unlink(LOCK)"),
                        purge.index("fcntl.flock(lockfd, fcntl.LOCK_UN)"))
        self.assertLess(purge.index('print("POSTCHECK:'),
                        purge.index('print("PURGE COMPLETE;'))

    def test_fd9_creates_have_nofollow(self):
        self.assertIn("os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW", source)
        self.assertIn("os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
