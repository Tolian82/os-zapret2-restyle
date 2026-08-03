# DEC-2026-08-03 — Firewall prerequisites precede every dvtws2 launch

Status: Approved and implemented
Date: 2026-08-03

## Decision

Every lifecycle path that may launch dvtws2 must prepare the complete firewall
prerequisites before entering the orchestrator runtime-launch path.

The service boundary therefore applies this order for both Start and Reconfigure:

1. verify the installed runtime;
2. render the current Zapret configuration;
3. load ipdivert and ipfw when absent;
4. establish the existing default-accept, one-pass, ipfw-enable, and PF reinjection
   prerequisites;
5. enter the orchestrator build, activation, dvtws2 launch, divert-rule installation,
   and supervisor sequence.

`firewall_prepare` is idempotent within one `zapret_service.sh` process. The existing
orchestrator firewall stage remains as a defensive boundary, but it does not repeat the
PF and sysctl operations after successful pre-launch preparation.

Stop and rollback continue to remove only plugin-owned rules and processes. They do not
unload ipdivert or ipfw.

## Reason

Live OPNsense cold-start evidence after reboot showed this deterministic failure:

- ipdivert was absent;
- ipfw was unavailable;
- dvtws2 attempted to create its DIVERT4 socket first;
- dvtws2 exited with `Address family not supported by protocol family`;
- the later `firewall_prepare` step was never reached;
- startup ended at the launcher stability check.

Manual `kldload ipdivert` followed by the same unchanged `configctl zapret start`
returned OK. The existing later firewall stage then loaded ipfw, installed rule 19000,
and completed dvtws2 plus supervisor startup. This isolates the defect to lifecycle
ordering rather than runtime version, strategy data, cache behavior, or configuration.

## Consequences

- package candidate advances from 0.2.8_10 to 0.2.8_11;
- reboot and cold Start no longer depend on a prior manual `kldload ipdivert`;
- Start and Reconfigure share the same pre-launch firewall contract;
- the existing orchestrator cleanup and transactional activation behavior remain
  unchanged;
- kernel modules remain loaded after stop or rollback;
- focused CI coverage enforces preparation before both orchestrator launch calls and
  the one-process idempotence guard;
- live reboot verification remains the decisive acceptance test;
- forced `pkg add -f` running-state preservation remains a separate lifecycle defect.

## Affected files and documentation

- `Makefile`
- `src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh`
- `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh`
- `scripts/test-config-activation-contract.sh`
- `docs/PROJECT_STATE.md`
- this decision record
