#!/usr/bin/env python3
"""Single Python profile policy regressions: native syntax and no service access."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/backend/profile_policy.py'
SPEC = importlib.util.spec_from_file_location('profile_policy', FILE)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class ProfilePolicyTests(unittest.TestCase):
    def test_native_new_order_and_names(self):
        raw = b'--filter-tcp=443\r\n<HOSTLIST:youtube>\r\n--new=named-udp\r\n--filter-udp=443\r\n--lua-desync=fake\r\n'
        self.assertEqual(policy.split_profiles(raw), [
            b'--filter-tcp=443\n<HOSTLIST:youtube>\n',
            b'--name=named-udp\n--filter-udp=443\n--lua-desync=fake\n',
        ])

    def test_zero_empty_and_rejections(self):
        for value in (b'', b'  \n', b'\r\n\t\r\n'):
            self.assertEqual(policy.split_profiles(value), [])
        for value in (b'--new\n', b'--new=bad\n', b'--filter-tcp=443\n--new\n',
                      b'--filter-tcp=443\n--new\n\n'):
            with self.assertRaises(policy.ProfilePolicyError):
                policy.split_profiles(value)

    def test_placeholders(self):
        self.assertEqual(policy._tokens(
            b'<HOSTLIST:youtube> <IPSET:telegram>\n<HOSTLIST:youtube>\n<BLOB:fake_1>\n'
        ), [('HOSTLIST', 'youtube'), ('IPSET', 'telegram'), ('BLOB', 'fake_1')])
        policy.validate_syntax(b'--lua-desync=fake\n<HOSTLIST:youtube>\n', 1)
        for value in (b'<HOSTLIST>\n', b'<HOSTLIST:>\n', b'<HOSTLIST:bad!>\n', b'bad <\n'):
            with self.assertRaises(policy.ProfilePolicyError):
                policy.validate_syntax(value, 2)

    def test_multiple_selectors_retain_handler_chain(self):
        raw = (b'--filter-tcp=443\n<IPSET:telegram>\n<HOSTLIST:user>\n'
               b'--payload=tls_client_hello\n--lua-desync=fake\n'
               b'--payload=http_req\n--lua-desync=multisplit\n')
        expanded = policy.expand_profiles([raw])
        self.assertEqual(len(expanded), 2)
        self.assertIn(b'<IPSET:telegram>\n\n--payload', expanded[0])
        self.assertIn(b'\n<HOSTLIST:user>\n--payload', expanded[1])
        for p in expanded:
            self.assertIn(b'--payload=tls_client_hello\n--lua-desync=fake\n', p)
            self.assertIn(b'--payload=http_req\n--lua-desync=multisplit\n', p)

    def test_repeated_selector_and_idempotence(self):
        source = b'<HOSTLIST:user>\n--filter-tcp=443\n<HOSTLIST:user>\n<IPSET:telegram>\n'
        first = policy.expand_profiles([source])
        self.assertEqual(len(first), 2)
        self.assertEqual(policy.expand_profiles(first), first)

    def test_cli_atomicity_with_invalid_input(self):
        with tempfile.TemporaryDirectory(prefix='profile-policy-') as tmp:
            directory = Path(tmp)
            command = [sys.executable, str(FILE)]
            (directory / 'traffic.input').write_text('--filter-udp=443\n')
            parse = subprocess.run(command + ['parse', tmp], capture_output=True, text=True)
            self.assertEqual(parse.returncode, 0, parse.stderr)
            self.assertEqual(parse.stdout.strip(), '1')
            original = (directory / 'profile-1.conf').read_bytes()
            (directory / 'traffic.input').write_text('--new\n')
            parse = subprocess.run(command + ['parse', tmp], capture_output=True, text=True)
            self.assertNotEqual(parse.returncode, 0)
            self.assertEqual((directory / 'profile-1.conf').read_bytes(), original)
            (directory / 'profile-1.conf').write_text('<HOSTLIST:youtube>\n<WRONG>\n')
            normalize = subprocess.run(command + ['normalize', tmp, '1'], capture_output=True, text=True)
            self.assertNotEqual(normalize.returncode, 0)
            self.assertEqual((directory / 'profile-1.conf').read_text(), '<HOSTLIST:youtube>\n<WRONG>\n')
            self.assertEqual((directory / 'profile-count').read_text(), '1\n')
            (directory / 'profile-1.conf').write_text('<IPSET:telegram>\n<HOSTLIST:user>\n')
            normalized = subprocess.run(command + ['normalize', tmp, '1'], capture_output=True, text=True)
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            self.assertEqual(normalized.stdout.strip(), '2')
            self.assertEqual((directory / 'profile-count').read_text(), '2\n')
            (directory / 'traffic.input').write_text(' \n')
            zero = subprocess.run(command + ['parse', tmp], capture_output=True, text=True)
            self.assertEqual(zero.returncode, 0, zero.stderr)
            self.assertEqual(zero.stdout.strip(), '0')
            self.assertFalse(list(directory.glob('profile-*.conf')))
            self.assertEqual((directory / 'profile-count').read_text(), '0\n')

    def test_resolved_list_file_identity_and_final_argv_adapter(self):
        with tempfile.TemporaryDirectory(prefix='resolved-list-policy-') as tmp:
            root = Path(tmp)
            static = root / 'static'
            release = root / 'candidate'
            managed = release / 'managed'
            reference = Path('/var/db/zapret2-restyle/runtime/next')
            static.mkdir()
            managed.mkdir(parents=True)
            for name in ('hostlist-user.txt', 'hostlist-youtube.txt', 'ipset-telegram.txt',
                         'ipset-exclude.txt'):
                (managed / name).write_text('example.com\n')
            (managed / 'hostlist-alias.txt').symlink_to('hostlist-user.txt')
            (static / 'other.txt').write_text('example.org\n')
            host = f'--hostlist={reference}/managed/hostlist-user.txt'
            alias = f'--hostlist={reference}/managed/hostlist-alias.txt'
            other = f'--hostlist={reference}/managed/hostlist-youtube.txt'
            ipset = f'--ipset={reference}/managed/ipset-telegram.txt'
            excluded = f'--hostlist-exclude={reference}/managed/hostlist-user.txt'
            ip_exclude = f'--ipset-exclude={reference}/managed/ipset-exclude.txt'
            cases = (
                (f'--filter-tcp=80,443 --filter-l7=http,tls {host} '
                 '--payload=tls_client_hello --lua-desync=fake '
                 '--payload=http_req --lua-desync=multisplit', None),
                (f'{host} {host}', 'DUPLICATE_RESOLVED_LIST profile=1 option=--hostlist'),
                (f'{host} --extra=anything {alias}', 'DUPLICATE_RESOLVED_LIST'),
                (f'{host} --new --filter-tcp=80 {host}', None),
                (f'{host} --new=other-tcp {alias}', None),
                (f'{host} {other} {ipset} {excluded}', None),
                (f'{ipset} {ipset}', 'DUPLICATE_RESOLVED_LIST'),
                (f'{host} {excluded}', None),
                (f'{host} --new=voice-stun {ip_exclude} --new {ip_exclude}', None),
                (f'--hostlist={static}/other.txt --hostlist={static}/./other.txt',
                 'DUPLICATE_RESOLVED_LIST'),
                (f'--hostlist={reference}/managed/missing.txt', 'LIST_REFERENCE_UNSAFE'),
                ('--hostlist=relative/path', 'LIST_REFERENCE_INVALID'),
            )
            for text, failure in cases:
                with self.subTest(args=text, failure=failure):
                    if failure:
                        with self.assertRaisesRegex(policy.ProfilePolicyError, failure):
                            policy.check_resolved_lists(text.encode(), static, reference, release)
                    else:
                        policy.check_resolved_lists(text.encode(), static, reference, release)
            (managed / 'outside.txt').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(policy.ProfilePolicyError, 'LIST_REFERENCE_UNSAFE'):
                policy.check_resolved_lists(
                    f'--hostlist={reference}/managed/outside.txt'.encode(),
                    static, reference, release)
            argsfile = root / 'dvtws.args'
            argsfile.write_text(f'{host}\n{alias}\n')
            before = argsfile.read_bytes()
            argv = [str(argsfile), str(static), str(reference), str(release)]
            cli = subprocess.run([sys.executable, str(FILE), 'check-lists', *argv],
                                 capture_output=True, text=True)
            self.assertNotEqual(cli.returncode, 0)
            self.assertIn('DUPLICATE_RESOLVED_LIST', cli.stderr)
            validator = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/backend/validator.sh'
            environment = dict(os.environ, PYTHON_RUNTIME=sys.executable,
                               BACKEND_DIR=str(FILE.parent))
            shell = subprocess.run(
                ['sh', '-c', '. "$1"; shift; validator_check_resolved_lists "$@"',
                 'sh', str(validator), *argv],
                env=environment, capture_output=True, text=True)
            self.assertNotEqual(shell.returncode, 0)
            self.assertIn('DUPLICATE_RESOLVED_LIST', shell.stderr)
            self.assertEqual(argsfile.read_bytes(), before)
            argsfile.write_text(f'{host}\n--new=second\n{alias}\n')
            success = subprocess.run(
                ['sh', '-c', '. "$1"; shift; validator_check_resolved_lists "$@"',
                 'sh', str(validator), *argv],
                env=environment, capture_output=True, text=True)
            self.assertEqual(success.returncode, 0, success.stderr)


    def test_mapped_generator_validator_a06_to_a09(self):
        """Actual mapped generator + full validator; never touches live Apply."""
        backend = FILE.parent
        common = backend / 'common.sh'
        ports = backend / 'ports.sh'
        generator = backend / 'generator.sh'
        validator = backend / 'validator.sh'
        with tempfile.TemporaryDirectory(prefix='profile-mapped-integration-') as tmp:
            root = Path(tmp)
            static = root / 'static'
            source = root / 'source'
            managed = source / 'managed'
            reference = root / 'future-active-release'
            static.mkdir()
            managed.mkdir(parents=True)
            lua = static / 'test.lua'
            lua.write_text('return true\n')
            for name, value in (
                ('hostlist-user.txt', 'example.com\n'),
                ('hostlist-youtube.txt', 'youtube.com\n'),
                ('ipset-telegram.txt', '149.154.160.0/20\n'),
                ('hostlist-exclude.txt', 'blocked.example\n'),
                ('ipset-exclude.txt', '10.0.0.0/8\n'),
            ):
                (managed / name).write_text(value)
            (managed / 'hostlist-alias.txt').symlink_to('hostlist-user.txt')
            host = f'--hostlist={reference}/managed/hostlist-user.txt'
            alias = f'--hostlist={reference}/managed/hostlist-alias.txt'
            other = f'--hostlist={reference}/managed/hostlist-youtube.txt'
            ipset = f'--ipset={reference}/managed/ipset-telegram.txt'
            domain_exclude = f'--hostlist-exclude={reference}/managed/hostlist-exclude.txt'
            ip_exclude = f'--ipset-exclude={reference}/managed/ipset-exclude.txt'
            args_file = source / 'dvtws.args'
            traffic_file = source / 'traffic-user.conf'
            extra_file = source / 'extra.conf'
            blobs = source / 'blob-args.conf'
            exclude_source = source / 'exclude-source.txt'
            tcp_file = source / 'tcp-ports.txt'
            udp_file = source / 'udp-ports.txt'
            blobs.write_text('')
            exclude_source.write_text('')
            tcp_file.write_text('80,443\n')
            udp_file.write_text('')
            environment = dict(os.environ, BACKEND_DIR=str(backend), PYTHON_RUNTIME=sys.executable)
            source_prefix = ['sh', '-c', '. "$1"; . "$2"; . "$3"; . "$4"; shift 4; ']
            shell_paths = ['sh', str(common), str(ports), str(generator), str(validator)]
            paths = [str(args_file), str(traffic_file), str(tcp_file), str(udp_file),
                     str(static), str(reference), str(source)]
            user_profile = '\n'.join((
                '--filter-tcp=80,443', '--filter-l7=http,tls', host,
                '--out-range=-d10', '--payload=tls_client_hello',
                '--lua-desync=fake:blob=fake_default_tls',
                '--payload=http_req', '--lua-desync=multisplit:pos=method+2',
            )) + '\n'

            def run(candidate: str, extra: str, *, tcp: str = '80,443',
                    expect: str | None = None, python: str | None = None) -> str:
                traffic_file.write_text(candidate)
                extra_file.write_text(extra)
                tcp_file.write_text(tcp + '\n')
                generator_call = subprocess.run(
                    source_prefix[:-1] + [source_prefix[-1] + 'generator_build_args_mapped "$@"',
                    *shell_paths, str(args_file), '989', str(traffic_file), str(extra_file),
                    str(blobs), str(exclude_source), f'{reference}/managed/hostlist-exclude.txt',
                    str(lua)], capture_output=True, text=True, env=environment)
                self.assertEqual(generator_call.returncode, 0, generator_call.stderr)
                generated = args_file.read_bytes()
                snapshots = {path: path.read_bytes() for path in
                             (args_file, traffic_file, extra_file, tcp_file, udp_file,
                              managed / 'hostlist-user.txt', managed / 'ipset-exclude.txt')}
                current_env = dict(environment)
                if python is not None:
                    current_env['PYTHON_RUNTIME'] = python
                check = subprocess.run(
                    source_prefix[:-1] + [source_prefix[-1] + 'validator_validate_build_mapped "$@"',
                    *shell_paths, *paths], capture_output=True, text=True, env=current_env)
                if expect is None:
                    self.assertEqual(check.returncode, 0, check.stderr)
                else:
                    self.assertNotEqual(check.returncode, 0, generated.decode('utf-8'))
                    self.assertIn(expect, check.stderr)
                for path, original in snapshots.items():
                    self.assertEqual(path.read_bytes(), original, f'validator modified {path.name}')
                return generated.decode('utf-8')

            with self.subTest(case='A08 one profile two payload+Lua actions'):
                result = run(user_profile, '')
                self.assertLess(result.index('--payload=tls_client_hello'),
                                result.index('--payload=http_req'))
                self.assertEqual(result.count('--lua-desync='), 2)
            with self.subTest(case='A06 duplicate supplied through Extra Arguments'):
                run(user_profile, host + '\n', expect='DUPLICATE_RESOLVED_LIST profile=1')
            with self.subTest(case='A06 symlink alias supplied through Extra Arguments'):
                run(user_profile, alias + '\n', expect='DUPLICATE_RESOLVED_LIST profile=1')
            with self.subTest(case='A06 different files allowed'):
                run(user_profile, other + '\n')
            with self.subTest(case='A07 A09 two distinct profiles share HOSTLIST'):
                two = (f'--filter-tcp=80\n{host}\n--new=named-tls\n'
                       f'--filter-tcp=443\n{host}\n')
                text = run(two, '', tcp='80,443')
                self.assertLess(text.index('--filter-tcp=80'), text.index('--new=named-tls'))
                self.assertLess(text.index('--new=named-tls'), text.index('--filter-tcp=443'))
            with self.subTest(case='Extra Arguments belong to last named profile'):
                two = (f'--filter-tcp=80\n{host}\n--new=named-tls\n'
                       f'--filter-tcp=443\n{host}\n')
                run(two, host + '\n', tcp='80,443',
                    expect='DUPLICATE_RESOLVED_LIST profile=2 option=--hostlist')
            with self.subTest(case='separate global collections across profiles'):
                two = (f'--filter-tcp=80,443\n{host}\n{domain_exclude}\n{ip_exclude}\n'
                       f'--new\n--filter-tcp=443\n{host}\n{domain_exclude}\n{ip_exclude}\n')
                run(two, '', tcp='80,443')
            with self.subTest(case='include and exclude independently scoped'):
                run(user_profile, domain_exclude + '\n' + ip_exclude + '\n')
            with self.subTest(case='IPSET duplicate at end of same profile'):
                run(user_profile + ipset + '\n', ipset + '\n',
                    expect='DUPLICATE_RESOLVED_LIST profile=1 option=--ipset')
            with self.subTest(case='qualified Python unavailable must fail closed'):
                run(user_profile, '', expect='PROFILE_POLICY_UNAVAILABLE',
                    python=str(root / 'missing-python'))

    def test_native_validation_wiring_precedes_activation(self):
        """Source-order contract, not a claim of an actual engine dry-run."""
        orchestrator = (FILE.parent / 'orchestrator.sh').read_text()
        start = orchestrator.index('    validator_validate_build_mapped \\')
        audit = orchestrator.index('    generator_apply_final_exclusions audit \\', start)
        native = orchestrator.index('        validator_validate_engine_mapped \\', audit)
        ready = orchestrator.index('        ready ok "release build is ready"', native)
        self.assertLess(start, audit)
        self.assertLess(audit, native)
        self.assertLess(native, ready)

if __name__ == '__main__':
    unittest.main()
