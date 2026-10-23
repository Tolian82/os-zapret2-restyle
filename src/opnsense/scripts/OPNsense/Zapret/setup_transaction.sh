#!/bin/sh

# Transactional wrapper around setup.sh install. It keeps the previous upstream
# checkout, compiled binaries, active release marker, and complete service state
# available until the selected release has been built and activated successfully.

SETUP_SCRIPT="${SETUP_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh}"
SERVICE_SCRIPT="${SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}"
CONFIGCTL="${CONFIGCTL:-/usr/local/sbin/configctl}"
GIT_BIN="${GIT_BIN:-/usr/local/bin/git}"
FIND_BIN="${FIND_BIN:-/usr/bin/find}"
ZAPRET_DIR="${ZAPRET_DIR:-/usr/local/etc/zapret2}"
STATE_DIR="${STATE_DIR:-/var/db/zapret2-restyle}"
SETUP_STATUS="${SETUP_STATUS:-${STATE_DIR}/setup.status}"
ACTIVE_RELEASE_FILE="${ACTIVE_RELEASE_FILE:-${STATE_DIR}/runtime.release}"
ROLLBACK_DIR="${ROLLBACK_DIR:-${STATE_DIR}/runtime-rollback}"
MODE="${1:-install}"
VERSION="${2:-}"
RUN_DIR="${RUN_DIR:-/var/run/zapret2-restyle}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
SETUP_LOCK_FILE="${SETUP_LOCK_FILE:-${RUN_DIR}/setup.lock}"
EXTRA_PYTHON="${EXTRA_PYTHON:-/usr/local/bin/python3.13}"
EXTRA_GUARD="${EXTRA_GUARD:-/usr/local/opnsense/scripts/OPNsense/Zapret/extra_resources_upstream_guard.py}"

set -eu
umask 022

release_tag_valid()
{
    printf '%s\n' "$1" | grep -Eq '^v[0-9]+(\.[0-9]+)+$'
}

status_write()
{
    mkdir -p "${STATE_DIR}"
    printf '%s\n' "$1" > "${SETUP_STATUS}"
}

write_active_release()
{
    _release="$1"
    release_tag_valid "${_release}" || return 1

    mkdir -p "${STATE_DIR}"
    _temporary=$(mktemp "${STATE_DIR}/runtime.release.XXXXXX") || return 1
    printf '%s\n' "${_release}" > "${_temporary}"
    chmod 0644 "${_temporary}"
    mv -f "${_temporary}" "${ACTIVE_RELEASE_FILE}"
}

read_active_release()
{
    _release=""
    if [ -r "${ACTIVE_RELEASE_FILE}" ]; then
        IFS= read -r _release < "${ACTIVE_RELEASE_FILE}" || true
        if release_tag_valid "${_release}"; then
            printf '%s\n' "${_release}"
            return 0
        fi
    fi

    if [ -x "${GIT_BIN}" ] && [ -d "${ZAPRET_DIR}/.git" ]; then
        _release=$("${GIT_BIN}" -C "${ZAPRET_DIR}" describe --tags --exact-match HEAD 2>/dev/null || true)
        if release_tag_valid "${_release}"; then
            printf '%s\n' "${_release}"
            return 0
        fi
    fi

    return 1
}

normalize_runtime_permissions()
{
    [ -d "${ZAPRET_DIR}" ] || return 1

    if [ -d "${ZAPRET_DIR}/lua" ]; then
        "${FIND_BIN}" "${ZAPRET_DIR}/lua" -type d -exec chmod 0755 {} +
        "${FIND_BIN}" "${ZAPRET_DIR}/lua" -type f -exec chmod 0644 {} +
    fi

    if [ -d "${ZAPRET_DIR}/files" ]; then
        "${FIND_BIN}" "${ZAPRET_DIR}/files" -type d -exec chmod 0755 {} +
        "${FIND_BIN}" "${ZAPRET_DIR}/files" -type f -exec chmod 0644 {} +
    fi

    if [ -d "${ZAPRET_DIR}/binaries/my" ]; then
        "${FIND_BIN}" "${ZAPRET_DIR}/binaries/my" -type d -exec chmod 0755 {} +
        "${FIND_BIN}" "${ZAPRET_DIR}/binaries/my" -type f -exec chmod 0755 {} +
    fi

    return 0
}

