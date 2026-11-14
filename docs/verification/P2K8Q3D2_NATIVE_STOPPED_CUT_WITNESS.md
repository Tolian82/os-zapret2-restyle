# #1052 P2k8q3d2 — real original native stopped-writer inode boundary witness

Source candidate v0.6.5_57, 15 November 2026. One ORIGINAL shared-generator disposable OPNsense 26.7 VM; no installed package, new worker, production signal code or debug rotator.

## Why this is needed

The already qualified _55 actual native HTTP/RST event during two independent file-name swaps physically entered NEW raw but OLD debug (`raw:current,debug:previous`). No process freeze is provided by the original P2a worker.lock. _56 blocks already-invalid debug before raw cut but does not prevent late native writes.

## Same guest, sequential source-level experiments

1. First run of `scripts/test-p2i-original-preview-native.py --native` is unchanged in intent. Use the genuine pinned original builder, P0 first-match, original FD9/native IPFW and P2a raw rotator; inject a distinct unknown HTTP event BETWEEN raw rotation and disposable debug replacement and retain actual old/new `raw:current,debug:previous` evidence. Original dvtws2 fully stops, original VM producer scope is removed, and native rules are restored.
2. Second sequential run `--native-quiesced` uses the same original VM, build, FD9 and origin-aware native profile, without concurrent dvtws2 processes. After first genuine native unknown, verify the same dropped-owner PID, process birth and UID. Send SIGSTOP only to this disposable native child, and require FreeBSD `ps -p PID -o stat=` to begin with T (kernel STOP state); sleeping alone is not accepted as proof.
3. While STILL STOPPED: original P2a `DurableInbox.exclusive()/rotate()` detaches raw as an exact old one-link pending, then only the disposable test renames/recreates debug and fsyncs it. Confirm same PID/birth STILL STOPPED, original unknown preserved in BOTH old raw and old debug and both current raw/debug files empty.
4. SIGCONT the same original PID, verify it resumed, deliver a distinct real HTTP/RST unknown to the observer. Require it exactly once in CURRENT raw and CURRENT debug and not in old files; preserve native first-match, original pending, P2b all-PID original old-raw FD snapshot and scoped IPFW/FD9 cleanup. Emit `REAL_NATIVE_QUIESCED_CUT`, `REAL_NATIVE_QUIESCED_POST_RESUME_ROUTE` and `REAL_NATIVE_QUIESCED_SAME_PID=PASS` only on genuine passed native path.
5. Every failure path when a STOP is in effect unconditionally sends SIGCONT before existing original process termination and scoped IPFW/FD9 cleanup. One VM, one original engine at any instant; no second producer or Config writer.

The CI portable `--self-test` continues to verify real old-vs-new raw/debug route classifier and duplicate refusal; actual positive stopped-writer claims require exact-HEAD genuine OPNsense workflow success and its native log lines.

## Strict non-production boundary

An isolated kernel STOP state bracket does **not** by itself prove safe installed `dvtws2` pauses. IPFW divert traffic may stall, process may die during a stop, unmanaged watchdogs or pkg updates may intervene, old FD snapshots may be stale, and disk-full, reboot and crash may leave the router inaccessible or events misattributed. No production signal caller/stop state-machine is introduced or authorized. Authenticate original FD9/P2c historical epochs, certify service availability and atomic durable raw/debug provenance and handle 4 MiB raw/debug and 512-step v2 cursor losslessly before ACTIVE same-build schema-2, minute cron or ACK. `commit_authorized=false`. No `_57.pkg` release, owner stable `_1` unchanged.

[Actual existing P2i test](../../scripts/test-p2i-original-preview-native.py) · [Original native live split](P2K8Q3C2_NATIVE_MIDCUT_RAW_DEBUG.md) · [Canonical plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).
