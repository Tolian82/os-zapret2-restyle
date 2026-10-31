#!/bin/sh
# Stage 0 platform witness. No updates/install/restart/Config/IPFW changes.
# Output contains versions, package origins, file metadata and digests only.
set -u

say() { printf '%s\n' "$*"; }
run()
{
    (
        _name="$1"; shift
        say "=== ${_name} ==="
        if ! command -v "$1" >/dev/null 2>&1; then
            say "UNAVAILABLE: $1"
            return 0
        fi
        "$@" 2>&1 || say "UNVERIFIED: ${_name} returned nonzero"
    )
}
file_report()
{
    _name="$1"
    _path="$2"
    say "=== FILE ${_name} ==="
    if [ -e "$_path" ] || [ -L "$_path" ]; then
        run "stat ${_name}" stat -f '%Sp|%Su|%Sg|%z|%N' "$_path"
        if [ -L "$_path" ]; then
            run "readlink ${_name}" readlink "$_path"
        fi
        if [ -f "$_path" ]; then
            run "sha256 ${_name}" sha256 -q "$_path"
        fi
        if command -v pkg >/dev/null 2>&1; then
            run "pkg owner ${_name}" pkg which "$_path"
        fi
    else
        say 'ABSENT'
    fi
}

say 'STAGE0_TARGET_PROBE=READ_ONLY'
say 'SCOPE=identity,installed and cached remote packages, interpreter owner, ELF and repository-override metadata'
run 'OPNsense product ABI' opnsense-version -a
run 'OPNsense product version' opnsense-version -v
run 'FreeBSD userland' freebsd-version -u
run 'machine' uname -m
run 'pkg architecture' pkg config ABI

for package in opnsense python313 python3 git git-lite jq luajit pkgconf gmake php85 os-zapret2-restyle
do
    say "=== INSTALLED PACKAGE ${package} ==="
    pkg query '%n|%v|%o|%R' "${package}" 2>&1 || say "NOT_INSTALLED_OR_UNVERIFIED: ${package}"
    say "=== CACHED REMOTE PACKAGE ${package} ==="
    pkg -o REPO_AUTOUPDATE=false rquery -r OPNsense '%n|%v|%o|%R' "${package}" 2>&1 || say "NO_CACHED_PROVIDER_OR_UNVERIFIED: ${package}"
done

file_report 'generic-python3' /usr/local/bin/python3
file_report 'versioned-python3.13' /usr/local/bin/python3.13
file_report 'service-entrypoint' /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
file_report 'bundled-curl-elf' /usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate
if [ -f /usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate ]; then
    run 'bundled ELF architecture' file /usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate
    run 'bundled ELF dynamic dependencies (static read)' elfdump -d /usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate
fi

repo=/usr/local/etc/pkg/repos/FreeBSD.conf
backup=/var/db/zapret2-restyle/FreeBSD.conf.backup
file_report 'former FreeBSD.conf override' "$repo"
file_report 'saved former FreeBSD.conf backup' "$backup"
if [ -f "$repo" ] && [ -f "$backup" ]; then
    if cmp -s "$repo" "$backup"; then
        say 'REPO_BACKUP_COMPARISON=IDENTICAL_BYTES'
    else
        say 'REPO_BACKUP_COMPARISON=DIFFERENT_BYTES'
    fi
else
    say 'REPO_BACKUP_COMPARISON=NO_PAIR'
fi
say 'REPO_OWNERSHIP=NOT_PROVEN_BY_THIS_PROBE'
say 'STAGE0_TARGET_PROBE=END_READ_ONLY'