service_state()
{
    # Preserve the *status command's* exit code. An if with no else returns
    # 0 on a false test in POSIX sh, accidentally treating stopped (1) or
    # incomplete/unknown (2+) native ownership as RUNNING.
    # Under the original native FD9, never recursively acquire lifecycle.lock.
    _status_mode=status
    if [ "${UPSTREAM_RECOVERY_LIFECYCLE_OWNER:-0}" = 1 ]; then
        _status_mode=strategy-lab-status
    fi
    if "${SERVICE_SCRIPT}" "${_status_mode}" >/dev/null 2>&1; then
        return 0
    else
        return $?
    fi
}

configctl_exact_ok()
{
    _output=$("${CONFIGCTL}" "$@" 2>&1) || {
        printf '%s\n' "${_output}" >&2
        return 1
    }

    if [ "${_output}" != "OK" ]; then
        printf '%s\n' "${_output}" >&2
        return 1
    fi

    return 0
}

extra_resources_upstream_guard()
{
    [ -f "${STATE_DIR}/extra-resources/installed.json" ] ||
        [ -L "${STATE_DIR}/extra-resources/installed.json" ] || return 0
    [ -x "${EXTRA_PYTHON}" ] && [ -r "${EXTRA_GUARD}" ] || {
        echo "ERROR: managed resource recovery guard unavailable" >&2
        return 69
    }
    ZAPRET_DIR="${ZAPRET_DIR}" STATE_DIR="${STATE_DIR}" \
    ROLLBACK_DIR="${ROLLBACK_DIR}" GIT_BIN="${GIT_BIN}" \
        "${EXTRA_PYTHON}" "${EXTRA_GUARD}" "$@"
}


# Always invoke the evidence guard, including when no Additional Resources
# manifest exists; absence itself is part of the sealed pre-mutation identity.
backup_evidence()
{
    [ -x "${EXTRA_PYTHON}" ] && [ -r "${EXTRA_GUARD}" ] || return 69
    ZAPRET_DIR="${ZAPRET_DIR}" STATE_DIR="${STATE_DIR}" \
    ROLLBACK_DIR="${ROLLBACK_DIR}" GIT_BIN="${GIT_BIN}" \
        "${EXTRA_PYTHON}" "${EXTRA_GUARD}" "$@"
}

# A minimal, strict, non-executable checkpoint. Do not source or eval it.
# The file is written atomically and synced BEFORE any runtime mutation.
write_recovery_checkpoint()
{
    _checkpoint_phase="$1"
    case "${_checkpoint_phase}" in prepared|mutating) ;; *) return 64 ;; esac
    _saved_commit="${PREVIOUS_COMMIT:-none}"
    _saved_release="${PREVIOUS_RELEASE:-none}"
    if [ "${_saved_commit}" != none ]; then
        printf '%s\n' "${_saved_commit}" | grep -Eq '^[0-9a-f]{40}$' || return 65
    fi
    if [ "${_saved_release}" != none ]; then
        release_tag_valid "${_saved_release}" || return 65
    fi
    case "${SERVICE_WAS_RUNNING}" in 0|1) ;; *) return 65 ;; esac
    case "${PREVIOUS_BINARIES}" in 0|1) ;; *) return 65 ;; esac
    [ -d "${ROLLBACK_DIR}" ] && [ ! -L "${ROLLBACK_DIR}" ] || return 69
    [ ! -L "${ROLLBACK_DIR}/checkpoint" ] || return 69
    _tmp=$(mktemp "${ROLLBACK_DIR}/checkpoint.XXXXXXXX") || return 1
    if ! {
        printf 'schema=2\nprevious_commit=%s\nprevious_release=%s\n' "${_saved_commit}" "${_saved_release}"
        printf 'service_was_running=%s\nprevious_binaries=%s\n' "${SERVICE_WAS_RUNNING}" "${PREVIOUS_BINARIES}"
        printf 'phase=%s\n' "${_checkpoint_phase}"
    } > "${_tmp}" || ! chmod 0600 "${_tmp}" || ! mv -f "${_tmp}" "${ROLLBACK_DIR}/checkpoint"; then
        rm -f "${_tmp}"
        return 1
    fi
    # Flush file + directory metadata as a single conservative pre-mutation
    # barrier on both FreeBSD and Linux; do not switch runtime if it fails.
    sync
}

