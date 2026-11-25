# TZ6v5 S10c2b3j — original FD9 bound engine → final S08d source (read-only)

**Accepted entry:** `main v0.6.5_224 cb5a3f47dbc512374223ac75afefef8fe56c2c17`,
[PR #1345](https://github.com/Tolian82/os-zapret2-restyle/pull/1345),
[postmerge native Stage5](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45662835271)
5/5 PASS. The **new** `v0.6.5_225` is a source candidate until its exact-head CI.
[S10 #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319) remains OPEN/NO-GO; S11 blocked.

## One original source, one original engine reader, zero physical permission

The installed original shell `shared_apply_original_source_gate` already streams
13 exact original loaded values through NUL-delimited stdin, under the original
FD9; the existing pure S07/S08c verifier `qualify_source_to_managed` can
compute a typed S08d snapshot **only** from a final sealed original root.
Its former `engine_version` parameter was supplied by detached tests, not by
a native original engine producer.

This step adds a **strict opt-in** `--sealed --s10-effective` suffix to that
same backend executable (all/list: operation ID + 2 flags; auto: operation ID +
the original PHP candidate SHA256 + 2 flags). The only bound engine source is
the already accepted `extra_resources_upstream_guard.native_bound_engine_for_s10_readback()`:
fixed FreeBSD root owner, inherited FD9, exact setup-owned three-line release
marker, tag=HEAD, binary ELF SHA, no unfinished setup and repeated inode/mode
readback. This code imports that existing guard; it cannot accept a caller
version, plugin revision, arbitrary root path, legacy one-line marker or
external receipt. Before and after the original sealed S07/S08c/S08d read,
the same bound identity is re-attested. If it changes, refuse with a fixed
content-free code.

On success, the existing original `native_original_fd9` (under the same
lock) compiles exactly one S08d `EffectiveSnapshot` from the same original
source and **checked** upstream version; its argv SHA must equal the authentic
S08c original argv, generation and seal SHA must match, and permissions must
still be `authorization=NONE, physical_transition_allowed=false`. The
CLI emits only `S10_ORIGINAL_EFFECTIVE_INPUT_READ_ONLY=<sha256>`. It does not
persist a receipt or authorize any physical transition; the typed receipt
stays in memory, not in a new journal or Config writer.

Ordinary preseal/sealed calls are byte-for-byte compatible, and the existing
shared Apply never switches to strict S10 by default. The original shell
accepts one additional argument solely to allow this opt-in read-only path
to be invoked **when a later S10 owner explicitly qualifies its PREPARED
candidate**. Existing `manifest-unbound` refusal and the bound
PREPARED→ACTIVATING gate remain closed; there is no new Start/Stop, PID/IPFW,
WAN, Found P1/ACK, config.xml or mutable hostlist mutation.

## Acceptance & next step

Regression uses the **actual original P2e sealed producer** and its real
S07/S08c/Voice/IPFW/auto-schema3 outputs for all/list/auto, with a simulated
read-only installed-bound identity (not a simulated physical activation).
Tests reject malformed flags, absent FD9, legacy/forged engine identity,
seal/argv/source drift and engine digest changes between two observations.
Original shell syntax and existing legacy G03/Voice unaffected; native
tests prove the original executable and renderer boundaries.

**Still needed:** connect this read-only receipt inside a validated original
`PREPARED` operation and bind the exact S09 immutable candidate through the
single original WAL. Prove previous active owner, WAN, Config, Found P1 CAS/ACK,
crash-safe physical root swap and rollback before enabling ANY
PREPARED→ACTIVATING. A stable SHA-only preview is not a live-owner proof.
