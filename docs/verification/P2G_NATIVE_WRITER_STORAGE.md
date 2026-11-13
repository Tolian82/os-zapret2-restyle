# #1052 P2g — protected nobody-compatible native producer storage

**Source candidate:** `v0.6.5_18`; source implementation only. **Not wired to the original FD9 service** and **not an activated observer**.

## Confirmed compatibility blocker

The original `shared_apply_request.php` intentionally enforces `0700` on `/var/db/zapret2`, protecting the existing shared-work and shared-apply journal. Upstream Zapret2 runs packet handling after dropping UID/GID to the selected `--user=nobody`. A proposed `--hostlist-auto=/var/db/zapret2/auto-detect/inbox.txt` cannot work there: a group-writable file cannot overcome a nontraversable ancestor. The disposable P0 witnesses used temporary `0666` files; this must not be copied into production.

The approved specification makes the earlier /var/db path illustrative, not normative. The **new protected prospective producer root** is `/var/db/zapret2-auto-detect`. Its existing `/var/db` parent must be root-owned, traversable and not writable by group/other. The original private `/var/db/zapret2` remains unchanged.

## Explicit file ownership model

| Object | Owner | Mode | Reason |
| --- | --- | --- | --- |
| `/var/db/zapret2-auto-detect/` | root : native `nobody` primary group | `0710` | Root can inspect; native engine can traverse known names, never list/create/unlink |
| `inbox.txt`, `debug.log` | root : native `nobody` primary group | `0660` | Native engine must read original inclusion and append; no world access |
| `pending/` | root : root | `0700` | No native path access; old inodes may still be open through existing engine FDs |
| `worker.lock` (when created) | root : root | `0600` | Worker-only lock; no daemon/cron is enabled |

The new backend `auto_detect_storage.py` is import-only and has no production caller/CLI. It refuses absent/untrusted ancestor modes, symlink or foreign entries and wrong ownership/modes, never resets an existing file's contents, creates only the required layout and syncs created objects. Root-only FreeBSD `prepare_native()` is dormant until original-FD9 integration. An interrupted partial setup stays fail-closed.

Existing `DurableInbox` retains its strict default private-only contract. An explicitly qualified `writer_gid` enables the root:group `0660` live inbox/pending-inode variant with exact `0710` root and root-private pending. New replacement files explicitly restore the original mode after umask. `auto_detect_fd.probe_pending_fd` similarly defaults to its old strict mode and accepts `0660` only when passed the exact qualified writer GID; this alone never authorizes acknowledgement.

**Limit:** The `nobody` UID/GID is shared with other possible local processes. These permissions exclude unrelated Unix credentials but do **not** authenticate who wrote the raw/debug bytes among peers with the same credentials. Raw/debug remain untrusted evidence until actual common-owner process/FD and native output correlation are established. Do not claim an anti-tamper guarantee from mode bits.

## One bounded verification

The existing P2e isolated OPNsense/FreeBSD workflow is extended **within the same disposable guest** to run `scripts/test-auto-detect-storage.py --native` after the already available original-builder source test. The native child drops UID/GID to `nobody` and must be able to open only the known raw/debug files for read/append; directory listing, creation, worker lock/pending must be denied. Native inspection uses actual FreeBSD file permissions, not fake `0666`. The same source test checks root queue hardlink+replace, protected new inode and negative acknowledgement without FD proof. The module is not yet called by installed production Apply.

Exact-head results must be recorded separately; a successful file credential test does **not** prove actual `dvtws2 --dry-run`, first-match, live raw/debug appends, authorized schema-2 generation or installed owner acceptance.

## Next P2 gate

Under the **existing** original root FD9 and canonical shared Apply, qualify these paths against the exact installed native engine, append the authorized no-action trailing observer to the real sealed release and generate schema-2 only from the genuine committed original owner. Then prove same-generation real raw/debug append and FreeBSD process/FD identity before any pending deletion or cron worker activation. First wire full purge handling for this new owned state root when production actually provisions it. Do not weaken the private common Apply parent permissions, write Config or alter Strategy Lab.

[Normative specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2f boundary](P2F_OFFLINE_OBSERVER_PLAN.md)