read_recovery_checkpoint()
{
    _checkpoint="${ROLLBACK_DIR}/checkpoint"
    [ -d "${ROLLBACK_DIR}" ] && [ ! -L "${ROLLBACK_DIR}" ] || return 69
    [ -f "${_checkpoint}" ] && [ ! -L "${_checkpoint}" ] || return 69
    [ "$(wc -l < "${_checkpoint}" | tr -d '[:space:]')" = 6 ] || return 69
    _schema=$(sed -n '1p' "${_checkpoint}")
    _commit=$(sed -n '2p' "${_checkpoint}")
    _release=$(sed -n '3p' "${_checkpoint}")
    _service=$(sed -n '4p' "${_checkpoint}")
    _binaries=$(sed -n '5p' "${_checkpoint}")
    _phase=$(sed -n '6p' "${_checkpoint}")
    case "${_schema}" in
        schema=1) RECOVERY_SCHEMA=1 ;; # Legacy: prepared-only verified cleanup.
        schema=2) RECOVERY_SCHEMA=2 ;; # Pre-mutation sealed binary/manifest evidence.
        *) return 69 ;;
    esac
    case "${_commit}" in previous_commit=*) PREVIOUS_COMMIT=${_commit#previous_commit=} ;; *) return 69 ;; esac
    case "${_release}" in previous_release=*) PREVIOUS_RELEASE=${_release#previous_release=} ;; *) return 69 ;; esac
    case "${_service}" in service_was_running=*) SERVICE_WAS_RUNNING=${_service#service_was_running=} ;; *) return 69 ;; esac
    case "${_binaries}" in previous_binaries=*) PREVIOUS_BINARIES=${_binaries#previous_binaries=} ;; *) return 69 ;; esac
    case "${_phase}" in phase=*) RECOVERY_PHASE=${_phase#phase=} ;; *) return 69 ;; esac
    case "${RECOVERY_PHASE}" in prepared|mutating) ;; *) return 69 ;; esac
    case "${SERVICE_WAS_RUNNING}:${PREVIOUS_BINARIES}" in 0:0|0:1|1:0|1:1) ;; *) return 69 ;; esac
    if [ "${PREVIOUS_COMMIT}" != none ]; then
        printf '%s\n' "${PREVIOUS_COMMIT}" | grep -Eq '^[0-9a-f]{40}$' || return 69
    fi
    if [ "${PREVIOUS_RELEASE}" != none ]; then
        release_tag_valid "${PREVIOUS_RELEASE}" || return 69
    fi
}

inspect_interrupted_recovery()
{
    # Read-only; serialized by the existing setup.lock, not the firewall FD9.
    if [ ! -e "${ROLLBACK_DIR}" ] && [ ! -L "${ROLLBACK_DIR}" ]; then
        printf 'recovery=none\n'
        return 0
    fi
    if ! read_recovery_checkpoint; then
        printf 'recovery=unverified\n'
        return 69
    fi
    if [ "${RECOVERY_PHASE}" = prepared ]; then
        printf 'recovery=prepared\n'
    else
        printf 'recovery=required\n'
    fi
    printf 'phase=%s\nprevious_commit=%s\nprevious_release=%s\n' "${RECOVERY_PHASE}" "${PREVIOUS_COMMIT}" "${PREVIOUS_RELEASE}"
    printf 'service_was_running=%s\nprevious_binaries=%s\n' "${SERVICE_WAS_RUNNING}" "${PREVIOUS_BINARIES}"
}

