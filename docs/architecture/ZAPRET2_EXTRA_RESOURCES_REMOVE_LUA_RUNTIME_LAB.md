# Remove Additional Resources — native Lua runtime isolation lab

**Status:** EXPERIMENTAL — NO RUNTIME PROOF / NO REMOVE AUTHORIZATION
**Increment:** v0.5.9_12, test-only FreeBSD 15 socket interposer and mock

## Original upstream call sequence

bol-van/zapret2 v1.0.6 in nfq2/nfqws.c calls rawsend_preinit() before lua_init() and lua_desync_functions_exist(). The FreeBSD nfq2/darkmagic.c tries PF_DIVERT + SOCK_RAW then falls back to AF_INET + SOCK_RAW + IPPROTO_DIVERT. An unsandboxed installed dvtws2 --intercept=0 is NOT a read-only Lua check; --dry-run does not run Lua.

## Exact experimental scope

scripts/fixtures/lua-init-no-network-shim.c dynamically intercepts only the upstream divert-socket patterns and substitutes harmless unconnected AF_UNIX datagram sockets. Other IPv4/IPv6/Divert sockets, IP connect/bind and every sendto are denied. scripts/test-freebsd-lua-no-network-shim.sh runs it on a synthetic mock engine only, with no real Lua or installed dvtws2. Tests run inside disposable FreeBSD 15 CI VM; the files under scripts are not shipped in the OPNsense package.

THIS INTERPOSER IS NOT A SECURITY SANDBOX. It can be bypassed by direct syscalls and must NEVER be used as a basis to execute the real installed binary on an appliance or to return compatible/authorized. Success means only that a mock divert-initialization path reached its synthetic Lua-stage marker without opening IP sockets.

## Mandatory gates before any REAL native Lua execution

1. Enforce disposable filesystem/kernel confinement before execution: a private FreeBSD jail with ip4=disable, ip6=disable, allow.raw_sockets=0, no host Config, resources, devices or writable runtime visible. Prove deny rules and teardown. Creating jails requires additional security review and itself has kernel namespace effects.
2. Pin exact installed dvtws2 hash/ABI, original FD9 locked saved Config, native dvtws.args and fully upstream-only Lua/BIN bytes. Never substitute unrelated Lua/luac or a patched engine binary for runtime proof.
3. Test actual engine lua_init, exported named lua_desync functions and transitive dependencies, including all --new profiles and BLOBs, without access to IPFW, service state or host network. Syntax-only, mock socket or Lua library ABI hints are NOT runtime proof.
4. Treat missing dependencies, dynamic imports, failed sandbox/engine execution, unsafe syscalls, race, crash, timeout, or any uncertainty as unknown/incompatible and authorized=false.
5. Stage 2 remains open until an isolated exact-engine proof passes; saved Voice (all five including meaningful disabled drafts) and combined transaction gate remain separate mandatory later milestones.

## Current evidence

FreeBSD 15 compiles the test-only shared library and a mock executable and checks that synthetic PF_DIVERT and legacy IPPROTO_DIVERT opens return AF_UNIX descriptors and that real network socket attempts and sendto are denied. This is NOT a jail, not actual Lua, not an engine test, and never a condition to delete files.

Only owner-approved source development; no appliance mutation, testing package publication or stable release.
## v0.5.9_13: kernel jail boundary experiment

The FreeBSD 15 CI executes scripts/test-freebsd-lua-jail-boundary.sh. It compiles the static native helper scripts/fixtures/lua-jail-native-boundary.c and checks that it *fails* outside jail, then runs it inside a new disposable private-root prison with ip4=disable, ip6=disable, allow.raw_sockets=0, allow.socket_af=0, allow.mount=0 and allow.sysvipc=0. The helper checks security.jail.jailed=1, a real canary existing only outside that jail root, denies PF_DIVERT and IPv4/IPv6 raw sockets and loopback binding, and requires AF_UNIX datagram creation. The test then removes jail and verifies it no longer exists.

These are kernel-enforced jail tests in a disposable CI VM, not on OPNsense; real dvtws2 and Lua are NOT executed, and no Lua sandbox validation is claimed. Future work must combine this kernel boundary with the separate mock shim without leaking host files or network. Do NOT run the shim alone on the appliance.

## Same-revision CI-only combined jail + synthetic shim experiment

`scripts/test-freebsd-lua-jail-shim-combined.sh` builds a static FreeBSD boundary probe and the existing dynamic mock/shim in a throwaway private jail root with only `libexec/ld-elf.so.1` and `lib/libc.so.7` staged. The statically linked probe verifies `security.jail.jailed=1`, host Config/canary invisibility, prohibited PF_DIVERT/raw IPv4/IPv6, IP bind refusal and AF_UNIX viability **without LD_PRELOAD**. The CI negative control executes the dynamic mock *inside jail without the shim* and requires the specific divert failure; the positive control repeats kernel checks, then the same static probe calls `execve("/mock-engine", ..., {"LD_PRELOAD=/no-net.so", ...})` only inside jail. The test requires the synthetic Lua-stage marker and cleans up the jail. No host jexec/sh/jail binary ever receives LD_PRELOAD, and the test never executes a real dvtws2, Lua or any installed resources/Config. The [exact-head FreeBSD15 PR #592 CI](https://github.com/Tolian82/os-zapret2-restyle/pull/592) reports `PASS: FreeBSD15 kernel jail + synthetic divert shim combined; no real engine or Lua; teardown complete`. Tests are disposable FreeBSD15 CI-only; they are not packaged. Neither combined mock success nor private-root isolation establishes real Lua exports/transitive dependency compatibility or authorizes deletion.

## v0.5.9_16: inert exact-input snapshot for eventual jail

`extra_resources_jail_inputs.py` is import-only; it does not offer a CLI or a production execution route. Caller must retain original native FD9/Config locks and Git HEAD upstream-only view, supply pinned engine/argv SHA256 and a lifecycle checker. It reuses native Lua/BIN reference validation and no-exec installed engine ELF SHA, copies bounded original engine, unmodified native argv and standard direct Lua/BIN into an owner-private, NON-EXECUTABLE context, checks source/staged bytes before and after consumer use, and removes the tree on exit. It cannot itself attest Git HEAD/FD9 provenance. No dynamic loader closure, argv path relocation, Lua transitive imports, FreeBSD jail creation or engine/Lua execution is implemented. Even a complete bundle is not runnable or authorized: `engine_lua_proof=not-run`, `compatibility=unknown`, `authorized=false`.

## v0.5.9_17: exact native direct Lua/BIN path relocation, NOT runnable

`extra_resources_jail_argv.py` uses the existing `extra_resources_lua_inputs._reference` pinned upstream resource provenance checker; it rewrites ONLY strict original native one-argument-per-line `--lua-init=@<upstream>/lua/<file>.lua` and `--blob=name:@<upstream>/files/fake/<file>.bin` into `/upstream/...` under the temporary private input tree. Original order and all `--new` profiles are preserved; inline Lua, non-file BLOB, traversal, symlinks and missing resources reject. Existing `_16` staged input context also creates `native/jailed-direct-resources.args` (non-executable), SHA-verifies it before and after use and removes it. Any other original paths, including native `--hostlist-exclude`, are NOT remapped and are counted as unresolved. This is NOT executable argv, not shared-library closure and not actual Lua/transitive/exports proof. Stage 2 remains OPEN, `engine_lua_proof=not-run`, `compatibility=unknown`, `authorized=false`.
