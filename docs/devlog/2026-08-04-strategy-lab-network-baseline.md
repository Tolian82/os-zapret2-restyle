# 2026-08-04 — Strategy Lab target and network baseline

Logical change:
Implement Strategy Lab stages 00, 30, and 40 without adding a candidate runtime or
strategy search.

Baseline:
`100f324d09539e672586b12e3cd96c26baf351b2`

Completed:

- normalized and classified domain or IPv4 targets;
- persisted target type and explicit required endpoints;
- added the approved Telegram two-endpoint contract;
- added concurrent IPv4, IPv6, and fixed QUIC/IPv4 control probes;
- required both IPv6 route and control connectivity;
- retained QUIC output only for diagnostics and classified success only from exit status;
- added explicit clean TLS 1.3 GET baseline for domain endpoints;
- added direct TCP/443 baseline for IPv4 targets;
- added early `TARGET_ACCESSIBLE` completion;
- added six-second and five-second stage budgets for stages 30 and 40;
- preserved mandatory stage 90 restoration after negative results and timeout;
- advanced package candidate to `0.3.2_6`.

Automated validation:

- target normalization, type classification, and malformed-input rejection passed;
- Telegram endpoints resolved exactly;
- IPv4-only and full IPv4/IPv6/QUIC classifications passed;
- fixed QUIC exit-status-only contract passed;
- clean TLS failure and clean accessible target paths passed;
- DNS failure and IPv4 control failure remained valid negative results;
- IPv4 target TCP/443 path passed;
- stage timeout produced `TIMEOUT` and still restored Zapret2;
- prior lifecycle, cancellation, job-state, API/configd, and legacy Blockcheck regression
  tests passed;
- POSIX shell syntax passed.

Not performed:

No owner-assisted OPNsense commands. Those checks remain deferred until all 13 patches
complete GitHub processing.

Next:
Patch 5 adds one isolated temporary candidate dvtws2 runtime only after Patch 4 closes
its complete serial-delivery gate.
