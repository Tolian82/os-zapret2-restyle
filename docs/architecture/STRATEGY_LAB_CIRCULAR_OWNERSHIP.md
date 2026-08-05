# Strategy Lab circular ownership and stale recovery

## Purpose

Circular validation owns Zapret2 lifecycle state independently from both the completed
parent result and the automated Strategy Lab launcher. Concurrent starts, PID reuse, and
a vanished worker must not leave an ambiguous active session or permit an unsafe retry.

## Launch serialization

Every circular `start`, `status`, and `stop` operation runs under the dedicated launcher
lock:

```text
/var/run/zapret2-restyle/strategy-lab/circular-launcher.lock
```

The daemonized worker closes the launcher lock descriptor. The lock serializes decisions
about the active pointer, owner identity, stop request, and stale recovery without holding
the lock throughout the validation session.

## Owner identity

Each active session stores private `owner.json` evidence containing:

- circular session ID;
- completed parent job ID;
- worker PID;
- process start token obtained from `ps -o lstart`;
- recorded process command;
- recording timestamp.

A live PID alone is insufficient. Ownership is valid only when the current process start
token exactly matches the recorded token, preventing PID reuse from impersonating the
original worker.

The launcher records ownership from the daemon PID file, and the worker refreshes it after
`exec` with its own process identity.

## Stale-session recovery

When an active nonterminal session has no valid owner, the launcher performs recovery
before another start is allowed.

If the worker disappeared before lifecycle mutation and no lifecycle snapshot exists,
private runtime residue and reserved firewall rules are removed and the session becomes a
terminal error.

If a lifecycle snapshot exists, recovery:

1. switches all runtime helpers to the private circular session;
2. removes the candidate process, divert socket, runtime files, and reserved IPFW rules;
3. restores the recorded initial RUNNING or STOPPED semantic service state;
4. verifies configuration, runtime arguments, normal firewall identity, and temporary
   runtime absence;
5. records restoration evidence in the circular session.

Successful stale recovery clears owner, PID, stop control, and active pointer. Failed
semantic restoration produces `state=restore_failed`, reason `RESTORE_FAILED`, and keeps
the active pointer so automatic retry remains blocked.

## Normal cleanup

A normally exiting worker clears ownership only after temporary runtime cleanup and
semantic restoration both succeed. Restoration failure keeps the session active and
blocked for operator inspection or a later verified recovery path.

## Verification

The mandatory owner test covers:

- launcher lock presence and daemon lock-descriptor isolation;
- valid owner recognition;
- rejection of PID reuse through a changed start token;
- stale cleanup with verified semantic restoration;
- retained active ownership after restoration failure;
- worker routing of lifecycle evidence into the private session.
