# 2026-08-04 — Strategy Lab Patch 5

Implemented the isolated one-candidate Zapret2 runtime required before family search.
The worker now enters stage 50 after a negative clean baseline, runs one smoke candidate,
persists its structured result, performs candidate teardown, and then continues through
mandatory stage 90 restoration.

New modules separate candidate orchestration, runtime process ownership, and temporary
firewall ownership. The reserved test range is independent of the normal plugin range.
Candidate rules are restricted to required endpoint IPv4 addresses and TCP/443. The
candidate child does not inherit lifecycle lock descriptor 9.

A POSIX-shell global-variable collision discovered during mocked DNS resolution was
removed by using function-specific variable prefixes. This preserves the target and
address-file contract across nested request helpers.

Owner-assisted OPNsense verification remains deferred until the complete Strategy Lab
series is published and processed. Patch 6 may begin only after Patch 5 passes CI,
FreeBSD package build, squash merge, post-merge processing, and task-branch cleanup.
