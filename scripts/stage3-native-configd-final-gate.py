#!/usr/bin/env python3
"""One-use negative-only final owner veto immediately before a test pkg tripwire.

No native mutating pkg operation exists in this module. Real cold admission
is supplied by the same authentic FD9 owner checker used by the native worker.
"""

JOURNAL_REFUSAL='UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:'


class FinalGateRefusal(Exception):
    pass


def deny_late_journal_before_pkg(owner_check, expected_inode, actual_inode):
    """Require genuine owner refusal; passing the check means the tripwire fired."""
    if (not isinstance(expected_inode,int) or expected_inode <= 0 or
            not isinstance(actual_inode,int) or actual_inode != expected_inode):
        raise FinalGateRefusal('ORIGINAL_FD9_INODE_CHANGED_BEFORE_FINAL_GATE')
    try:
        owner_check()
    except Exception as exc:
        # The real native cold checker dynamically loads a qualified module;
        # its Refusal class is distinct from the test adapter's exception.
        reason=str(exc)
        if type(exc).__name__ != 'Refusal' or not reason.startswith(JOURNAL_REFUSAL):
            raise FinalGateRefusal('UNQUALIFIED_FINAL_GATE_REFUSAL') from None
        return {'schema':1,'status':'REFUSED_LATE_JOURNAL_BEFORE_MUTATING_PKG',
                'real_owner_check_invoked':True,
                'native_mutating_pkg_dispatch_reached':False,
                'reason':'REAL_ORIGINAL_FD9_JOURNAL_VETO'}
    # If this branch is reached, the would-be pkg-dispatch boundary is unsafe.
    raise FinalGateRefusal('UNSAFE_LATE_OWNER_REACHED_PKG_DISPATCH_TRIPWIRE')
