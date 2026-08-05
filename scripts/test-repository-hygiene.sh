#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GITIGNORE="${ROOT_DIR}/.gitignore"
CI="${ROOT_DIR}/.github/workflows/ci.yml"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

tracked=$(git -C "${ROOT_DIR}" ls-files)
bad=$(printf '%s\n' "${tracked}" | grep -E '(^|/)([^/]+\.(orig|rej|patch|diff|b64|base64|bak)|[^/]+\.part-[0-9]+|[^/]+~)$' || true)
[ -z "${bad}" ] || {
    printf '%s\n' 'Forbidden tracked repository artifacts:' >&2
    printf '%s\n' "${bad}" >&2
    exit 1
}

[ ! -e "${ROOT_DIR}/docs/PROJECT_STATE.md.orig" ] || fail 'stale PROJECT_STATE backup is tracked'

for pattern in '*.orig' '*.rej' '*.patch' '*.diff' '*.b64' '*.base64' '*.bak' '*.part-*' '*~'
do
    grep -Fqx "${pattern}" "${GITIGNORE}" || fail "missing ignore rule: ${pattern}"
done

grep -Fq 'Version line: **0.3.x**' "${ROOT_DIR}/docs/REQUIREMENTS.md" || fail 'requirements version line is stale'
grep -Fq 'Corrective Patches 1–11 are complete in source' "${ROOT_DIR}/docs/PROJECT_STATE.md" || fail 'project state does not close the corrective source series'
grep -Fq 'Historical delivery record' "${ROOT_DIR}/docs/audit/DIAG-001-strategy-lab.md" || fail 'historical DIAG record has no authority banner'
grep -Fq 'scripts/test-repository-hygiene.sh' "${CI}" || fail 'repository hygiene test is not wired into CI'

echo 'Repository artifact and documentation authority hygiene tests passed.'
