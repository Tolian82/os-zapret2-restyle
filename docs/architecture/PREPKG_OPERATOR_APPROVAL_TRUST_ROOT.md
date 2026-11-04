# Pre-pkg operator approval — independent trust-root provisioning contract

**Status:** **DESIGN / NO PRODUCTION TRUST ROOT PROVISIONED.** Source-only Stage 3.24 `_113`, 4 November 2026. This is a preparatory process design; it does not constitute operator authorization, approved cryptographic identity, an OPNsense upgrade recipe or LH-08/AC-11 acceptance. [Normative native packaging TЗ v1.4](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) and [implementation plan v1.4](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) remain binding.

## Separate roles and bootstrap — nothing may authorize itself

1. **Operator authorization authority:** an offline/private signing identity *different* from the actual package provenance signer. Its private key must not live in a downloaded `.pkg`, GitHub Actions artifact, source tree or appliance. A separately authorized person/process must review exact release identity and sign the **byte-exact manual `operator-pins.json`** as a detached RSA SHA-256 signature. The native _113 code mechanically rejects verification with the same pinned public PEM as the package signer.
2. **Out-of-band trust anchor:** the public PEM fingerprint `SHA256(operator-approval-authority.pem)` must be verified by the actual owner through an authenticated channel **outside** incoming package, adjacent checksum, signed receipt and CI. The `--operator-authority` command's digest is only a *caller-supplied input*; without external authentication it may be attacker chosen. The first `python -I -B -c` trust seed source and its SHA-256 MUST likewise be independently vetted before execution. A seed cannot authenticate itself by reading the `seed_sha256` field it already executes.
3. **Package provenance signer:** independently authorized signing identity for `claims.json`, anchored by exact `public_key_sha256` in the signed, owner-reviewed receipt. It proves exact source commit, entrypoint SHA, incoming/current and old archive SHA/versions. Its identity is not inferred from a CI-generated test signer.
4. **Operator receipt:** an exclusive root-owned single-link `0600` file beneath root-owned `0700` private directory, schema `zapret2-prepkg-operator-pins-v1`, fixed repository, eight manual fields, `trust_status=PINS_RECORDED_NOT_AUTHENTICATED`. It carries **NO status asserting accepted publisher identity**. The detached `operator-pins.sig` signs these exact bytes without sorting/re-encoding during verification. A modified byte, missing signature or modified authority public key MUST fail before any external verifier source executes.
5. **Runtime after approval (read-only today):** only the independently authenticated `-c` seed can read receipt and authority file/sig from root-private paths, SHA-check the authority key against the *independently authenticated* expected SHA, run the OS-owned OpenSSL RSA signature verification on frozen bytes, strictly parse unique JSON keys/identities/target/version, SHA-check external verifier and RSA-check signed provenance and both package digests before the standalone original-FD9 inspection. It still **MUST NOT call `pkg add`, `pkg upgrade`, `pkg delete`, or modify the live firewall/service** until every LH-08/AC-11 admission/recovery requirement is met.

## Minimal independent approval record — future operator responsibility

Record, in a controlled owner-reviewed audit trail *outside CI and incoming archives*: separately verified authority public PEM SHA; verification of its possession/provenance and authorized signers; initial `-c` seed exact SHA/source; helper/verifier SHA; source commit approved for that particular operation; expected native ABI/version/current and old archive SHA; valid-from, planned expiry/revocation, no-downgrade and one-use transaction intention; appropriate human approval. Keep issuer private signing keys offline. No security claim about these fields is justified by typing the hash manually or by replaying a previous valid signature.

**_113 deliberately does not implement** a trusted online verifier of the approval audit trail, key-rotation/revocation, freshness or anti-replay. It only proves the signature, key fingerprint *input*, file integrity and semantic bindings in an isolated disposable CI VM with **two independent ephemeral RSA pairs** generated on that test VM. CI PASS is not proof of an authentic owner/publisher key. There is currently no release-signing or operator authority provisioned by the owner.

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
