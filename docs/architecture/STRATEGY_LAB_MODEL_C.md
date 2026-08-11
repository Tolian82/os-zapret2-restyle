# Strategy Lab Model C Stage-60 runtime architecture

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How does the `_23` one-worker Model C Stage-60 runtime select and isolate candidates?

Purpose:
Define the current Model-C production-candidate execution contract without rewriting the
stable adaptive graph, CandidateSpec, lifecycle or downstream validation architecture.

Read after:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` and `docs/PROJECT_STATE.md`.

==================================================
BOUNDARY
==================================================

`v0.4.0_23` changes the Stage-60 runtime accelerator, not search semantics. Python keeps the
same native Zapret2 DAG, resolved-frontier scheduling, endpoint epoch, candidate identity,
budget admission, cancellation, winner band, deterministic result persistence and Stage-70
handoff.

Normal Stage 60 prefers `C-warm-bucket-source-port-dispatch`. One admitted adaptive-frontier
batch contains at most three candidates and one physical warm `dvtws2` worker. Independent
candidate probes may overlap; endpoints inside one candidate remain sequential.

==================================================
DISPATCH
==================================================

A normal client-mode Zapret2 profile cannot distinguish candidates by client source port,
because the normal TCP profile port filter refers to the server port. Model C therefore uses
Lua orchestration rather than multiple first-match profiles.

Each candidate/endpoint probe already receives a unique controlled TCP source port. Model C
retains that `_21`/`_22` mechanism and uses it twice:

1. IPFW route identity: rule matches exact source port + exact pinned destination IPv4 +
   TCP/443 and diverts to the shared bucket;
2. in-bucket identity: `zapret-auto.lua` `condition` invokes packaged
   `strategy_lab_model_c_source_port`, which compares the flow's client port with that
   candidate's exact allowed source-port set.

For outgoing packets the selector reads TCP source port; for reverse-direction packets it
reads TCP destination port so the same client-port identity is retained. Missing or invalid
packet/selector metadata returns false. There is no fall-through to another candidate as a
success condition.

==================================================
CANDIDATE SEMANTICS
==================================================

The bucket does not create new candidate identities. Every candidate remains the immutable
`CandidateSpec` already owned by Python.

Before each condition/action chain, the renderer resets that candidate's effective:

- `--in-range`;
- `--out-range`;
- `--payload`.

The following exact ordered `--lua-desync` instances are then placed behind one condition
whose `instances=N` equals that candidate's action count. This preserves the graph's existing
`-d8`, `-d10` and default/absent range semantics rather than promoting a bucket-wide range.

Candidate BLOB declarations are unioned once at bucket startup. Built-ins and inline values
keep their original names/values; installed external BLOBs are resolved from the immutable
job `ResourceInventory`. Conflicting declarations, unsupported directives or incompatible
profile dimensions reject Model C for that batch rather than approximating the candidate.

`zapret-auto.lua` and `strategy_lab_model_c.lua` are runtime dispatcher dependencies; they
do not become functional dependencies of the underlying CandidateSpec and therefore do not
change candidate identity.

==================================================
PHYSICAL / FIREWALL OWNERSHIP
==================================================

The first dedicated warm slot is the one physical bucket worker (current divert port 9990).
Up to three logical candidate routes use the existing dedicated rule numbers 19128-19130 but
all point to that same divert endpoint. Exact source-port qualification prevents one
candidate's probe from matching another candidate route.

Successful probes retain connected-socket endpoint and local-port identity. Failed/blocked
probes retain the accepted `_21` attribution contract: exact executed local port, exact
pinned `--resolve`, matching exact IPFW rule counter growth and successful route deletion.

==================================================
FALLBACK / RESTORATION
==================================================

Model-C failures are infrastructure failures, not candidate network results. Selector-file,
rendering, readiness, attribution, required-overlap or cleanup failure disables Model C and
replays through the accepted `_22` Model B runtime. Model B retains its existing cold Model A
fallback.

Fallback order:

`Model C -> Model B -> Model A cold`.

No fallback weakens candidate attribution, budget containment or restoration. Batch cleanup
runs before the next bucket and on the existing owner-runner signal/exit traps. Stage 90
still owns semantic restoration of the original Zapret2 service/configuration state.

==================================================
ACCEPTANCE
==================================================

`_23` is source/CI qualified before publication, then owner-live tested from the published
FreeBSD 15 package. Owner-live acceptance requires normal Model-C execution to be observable,
one physical worker for a multi-candidate batch, exact selector/route evidence, truthful
no-candidate and working-candidate results, and clean Stage-90 restoration/residue checks.

Until that live evidence is recorded, `_22` Model B remains the latest accepted appliance
baseline and `_23` remains the owner-authorized Model-C production candidate.
