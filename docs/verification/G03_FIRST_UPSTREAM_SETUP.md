# G03 — First upstream runtime installation through OPNsense GUI

**Identity:** SOURCE candidate v0.6.3_6. Published stable remains v0.6.3_1. LC-03/04, issue #970, A02–A04. SOURCE and installed-native qualification do not imply owner-browser acceptance.

## User contract

On a truly clean OPNsense 26.7 with the plugin installed, no upstream Git HEAD, runtime.release or executable, the Zapret2 Service upper Apply installs selected upstream release v1.0.7 by POST /api/zapret/service/install. The existing controller invokes configd setup_install, setup_launcher.sh, setup_transaction.sh and setup.sh. No manual shell prerequisite, no runtime compiler in pkg hooks, and no Strategies Apply required.

Correct terminal state: installed=1, version=v1.0.7, setup=ready, service=stopped, busy=0. The GUI must distinguish this first-install STOPPED result from its prior error/absent engine state. If the build fails and observed worker progress establishes a new result, show failed even if installed=0. Transient API failures or uncertain prior receipts still require review instead of optimistic replay.

## Lifecycle and failure boundaries

Keep the one existing setup.lock → shared original FD9 owner. A genuinely absent upstream root takes a dedicated first-install branch; never fabricate old Git HEAD, release marker or compiled binaries for the update-only rollback. Reject old recovery state, managed Additional Resources, ambiguous existing paths and symlinks before mutation. Preserve other OPNsense Config and all non-Zapret IPFW.

Stock OPNsense template reload creates three files in the upstream directory before engine installation: zapret.conf, hostlist.txt, and hostlist-exclude.txt. A clean first install must accept **only** these known regular files (or an absent root), preserve their exact bytes, and reject any additional/linked/unknown path. During promotion, temporarily move the original template-only directory into the verified owned stage and recover its bytes safely if interrupted between two same-filesystem renames.

Build the selected release in a private staging directory adjacent to the actual upstream root (same filesystem). Verify exact Git tag and commit, executable and staged-path ownership before atomic promotion. The observed upstream v1.0.7 Makefile creates three known relative links from nfq2/dvtws2, ip2net/ip2net and mdig/mdig to binaries/my; accept only those exact in-tree targets with real non-linked compiled binaries. Any external, unknown or escaping symlink must fail closed without publishing the staged tree. Commit the release marker only after real native STOPPED verification. The private first-install intent records the selected version before work starts; failed builds clean only the verified private stage. Interrupted pre-promotion work may be safely retried; post-promotion recovery may finish only an exact matching verified checkout. Suspicious state stays intact with RECOVERY_REQUIRED diagnostics.

The existing RUNNING/STOPPED upgrade, downgrade, same-release reinstall, FD9 and sealed previous-runtime rollback remain unchanged.

## Evidence levels

**SOURCE:** syntax-check production shell and the new first-install harness, run scripts/test-g03-first-install.sh, scripts/test-setup-runtime-transaction.sh and scripts/test-gui-upstream-progress.mjs. Cover new setup, failed build/retry, interruption before/after promotion, foreign/symlink/managed-resource refusal and GUI success/failure classification.

**INSTALLED-CI:** exactly one targeted disposable OPNsense 26.7 guest in .github/workflows/g03-native-disposable-first-install.yml. Build/install one actual plugin package using stock Mk and native hooks, execute the real selected v1.0.7 configd action, check executable, Git identity, ready/stopped, absence of staging/recovery residue, same-release reinstall and preservation of unrelated Config/IPFW. This is native backend evidence, not an authenticated GUI-browser click.

**OWNER-LIVE at G11 (after G10 testing package):** Click the upper Apply for v1.0.7 from a truly clean plugin installation, observe actual authenticated POST, progress/errors, terminal STOPPED, F5 and repeated operations. No owner-live acceptance or full stable release is authorized by this source increment.
