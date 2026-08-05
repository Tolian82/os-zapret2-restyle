#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"

grep -Fq 'function renderResultSummary(data)' "${VIEW}"
grep -Fq "item.profile || item.strategy" "${VIEW}"
grep -Fq 'item.protocol' "${VIEW}"
grep -Fq 'item.port' "${VIEW}"
grep -Fq 'function endpointText(item)' "${VIEW}"
grep -Fq 'item.profile_replay' "${VIEW}"
grep -Fq 'strategyLabCopyProfile' "${VIEW}"
grep -Fq 'navigator.clipboard.writeText' "${VIEW}"
grep -Fq "document.execCommand('copy')" "${VIEW}"
grep -Fq 'renderedProfiles[Number' "${VIEW}"
grep -Fq 'id="strategyLabResultBox"' "${VIEW}"
grep -Fq 'id="strategyLabResultTarget"' "${VIEW}"
grep -Fq 'id="strategyLabResultOutcome"' "${VIEW}"
grep -Fq 'id="strategyLabResultRestoration"' "${VIEW}"
grep -Fq "lang._('Complete Traffic Strategy profile')" "${VIEW}"
if grep -Fq 'data-profile=' "${VIEW}"; then
    echo 'FAIL: profile bytes must not be embedded in HTML data attributes' >&2
    exit 1
fi
echo 'PASS: terminal results expose structured evidence and safe complete-profile copy controls'
