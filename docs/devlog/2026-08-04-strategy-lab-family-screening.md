# 2026-08-04 — Strategy Lab Patch 6

Implemented stage-50 screening for the approved seven TLS 1.3 Zapret2 strategy families.
The catalog contains Zapret2 Lua syntax only and follows upstream function and instance-order contracts.

Families run strictly sequentially. One temporary strategy may serve up to two required endpoints concurrently, but the next family cannot start until the prior candidate is fully removed. A family is accepted only when every required endpoint passes.

The result persists all completed family records plus accepted and rejected lists. Candidate timeout is a valid rejected result; internal executor or cleanup failure stops screening and proceeds to mandatory restoration. The probe runner recursively terminates child request processes when a stage timeout interrupts parallel controls.

Owner-assisted OPNsense verification remains deferred until the complete 13-patch series has passed the GitHub serial gate.
