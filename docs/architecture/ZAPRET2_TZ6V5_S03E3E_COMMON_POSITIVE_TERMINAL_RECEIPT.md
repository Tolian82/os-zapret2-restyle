# ТЗ_6v5 S03e3e — положительный native Common Stop/Restart и terminal receipt

**Source-only candidate `v0.6.5_143` (23.11.2026), base `main 0738f2ea` / `v0.6.5_142`.** This is an additional acceptance test for the already-merged S03e3d receipt correction, **not** a new physical service dispatcher. No public operator package, no release tag and no owner OPNsense changes.

## What this test proves (only after native PASS)

`scripts/stage2-opnsense-g07-native-lifecycle.py` already installs the exact Mk-built plugin and pinned upstream `dvtws2 v1.0.7` in one disposable OPNsense 26.7 guest. G04 leaves it cold; G07 WAN-only Save and real HTTPS Strategies Apply create a *committed Common* native owner with exactly one RUNNING engine. The test now additionally requires, for *real installed authenticated HTTPS* `POST /api/zapret/service/stop` and `restart`:

- `response=OK`, `status=ok`, `verified=true`, exact `action=stop|restart`, exact `state=stopped|started`. An inherited configd HTTP 200 lacking any field or a contradictory action/state **fails**.
- Independent native after-state checks from the existing G07 suite: Stop means STOPPED, child PID gone, no owned IPFW rules, foreign rules preserved; subsequent Start produces exactly one engine in the same owner generation, Restart produces a different running engine PID in that same generation.
- The verified receipt is emitted by the existing original FD9 holder; there is no test-only fake service endpoint, no new Config writer, no injected PID, IPFW rule or process.
- G07's unchanged lower Apply/invalid-profile/cleanup and WAN-first gates remain in force. The existing fast fixture rejects `response=OK` without the verified terminal envelope.

**Evidence boundary:** Existing G07 is an authenticated HTTP *API* integration test, not a Chromium click test. This specific run is **Common only** because G04/Apply creates the committed shared owner. Neither Legacy runtime nor positive Chromium UI/Restart control is claimed. The earlier S03e3d negative held-FD9 Chromium EN/RU proof remains independent.

## Separate pending acceptance

A second, clean, *no shared-Apply journal* native guest must qualify the **Legacy** owner, Start a genuine engine through the old original dispatcher, record its exact owner/epoch/PID/owned IPFW, then obtain Stop/Restart terminal receipts through the same installed PHP/configd route. Must not remove a Common journal or invent a legacy owner merely to enter the fallback path. Stop needs real STOPPED; Restart needs one RUNNING process after a genuine Stop→Start; unresolved/foreign or partial transitions must refuse receipt. This pending test is required before full S03 GO.

Auto native update flakiness [#1223](https://github.com/Tolian82/os-zapret2-restyle/issues/1223) stays separate, with original failed logs preserved and no safety guard relaxed. Full S03 remains NO-GO; S04–S20 remain blocked.
