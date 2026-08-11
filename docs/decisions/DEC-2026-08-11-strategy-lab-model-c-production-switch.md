# Decision — Strategy Lab Stage 60 Model C production candidate

Date: 2026-08-11
Status: **OWNER-AUTHORIZED FOR PRODUCTION CANDIDATE `_23`; OWNER-LIVE ACCEPTANCE PENDING**

## Decision

The project owner explicitly selected the next packaged Strategy Lab cycle as a direct Stage-60 transition to Model C and authorized publication of the resulting `v0.4.0_23` testing package before owner-live verification.

`v0.4.0_23` therefore makes `C-warm-bucket-source-port-dispatch` the normal Stage-60 runtime candidate. This does not erase the accepted `_22` Model B evidence. `B-warm-worker-parallel-batched` remains the first correctness/runtime fallback and comparison reference; cold Model A remains the final fail-closed fallback.

## Model C boundary

One adaptive frontier batch uses one physical warm `dvtws2` process. Up to three candidate tasks may probe concurrently through three exact source-port-qualified IPFW routes that all divert to that one worker. Endpoints inside one candidate remain sequential.

Candidate selection is performed inside the bucket with native Zapret2 Lua orchestration:

1. Python assigns the existing unique controlled client source ports to each candidate/endpoint probe.
2. The bucket renders each immutable `CandidateSpec` as its original ordered Lua action chain.
3. Each chain is preceded by `zapret-auto.lua` `condition` with the packaged `strategy_lab_model_c_source_port` iff selector.
4. The selector compares the flow's client port with the exact candidate source-port set and fails closed on missing/invalid metadata.
5. Candidate-specific payload/range state is reset before every condition/action chain, preserving `-d8`, `-d10` and any absence/default semantics rather than applying one hidden global range.

Standard Zapret2 profile matching is not used as the candidate selector because client/source port is not a normal client-mode profile-port discriminator. Source-port selection is deliberately inside Lua while IPFW independently provides exact route attribution.

## Required safety

Model C is valid only while all of the following remain true:

- the batch contains only currently reachable adaptive-frontier candidates;
- candidate width is at most three;
- there is one physical bucket worker and distinct source-port-qualified routes;
- every candidate retains exact `CandidateSpec` Lua actions, filters, ranges and resource identity;
- external BLOBs resolve from the immutable job `ResourceInventory`;
- selected-route counter growth and exact curl source-port/endpoint binding remain mandatory attribution evidence;
- worker readiness/identity/RSS are observable;
- cleanup removes all batch-owned rules/processes/listeners before the next bucket;
- cancellation, stage/job budgets and Stage-90 semantic restoration remain unchanged.

A Model-C infrastructure/selector/rendering/attribution/cleanup failure must not be interpreted as a candidate network result. It disables Model C and replays through accepted Model B. A Model-B warm infrastructure failure then uses the existing cold Model A fallback.

## Acceptance boundary

Source/CI/FreeBSD package qualification is required before publication. Owner-live testing occurs on the published `_23` package. Until those owner-live runs pass, `_23` is the owner-authorized production **candidate**, not a claim that Model C has already been appliance-accepted.

The initial owner-live gate should establish at least:

- normal Stage 60 actually reports Model C rather than silently using Model B;
- one physical worker services a multi-candidate batch;
- selector source-port sets and exact IPFW attribution are present;
- no-candidate and working-candidate outcomes remain truthful;
- Model B fallback remains safe if deliberately/organically exercised;
- Stage-90 restoration and post-run rule/process cleanup pass.

If Model C fails those correctness/safety gates, production returns to the accepted Model B boundary rather than weakening attribution or candidate semantics.