# A snapshot still marked "prepared" was fully persisted before *any*
# chmod/checkout/service operation. Only this narrow state can be released
# without restoring a runtime; anything potentially mutating stays blocked.
verify_prepared_recovery()
{
    if ! read_recovery_checkpoint || [ "${RECOVERY_PHASE}" != prepared ]; then
        echo "ERROR: recovery evidence is missing, malformed, or may have mutated runtime" >&2
        return 69
    fi
    # Without a complete previous identity, we cannot attest that the
    # checkout and release marker stayed unchanged during the interruption.
    [ "${PREVIOUS_COMMIT}" != none ] && [ "${PREVIOUS_RELEASE}" != none ] || return 69
    [ -x "${GIT_BIN}" ] && [ -d "${ZAPRET_DIR}/.git" ] || return 69
    _current_commit=$("${GIT_BIN}" -C "${ZAPRET_DIR}" rev-parse --verify HEAD 2>/dev/null) || return 69
    [ "${_current_commit}" = "${PREVIOUS_COMMIT}" ] || return 69
    [ -f "${ACTIVE_RELEASE_FILE}" ] && [ ! -L "${ACTIVE_RELEASE_FILE}" ] || return 69
    _current_release=$(cat "${ACTIVE_RELEASE_FILE}") || return 69
    [ "${_current_release}" = "${PREVIOUS_RELEASE}" ] || return 69

    if service_state; then
        _running=1
    else
        _state=$?
        [ "${_state}" -eq 1 ] || return 69
        _running=0
    fi
    [ "${_running}" = "${SERVICE_WAS_RUNNING}" ] || return 69

    # Reject unknown data or symlinked backup entries. No foreign content is
    # removed merely because it sits beside the checkpoint.
    for _entry in "${ROLLBACK_DIR}"/* "${ROLLBACK_DIR}"/.[!.]* "${ROLLBACK_DIR}"/..?*; do
        [ -e "${_entry}" ] || [ -L "${_entry}" ] || continue
        case "${_entry##*/}" in
            checkpoint|binaries|extra-managed) ;;
            backup-attestation.json) [ "${RECOVERY_SCHEMA}" = 2 ] || return 69 ;;
            *) return 69 ;;
        esac
    done
    [ ! -L "${ROLLBACK_DIR}/binaries" ] && [ ! -L "${ROLLBACK_DIR}/extra-managed" ] || return 69
    if [ "${PREVIOUS_BINARIES}" -eq 1 ]; then
        # Snapshot creation stores only binaries/my. Foreign siblings must not
        # be swept up by rm -rf, even when the actual binary bytes match.
        for _saved_entry in "${ROLLBACK_DIR}/binaries"/* "${ROLLBACK_DIR}/binaries"/.[!.]* "${ROLLBACK_DIR}/binaries"/..?*; do
            [ -e "${_saved_entry}" ] || [ -L "${_saved_entry}" ] || continue
            [ "${_saved_entry}" = "${ROLLBACK_DIR}/binaries/my" ] || return 69
        done
        [ -d "${ROLLBACK_DIR}/binaries/my" ] && [ ! -L "${ROLLBACK_DIR}/binaries/my" ] || return 69
        [ -d "${ZAPRET_DIR}/binaries/my" ] && [ ! -L "${ZAPRET_DIR}/binaries/my" ] || return 69
        [ -z "$("${FIND_BIN}" "${ROLLBACK_DIR}/binaries/my" -type l -print)" ] || return 69
        [ -z "$("${FIND_BIN}" "${ZAPRET_DIR}/binaries/my" -type l -print)" ] || return 69
        diff -r "${ROLLBACK_DIR}/binaries/my" "${ZAPRET_DIR}/binaries/my" >/dev/null || return 69
    else
        [ ! -e "${ROLLBACK_DIR}/binaries" ] && [ ! -L "${ROLLBACK_DIR}/binaries" ] || return 69
        [ ! -e "${ZAPRET_DIR}/binaries/my" ] && [ ! -L "${ZAPRET_DIR}/binaries/my" ] || return 69
    fi

    if [ ! -f "${STATE_DIR}/extra-resources/installed.json" ] &&
       { [ -e "${ROLLBACK_DIR}/extra-managed" ] || [ -L "${ROLLBACK_DIR}/extra-managed" ]; }; then
        return 69
    fi
    # A prepared checkpoint must prove BOTH unchanged live managed files
    # and immutable saved backup bytes. The saved-byte check alone is also
    # useful when a mutating checkout legitimately removed live resources.
    extra_resources_upstream_guard verify || return 69
    extra_resources_upstream_guard verify-snapshot || return 69
    if [ "${RECOVERY_SCHEMA}" = 2 ]; then
        backup_evidence verify-evidence "${PREVIOUS_BINARIES}" || return 69
    else
        # Legacy prepared-only snapshots cannot be promoted to safe mutating
        # recovery; unchanged-live diff above is the sole cleanup proof.
        [ ! -e "${ROLLBACK_DIR}/backup-attestation.json" ] &&
            [ ! -L "${ROLLBACK_DIR}/backup-attestation.json" ] || return 69
    fi
    return 0
}

# This mode is intentionally restricted to a COMPLETELY stopped native owner.
# It never stops a running process or guesses who owns incomplete IPFW state.
# The dispatcher holds setup.lock -> original native lifecycle FD9 until the
# final semantic status check; any preflight failure leaves every byte alone.
recover_mutating_stopped()
{
    if [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" != 1 ] ||
       [ "${UPSTREAM_RECOVERY_LIFECYCLE_OWNER:-0}" != 1 ] ||
       ! ( : >&9 ) 2>/dev/null; then
        echo "ERROR: both setup.lock and native lifecycle FD9 are required" >&2
        return 75
    fi
    if ! read_recovery_checkpoint || [ "${RECOVERY_SCHEMA}" != 2 ] ||
       [ "${RECOVERY_PHASE}" != mutating ] ||
       [ "${PREVIOUS_COMMIT}" = none ] ||
       [ "${PREVIOUS_RELEASE}" = none ]; then
        echo "ERROR: RECOVERY_REQUIRED: unverified or legacy mutating checkpoint" >&2
        return 69
    fi
    # An interrupted checkout may replace live Lua/BIN. Verify saved bytes
    # only, plus the raw original manifest, not the modified live files.
    backup_evidence verify-evidence "${PREVIOUS_BINARIES}" || return 69
    # No unexpected/linked evidence is allowed to be swept up by cleanup.
    for _entry in "${ROLLBACK_DIR}"/* "${ROLLBACK_DIR}"/.[!.]* "${ROLLBACK_DIR}"/..?*; do
        [ -e "${_entry}" ] || [ -L "${_entry}" ] || continue
        case "${_entry##*/}" in
            checkpoint|backup-attestation.json|binaries|extra-managed) ;;
            *) echo "ERROR: RECOVERY_REQUIRED: foreign upstream backup entry" >&2; return 69 ;;
        esac
        [ ! -L "${_entry}" ] || return 69
    done
    [ ! -L "${ZAPRET_DIR}/binaries" ] &&
        [ ! -L "${ZAPRET_DIR}/binaries/my" ] || return 69
    [ -x "${GIT_BIN}" ] && [ -d "${ZAPRET_DIR}/.git" ] &&
        [ ! -L "${ZAPRET_DIR}/.git" ] || return 69
    "${GIT_BIN}" -C "${ZAPRET_DIR}" cat-file -e "${PREVIOUS_COMMIT}^{commit}" >/dev/null 2>&1 || return 69
    # Prevent restoring a tag name which does not resolve to the saved commit.
    _release_commit=$("${GIT_BIN}" -C "${ZAPRET_DIR}" rev-parse --verify "${PREVIOUS_RELEASE}^{commit}" 2>/dev/null) || return 69
    [ "${_release_commit}" = "${PREVIOUS_COMMIT}" ] || return 69
    _recovery_head=$("${GIT_BIN}" -C "${ZAPRET_DIR}" rev-parse --verify HEAD 2>/dev/null) || return 69
    printf '%s\n' "${_recovery_head}" | grep -Eq '^[0-9a-f]{40}$' || return 69
    # Never run reset --hard across uncommitted tracked user changes or a
    # partially checked-out dirty tree. Such a case needs owner investigation.
    _recovery_dirty=$("${GIT_BIN}" -C "${ZAPRET_DIR}" status --porcelain --untracked-files=no 2>/dev/null) || return 69
    [ -z "${_recovery_dirty}" ] || {
        echo "ERROR: RECOVERY_REQUIRED: upstream tree has uncommitted tracked changes" >&2
        return 69
    }
    # The only safe automated action is on a verified STOPPED native owner.
    if service_state; then
        echo "ERROR: RECOVERY_REQUIRED: service is running; no automatic Stop" >&2
        return 69
    else
        [ "$?" -eq 1 ] || {
            echo "ERROR: RECOVERY_REQUIRED: incomplete or foreign service owner" >&2
            return 69
        }
    fi
    # From this point only an explicitly owner-requested recovery can mutate.
    # Do not remove the journal until Git, saved resources and native lifecycle
    # have all been semantically restored.
    if ! restore_previous_checkout; then
        echo "ERROR: RESTORE_FAILED: original upstream checkout/binaries not restored" >&2
        status_write failed || true
        return 70
    fi
    _restored_head=$("${GIT_BIN}" -C "${ZAPRET_DIR}" rev-parse --verify HEAD 2>/dev/null) || return 70
    [ "${_restored_head}" = "${PREVIOUS_COMMIT}" ] || return 70
    extra_resources_upstream_guard verify || return 70
    backup_evidence verify-evidence "${PREVIOUS_BINARIES}" || return 70
    if [ "${PREVIOUS_BINARIES}" -eq 1 ]; then
        diff -r "${ROLLBACK_DIR}/binaries/my" "${ZAPRET_DIR}/binaries/my" >/dev/null || return 70
    else
        [ ! -e "${ZAPRET_DIR}/binaries/my" ] || return 70
    fi
    write_active_release "${PREVIOUS_RELEASE}" || return 70
    if [ "${SERVICE_WAS_RUNNING}" -eq 1 ]; then
        "${SERVICE_SCRIPT}" strategy-lab-start >/dev/null 2>&1 || {
            echo "ERROR: RESTORE_FAILED: native service refused Start" >&2
            return 70
        }
        service_state || return 70
    else
        if service_state; then
            return 70
        else
            [ "$?" -eq 1 ] || return 70
        fi
    fi
    rm -rf "${ROLLBACK_DIR}" || return 70
    status_write failed || return 70
    echo "RECOVERY_MUTATING_RESTORED: original upstream checkout and native service state verified"
}

