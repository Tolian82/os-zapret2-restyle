#!/bin/sh
# Isolated negative/positive contract for setup.sh native package ownership.
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SETUP="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/setup.sh"
MAKEFILE="${ROOT_DIR}/Makefile"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/zapret-native-deps.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT INT TERM HUP

fail() { echo "FAIL: $*" >&2; exit 1; }
sh -n "${SETUP}"

# A package may be provisioned only through native Makefile PLUGIN_DEPENDS.
deps=$(sed -n 's/^PLUGIN_DEPENDS=[[:space:]]*//p' "${MAKEFILE}")
for name in gmake pkgconf luajit git jq ca_root_nss; do
    case " ${deps} " in *" ${name} "*) ;; *) fail "Makefile missing ${name}" ;; esac
done
grep -Fq 'verify_stock_freebsd_repository || return $?' "${SETUP}" || fail "missing pre-mutation repository check"
grep -Fq 'verify_native_dependencies || return $?' "${SETUP}" || fail "missing pre-mutation dependency check"
grep -Fq 'pkg info -q "${_native_dep}"' "${SETUP}" || fail "missing native installed-package verification"
if grep -Eq 'pkg[[:space:]]+(install|update)|enable_freebsd_repo_temporarily|restore_freebsd_repo|install_dep[[:space:]]*\(' "${SETUP}"; then
    fail "setup still installs system packages or mutates FreeBSD repository"
fi

# Extract only pure/read-only helpers: do not invoke actual setup, pkg, git,
# configd, lockf or engine operations on the CI runner.
awk '
/^verify_stock_freebsd_repository\(\)$/ { on=1 }
/^verify_native_dependencies\(\)$/ { on=1 }
on { print }
on && /^}$/ { on=0 }
' "${SETUP}" > "${TMP}/helpers.sh"
grep -Fq 'verify_native_dependencies()' "${TMP}/helpers.sh" || fail "helper extraction failed"
grep -Fq 'verify_stock_freebsd_repository()' "${TMP}/helpers.sh" || fail "repository helper extraction failed"
sh -n "${TMP}/helpers.sh"

BIN="${TMP}/bin"
mkdir -p "${BIN}"
ln -s "$(command -v grep)" "${BIN}/grep"
for tool in gmake pkgconf luajit git jq; do
    printf '#!/bin/sh\nexit 0\n' > "${BIN}/${tool}"
    chmod +x "${BIN}/${tool}"
done
cat > "${BIN}/pkg" <<'MOCK'
#!/bin/sh
printf '%s\n' "$*" >> "${MOCK_PKG_LOG}"
[ "$#" -eq 3 ] && [ "$1" = info ] && [ "$2" = -q ] || exit 77
[ "${MOCK_PKG_FAIL:-}" != "$3" ] || exit 1
exit 0
MOCK
chmod +x "${BIN}/pkg"

REPO="${TMP}/FreeBSD.conf"
BACKUP="${TMP}/FreeBSD.conf.backup"
LOG="${TMP}/pkg.log"
STDERR="${TMP}/stderr"
printf 'FreeBSD-ports: { enabled: no }\n' > "${REPO}"

verify()
{
    PATH="${BIN}" MOCK_PKG_LOG="${LOG}" MOCK_PKG_FAIL="${MOCK_PKG_FAIL:-}" \
        FREEBSD_REPO_OVERRIDE="${REPO}" FREEBSD_REPO_BACKUP="${BACKUP}" \
        /bin/sh -c '. "$1"; verify_stock_freebsd_repository && verify_native_dependencies' \
        sh "${TMP}/helpers.sh"
}

verify 2> "${STDERR}" || fail "normal native dependency preflight refused"
[ "$(wc -l < "${LOG}" | tr -d ' ')" -eq 6 ] || fail "expected exactly six native package queries"
! grep -Ev '^info -q (gmake|pkgconf|luajit|git|jq|ca_root_nss)$' "${LOG}" | grep -q . || fail "unexpected pkg command"

MOCK_PKG_FAIL=jq
if verify 2> "${STDERR}"; then fail "missing OPNsense dependency accepted"; fi
grep -Fq 'missing OPNsense package jq' "${STDERR}" || fail "missing actionable package diagnostic"
unset MOCK_PKG_FAIL

mv "${BIN}/jq" "${TMP}/jq-disabled"
if verify 2> "${STDERR}"; then fail "missing executable accepted"; fi
grep -Fq 'has no executable in PATH' "${STDERR}" || fail "missing executable diagnostic"
mv "${TMP}/jq-disabled" "${BIN}/jq"

# Commented references must not be treated as an enabled repository.
printf '# enabled: yes\nFreeBSD-ports: { enabled: no }\n' > "${REPO}"
verify 2> "${STDERR}" || fail "commented-out repo enable was rejected"

printf 'FreeBSD-ports: { enabled: yes }\n' > "${REPO}"
BEFORE=$(cat "${REPO}")
if verify 2> "${STDERR}"; then fail "enabled stock FreeBSD repository accepted"; fi
grep -Fq 'stock FreeBSD repository is enabled' "${STDERR}" || fail "missing repository diagnostic"
[ "$(cat "${REPO}")" = "${BEFORE}" ] || fail "repository file modified by refusal"

printf 'FreeBSD-ports: { enabled: no }\n' > "${REPO}"
printf '%s\n' historical-admin-backup > "${BACKUP}"
if verify 2> "${STDERR}"; then fail "ambiguous legacy backup accepted"; fi
grep -Fq 'legacy FreeBSD repository backup remains' "${STDERR}" || fail "missing backup diagnostic"
[ "$(cat "${BACKUP}")" = historical-admin-backup ] || fail "legacy backup was modified"
[ "$(cat "${REPO}")" = 'FreeBSD-ports: { enabled: no }' ] || fail "repo was modified while backup exists"

echo 'PASS: native OPNsense pkg owns dependencies; missing package/tool or legacy FreeBSD repo state refuses without package/repository mutation'
