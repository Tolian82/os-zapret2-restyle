#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"

for file in \
    "${MODULE_DIR}/firewall.sh" \
    "${MODULE_DIR}/extended_runtime.sh" \
    "${MODULE_DIR}/quic_candidate.sh" \
    "${MODULE_DIR}/udp_candidate.sh"
do
    grep -Eq '(tcp|udp) from me to ' "${file}"
    if grep -Eq '(tcp|udp) from any to ' "${file}"; then
        echo "automatic Strategy Lab rule remains client-wide: ${file}" >&2
        exit 1
    fi
done

grep -Eq 'tcp from any to ' "${MODULE_DIR}/circular.sh"
grep -Eq 'tcp from .* 443 to any in ' "${MODULE_DIR}/circular.sh"

echo 'PASS: automated Strategy Lab rules are local-only while circular validation remains client-wide'
