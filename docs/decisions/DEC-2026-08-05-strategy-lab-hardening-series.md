# DEC-2026-08-05 — Strategy Lab hardening series

Status: Active
Date: 2026-08-05

## Context

A read-only audit of source candidate `0.3.2_24` confirmed that the asynchronous Strategy
Lab architecture was substantially improved but still had failure modes around cleanup
proof, global deadlines, stale state, concurrent status updates, interception evidence,
reproducible output profiles, circular isolation, Settings coordination, GUI recovery,
and CI coverage.

## Product decision

Execute the approved hardening plan as revisioned package patches. Runtime safety is
corrected before search quality and presentation.

The final shortlist contract is strengthened: each item carries the tested target,
protocol, port, resolved addresses, complete Traffic Strategy profile, evidence, and
replay verification. Catalog strategy fragments remain internal evidence and are not
treated as user-ready output.

Static selectors are authoritative for self-contained output:

- domain: `--hostlist-domains=<domain>`;
- IP: `--ipset-ip=<address>`.

Global runtime arguments are excluded from Traffic Strategy output.

IPFW range `19100–19131` is a dedicated Strategy Lab reservation. Existing rules in that
range are intentionally removed without occupancy detection, ownership checks,
snapshotting, or restoration.

## Delivery-governance amendment

The original execution record used a strict serial publication rule while early hardening
patches were being stabilized. That repository-process rule is superseded.

Current GitHub delivery is controlled by:

- `docs/GITHUB_PUBLICATION.md`;
- `DEC-2026-08-05-efficient-github-delivery.md`;
- `DEC-2026-08-05-universal-versioned-github-titles.md`.

This product decision does not require exactly one branch commit, exactly one workflow
run, mandatory idle waiting during CI, or replacement of a valid PR after an ordinary
same-scope failure. It does require that the hardening scope remain coherent, documented,
and fully verified before merge.

## Consequences

- candidate cleanup proves process and divert-port absence;
- job and circular state require serialization and stale-owner reconciliation;
- automated probes may intercept only firewall-originated traffic;
- success requires evidence that the intended temporary rule and runtime handled the
  connection;
- the exact displayed profile is replay-tested before recommendation;
- verified TLS 1.3, TLS 1.2, HTTP, QUIC, and configured UDP results share one deterministic
  final shortlist while circular validation remains TLS 1.3-only;
- GUI and API expose structured user-facing results rather than relying on raw JSON;
- the complete corrective test set becomes mandatory CI authority;
- every package-patch PR, repair commit, and final squash commit uses the exact current
  package-candidate prefix.
