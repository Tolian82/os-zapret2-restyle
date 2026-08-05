# Audit update — Strategy Lab target contract

Date: 2026-08-05
Corrective patch: 9
Finding: `SL-COR-008`

## Source remediation

The active Strategy Lab workflow now accepts normalized ASCII domain targets only. API and shell validation use the same semantics:

- lowercase normalization;
- one optional trailing dot removed;
- total and label length limits;
- labels contain only letters, digits, and interior hyphens;
- at least two labels;
- the final label contains a letter;
- raw IPv4, IPv6, URL, host:port, and single-label inputs are rejected.

A bare IP is no longer interpreted as an implicit HTTPS target. It therefore cannot silently invent DNS, hostname/SNI, TLS, or port semantics. Future IP support requires an explicit type, port, and probe contract.

The GUI remains explicitly labelled `Blocked Domain` and supplies a domain example. Circular validation remains domain-only.

## Automated evidence

`scripts/test-strategy-lab-target-contract.sh` verifies normalization, Telegram endpoint expansion, rejected target classes, API validation, GUI wording, and removal of the old generic colon-permitting target pattern. The precheck integration fixture now verifies bare-IP rejection.

## Remaining boundaries

Corrective Patch 10 must exercise the complete API/configd-to-worker state machine with persisted result assertions.
