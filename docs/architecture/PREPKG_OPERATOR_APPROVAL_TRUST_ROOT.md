# Pre-pkg operator approval — independent trust-root provisioning contract

**Status:** **DESIGN / NO PRODUCTION TRUST ROOT PROVISIONED.** Source-only Stage 3.25 `_115`, 4 November 2026. This is a preparatory process design; it does not constitute operator authorization, approved cryptographic identity, an OPNsense upgrade recipe or LH-08/AC-11 acceptance. [Normative native packaging TЗ v1.4](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) and [implementation plan v1.4](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) remain binding.

## Separate roles and bootstrap — nothing may authorize itself

1. **Operator authorization authority:** an offline/private signing identity *different* from the actual package provenance signer. Its private key must not live in a downloaded `.pkg`, GitHub Actions artifact, source tree or appliance. A separately authorized person/process must review exact release identity and sign the **byte-exact manual `operator-pins.json`** as a detached RSA SHA-256 signature. The native _113 code mechanically rejects verification with the same pinned public PEM as the package signer.
2. **Out-of-band trust anchor:** the public PEM fingerprint `SHA256(operator-approval-authority.pem)` must be verified by the actual owner through an authenticated channel **outside** incoming package, adjacent checksum, signed receipt and CI. The `--operator-authority` command's digest is only a *caller-supplied input*; without external authentication it may be attacker chosen. The first `python -I -B -c` trust seed source and its SHA-256 MUST likewise be independently vetted before execution. A seed cannot authenticate itself by reading the `seed_sha256` field it already executes.
3. **Package provenance signer:** independently authorized signing identity for `claims.json`, anchored by exact `public_key_sha256` in the signed, owner-reviewed receipt. It proves exact source commit, entrypoint SHA, incoming/current and old archive SHA/versions. Its identity is not inferred from a CI-generated test signer.
4. **Operator receipt:** an exclusive root-owned single-link `0600` file beneath root-owned `0700` private directory, schema `zapret2-prepkg-operator-pins-v1`, fixed repository, eight manual fields, `trust_status=PINS_RECORDED_NOT_AUTHENTICATED`. It carries **NO status asserting accepted publisher identity**. The detached `operator-pins.sig` signs these exact bytes without sorting/re-encoding during verification. A modified byte, missing signature or modified authority public key MUST fail before any external verifier source executes.
5. **Runtime after approval (read-only today):** only the independently authenticated `-c` seed can read receipt and authority file/sig from root-private paths, SHA-check the authority key against the *independently authenticated* expected SHA, run the OS-owned OpenSSL RSA signature verification on frozen bytes, strictly parse unique JSON keys/identities/target/version, SHA-check external verifier and RSA-check signed provenance and both package digests before the standalone original-FD9 inspection. It still **MUST NOT call `pkg add`, `pkg upgrade`, `pkg delete`, or modify the live firewall/service** until every LH-08/AC-11 admission/recovery requirement is met.

## _114 bounded signed policy snapshot — not a one-use guarantee

The initial source-only operator seed now **also requires** `--approval-policy <expected-SHA256> /root/private/operator-approval-policy.json /root/private/operator-approval-policy.sig` **before** checking any external RSA evaluator code. Both the policy SHA and approval-authority PEM SHA are separate input expectations which **must be owner-authenticated out of band**. A second detached RSA-SHA256 signature uses the independent approval authority's public key (not the claims signer) and covers the exact bytes of a strict policy snapshot. This snapshot binds exact signed-receipt SHA, authority SHA, positive `sequence` and Unix-second `issued_at`/`not_before`/`not_after` with maximum validity 3600 seconds and two bounded, deduplicated SHA deny lists for revoked receipt and authority.

Matching expiry, invalid times, wrong digest/identity or explicit revocation rejects **before** the external verifier executes. Full mechanics and negative tests: [Stage 3.24 _114 short-lived policy evidence](../verification/evidence/2026-11-04-v0.6.2_114-stage3-short-lived-approval-policy.md).

**Do not overstate security:** `sequence` currently has *no persistent trusted high-watermark*; the machine's wall clock is not independently trusted; a stale previously signed and not-yet-expired policy may be replayed by a caller choosing the old matching expected SHA. There is no atomic consumption journal, one-use id, independently witnessed latest revocation, production trust root, authority rotation or trusted distribution. The native fast/OPNsense tests use **test-only self-provided policy digests** and signer. These are preparatory file-semantic/crypto refusal proofs only; no production one-use authorization, revocation freshness, or safe upgrade.

## _115 isolated atomic local one-use primitive — NOT owner authorization