recover_prepared()
{
    # Serialized by the exact same setup.lock as install/inspect. Never call
    # rollback_runtime() or any native Stop/Start from this action.
    if ! verify_prepared_recovery; then
        echo "ERROR: RECOVERY_REQUIRED: prepared snapshot cannot be verified; preserving evidence" >&2
        return 69
    fi
    rm -rf "${ROLLBACK_DIR}" || return 1
    status_write failed || return 1
    echo "RECOVERY_PREPARED_CLEARED: previous runtime and service are unchanged"
}

prepare_rollback()
{
    # A previous interrupted upgrade may still own backups. Never erase its
    # rollback evidence before explicit audited recovery.
    if [ -e "${ROLLBACK_DIR}" ] || [ -L "${ROLLBACK_DIR}" ]; then
        echo "ERROR: RECOVERY_REQUIRED: previous upstream rollback snapshot exists: ${ROLLBACK_DIR}" >&2
        return 69
    fi
    PREVIOUS_COMMIT=""
    PREVIOUS_RELEASE=""
    PREVIOUS_BINARIES=0

    if _release=$(read_active_release); then
        PREVIOUS_RELEASE="${_release}"
    fi

    if [ -x "${GIT_BIN}" ] && [ -d "${ZAPRET_DIR}/.git" ]; then
        PREVIOUS_COMMIT=$("${GIT_BIN}" -C "${ZAPRET_DIR}" rev-parse --verify HEAD 2>/dev/null || true)
    fi

    # No checkout, service or IPFW mutation has happened at this point.
    # Discard ONLY our own incomplete snapshot if pre-mutation preparation
    # fails. A preexisting interrupted snapshot is rejected above.
    mkdir -p "${STATE_DIR}" || return 1
    mkdir "${ROLLBACK_DIR}" || return 1

    if [ -d "${ZAPRET_DIR}/binaries/my" ]; then
        if ! mkdir -p "${ROLLBACK_DIR}/binaries" ||
           ! cp -Rp "${ZAPRET_DIR}/binaries/my" "${ROLLBACK_DIR}/binaries/"; then
            echo "ERROR: previous binaries could not be snapshotted" >&2
            rm -rf "${ROLLBACK_DIR}" || true
            return 1
        fi
        PREVIOUS_BINARIES=1
    fi

    if ! extra_resources_upstream_guard snapshot; then
        # This guard only reads runtime bytes and writes its own backup.
        echo "ERROR: managed-resource snapshot preparation failed" >&2
        rm -rf "${ROLLBACK_DIR}" || true
        return 1
    fi
    # Refuse to arm a transaction that could not later identify its original
    # exact release/checkout. Seal all backup and manifest digests BEFORE the
    # recoverable checkpoint and before any mutation.
    if [ -z "${PREVIOUS_COMMIT}" ] || [ -z "${PREVIOUS_RELEASE}" ] ||
       ! backup_evidence snapshot-evidence "${PREVIOUS_BINARIES}"; then
        echo "ERROR: original runtime identity or backup attestation unavailable" >&2
        rm -rf "${ROLLBACK_DIR}" || true
        return 1
    fi
    # A power cut can now distinguish legacy backups from schema-2 evidence.
    if ! write_recovery_checkpoint prepared; then
        echo "ERROR: durable recovery checkpoint could not be prepared" >&2
        rm -rf "${ROLLBACK_DIR}" || true
        return 1
    fi
    return 0
}

