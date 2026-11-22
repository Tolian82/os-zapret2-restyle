# Original FD9 whole-package continuation of a failed POST_INSTALL restore

Scope: P0 #1213, recovery code `v0.6.5_114`, 22 November 2026. The recovery implementation is merged and its package is published; this documentation-only `_115` record adds the qualified handoff below. Owner recovery and physical power-loss testing remain unconfirmed.

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

## Executed native evidence and published code identity

[P0 native run 45020690225](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45020690225), [actual guest job 137202727061](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45020690225/job/137202727061), exact source `c5a0317a4aedf3be9f35cf7afb6439c6585b1204`: **PASS** on disposable OPNsense 26.7. Its recorded results are:

| Evidence | Observed result |
| --- | --- |
| `P0_OWNER_NATIVE_109_P2_BOOT_REFUSAL` | Genuine published `_109`, original finish rc70, exact global-exclusion P2 refusal, retained `postinstall-attested`. |
| `P0_NATIVE_CONTINUATION_PREPARED_CRASH` | Abrupt coordinator exit 91 after real FD9 journal publication; installed `_109` sources unchanged, original record bytes retained. |
| `P0_NATIVE_CONTINUATION_POSTINSTALL_CRASH` | Abrupt exit 92 after real native `_111` POST_INSTALL; fully installed `_111` remains STOPPED, original record retained. |
| `P0_OWNER_NATIVE_111_RECONCILED` | Normal package-contained bootstrap rc0; installed `_111` RUNNING, schema3, 14 learning profiles, Config and dvtws binary unchanged, original archive preserved, guard/marker absent. |

[PR #1217](https://github.com/Tolian82/os-zapret2-restyle/pull/1217) merged as `5a9b771757717b6c800e418cfdc6f199af3cd95c`; its tree matches the tested PR head. [Post-merge CI 45021737676](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45021737676) passed. A separate ordinary protected-update run [45020690208](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45020690208) initially refused during a later Stop/retirement setup; its single unchanged-source retry passed. That intermittent refusal remains an unresolved risk, not a demonstrated fix.

The [publication receipt](testing-publications/v0.6.5_114.md) pins the actual public `_114.pkg` SHA-256, ABI and source/tag. Independent inspection of those downloaded bytes verifies all 317 service/API files against the merged source. Native P0 used a different CI carrier archive, SHA-256 `9d8db10a8aa000aa30672410ae9633bb32d688504bda124e6de64ba29369d7ab`; the published rebuild has SHA-256 `e1015197e33b326ff5debe474caa0f3a13ee0b7c73c952c74899b7acac08101b`. Code-byte equivalence qualifies the interpreted recovery code; the public rebuild is not claimed to have been installed in that native run. The installed recovery target is the exact unchanged published `_111.pkg` tested there.

## Owner command block for the preserved initial _109 incident

Use this block once from the OPNsense root console for the last reported state: installed `_109`, original `_107→_109` record `postinstall-attested`, `was_running=true`, committed shared Apply and no engine. It first downloads the two native packages and verifies their exact SHA-256 and the expected initial record. The only extracted executable is the coordinator already delivered inside `_114.pkg`; it stages its own manifested package code, continues the same operation under original FD9 and installs the whole `_111.pkg` before restoring service. No separate installer is downloaded or created.

The first `sh` enters POSIX shell from the default root csh; the final `exit` returns to csh. A failed download cannot bypass the following SHA checks. Any refusal requires inspection of the reported result; do not repeat the block or change the journal. Interrupted continuation has a separate protected resume contract above; this initial-state block deliberately does not guess that state.

```sh
sh
fetch -o /root/os-zapret2-restyle-0.6.5_114.pkg https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.5_114/os-zapret2-restyle-0.6.5_114.pkg
fetch -o /root/os-zapret2-restyle-0.6.5_111.pkg https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.5_111/os-zapret2-restyle-0.6.5_111.pkg
/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh - <<'PY'
import hashlib, json, os, subprocess, tempfile
from pathlib import Path

service = Path('/usr/local/opnsense/scripts/OPNsense/Zapret')
carrier = Path('/root/os-zapret2-restyle-0.6.5_114.pkg')
target = Path('/root/os-zapret2-restyle-0.6.5_111.pkg')
carrier_sha = 'e1015197e33b326ff5debe474caa0f3a13ee0b7c73c952c74899b7acac08101b'
target_sha = '7257f54d74ef10fedc30d75e5e4a13861253bc8ad64d64ab232c537c2a56fae3'
for archive, expected in ((carrier, carrier_sha), (target, target_sha)):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise SystemExit('recovery-refused=PACKAGE_SHA_MISMATCH')
original = Path('/var/db/zapret2/pkg-update/operation.json').read_bytes()
record = json.loads(original)
if (record.get('schema') != 1 or record.get('phase') != 'postinstall-attested'
        or record.get('from_version') != '0.6.5_107'
        or record.get('to_version') != '0.6.5_109'
        or record.get('was_running') is not True or 'continuation' in record):
    raise SystemExit('recovery-refused=INITIAL_RECORD_CHANGED')
original_sha = hashlib.sha256(original).hexdigest()
member = '/usr/local/opnsense/scripts/OPNsense/Zapret/protected_pkg_update.py'
payload = subprocess.check_output(['/usr/bin/tar', '-xOf', str(carrier), member])
if hashlib.sha256(payload).hexdigest() != 'a65845f0fdcb6bdc6e3937c2b129d07116a5c4dbcd2f452c0e0eb2de7cd1f4e4':
    raise SystemExit('recovery-refused=COORDINATOR_SHA_MISMATCH')
bootstrap = Path(tempfile.mkdtemp(prefix='zapret-recovery-', dir='/root')) / 'protected_pkg_update.py'
with bootstrap.open('xb') as output:
    os.fchmod(output.fileno(), 0o600)
    output.write(payload)
    output.flush()
    os.fsync(output.fileno())
result = subprocess.run([str(service / 'python_runtime.sh'), str(bootstrap),
    'bootstrap-continuation', str(carrier), carrier_sha, str(target), original_sha])
print('recovery_rc=' + str(result.returncode), flush=True)
subprocess.run(['/usr/sbin/pkg', 'info', '-x', 'os-zapret2-restyle'])
status = subprocess.run([str(service / 'zapret_service.sh'), 'status'])
print('status_rc=' + str(status.returncode), flush=True)
raise SystemExit(result.returncode or status.returncode)
PY
exit
```

Required success evidence: `pkg-recovery=verified-installed-and-restored`, `recovery_rc=0`, installed `os-zapret2-restyle-0.6.5_111`, native `RUNNING` and `status_rc=0`. These results must come from the owner's device before #1213 can be resolved. Subsequent provider attribution, GUI and longer lifecycle acceptance retain their separate open status.
