# DEC-2026-08-05 — Strategy Lab hardening series

Status: accepted

## Context

A read-only audit of source candidate `0.3.2_24` confirmed that the asynchronous Strategy Lab architecture is substantially improved but still has failure modes around cleanup proof, global deadlines, stale state, concurrent status updates, interception evidence, reproducible output profiles, circular isolation, Settings coordination, GUI recovery, and CI coverage.

## Decision

Execute the approved hardening plan as a revisioned patch series. Runtime safety is corrected before search quality and presentation.

The final shortlist contract is strengthened: each item carries the tested target, protocol, port, resolved addresses, complete Traffic Strategy profile, evidence, and replay verification. Catalog strategy fragments remain internal evidence and are not treated as user-ready output.

Static selectors are authoritative for self-contained output:

- domain: `--hostlist-domains=<domain>`;
- IP: `--ipset-ip=<address>`.

Global runtime arguments are excluded from Traffic Strategy output.

IPFW range `19100–19131` is a dedicated Strategy Lab reservation. Existing rules in that range are intentionally removed without occupancy detection, ownership checks, snapshotting, or restoration.

## Serialized GitHub publication

The patch series is published strictly one commit at a time.

- A task branch may contain only one new commit whose required GitHub checks have not yet completed successfully.
- After publishing a commit, no later patch may be prepared, committed, or published until all required checks for the current commit reach a successful terminal result and the remote commit is verified.
- A failed check keeps development focused on the same patch. The failure is corrected without stacking later patches.
- Only after the current patch is fully verified may the next logical patch begin.

## Consequences

- candidate cleanup must prove process and divert-port absence;
- job and circular state require serialization and stale-owner reconciliation;
- automated probes may intercept only firewall-originated traffic;
- success requires evidence that the intended temporary rule and runtime handled the connection;
- the exact displayed profile is replay-tested before recommendation;
- GUI and API expose structured user-facing results rather than relying on raw JSON;
- the complete corrective test set becomes mandatory CI authority;
- GitHub delivery itself follows one patch → one commit → completed checks → remote verification before the next patch.
