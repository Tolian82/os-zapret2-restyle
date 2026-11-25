# S10 grouped task 2 — original pinned S08d and genuine prior-owner comparison

Accepted main v0.6.5_227, `162df156c67e83262d6c6d44c55ca95c9d6764fb` (PR #1348, all seven workflows SUCCESS). Candidate v0.6.5_228. **Not yet qualified.** The prepared semantic source is now based on the accepted identical tree; exact-head source/native checks required.

## One original source and planner

The original WAL keeps one current candidate and one predecessor pin. The
manifest contains structural hashes and mutable locators, not an independent
persisted snapshot. Reconstruct the effective snapshot from the old pinned
root/seal, sealed candidate.xml and original release files. The unsealed
traffic.input is allowed only when equal to the sealed model's trafficargs
modulo trailing LF, matching the original heredoc/printf semantics.
Re-use the same config projection, original target policy, storage catalog
and S08d snapshot compiler; original schema3 uses original args rather than
the generation-specific promoted args. Readback verifies pinned SHA and
the reproduced original structural fingerprint and mutable references.
Engine version is the genuine installed setup-bound identity; never invent
the historical version. A mismatch refuses; old managed bytes come from
the sealed old release, not a current GUI/P1 list.

The original native prior runtime, saved Config/WAN and full physical
preimage readers are generalized to schema 1/2, with exact native mode and
promotion checks. The installed import-only native_plan_original_prepared_fd9
requires the same original held FD9 and ordinary bound PREPARED. It
reconstructs the candidate from its own pin and must equal the genuine
in-memory S08d source. It reuses the existing actual RUNNING old owner
observer (full active tree hash, original Config/WAN, native-common
process/IPFW, exact kernel argv/PID and monitor birth), then runs the
existing S08d plan() for both pinned generations. A first legacy old owner
with no manifest yields only RESTART_REQUIRED, never false NO_CHANGE or
RELOAD_SAFE_CANDIDATE. Recheck both pins, original engine identity and WAL.
No new Config writer, lock, journal, active state or CLI/GUI route.

The decision is analytic (NO_CHANGE, SAVE_ONLY, RELOAD_SAFE_CANDIDATE,
RESTART_REQUIRED), not authorization. Live mutable-content drift, absent
old structural evidence, changed engine identity or any ambiguous owner
must not create reload permission. The current positive-bound physical
transition remains fenced; stopped/initial/disabled and Found paths need
their existing exact cold/epoch/P1 proofs, and crash-safe physical promotion
and rollback before any production dispatch. No owner package.

## Acceptance

Extend the already existing genuine portable All/List/Auto binding fixture:
read exact pinned S08d from actual sealed source, require NO_CHANGE with
the same effective source, reject changed version and altered unsealed
traffic input. Extend the existing installed G03 ordinary PREPARED fixture
to call the native semantic planner on the SAME real running legacy owner;
require RESTART_REQUIRED proposal and no physical rights, original WAL,
Config, P1, process and IPFW unchanged, then recover. No extra VM; existing
G03 will perform the new actual test during candidate qualification.