The **test-only** `scripts/stage3-prepkg-approval-ledger.py` creates a private ledger exclusively on a disposable FreeBSD amd64 CI VM after _114's independently executed read-only RSA verification. Under an actual `flock`, only the next contiguous positive `sequence` is accepted; receipt and policy SHA values are locally non-reusable. A complete exclusive-create `spent-...` record and chained predecessor digest are flushed with `fsync` on the record and directory. Unknown or partial records poison the ledger, stopping all future operations without deleting or repairing a failed attempt. The two-concurrent-attempt and simulated crash boundaries are described in [Stage 3.25 _115 acceptance evidence](../verification/evidence/2026-11-04-v0.6.2_115-stage3-local-one-use-ledger.md).

**Major boundary:** this ledger does **not** authenticate the received receipt/policy/issuer SHA, consume an actual production authorization, or grant the right to run `pkg`; its CLI only accepts caller values with 4 disposable-only environment flags. A filesystem-local SHA chain is **not** a root-adversary-proof ledger: its last entry can be removed/rolled back with root. It has no independent external sequence witness, current-snapshot oracle, trusted time or durable owner-approved key provisioning. Never connect it directly to supported update routes without external authorization, monotonic storage and crash-safe original FD9 ownership evidence. The established _114 seed and old-owner inspection remain **read-only**, and the published package, production hooks and user's OPNsense remain unchanged.

## Minimal independent approval record — future operator responsibility

Record, in a controlled owner-reviewed audit trail *outside CI and incoming archives*: separately verified authority public PEM SHA; verification of its possession/provenance and authorized signers; initial `-c` seed exact SHA/source; helper/verifier SHA; source commit approved for that particular operation; expected native ABI/version/current and old archive SHA; valid-from, planned expiry/revocation, no-downgrade and one-use transaction intention; appropriate human approval. Keep issuer private signing keys offline. No security claim about these fields is justified by typing the hash manually or by replaying a previous valid signature.

**_114 still does not implement** a trusted online verifier of policy authority or latest snapshot, key-rotation, monotonic revocation freshness, persistent anti-replay state or one-use consumption. It only proves the signature, key fingerprint *input*, file integrity and semantic bindings in an isolated disposable CI VM with **two independent ephemeral RSA pairs** generated on that test VM. CI PASS is not proof of an authentic owner/publisher key. There is currently no release-signing or operator authority provisioned by the owner.

## Threat-to-negative-test matrix

| Threat | Required refusal before standalone source |
|---|---|
| Receipt modified after detached signing | `OPERATOR_RECEIPT_SIGNATURE_INVALID` |
| Detached signature swapped/forged | `OPERATOR_RECEIPT_SIGNATURE_INVALID` |
| Operator approval public PEM replaced | `OPERATOR_AUTHORITY_NOT_INDEPENDENTLY_PINNED` |
| Missing/wrong operator approval fingerprint | `OUT_OF_BAND_OPERATOR_AUTHORITY_SHA_REQUIRED` / mismatched key |
| Symlink/writable/foreign-root authority/sig/receipt | private-path/owner/mode refusal |
| Same PEM role for receipt approval and package provenance | `RECEIPT_APPROVAL_AND_PACKAGE_SIGNER_MUST_DIFFER` |
| Correctly re-signed receipt with wrong source commit, archive SHA, verifier/public-key SHA | _112 semantic digest/key/commit refusal even if detached signature and claims signature are both valid |
| Correctly re-signed claims for different/current/old archive | authenticated source/target policy refusal before external source |
| Unsupported caller argv, unsigned legacy seed mode, `upgrade` | immediate read-only command refusal |

## Operator approval and native upgrade remain BLOCKED

There is no authenticated external channel for the initial `-c` seed or authority fingerprint, no production signer/approval key, no rotation/replay policy, no unavoidable OPNsense firmware/Web/managed CLI pre-pkg gate, no full old RUNNING/STOPPED PID/FD9/IPFW/Config/hook ownership, no uninterrupted FD9 through actual destructive pkg and no bounded concurrency/cancellation/rollback evidence. Direct privileged `pkg` is a separate explicitly unsupported bypass. Native disposable tests cannot approve the actual owner appliance.

**Next after _113 acceptance:** owner-controlled production authority and out-of-band seed/source/approval verification design, explicit key-rotation and freshness/refusal contract, then supported pre-pkg gateway with full old-owner and real native pkg transaction negative postconditions. **LH-08/AC-11 BLOCKED**. Published `0.6.2_1.pkg`, four package hooks, owner OPNsense and stable `v0.6.2` remain untouched.