restore_previous_checkout()
{
    [ -n "${PREVIOUS_COMMIT}" ] || return 1
    [ -x "${GIT_BIN}" ] || return 1
    [ -d "${ZAPRET_DIR}/.git" ] || return 1

    "${GIT_BIN}" -C "${ZAPRET_DIR}" checkout --detach "${PREVIOUS_COMMIT}" >/dev/null 2>&1 || return 1
    "${GIT_BIN}" -C "${ZAPRET_DIR}" reset --hard "${PREVIOUS_COMMIT}" >/dev/null 2>&1 || return 1

    if [ "${PREVIOUS_BINARIES}" -eq 1 ] && [ -d "${ROLLBACK_DIR}/binaries/my" ]; then
        rm -rf "${ZAPRET_DIR}/binaries/my" || return 1
        mkdir -p "${ZAPRET_DIR}/binaries" || return 1
        cp -Rp "${ROLLBACK_DIR}/binaries/my" "${ZAPRET_DIR}/binaries/" || return 1
    fi

    normalize_runtime_permissions || return 1
    extra_resources_upstream_guard restore || return 1
    extra_resources_upstream_guard verify-exact || return 1
    return 0
}

restore_previous_service_state()
{
    if service_state; then
        _current_state=0
    else
        _current_state=$?
    fi

    case "${_current_state}" in
        0|2)
            "${SERVICE_SCRIPT}" stop >/dev/null 2>&1 || return 1
            ;;
        1)
            ;;
        *)
            return 1
            ;;
    esac

    if [ "${SERVICE_WAS_RUNNING}" -eq 1 ]; then
        configctl_exact_ok zapret start || return 1
        service_state || return 1
    else
        if service_state; then
            _final_state=0
        else
            _final_state=$?
        fi
        [ "${_final_state}" -eq 1 ] || return 1
    fi

    return 0
}

