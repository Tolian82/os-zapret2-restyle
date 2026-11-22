# Original FD9 whole-package continuation of a failed POST_INSTALL restore

Scope: P0 #1213, source candidate `v0.6.5_114`, 22 November 2026. This document describes the implemented transition and its qualification criteria. It does not claim owner recovery, physical power-loss testing or publication of a new package.

## Observable scenario and source boundary

The owner's immutable `_107→_109` update installed the full `_109` payload and completed native POST_INSTALL, then failed before launching the engine. The retained `postinstall-attested` record, original committed shared Apply and already retired schema2 epoch are valid. The published `_111.pkg` corrects the global exclusion bug. An ordinary repeat update refuses the existing record; a temporary private-backend finish produces a source split at PHP's fixed installed child. The [earlier diagnostic proof](2026-11-22-owner-p0-109-111-disposable-recovery.md) establishes those failures but its installed three-module graft is not a recovery procedure.

The equivalent protected transition avoids that intermediary runtime entirely. It is implemented in the existing `protected_pkg_update.py` and original `zapret_service.sh`, already included by native package metadata. The only additional entrypoints are explicit recovery actions; ordinary update/Start/Stop/Apply behavior is retained. No new installed file, dependency, service, Config writer, domain policy or lifecycle lock is introduced.

## Transaction

| Step | Owner and evidence | Durable result |
| --- | --- | --- |
| Read and stage | Root coordinator verifies the original record/hash, old staged archive and new native package SHA/identity/ABI. An exclusive flock on the retained original archive prevents concurrent recovery coordinators. | Original operation and installed sources remain intact. |
| Prepare continuation | Original service acquires the same native FD9, independently proves committed STOPPED and original read-only terminal retirement, then calls `continue-record`. | One fsynced atomic replacement of the existing `operation.json` changes its target to the new `prepared` package. `continuation.record` retains the exact original JSON bytes; `continuation.sha256` pins them. The old archive and `was_running` intent survive. |
| Native install | Coordinator releases FD9 before ordinary `pkg add -f` so actual native hooks can acquire it. The package child gets a clean environment without staging/alternative hook overrides. | Whole successor payload is installed. Only its actual native POST_INSTALL can set `postinstall-attested`. |
| Restore | Coordinator invokes the canonical fully installed successor service, with a clean environment, for its original guarded finish. | Normal WAN/Config/runtime/IPFW/epoch checks, first corrected engine launch, verified RUNNING, then normal marker/journal completion. |

No three-file installed promotion exists. The original failed record is not manually erased or fabricated as completed. It remains recoverable inside the active prepared/attested operation until the normal final finish verifies the resulting service. The old archive remains available after success.

## Package-contained bootstrap

The new coordinator can be read from its SHA-verified native `.pkg` into a root-private file. Its `bootstrap-continuation` mode verifies that its own exact bytes belong to that same package, then reads manifested service/API members with `tar -xOf` into a fresh private tree. Archive headers never select filesystem write destinations; traversal, aliases, wrong source, excessive size and changed package SHA refuse. Binary bytes are preserved. The complete tree is fsynced before invoking its original FD9 service.

This is execution of code delivered inside one native package, not a separately downloaded SH installer. The bootstrap never replaces installed source files. The full successor installed by native pkg remains the only source used for actual engine restore and subsequent status. A staging environment is intentionally restricted to pre-install read/prepare; it is not inherited by package hooks or final finish.

An owner command block may be supplied only after the exact native gate and published recovery-code package identity are verified. No commands in this source contract are permission to retry the owner's old finish or directly install over its held operation.

## Interruption contract

- Before atomic journal publication: the old record is byte-for-byte intact. Unreferenced private staging cannot authorize lifecycle mutation.
- After publication, before native pkg: the same guard contains both original evidence and the pinned successor. Recovery accepts only that exact target, predecessor and original restore intent; a normal premature finish still refuses.
- After successful native POST_INSTALL, before restore: recovery recognizes the exact existing attested successor and invokes finish without another package replacement.
- Failed hooks, unknown installed package identity, changed record/archive, a live or incomplete owner, nonterminal old Auto state and mismatched successor refuse with the guard retained. No unsafe automatic reinstall or source repair is inferred.
- Native payload interruption remains guarded by the pre-existing prepared protocol. Arbitrary broken pkgdb/payload, physical disk/power failure and loss during the engine's own final Boot transaction are not claimed repaired by the two coordinator-boundary tests. A RUNNING/incomplete state encountered on recovery is refused for explicit review. These limits do not permit clearing any journal.

## Selected verification

`scripts/test-protected-pkg-update.py` exercises actual filesystem journal rename/fsync, interruption before/after publication, exact-byte predecessor retention, original-FD9 refusal, target/record/intent mismatches, actual shell STOPPED/retired gates, separate staged/native environments, and real tar-to-private-tree extraction including binary bytes and traversal/duplicate rejection. Linux root/platform trust adapters are substituted; these are portable source tests, not installed OPNsense proof.

The existing `owner-p0-protected-rescue.yml` is the required native acceptance. One genuine disposable OPNsense 26.7 builds a native candidate and verifies package-contained bootstrap source, installs the exact immutable `_107`, populates both exclusions via the native Model, and reproduces the exact `_109` P2 refusal. A test-only subprocess adapter exits **without finally** after the actual FD9 handoff and then after actual `_111` POST_INSTALL. Installed sources remain original `_109` until native pkg replaces the full payload. Normal package-contained bootstrap must resume to fully installed `_111`, native status RUNNING, schema3, unchanged Config/dvtws binary, retained old archive and absent update guard/marker. Test fault adapters never modify installed source or shipped code.

Required merge checks also cover the changed original shell/coordinator and native package inclusion through the existing scope router. Existing unrelated ISP/GUI/Voice-media evidence is not repeated or upgraded by these tests. Results belong to the exact source PR's workflow runs; failure, skip or infrastructure outage is not PASS. Issue #1213 remains OPEN until the actual owner confirms restored service.
