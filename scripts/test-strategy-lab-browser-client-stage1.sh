#!/bin/sh
set -eu

# No external network or client download in this lightweight source contract.
# The FreeBSD package job performs the actual signed fetch and ELF execution.
grep -Fq 'scripts/build-private-curl-impersonate.sh' scripts/build-pkg.sh
grep -Fq 'signature_type: "fingerprints"' scripts/build-private-curl-impersonate.sh
grep -Fq 'profile="chrome${profile_number}"' scripts/build-private-curl-impersonate.sh
grep -Fq 'libcurl-impersonate.so' scripts/build-private-curl-impersonate.sh
grep -Fq -- '--impersonate "${profile}"' scripts/build-private-curl-impersonate.sh
grep -Fq 'BrowserClientUnavailable' src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/browser_client.py
python3 -m py_compile src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/browser_client.py
echo "PASS: Stage-1 private Chrome client source and packaging contract"
