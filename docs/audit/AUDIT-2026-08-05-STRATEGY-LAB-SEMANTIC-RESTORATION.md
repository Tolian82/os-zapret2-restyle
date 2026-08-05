# Audit update — Strategy Lab semantic restoration

Date: 2026-08-05
Corrective patch: 7
Finding: `SL-COR-006`

## Source remediation

The normal Zapret2 service now exposes a lock-owned `strategy-lab-evidence` action. It reports:

- aggregate lifecycle state;
- verified dvtws2 child identity;
- verified supervisor identity;
- active runtime argument identity;
- effective generated configuration identity;
- normal plugin-owned IPFW rule identity.

Strategy Lab stores that evidence before stopping the normal service. After every success, cancellation, timeout, prerequisite failure, or internal error it:

1. stops the temporary candidate runtime;
2. removes and verifies the complete Strategy Lab IPFW range;
3. verifies no candidate pidfile or live candidate remains;
4. restores the initial RUNNING or STOPPED state;
5. captures fresh semantic evidence;
6. compares process, runtime, effective strategy, and normal firewall identities;
7. persists a structured restoration verdict.

A semantic mismatch forces `RESTORE_FAILED`; it cannot be reported as successful completion.

## Compatibility boundary

Legacy test service fixtures that do not implement `strategy-lab-evidence` retain aggregate lifecycle verification. The packaged production service implements the semantic action and therefore uses the strict path. The action remains internal and requires the inherited lifecycle-lock ownership marker and descriptor 9.

## Automated evidence

`scripts/test-strategy-lab-semantic-restoration.sh` verifies healthy RUNNING restoration, STOPPED preservation, effective-strategy mutation rejection, temporary firewall residue rejection, persisted evidence, and production action wiring.

## Remaining boundaries

- Corrective Patch 8 must require this successful restoration evidence before circular validation becomes eligible.
- Live OPNsense process and IPFW evidence remains deferred until the complete corrective series passes its serial source gate.
