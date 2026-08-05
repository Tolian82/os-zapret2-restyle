# Audit update — Strategy Lab circular eligibility

Date: 2026-08-05
Corrective patch: 8
Finding: `SL-COR-007`

## Source remediation

Circular validation is now fail-closed behind one backend eligibility contract. A job is eligible only when all conditions are true:

- terminal `state=completed`;
- terminal `outcome=SUCCESS`;
- target type is `domain`;
- stages 85 and 90 both passed;
- semantic restoration is verified;
- the final shortlist contains exactly 3–5 structurally valid candidates;
- the persisted eligibility decision matches the current job and shortlist.

The decision and reason are persisted in the job result. The circular launcher recomputes the conditions before every start and returns a structured rejection reason. An active automated job remains an independent lifecycle-lock blocker.

The Diagnostics page renders circular controls only when `circular_eligible=true`; it no longer infers readiness from target type and shortlist length. Guidance now states the enforced 150-second standard and 270-second extended limits.

## Automated evidence

`scripts/test-strategy-lab-circular.sh` covers domain, terminal outcome, restoration, persisted decision, shortlist, profile construction, firewall scope, lifecycle-lock failure, GUI gating, and truthful timing text.

## Remaining boundaries

- Corrective Patch 9 must make target semantics explicit and remove the API/shell mismatch.
- Live browser and OPNsense circular validation remains part of the final owner-assisted gate.