rollback_runtime()
{
    echo "Restoring the previously active bol-van/zapret2 runtime..."
    # Never overwrite a checkout with binaries/managed files from an
    # unverified or damaged backup, even during immediate automatic rollback.
    if ! read_recovery_checkpoint || [ "${RECOVERY_SCHEMA}" != 2 ] ||
       [ "${RECOVERY_PHASE}" != mutating ] ||
       ! backup_evidence verify-evidence "${PREVIOUS_BINARIES}"; then
        echo "ERROR: RESTORE_FAILED: saved upstream bytes/manifest not attested; evidence retained" >&2
        return 1
    fi

    if ! restore_previous_checkout; then
        echo "ERROR: previous bol-van/zapret2 checkout could not be restored" >&2
        return 1
    fi

    if [ -n "${PREVIOUS_RELEASE}" ]; then
        write_active_release "${PREVIOUS_RELEASE}" || {
            echo "ERROR: previous active release marker could not be restored" >&2
            return 1
        }
    fi

    if ! restore_previous_service_state; then
        echo "ERROR: previous zapret service state could not be restored" >&2
        return 1
    fi

    # Retain backups on any failed verification above; remove them only after
    # the previous checkout AND native service state were fully restored.
    rm -rf "${ROLLBACK_DIR}" || return 1
    status_write "failed"
    echo "Previous bol-van/zapret2 runtime and service state restored."
    return 0
}

install_transaction()
{
    [ -x "${SETUP_SCRIPT}" ] || {
        echo "ERROR: setup backend is unavailable: ${SETUP_SCRIPT}" >&2
        return 1
    }
    [ -x "${SERVICE_SCRIPT}" ] || {
        echo "ERROR: zapret service control is unavailable: ${SERVICE_SCRIPT}" >&2
        return 1
    }
    [ -x "${CONFIGCTL}" ] || {
        echo "ERROR: configctl is unavailable: ${CONFIGCTL}" >&2
        return 1
    }

    if service_state; then
        SERVICE_WAS_RUNNING=1
    else
        _initial_state=$?
        case "${_initial_state}" in
            1)
                SERVICE_WAS_RUNNING=0
                ;;
            *)
                echo "ERROR: zapret service is in an incomplete or unknown state" >&2
                return 1
                ;;
        esac
    fi

    # Inspect the old upstream Git tree and all installed Lua/BIN before
    # arming a mutating checkpoint. Orphans require a manual resource sync.
    extra_resources_upstream_guard preflight-exact HEAD || {
        echo "ERROR: existing Lua/BIN files are not an attested exact set" >&2
        return 1
    }

    prepare_rollback || {
        # The only cleanable artifact is this attempt's incomplete snapshot.
        # An older interrupted rollback remains untouched.
        status_write "failed" || true
        echo "ERROR: rollback snapshot could not be prepared; no upstream switch attempted" >&2
        return 1
    }

    # Mark possible mutation durably BEFORE the first chmod/checkout/Stop.
    # Any interrupted snapshot at this phase requires explicit review.
    if ! write_recovery_checkpoint mutating; then
        status_write "failed" || true
        echo "ERROR: durable upstream recovery intent cannot be committed" >&2
        return 1
    fi

    # Repair restrictive modes left by an older checkout before setup attempts a
    # same-version reinstall, and impose a safe inherited umask for all new files.
    normalize_runtime_permissions || {
        echo "ERROR: current runtime permissions could not be normalized" >&2
        return 1
    }

    if [ -n "${VERSION}" ]; then
        if "${SETUP_SCRIPT}" install-under-parent-lock "${VERSION}"; then
            _setup_result=0
        else
            _setup_result=$?
        fi
    else
        if "${SETUP_SCRIPT}" install-under-parent-lock; then
            _setup_result=0
        else
            _setup_result=$?
        fi
    fi

    if [ "${_setup_result}" -eq 0 ]; then
        normalize_runtime_permissions || {
            status_write "failed"
            echo "ERROR: installed runtime permissions could not be normalized" >&2
            rollback_runtime || true
            return 1
        }

        extra_resources_upstream_guard verify || {
            status_write "failed"
            echo "ERROR: resource integrity lost after upstream refresh" >&2
            rollback_runtime || true
            return 1
        }

        _installed_release=$("${GIT_BIN}" -C "${ZAPRET_DIR}" describe --tags --exact-match HEAD 2>/dev/null || true)
        if ! release_tag_valid "${_installed_release}"; then
            status_write "failed"
            echo "ERROR: installed runtime does not resolve to a stable release tag" >&2
            rollback_runtime || true
            return 1
        fi

        write_active_release "${_installed_release}" || {
            status_write "failed"
            echo "ERROR: active runtime release marker could not be written" >&2
            rollback_runtime || true
            return 1
        }

        rm -rf "${ROLLBACK_DIR}"
        return 0
    fi

    if rollback_runtime; then
        return "${_setup_result}"
    fi

    status_write "failed"
    echo "ERROR: selected runtime failed and automatic rollback was unsuccessful" >&2
    return 1
}

