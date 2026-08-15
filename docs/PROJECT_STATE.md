# os-zapret2-restyle — Current state for `v0.4.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-08-15
State-line scope: **`v0.4.x`**

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md);
- project-development rules: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md);
- chat rules: [`CHAT_RULES.md`](CHAT_RULES.md);
- GitHub rules: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology/proof: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

Current-work state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Repository and package facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.4.1`;
- packaged source revision: `_16`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- testing-package SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- source merge/testing-tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- publication workflow run: `31882091770`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_16`;
- internal service key: `zapret`.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_16.md`](verification/evidence/testing-publications/v0.4.1_16.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- Automatic normal-production Model B/A replay remains removed.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence remains accepted.
- `_14` established explicit Enable QUIC as the sole QUIC candidate execution gate; Stage-30 measured QUIC reachability remains diagnostic only.
- `_15` owner-live QUIC observability is positively demonstrated: the normal Stage-80 UI showed all four attempted QUIC candidate IDs while ordinary QUIC remained blocked.
- `_16` source acceptance, exact-head merge and immutable testing-package publication are complete.
- `_16` Generic UDP browser-to-job path is now **OWNER-LIVE PASS** with exact 140-byte payload evidence.

## Generic UDP current conclusion

Generic UDP does not use a multipart upload directory. The product path is:

`browser File -> ArrayBuffer -> Base64 start POST -> PHP/API -> configd -> launcher -> private job-local udp-payload.bin/udp-port -> Python Extended`.

The product contract is exact decoded size **`1..4096 bytes`**, not KiB.

The owner later identified that the repeated pre-PASS size errors came from selecting files around **140 KiB**. A controlled Windows fixture was then created and filesystem-verified as exactly `140` bytes. With that file, `_16` behaved correctly.

Durable owner-live PASS evidence:
[`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md).

The earlier `_15` failure record remains historical chronology, but its then-current suspicion of a browser/upload/filesystem defect is superseded by the exact-byte `_16` result:
[`verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

## `_16` owner-live Generic UDP — PASS

Controlled scenario:

- job: `job.j09XUc`;
- target: `rutracker.org`;
- mode: Extended;
- Generic UDP port: `53`;
- payload: `udp-140.bin`, exact `140` bytes;
- Enable QUIC: OFF.

Observed:

- GUI immediately showed the payload as ready to send with exact 140-byte count;
- Stage 80 showed port `53`, payload `140` bytes and endpoint `172.67.182.196`;
- direct control reply was not observed;
- wording explicitly stated that no reply does not mean the UDP port is closed;
- candidate search still executed all three current UDP candidates: `udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`;
- no working UDP candidate was found, which is a valid negative search result;
- QUIC OFF was presented as QUIC strategy search disabled;
- Stage 90 visibly removed temporary processes/rules and restored the original Zapret2 service to running/healthy state;
- overall result: `SUCCESS`.

The earlier permissions theory is therefore **not a confirmed product defect for this scenario**. `_16` retains precise server-side failure classes for any genuine later storage/permissions error if one appears in future evidence.

Canonical specialist contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_16` automated and publication verification — PASS

- source PR `#245` exact verified head: `f7974f21dc7340b1e1416c24f9e7dade0322f0f3`;
- staged-browser Generic UDP contract: PASS;
- exact 140-byte backend/job-local regression: PASS;
- precise server preparation failure attribution: PASS;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package build/inspection qualification: PASS;
- exact-head source merge: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- publisher FreeBSD-15 build/manifest/digest verification: PASS;
- release/tag `v0.4.1_16` points exactly to the candidate-defining source merge;
- asset `os-zapret2-restyle-0.4.1_16.pkg` is uploaded and verified;
- SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`.

PR `#246` completed the required bounded publication-record documentation tail after the publisher's automatic Draft-PR step was blocked by repository GitHub Actions settings. Package identity/bytes were not changed.

## Current owner-live boundary

Generic UDP is closed as accepted for the tested `_16` scenario. Do not repeat it without new contradictory evidence.

Next selected Strategy Lab rows:

1. Enable QUIC OFF/default persistence across reload/revisit;
2. remaining RU/EN presentation review;
3. then the next risk-selected regression items from `ROADMAP.md`.

## Documentation authority note

The owner’s latest instruction is current truth. Earlier failure hypotheses remain historical evidence of what was believed at that time, but they do not override the exact-byte live PASS.

## Current architecture entry points

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md)
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md)

## Current documentation/governance facts

The four canonical general rule books remain `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`. Package-affecting source changes automatically continue through persistent testing publication and the required publication-record tail. `START_HERE.md` owns the exact revision handoff, this file owns current `v0.4.x` facts, and the version-line ledger preserves chronology.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).
