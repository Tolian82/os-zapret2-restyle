# TZ6v5 S10 — preserve predecessor immutable-root identity

Entry: accepted main `v0.6.5_226` (`bd7b2a98ea6a80810b5f18a044d7a893dfd9ddcf`), PR #1347.
The genuine installed G03 witness emitted
`G03_S10_BOUND_PREPARED=PASS_REAL_ENGINE_CONFIG_FD9_WAL_ROOT_RECOVERY`.
Exact-head native Stage5 (5/5) and source CI passed. Candidate `v0.6.5_227`.

## One original operation, two generations, no second writer

The existing `operation.json` retains optional `previous_manifest` beside
the existing `previous` detail. Its generation, candidate SHA, root SHA
and seal SHA are validated by the same existing manifest binding validator.
`committed_manifest` selects the candidate manifest only for COMMITTED
and the predecessor manifest only for RESTORED. A rejected candidate's
manifest never becomes the old owner's pin. An unbound legacy owner
remains unbound. Ordinary PREPARED copies the actual terminal owner pin;
the existing original writer carries it forward. Legacy records without
either pin retain their existing representation.

Reuse the existing original root/seal/plan verifier for both pinned
generations in PREPARED-only recovery, and for the previous pin on
both sides of the original root binding. Do not close a pinned PREPARED
after a changed predecessor/root/seal. The legacy generic activating
and restored transitions remain fenced. The legacy native Apply/Lab
gate refuses an actual immutable owner before ordinary retirement;
the direct original Found entry refuses a bound predecessor before
preparing a Found write. Found is not yet converted to bound ownership:
its original P1/Config phases must bind and preserve both pins before
the first physical write, not bypass this guard.

This is durable identity retention and byte attestation, not old
runtime proof, semantic action selection or a positive transition.
No new lock, Config writer, journal, process, IPFW, GUI action or
extra VM. Tests exercise the existing S10b1 stage/bind/recover fixture,
including a **synthetic future committed bound owner** because no
installed positive bound activation exists yet. Test terminal selection,
successor pin retention after abort, corrupt old pin refusal, illegal
legacy activation and Found refusal. Source and existing native regression
CI still required; no assertion of actual running bound owner.

## Next

Connect the original saved Config/WAN, old full tree/process/epoch proof
and new typed S08d comparison before any retirement or mutation. The
current manifest stores structural hash and mutable references, not full
old S08d content; reconstruct or attest original old effective input
against its pinned bytes, and treat ambiguity as refusal, never as a
reload permit. Then connect the existing physical rollback path and
Found phase before allowing the positive original PREPARED transition.
S10 OPEN/NO-GO; S11 blocked.
