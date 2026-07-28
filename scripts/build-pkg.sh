#!/bin/sh
# Build a FreeBSD package for os-zapret2-restyle.
#
# VERSION is the single source of the project version.
# Output: dist/os-zapret2-restyle-<version>[_revision].pkg

set -eu

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "${REPO_ROOT}"

fail()
{
    echo "ERROR: $*" >&2
    exit 1
}

get_make_var()
{
    sed -n "s/^${1}=[[:space:]]*\(.*\)$/\1/p" Makefile |
        head -1 |
        sed 's/[[:space:]]*$//'
}

read_version()
{
    [ -f VERSION ] || fail "VERSION file is missing"

    version=$(tr -d '[:space:]' < VERSION)
    case "${version}" in
        ''|*[!0-9.]*|.*|*..*|*.)
            fail "invalid VERSION value '${version}'"
            ;;
    esac

    old_ifs=${IFS}
    IFS=.
    set -- ${version}
    IFS=${old_ifs}
    [ "$#" -eq 3 ] || fail "VERSION must use MAJOR.MINOR.PATCH"
    for component in "$@"; do
        case "${component}" in
            ''|*[!0-9]*)
                fail "VERSION must use numeric MAJOR.MINOR.PATCH"
                ;;
        esac
    done

    printf '%s\n' "${version}"
}

command -v jq >/dev/null 2>&1 || fail "jq is required"
command -v pkg-static >/dev/null 2>&1 || fail "pkg-static is required"

PLUGIN_NAME=$(get_make_var PLUGIN_NAME)
PLUGIN_REVISION=$(get_make_var PLUGIN_REVISION)
PLUGIN_COMMENT=$(get_make_var PLUGIN_COMMENT)
PLUGIN_MAINTAINER=$(get_make_var PLUGIN_MAINTAINER)
PLUGIN_DEPENDS=$(get_make_var PLUGIN_DEPENDS)
PLUGIN_LICENSE=$(get_make_var PLUGIN_LICENSE)
PLUGIN_VERSION=$(read_version)

[ "${PLUGIN_NAME}" = "zapret2-restyle" ] ||
    fail "PLUGIN_NAME must be zapret2-restyle"

PKG_NAME="os-${PLUGIN_NAME}"
[ "${PKG_NAME}" = "os-zapret2-restyle" ] ||
    fail "unexpected package name '${PKG_NAME}'"

if [ -n "${PLUGIN_REVISION}" ] && [ "${PLUGIN_REVISION}" != "0" ]; then
    FULL_VERSION="${PLUGIN_VERSION}_${PLUGIN_REVISION}"
else
    FULL_VERSION="${PLUGIN_VERSION}"
fi

echo "==> Building ${PKG_NAME}-${FULL_VERSION}"

STAGE="${REPO_ROOT}/work/stage"
rm -rf "${REPO_ROOT}/work"
mkdir -p "${STAGE}/usr/local"

cp -R src/opnsense "${STAGE}/usr/local/opnsense"
if [ -d src/etc ]; then
    cp -R src/etc "${STAGE}/usr/local/etc"
fi

find "${STAGE}" -type f -name "*.sh" -exec chmod 755 {} +
find "${STAGE}" -type f -name "zapret" -path "*/rc.d/*" -exec chmod 755 {} +
if [ -d "${STAGE}/usr/local/etc/rc.syshook.d" ]; then
    find "${STAGE}/usr/local/etc/rc.syshook.d" -type f -exec chmod 755 {} +
fi

PLIST="${REPO_ROOT}/work/pkg-plist"
(
    cd "${STAGE}"
    find usr \( -type f -o -type l \)
) | sed 's|^|/|' | sort > "${PLIST}"

[ -s "${PLIST}" ] || fail "empty plist; nothing was staged"
echo "==> plist: $(wc -l < "${PLIST}" | tr -d ' ') entries"

DESC_JSON=$(jq -Rs . < pkg-descr)
POST_INSTALL_JSON=$(jq -Rs . < pkg/+POST_INSTALL)
PRE_DEINSTALL_JSON=$(jq -Rs . < pkg/+PRE_DEINSTALL)
POST_DEINSTALL_JSON=$(jq -Rs . < pkg/+POST_DEINSTALL)

dep_origin()
{
    case "$1" in
        luajit) echo "lang/luajit" ;;
        jq)     echo "textproc/jq" ;;
        git)    echo "devel/git" ;;
        *)      echo "$1" ;;
    esac
}

DEPS_ENTRIES=""
for dep in ${PLUGIN_DEPENDS}; do
    [ -n "${dep}" ] || continue
    origin=$(dep_origin "${dep}")
    if [ -n "${DEPS_ENTRIES}" ]; then
        DEPS_ENTRIES="${DEPS_ENTRIES},"
    fi
    DEPS_ENTRIES="${DEPS_ENTRIES}\"${dep}\":{\"origin\":\"${origin}\",\"version\":\"0\"}"
done
DEPS="{${DEPS_ENTRIES}}"
echo "==> deps: ${DEPS}"

MANIFEST="${REPO_ROOT}/work/+MANIFEST"
jq -n \
    --arg name "${PKG_NAME}" \
    --arg version "${FULL_VERSION}" \
    --arg origin "opnsense/${PKG_NAME}" \
    --arg comment "${PLUGIN_COMMENT}" \
    --arg maintainer "${PLUGIN_MAINTAINER}" \
    --arg www "https://github.com/Tolian82/os-zapret2-restyle" \
    --arg license "${PLUGIN_LICENSE}" \
    --argjson desc "${DESC_JSON}" \
    --argjson deps "${DEPS}" \
    --argjson post_install "${POST_INSTALL_JSON}" \
    --argjson pre_deinstall "${PRE_DEINSTALL_JSON}" \
    --argjson post_deinstall "${POST_DEINSTALL_JSON}" \
    '{
        name: $name,
        version: $version,
        origin: $origin,
        comment: $comment,
        maintainer: $maintainer,
        www: $www,
        prefix: "/usr/local",
        desc: $desc,
        categories: ["opnsense", "security"],
        licenselogic: "single",
        licenses: [$license],
        deps: $deps,
        scripts: {
            "post-install": $post_install,
            "pre-deinstall": $pre_deinstall,
            "post-deinstall": $post_deinstall
        }
    }' > "${MANIFEST}"

echo "==> +MANIFEST written to ${MANIFEST}"

OUT="${REPO_ROOT}/dist"
rm -rf "${OUT}"
mkdir -p "${OUT}"

pkg-static create \
    -M "${MANIFEST}" \
    -p "${PLIST}" \
    -r "${STAGE}" \
    -o "${OUT}"

EXPECTED="${OUT}/${PKG_NAME}-${FULL_VERSION}.pkg"
[ -f "${EXPECTED}" ] ||
    fail "expected package was not created: ${EXPECTED}"

echo "==> built:"
ls -lh "${EXPECTED}"
