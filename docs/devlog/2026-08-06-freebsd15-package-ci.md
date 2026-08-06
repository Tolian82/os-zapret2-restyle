# 2026-08-06 — FreeBSD 15 package CI correction

The final Strategy Lab source series was rechecked after revisions 43–46 merged. Runtime contracts, retention, the corrective matrix, warning-free fixtures, and the final live-verification documentation were complete.

A packaging-gate defect remained: the general pull-request CI workflow still selected FreeBSD 14.2. Consequently, the revision 46 package artifact reported ABI `FreeBSD:14:amd64` even though the project target and release workflow use FreeBSD 15 amd64.

Revision 47 corrects the PR package builder to FreeBSD 15.0, verifies the VM major version, checks the generated package ABI and architecture, removes package-inspection truncation warnings, and adds a permanent regression contract. The revision 46 package artifact is excluded from installation and live verification; revision 47 is the replacement candidate.

No Strategy Lab runtime behavior and no published release are changed.
