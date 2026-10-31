#!/usr/bin/env python3
"""Execute real candidate probe and curl argv builders without network/OPNsense.

AST selects the production functions, not a copied implementation. Strict
command and evidence assertions catch a hidden --ipv4 on IPv6 Stage50/85.
"""
from __future__ import annotations

import ast
import ipaddress
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py'


def own_function(path: Path, name: str, globals_: dict):
    node = next(node for node in ast.parse(path.read_text(encoding='utf-8')).body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = dict(globals_)
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[name]


class UsageError(Exception):
    pass


class FakeResult:
    def __init__(self, command, ip: str):
        self.command = command
        self.stdout = f'exit=0 remote_ip={ip} http=2 code=200 bytes=0 ssl_verify=0 appconnect=0.15\n'
        self.returncode = 0
        self.timed_out = False

    def evidence(self):
        return {'command': self.command, 'stdout': self.stdout, 'returncode': 0}


class FakeRequest:
    def __init__(self, curl_builder):
        self.curl_builder = curl_builder
        self.calls = []

    def curl_request(self, host, *, scheme, family='ipv4', tls_version=None, bound_ip=None):
        args = self.curl_builder(host, scheme=scheme, family=family,
                                 tls_version=tls_version, bound_ip=bound_ip)
        self.calls.append((host, family, scheme, bound_ip, args))
        return FakeResult(args, bound_ip)

    @staticmethod
    def curl_exit(value):
        return value.returncode

    @staticmethod
    def chrome_https_evidence(value, *, expected_ip):
        assert f'remote_ip={expected_ip} ' in value.stdout
        return {'accessible': True, 'remote_ip': expected_ip}

    @staticmethod
    def chrome_http_evidence(value, *, expected_ip):
        return FakeRequest.chrome_https_evidence(value, expected_ip=expected_ip)

    @staticmethod
    def chrome_quic_evidence(value, *, expected_ip):
        return {'accessible': False, 'reason': 'unsupported'}


class ProtocolSpec:
    def __init__(self, protocol, transport, port, l7):
        self.protocol, self.transport, self.port, self.l7 = protocol, transport, port, l7
        self.payload_path = None


def run():
    curl_builder = own_function(
        PKG / 'request.py', '_curl_command',
        {'ipaddress': ipaddress, 'UsageError': UsageError, 'binary': lambda _: 'stub-curl'},
    )
    fake = FakeRequest(curl_builder)
    counts = iter([(0, 0), (1, 128)] * 12)
    probe = own_function(
        PKG / 'candidate.py', '_probe_endpoint',
        {'Any': object, 'ProtocolSpec': ProtocolSpec, 'request': fake,
         '_counter': lambda _: next(counts), '_is_ipv4': lambda addr: (
             ipaddress.ip_address(addr).version == 4 if addr != 'name.test' else False),
         '_execution_status': lambda x: x.returncode, '_detail': lambda _: '',
         '_remote_ip': lambda x: x.split('remote_ip=')[1].split()[0],
         '_unsupported_execution': lambda msg: FakeResult([], ''),
         },
    )
    cases = [
        ('name.test', '198.51.100.10', 'tls13', 'https', 'ipv4'),
        ('name.test', '2001:db8::10', 'tls13', 'https', 'ipv6'),
        ('2001:db8::10', '2001:db8::10', 'tls13', 'https', 'ipv6'),
        ('name.test', '2001:db8::10', 'tls12', 'https', 'ipv6'),
        ('name.test', '2001:db8::10', 'http', 'http', 'ipv6'),
    ]
    for endpoint, selected, protocol, scheme, family in cases:
        result = probe({'endpoint': endpoint, 'selected_ip': selected, 'rule': 19100},
                       ProtocolSpec(protocol, 'tcp', 443 if scheme == 'https' else 80, 'tls'))
        _, observed_family, observed_scheme, pin, argv = fake.calls[-1]
        assert (observed_family, observed_scheme, pin) == (family, scheme, selected)
        assert f'--{family}' in argv
        assert f'--{"ipv4" if family == "ipv6" else "ipv6"}' not in argv
        if family == 'ipv6' and endpoint == 'name.test':
            assert '--resolve' in argv
            assert f'name.test:{443 if scheme == "https" else 80}:[2001:db8::10]' in argv
        if family == 'ipv6' and ':' in endpoint:
            assert 'https://[2001:db8::10]/' in argv
        assert result['status'] == 'PASS' and result['firewall']['intercepted'] is True
        assert result['endpoint_match'] is True
        assert result['transport'].endswith('-' + family), result['transport']
    # A bound family mismatch must stay a strict error; do not let the
    # command-builder silently fall back to an alternate family.
    for actual_family in ('ipv4', 'ipv6'):
        wrong = '2001:db8::10' if actual_family == 'ipv4' else '198.51.100.10'
        try:
            curl_builder('name.test', scheme='https', family=actual_family, bound_ip=wrong)
        except UsageError:
            pass
        else:
            raise AssertionError('curl accepted mismatched family and pinned address')
    # Optional QUIC is IPv4-only; attempting a selected AAAA must explicitly
    # remain unavailable, never invoke the unsupported engine or claim PASS.
    rejected = probe({'endpoint': 'name.test', 'selected_ip': '2001:db8::10', 'rule': 19100},
                     ProtocolSpec('quic', 'udp', 443, 'quic'))
    assert rejected['status'] == 'FAIL' and rejected['exit_code'] == 64
    assert rejected['transport'] == 'quic-ipv6-unavailable'
    print('PASS: Stage50/85 real candidate probe chooses pinned IPv4/IPv6 curl and rejects wrong-family/unsupported QUIC')


if __name__ == '__main__':
    run()
