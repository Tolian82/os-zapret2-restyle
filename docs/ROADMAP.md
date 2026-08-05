# os-zapret2-restyle — Roadmap

Current package candidate: `0.3.2_23`.

## Initial Strategy Lab delivery

- [x] Patch 1 — architecture decision and documentation.
- [x] Patch 2 — asynchronous job/lifecycle foundation.
- [x] Patch 3 — network capability precheck and explicit requests.
- [x] Patch 4 — clean baseline contract.
- [x] Patch 5 — isolated candidate runtime.
- [x] Patch 6 — TLS 1.3 family screening.
- [x] Patch 7 — accepted-family parameter expansion.
- [x] Patch 8 — 3-of-3 stability and shortlist.
- [x] Patch 9 — TLS 1.2 and plain HTTP.
- [x] Patch 10 — capability-gated QUIC.
- [x] Patch 11 — configured request-response UDP.
- [x] Patch 12 — temporary circular validation.
- [x] Patch 13 — activate asynchronous Diagnostics UI and retire synchronous Blockcheck.

## Strategy Lab corrective series

- [x] Corrective Patch 1 — authoritative corrective contract, audit baseline, decision, roadmap, project state, and devlog.
- [x] Corrective Patch 2 — atomically persist localized, timestamped, idempotent cancel request state.
- [x] Corrective Patch 3 — cancellation-aware active runners for stages 60, 70, and 80.
- [x] Corrective Patch 4 — explicit monotonic stage machine.
- [x] Corrective Patch 5 — correct terminal state, outcome, and localized message generation.
- [x] Corrective Patch 6 — shared overall and stage-80 time budgets.
- [x] Corrective Patch 7 — stronger semantic restoration snapshot and verification.
- [x] Corrective Patch 8 — GUI and backend circular eligibility contract.
- [x] Corrective Patch 9 — explicit domain target contract; implicit raw-IP behavior removed.
- [ ] Corrective Patch 10 — complete API-to-worker integration regression harness.
- [ ] Corrective Patch 11 — repository hygiene and stale artifact cleanup.

## Final owner-assisted verification gate

After all corrective patches are squash merged and all GitHub workflows pass:

- [ ] Install the resulting package candidate on the owner OPNsense appliance.
- [ ] Verify standard and extended Strategy Lab jobs against a blocked domain.
- [ ] Verify cancellation during active stages 60, 70, and 80.
- [ ] Verify bounded timeout handling and retained partial evidence.
- [ ] Verify initial RUNNING restores to healthy RUNNING.
- [ ] Verify initial STOPPED remains STOPPED.
- [ ] Verify temporary circular start/stop and TTL cleanup.
- [ ] Verify no Strategy Lab dvtws2 process, divert listener, or IPFW rules remain.
- [ ] Verify the saved Traffic Strategy is unchanged.
- [ ] Record live evidence before any release authorization.

Strict serial delivery remains mandatory. The next corrective patch does not begin until the previous PR is squash merged, post-merge workflows pass, and the exact task branch is verified absent.
