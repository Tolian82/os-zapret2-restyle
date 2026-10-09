#!/usr/bin/env python3
"""Differential acceptance test: native GUI PHP validator vs backend Python compiler.

Only validates syntax acceptance parity, not an installed dvtws2 or live IPFW.
Runs both parsers on the same form data. PHP is invoked as a subprocess with
JSON stdin, without shell or live config.xml interactions.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parent.parent
BACKEND=ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
PHP_FILE=ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateValidator.php"
sys.path.insert(0,str(BACKEND))
from voice_profile_compiler import compile_candidate, VoiceConfigurationError

PHP_SCRIPT = (
    "require_once $argv[1]; "
    "$data=json_decode(stream_get_contents(STDIN),true); "
    "$errors=\\OPNsense\\Zapret\\Api\\VoiceCandidateValidator::check($data);"
    "echo json_encode($errors,JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);"
)
ARGS="--filter-udp=596-599\n--filter-l7=stun\n--payload=stun\n"
FAKE="--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2"

def form():
    voice={'waninterface':'WAN'}
    targets={}
    for name in ('telegram','discord','x','sip','custom'):
        voice[name]={'enabled':'0','args':''}
        targets[name+'ips']=''
    return {'voice':voice,'hostlist':targets}

def enabled(data,name='telegram',args=ARGS,ips='91.108.0.0/16'):
    data['voice'][name]={'enabled':'1','args':args}
    data['hostlist'][name+'ips']=ips
    return data

def python_accepts(data):
    state={
        'strategy_wan':'WAN',
        'voice_wan':data['voice'].get('waninterface',''),
        'services':{
            name:{
                'enabled':data['voice'][name]['enabled']=='1',
                'args':data['voice'][name]['args'],
                'ips':data['hostlist'][name+'ips'],
            }
            for name in ('telegram','discord','x','sip','custom')
        }
    }
    try:
        compile_candidate(state,Path("/usr/local/etc/zapret2/runtime-v2/managed"))
        return True
    except (VoiceConfigurationError,ValueError):
        return False

class ParserParity(unittest.TestCase):
    def compare(self,data,label):
        proc=subprocess.run(
            ['php','-r',PHP_SCRIPT,str(PHP_FILE)],
            input=json.dumps(data),capture_output=True,text=True,check=False
        )
        self.assertEqual(0,proc.returncode,proc.stderr)
        errors=json.loads(proc.stdout)
        self.assertIsInstance(errors,dict)
        self.assertEqual(not bool(errors),python_accepts(data),
                         f"{label}: Python/PHP validator divergence: {errors}")

    def test_allowed_and_rejected_cases_in_both_parsers(self):
        cases=[
            ('OFF',form()),
            ('Telegram',enabled(form())),
            ('Telegram fake TTL',enabled(form(),args=ARGS+FAKE+':ip_ttl=3')),
            ('Telegram fake fragmentation',enabled(form(),args=ARGS+FAKE+':ipfrag:ipfrag_pos_udp=8')),
            ('Telegram badsum',enabled(form(),args=ARGS+FAKE+':badsum')),
            ('Telegram out-range',enabled(form(),args=ARGS+'--out-range=n1-n10\n'+FAKE)),
            ('invalid CIDR',enabled(form(),ips='91.108.13.10/24')),
            ('invalid IPv6',enabled(form(),ips='2001:db8::1')),
            ('missing IPSET',enabled(form(),ips='')),
            ('repeated -l7',enabled(form(),args=ARGS+'--filter-l7=stun\n')),
            ('illegal shell',enabled(form(),args=ARGS+'--new\n')),
            ('fake duplicated options',enabled(form(),args=ARGS+FAKE+':ip_ttl=3:ip_ttl=4')),
            ('out of bounds ports',enabled(form(),args=ARGS.replace('596-599','65536'))),
            ('fake fragment too far',enabled(form(),args=ARGS+FAKE+':ipfrag:ipfrag_pos_udp=4096')),
            ('fake badsum frag conflict',enabled(form(),args=ARGS+FAKE+':ipfrag:badsum')),
        ]
        both=enabled(form(),name='telegram',args=ARGS,ips='91.108.0.0/16')
        both=enabled(both,name='discord',args=ARGS,ips='91.108.13.10')
        cases.append(('overlapping UDP/IP',both))
        both=enabled(form(),name='telegram',args=ARGS,ips='91.108.0.0/16')
        both=enabled(both,name='discord',args=ARGS.replace('596-599','20000'),ips='91.108.13.10')
        cases.append(('disjoint UDP',both))
        for label,data in cases:
            with self.subTest(label=label):
                self.compare(data,label)

if __name__ == '__main__':
    unittest.main(verbosity=2)
