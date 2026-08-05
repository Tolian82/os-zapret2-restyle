# Strategy Lab circular session isolation

## Purpose

Circular validation is a separate temporary lifecycle transaction. It consumes immutable
evidence from a completed Strategy Lab job but must never reuse that job as its runtime,
state, PID, log, stop-control, lifecycle-evidence, or restoration directory.

## Session model

Each circular start creates an opaque internal session identifier matching `job.*` under:

```text
/var/run/zapret2-restyle/strategy-lab/circular/sessions/<session-id>/
```

The session contains:

- `parent.job` — immutable parent identifier;
- `parent-status.json` — snapshot of the completed result state;
- `shortlist.json` — snapshot of the TLS 1.3 circular candidate set;
- `endpoints.txt` — snapshot of parent endpoints;
- `state.json` — circular lifecycle and restoration evidence;
- `worker.pid`, `stop.request`, and `worker.log`;
- `candidate-runtime/` — session-only dvtws2 arguments, PID, log, hostlist, and addresses;
- lifecycle snapshot and restoration evidence created by the shared lifecycle helpers.

The global circular directory contains `active.session`, `latest.session`, the session
collection, and two transition-only symlink aliases:

- `state.json -> sessions/<active-or-latest>/state.json`;
- `stop -> sessions/<active>/stop.request`.

The aliases do not store independent state and never point into a parent job. They retain
compatibility with the pre-isolation internal runner and are scheduled for removal with
the obsolete compatibility surfaces in revision 43. Parent job directories are read only.

## Immutability contract

Before creating a session, eligibility is decided from the completed parent status,
shortlist, and endpoints. Those files are copied once. Every later build, DNS resolution,
runtime launch, state transition, stop request, and restoration record operates only on
the snapshots and the private session directory.

A circular session never creates `candidate-runtime/` under the parent job, never writes
the parent `status.json`, and never changes the parent shortlist or endpoints.

## State contract

Circular state includes both identities:

- `session_id` — the independent circular transaction;
- `parent_job_id` / compatibility `job_id` — the completed result used as input.

State updates merge into the existing JSON document so lifecycle snapshot, restoration,
and future circular evidence are not discarded by a later state transition.

`status` returns the active session, otherwise the latest terminal session, otherwise
`idle`.

## Security and permissions

Session directories and snapshots are private (`0700` directory, `0600` files). The
browser never receives a filesystem path. Existing API calls continue using the parent
job identifier. Compatibility aliases are created only by the root-owned launcher inside
the root-owned runtime directory.

## Verification

The focused circular contract test proves:

- eligibility remains backend-enforced;
- session snapshots match parent evidence;
- parent checksums remain unchanged;
- runtime/profile files exist only in the session;
- state transitions preserve previously recorded evidence;
- lifecycle-lock failure is written only to the session state;
- circular firewall behavior remains intentionally client-wide.

The end-to-end fixture additionally proves that the transitional aliases resolve to the
same private session state and stop control rather than creating a second state model.
