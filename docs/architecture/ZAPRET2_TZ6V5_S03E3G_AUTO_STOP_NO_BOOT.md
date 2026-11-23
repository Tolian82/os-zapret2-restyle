# S03e3g — Auto Stop failure cannot authorize Boot

**Date:** 23 November 2026. **Candidate:** v0.6.5_145, test/docs/CI only, based on merged main _144. No product runtime modification or public .pkg.

First native [published _107 schema2→schema3 run #45147056251](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45147056251) returned Stop rc70 and retired_source_verified=false while the old disposable test subsequently called physical Start. That Boot was not authorized by verified old retirement. The rerun passed, without root-cause proof. Separate protected same-pkg Auto intermittent rc69 [#45147056290](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45147056290) remains open in [issue #1223](https://github.com/Tolian82/os-zapret2-restyle/issues/1223).

The original OPNsense native test now calls one helper immediately after real Stop and an independent original-epoch/retirement witness. Only Stop rc0 AND verified retirement authorize one physical Boot. Else it calls read-only service Status, emits STOP_REFUSAL with stop rc, read-only status rc and boot_attempted=false, then refuses before Start. It does NOT retry Stop, repair epoch, erase protected journal, restart or touch unrelated firewall rules.

Sanitized classifications learning_guard, original_guard and failure_class are validated against actual literal frozenset categories declared in the checked-out production auto_detect_minute.py, parsed with Python AST without importing/running the worker. Hostnames, IPs, arguments and arbitrary stderr cannot appear. Linux self-test checks three negative Stop/retire combinations with zero Start calls, one verified-positive with one Start, allowed and malicious marker values. Original native protected test remains intact and does real published _107 .pkg→current schema3, physical engine and FD9; it must PASS its full previously accepted lifecycle on a normal successful run.

**Limit:** This repairs a testing safety/observability bug, not unknown native Auto nondeterminism. Original failure logs remain evidence. DEV-064/DEV-065/DEV-069 stay authoritative. S03 NO-GO, S04–S20 blocked; no owner gateway touched.
