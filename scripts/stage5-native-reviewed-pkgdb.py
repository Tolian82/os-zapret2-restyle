#!/usr/bin/env python3
"""Disposable test-only native pkgdb dual-probe eligibility; no DB access/writes.

The original FD9 prepared record provides the expected *prior* version. Native
pkg remains the only database reader. Nothing here authorizes an installer.
"""

PKGDB_ERROR_SIGNATURES = (
    ("locked", "database is locked"),
    ("malformed", "malformed"),
    ("corrupt", "corrupt"),
    ("sql_error", "sql error"),
    ("io_error", "io error"),
)


def pkgdb_error_categories(stderr):
    value = stderr.lower()
    return [label for label, pattern in PKGDB_ERROR_SIGNATURES if pattern in value]


def classify_pkgdb(query, info, prior_version):
    """One of absent, registered-prior, refused; return sanitized evidence.

    No guessed version, partial prefix match or raw sqlite query. A new prior
    version can only come from the originally protected FD9 prepared record.
    """
    query_errors = pkgdb_error_categories(query.stderr)
    info_errors = pkgdb_error_categories(info.stderr)
    bad_db = bool(query_errors or info_errors)
    match_prior = (isinstance(prior_version, str) and bool(prior_version) and
                   query.stdout.strip() == prior_version)
    absent = (query.returncode == 1 and not query.stdout.strip() and
              info.returncode == 1 and not info.stdout.strip() and not bad_db)
    registered = (query.returncode == 0 and info.returncode == 0 and
                  match_prior and not query.stderr.strip() and
                  not info.stderr.strip())
    verdict = "absent" if absent else ("registered-prior" if registered else "refused")
    evidence = {
        "query_rc": query.returncode,
        "info_exists_rc": info.returncode,
        "query_stdout_nonempty": bool(query.stdout.strip()),
        "info_stdout_nonempty": bool(info.stdout.strip()),
        "query_db_error_categories": query_errors,
        "info_db_error_categories": info_errors,
        "possible_db_error": bad_db,
        "prior_version_matches": match_prior,
        "state": verdict,
        "no_write": True,
    }
    return verdict, evidence
