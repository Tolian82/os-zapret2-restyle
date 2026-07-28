#!/bin/sh

# Public API:
#
#   atomic_install_tree SOURCE_DIR DEST_DIR BACKUP_ROOT
#
# Installs an already validated directory tree as one unit.
#
# Guarantees:
#   - SOURCE_DIR is never modified.
#   - DEST_DIR is replaced only after a complete staging copy is ready.
#   - Existing DEST_DIR is moved to a timestamped backup first.
#   - If final activation fails, the previous DEST_DIR is restored.
#   - The function prints the created backup path to stdout, or an empty line
#     when DEST_DIR did not previously exist.
#
# Requirement:
#   staging and destination must be on the same filesystem so rename(2) is
#   atomic. The staging directory is therefore created beside DEST_DIR.

atomic_validate_path()
{
    _atomic_validate_path_value="$1"
    _atomic_validate_path_label="$2"

    case "${_atomic_validate_path_value}" in
        /*) ;;
        *)
            common_error "${_atomic_validate_path_label} must be an absolute path: ${_atomic_validate_path_value}"
            return 1
            ;;
    esac

    case "${_atomic_validate_path_value}" in
        /|/usr|/usr/local|/var|/tmp|/root)
            common_error "refusing unsafe ${_atomic_validate_path_label}: ${_atomic_validate_path_value}"
            return 1
            ;;
    esac
}

atomic_copy_tree()
{
    _atomic_copy_source="$1"
    _atomic_copy_destination="$2"

    mkdir -p "${_atomic_copy_destination}" || return 1

    # pax is part of the FreeBSD base system and preserves modes, symlinks,
    # timestamps, and directory structure without depending on GNU options.
    (
        cd "${_atomic_copy_source}" &&
        pax -rw -pe . "${_atomic_copy_destination}"
    )
}

atomic_verify_tree()
{
    _atomic_verify_source="$1"
    _atomic_verify_destination="$2"

    # Compare a stable manifest containing relative path, type, mode, and size.
    # File contents are then checked with cmp. This avoids relying on non-base
    # checksum implementations or GNU-specific find features.
    _atomic_verify_source_manifest=$(mktemp /tmp/zapret-atomic-src.XXXXXX) ||
        return 1
    _atomic_verify_destination_manifest=$(mktemp /tmp/zapret-atomic-dst.XXXXXX) ||
        {
            rm -f "${_atomic_verify_source_manifest}"
            return 1
        }

    (
        cd "${_atomic_verify_source}" &&
        find . -print | sort |
        while IFS= read -r _atomic_verify_item; do
            if [ -L "${_atomic_verify_item}" ]; then
                printf 'L %s %s\n' \
                    "${_atomic_verify_item}" \
                    "$(readlink "${_atomic_verify_item}")"
            elif [ -d "${_atomic_verify_item}" ]; then
                printf 'D %s\n' "${_atomic_verify_item}"
            elif [ -f "${_atomic_verify_item}" ]; then
                printf 'F %s %s\n' \
                    "${_atomic_verify_item}" \
                    "$(wc -c < "${_atomic_verify_item}" | tr -d ' ')"
            else
                printf 'O %s\n' "${_atomic_verify_item}"
            fi
        done
    ) > "${_atomic_verify_source_manifest}" || {
        rm -f \
            "${_atomic_verify_source_manifest}" \
            "${_atomic_verify_destination_manifest}"
        return 1
    }

    (
        cd "${_atomic_verify_destination}" &&
        find . -print | sort |
        while IFS= read -r _atomic_verify_item; do
            if [ -L "${_atomic_verify_item}" ]; then
                printf 'L %s %s\n' \
                    "${_atomic_verify_item}" \
                    "$(readlink "${_atomic_verify_item}")"
            elif [ -d "${_atomic_verify_item}" ]; then
                printf 'D %s\n' "${_atomic_verify_item}"
            elif [ -f "${_atomic_verify_item}" ]; then
                printf 'F %s %s\n' \
                    "${_atomic_verify_item}" \
                    "$(wc -c < "${_atomic_verify_item}" | tr -d ' ')"
            else
                printf 'O %s\n' "${_atomic_verify_item}"
            fi
        done
    ) > "${_atomic_verify_destination_manifest}" || {
        rm -f \
            "${_atomic_verify_source_manifest}" \
            "${_atomic_verify_destination_manifest}"
        return 1
    }

    cmp -s \
        "${_atomic_verify_source_manifest}" \
        "${_atomic_verify_destination_manifest}" || {
            rm -f \
                "${_atomic_verify_source_manifest}" \
                "${_atomic_verify_destination_manifest}"
            common_error "staging tree manifest does not match source"
            return 1
        }

    rm -f \
        "${_atomic_verify_source_manifest}" \
        "${_atomic_verify_destination_manifest}"

    (
        cd "${_atomic_verify_source}" &&
        find . -type f -print | sort |
        while IFS= read -r _atomic_verify_file; do
            cmp -s \
                "${_atomic_verify_source}/${_atomic_verify_file#./}" \
                "${_atomic_verify_destination}/${_atomic_verify_file#./}" ||
                exit 1
        done
    ) || {
        common_error "staging tree file contents do not match source"
        return 1
    }
}

atomic_remove_tree()
{
    _atomic_remove_path="$1"

    [ -e "${_atomic_remove_path}" ] || [ -L "${_atomic_remove_path}" ] ||
        return 0

    rm -rf "${_atomic_remove_path}"
}

atomic_install_tree()
{
    _atomic_install_source="$1"
    _atomic_install_destination="$2"
    _atomic_install_backup_root="$3"

    atomic_validate_path \
        "${_atomic_install_source}" "source directory" || return 1
    atomic_validate_path \
        "${_atomic_install_destination}" "destination directory" || return 1
    atomic_validate_path \
        "${_atomic_install_backup_root}" "backup root" || return 1

    [ -d "${_atomic_install_source}" ] || {
        common_error "source directory does not exist: ${_atomic_install_source}"
        return 1
    }

    _atomic_install_parent=$(dirname "${_atomic_install_destination}")
    _atomic_install_name=$(basename "${_atomic_install_destination}")
    _atomic_install_stamp=$(date +%Y%m%d-%H%M%S)
    _atomic_install_stage="${_atomic_install_parent}/.${_atomic_install_name}.stage.$$"
    _atomic_install_old="${_atomic_install_parent}/.${_atomic_install_name}.old.$$"
    _atomic_install_backup=""

    mkdir -p "${_atomic_install_parent}" "${_atomic_install_backup_root}" ||
        return 1

    atomic_remove_tree "${_atomic_install_stage}" || return 1
    atomic_remove_tree "${_atomic_install_old}" || return 1

    atomic_copy_tree \
        "${_atomic_install_source}" \
        "${_atomic_install_stage}" || {
            atomic_remove_tree "${_atomic_install_stage}"
            common_error "cannot create staging tree"
            return 1
        }

    atomic_verify_tree \
        "${_atomic_install_source}" \
        "${_atomic_install_stage}" || {
            atomic_remove_tree "${_atomic_install_stage}"
            return 1
        }

    if [ -e "${_atomic_install_destination}" ] ||
       [ -L "${_atomic_install_destination}" ]; then
        _atomic_install_backup="${_atomic_install_backup_root}/${_atomic_install_name}-${_atomic_install_stamp}-$$"

        mv \
            "${_atomic_install_destination}" \
            "${_atomic_install_old}" || {
                atomic_remove_tree "${_atomic_install_stage}"
                common_error "cannot move current destination aside"
                return 1
            }

        if ! mv \
            "${_atomic_install_old}" \
            "${_atomic_install_backup}"; then
            mv \
                "${_atomic_install_old}" \
                "${_atomic_install_destination}" 2>/dev/null || true
            atomic_remove_tree "${_atomic_install_stage}"
            common_error "cannot create backup of current destination"
            return 1
        fi
    fi

    if ! mv \
        "${_atomic_install_stage}" \
        "${_atomic_install_destination}"; then
        atomic_remove_tree "${_atomic_install_stage}"

        if [ -n "${_atomic_install_backup}" ] &&
           [ -e "${_atomic_install_backup}" ]; then
            mv \
                "${_atomic_install_backup}" \
                "${_atomic_install_destination}" 2>/dev/null || {
                    common_error "activation failed and rollback also failed"
                    return 1
                }
        fi

        common_error "cannot activate staged tree"
        return 1
    fi

    printf '%s\n' "${_atomic_install_backup}"
}

# Restore the previous destination after a post-activation failure.
atomic_restore_tree()
{
    _atomic_restore_destination="$1"
    _atomic_restore_backup="$2"

    atomic_validate_path \
        "${_atomic_restore_destination}" "destination directory" || return 1

    if [ -e "${_atomic_restore_destination}" ] ||
       [ -L "${_atomic_restore_destination}" ]; then
        atomic_remove_tree "${_atomic_restore_destination}" || return 1
    fi

    if [ -n "${_atomic_restore_backup}" ]; then
        [ -d "${_atomic_restore_backup}" ] || {
            common_error "atomic rollback backup does not exist: ${_atomic_restore_backup}"
            return 1
        }
        mv "${_atomic_restore_backup}" "${_atomic_restore_destination}" || {
            common_error "cannot restore atomic rollback backup"
            return 1
        }
    fi
}
