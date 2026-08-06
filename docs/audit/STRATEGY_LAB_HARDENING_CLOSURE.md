# Strategy Lab hardening closure

## Source and CI status

Status: **COMPLETE**

The corrective series from revision 25 through revision 46 closes the accepted source findings recorded in `AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

Implemented source contracts include:

- strict runtime cleanup, readiness, deadline, stale-worker, and serialized-state safety;
- local-only automated traffic interception and endpoint-bound proof;
- complete exact-replay Traffic Strategy profiles across supported protocols;
- validated generic UDP input;
- immutable circular parent evidence, private sessions, owner identity, stale restoration, and retry blocking;
- Settings lifecycle coordination;
- persisted terminal-result reload and structured profile-copy presentation;
- deterministic progress and complete Russian/English presentation;
- removal of transitional aliases and duplicate hooks;
- lock-protected evidence-preserving retention;
- one authoritative nonrecursive Strategy Lab corrective CI matrix.

Revision 46 itself changed no Strategy Lab runtime behavior. It froze the final documentation authority and live-appliance release gate.

## FreeBSD 15 package correction

Status: **COMPLETE IN REVISION 47**

The revision 46 pull-request package artifact was built by the general CI workflow on FreeBSD 14.2 and contains package ABI `FreeBSD:14:amd64`. That artifact is incompatible with the documented OPNsense 26.7 / FreeBSD 15 target and is explicitly excluded from live verification.

Revision 47:

- moves the pull-request package builder to FreeBSD 15.0;
- verifies the VM major version before building;
- rejects any package whose manifest is not `FreeBSD:15:amd64` and `freebsd:15:x86:64`;
- adds a permanent contract that rejects FreeBSD 14 package builders in GitHub workflows;
- designates `os-zapret2-restyle-0.3.2_47.pkg` as the only valid live-matrix candidate.

This correction does not reopen findings 1–15 and does not change Strategy Lab runtime behavior.

## Verified automated gates

Every merged source revision is required to pass:

- exact versioned PR and commit-title identity;
- PHP, XML, and shell validation;
- the mandatory Strategy Lab corrective matrix;
- the FreeBSD 15 package-workflow contract;
- project lifecycle, release, governance, and repository-hygiene contracts;
- FreeBSD 15 package build and package-manifest inspection;
- post-merge `main` integrity.

## Live appliance status

Status: **PENDING OWNER**

The repository cannot truthfully claim live OPNsense success without execution on the owner's appliance. The authoritative live plan is:

`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`

All rows are intentionally `PENDING OWNER`. No live PASS is inferred from CI, mocked integration tests, or package build success. Only revision 47 or a later FreeBSD 15 amd64 candidate may be used.

## Reopened semantic evidence contract

Status: **CORRECTIVE CANDIDATE 0.3.3_4**

Live scenario 1 attempts on `0.3.3_1` and `0.3.3_2` exposed one affected contract: semantic lifecycle evidence must identify the same running daemon processes as the normal service backend.

The `0.3.3_2` diagnostic isolated the defect:

- the FreeBSD-safe wrapper returned both dvtws2 and supervisor commands;
- the shared backend matcher returned true for both processes;
- the complete `zapret_service.sh strategy-lab-evidence` path returned false for both;
- `zapret_service.sh` had overwritten the wrapper inherited from `backend/common.sh` with direct `/bin/ps`.

Revision `0.3.3_4` removes that later override, binds service semantic evidence to the common process wrapper, and strengthens CI so a future direct `/bin/ps` override is rejected. This correction does not claim scenario 1 PASS; the row must be repeated on the owner appliance with the corrected FreeBSD 15 package.

Revision `0.3.3_3` remains an independent presentation correction for Diagnostics reload behavior and does not substitute for the scenario 1 runtime retest.

## Release status

Status: **BLOCKED ON LIVE MATRIX**

The hardening and ABI-correction revisions do not authorize or perform:

- a Git tag;
- GitHub Release creation;
- release asset publication;
- pkg-repository publication;
- declaration of production readiness.

Release preparation may begin only after every required live row is marked PASS with recorded evidence and the owner gives separate explicit release authorization.

## Reopening rule

A live failure reopens only the affected logical contract. The correction must use a new versioned patch, update the relevant authority and evidence, pass the full corrective matrix and FreeBSD 15 package build, and repeat the affected live scenario plus dependent scenarios.
