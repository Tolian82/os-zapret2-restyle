# #1052 P2k8q3c2 — real native interstitial raw/debug event across two pathname swaps

**Increment:** source `v0.6.5_55`, 14 November 2026. This is a **native observation of a live race window**, reusing the exact original P2e/P2g/P2i OPNsense 26.7 disposable generator VM and existing P2i loopback test. No extra engine, product writer, source module, debug rollover, Config mutation, cron or installed package is involved.

## Why _54 alone could not prove lossless raw/debug epoch continuity

Previous `_54` measured a second unknown host **after both file replacements** and got `raw:current,debug:current,old_inode_fd:drained` with genuine native dvtws2, but root cannot atomically replace `inbox.txt` and `debug.log` as one filesystem operation. A native event between them may land in **new raw** and **old debug**, with no corresponding generation-consistent pair in either the old or new cohort. The existing original `CursorChain` couples pending raw inode SHA to a specific debug inode/prefix and immutable P2c epoch; it cannot simply reset debug to zero without certified archival lineage. A blind dual rename or pre-/post-both-only witness is not a valid lossless strategy.

## Existing single FreeBSD guest: exact physical three-stage native test

1. Reuse the original shared FD9, one postdrop real `dvtws2`, correct native P0 first-match and original P2a protected producer. Native first unknown `unknown.p2i.invalid` is present in raw/debug, original initial inodes and owner remain unchanged.
2. Rotate **raw only** via the single original `DurableInbox.exclusive()/rotate(generation=32hex)` while engine remains running; the first raw event is retained in the original single-link pending inode, fresh `inbox.txt` is empty. **Before replacing debug**, send `midcut.p2i.invalid` via real loopback HTTP/RST. Require the exact interstitial host in the **new raw path** exactly once, and in the **still-original debug name** through the real native observer; old pending must not be relabelled. Report physical `REAL_NATIVE_MIDCUT_ROUTE=raw:...,debug:previous`. Same PID/birth must remain.
3. Guest diagnostic only: archive the original debug filename and create a fresh same-group/mode debug inode; send a fourth distinct host `rotated.p2i.invalid`. Require it exactly once in old-or-new raw and old-or-new debug, and require the interstitial raw/debug event to persist on its exact measured physical inodes. Print separate `REAL_NATIVE_POST_ROTATION_ROUTE=raw:...,debug:...,old_inode_fd:...`, preserving first native event and original first-match signals.
4. No ACK or commit of the old pending, no second producer/worker, no installed OPNsense mutation. Tear down native IPFW and engine and delete only the disposable VM's isolated guest data. Reuse original P2e/P2g/P2i workflow, no duplicate VM lane.

Source-only `--self-test` exercises both split-route classification and missing/duplicate event refusal; exact-head fast CI and genuine OPNsense workflow are required separately. A passing native witness proves **this specific interstitial event path** only. It does not freeze two native writes atomically, guarantee all overlapping signal/traffic schedules, or permit ACK after reboot.

## Design gate derived from native evidence

Do **not** implement naïve `rename(raw); rename(debug)` during live collection as a production same-generation rollover without a verified **joint source boundary**. The next design must stay within the ONE original FD9 / P2a lock / P2c owner / Config-held v2 chain, must retain authenticated old and new raw/debug provenance with exact end-offsets/digests and all-PID old writer-FD state, and must resist crash at every boundary. It must also solve the genuine 4 MiB per raw/debug, 512 slot chain capacity, disk full and P0 first-match constraints. No old `zapret-hosts-auto.txt` migration, parallel worker or secondary Config writer. `authorize`, cron, real native active observer and `commit_authorized` remain OFF.

[Prior P2k8q3c1 native both-swapped proof](P2K8Q3C1_NATIVE_WRITER_INODE_ROUTE.md) · [Actual test](../../scripts/test-p2i-original-preview-native.py) · [Current plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).