case "${MODE}" in
    recover-mutating-stopped)
        [ "$#" -eq 1 ] || exit 64
        mkdir -p "${RUN_DIR}"
        [ -x "${LOCKF_BIN}" ] && [ -x "${SERVICE_SCRIPT}" ] || exit 69
        "${LOCKF_BIN}" -s -t 60 "${SETUP_LOCK_FILE}" \
            /usr/bin/env SETUP_TRANSACTION_LOCK_OWNER=1 \
            "${SERVICE_SCRIPT}" upstream-recover-mutating
        ;;
    recover-mutating-under-parent-lock)
        [ "$#" -eq 1 ] || exit 64
        recover_mutating_stopped
        ;;
    recover-prepared)
        [ "$#" -eq 1 ] || exit 64
        mkdir -p "${RUN_DIR}"
        [ -x "${LOCKF_BIN}" ] || exit 69
        "${LOCKF_BIN}" -s -t 30 "${SETUP_LOCK_FILE}" \
            /usr/bin/env SETUP_TRANSACTION_LOCK_OWNER=1 "$0" recover-prepared-under-parent-lock
        ;;
    recover-prepared-under-parent-lock)
        [ "$#" -eq 1 ] && [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] || exit 75
        recover_prepared
        ;;
    inspect-recovery)
        [ "$#" -eq 1 ] || exit 64
        mkdir -p "${RUN_DIR}"
        [ -x "${LOCKF_BIN}" ] || exit 69
        "${LOCKF_BIN}" -s -t 30 "${SETUP_LOCK_FILE}" \
            /usr/bin/env SETUP_TRANSACTION_LOCK_OWNER=1 "$0" inspect-recovery-under-parent-lock
        ;;
    inspect-recovery-under-parent-lock)
        [ "$#" -eq 1 ] && [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] || exit 75
        inspect_interrupted_recovery
        ;;
    install)
        [ "$#" -le 2 ] || {
            echo "usage: setup_transaction.sh install [VERSION]" >&2
            exit 64
        }
        if [ -n "${VERSION}" ] && ! release_tag_valid "${VERSION}"; then
            echo "ERROR: invalid release version: ${VERSION}" >&2
            exit 64
        fi
        mkdir -p "${RUN_DIR}"
        [ -x "${LOCKF_BIN}" ] || {
            echo "ERROR: setup lock utility unavailable" >&2
            exit 69
        }
        "${LOCKF_BIN}" -s -t 600 "${SETUP_LOCK_FILE}" \
            /usr/bin/env SETUP_TRANSACTION_LOCK_OWNER=1 "$0" install-under-parent-lock "${VERSION}"
        ;;
    install-under-parent-lock)
        [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] || {
            echo "ERROR: setup transaction was invoked without its setup.lock" >&2
            exit 75
        }
        install_transaction
        ;;
    *)
        echo "usage: setup_transaction.sh {install [VERSION]|inspect-recovery|recover-prepared|recover-mutating-stopped}" >&2
        exit 64
        ;;
esac
