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
