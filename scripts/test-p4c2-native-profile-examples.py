#!/usr/bin/env python3
"""P4c2: bounded, isolated, *native* upstream v1.0.7 profile witness.

This is not a DPI-bypass test. Do not execute on an owner's appliance.
S0: --self-test (any host). S2: --native <temporary upstream checkout> from
an explicitly opted-in disposable GitHub OPNsense 26.7 FreeBSD guest only.
"""
from __future__ import annotations

import os
import platform
import stat
import subprocess
import sys
from pathlib import Path

UPSTREAM_COMMIT = "038c97e5819df10f8e8c22a2f1fffe57f2f7379b"
MARKER = "P4C2_NATIVE_EXAMPLES"
REQUIRED_LUA = ("zapret-lib.lua", "zapret-antidpi.lua")
MAX_OUTPUT = 1800

# Fixed, source-controlled complete profile actions. No list expansion,
# additional resources, user payloads, unknown --lua-init files or WAN ports.
PROFILES: dict[str, tuple[str, ...]] = {
    "http": (
        "--filter-tcp=80", "--filter-l7=http", "--payload=http_req",
        "--lua-desync=multisplit:pos=method+2",
    ),
    "tls": (
        "--filter-tcp=443", "--filter-l7=tls", "--payload=tls_client_hello",
        "--lua-desync=multisplit:pos=midsld:seqovl=1",
    ),
    "quic": (
        "--filter-udp=443", "--filter-l7=quic", "--payload=quic_initial",
        "--lua-desync=fake:blob=fake_default_quic:repeats=5",
    ),
}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def verify_catalog() -> None:
    require(set(PROFILES) == {"http", "tls", "quic"}, "PROFILE_SET_CHANGED")
    for name, args in PROFILES.items():
        require(len(args) == 4, "PROFILE_SIZE_" + name)
        require(args[0].startswith(("--filter-tcp=", "--filter-udp=")),
                "MISSING_L4_" + name)
        require(args[1].startswith("--filter-l7="), "MISSING_L7_" + name)
        require(args[2].startswith("--payload="), "MISSING_PAYLOAD_" + name)
        require(args[3].startswith("--lua-desync="), "MISSING_LUA_" + name)
        require(all("\n" not in a and "\r" not in a for a in args),
                "UNSAFE_PROFILE_LINE_" + name)
        require(all(not a.startswith("--port=") for a in args),
                "PROFILE_MUST_NOT_OWN_DIVERT_PORT")
    require("fake_default_quic" in PROFILES["quic"][-1], "QUIC_BLOB_UNKNOWN")


def guest_guard(checkout: Path) -> tuple[Path, Path]:
    require(os.environ.get("GITHUB_ACTIONS") == "true" and
            os.environ.get("ZAPRET2_P4C2_DISPOSABLE_NATIVE") == "1",
            "DISPOSABLE_CI_OPT_IN_REQUIRED")
    require(platform.system() == "FreeBSD" and os.geteuid() == 0,
            "FREEBSD_ROOT_GUEST_REQUIRED")
    # The checkout MUST be created inside the one-use guest /tmp. No
    # permitted /usr/local/etc/zapret2, /conf or installed runtime paths.
    require(not checkout.is_symlink(), "CHECKOUT_SYMLINK")
    root = checkout.resolve(strict=True)
    require(root.parent == Path("/tmp") and root.name.startswith("p4c2-native-"),
            "ISOLATED_TMP_CHECKOUT_REQUIRED")
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=8, check=True,
    ).stdout.strip()
    require(revision == UPSTREAM_COMMIT, "UPSTREAM_SHA_MISMATCH")
    engine = root / "nfq2/dvtws2"
    require(engine.is_file() and not engine.is_symlink() and
            bool(engine.stat().st_mode & stat.S_IXUSR),
            "BUILT_PINNED_DVTWS2_REQUIRED")
    for name in REQUIRED_LUA:
        path = root / "lua" / name
        require(path.is_file() and not path.is_symlink() and
                path.stat().st_size > 1000, "MISSING_NATIVE_LUA_" + name)
    return root, engine


def engine_args(root: Path, name: str) -> list[str]:
    require(name in PROFILES, "UNKNOWN_NATIVE_PROFILE")
    return [
        "--port=19897",
        "--lua-init=@" + str(root / "lua" / REQUIRED_LUA[0]),
        "--lua-init=@" + str(root / "lua" / REQUIRED_LUA[1]),
        # A checked real Lua global, not merely an existing script path.
        "--lua-init=assert(type(multisplit)=='function' and type(fake)=='function')",
        *PROFILES[name],
    ]


def run_native(root: Path, engine: Path) -> None:
    # Both execution modes are documented upstream: dry-run validates args
    # and file existence, but DOES NOT verify Lua correctness. intercept=0
    # runs initializers without creating NFQUEUE/divert interception.
    # Neither mode is used to generate or replay actual network packets.
    for name in PROFILES:
        args = engine_args(root, name)
        for phase, option in (("parse", "--dry-run"), ("lua-init", "--intercept=0")):
            proc = subprocess.run(
                [str(engine), *args, option],
                cwd=root, capture_output=True, timeout=12, check=False,
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout).decode(
                    "utf-8", errors="replace")[-MAX_OUTPUT:]
                raise RuntimeError(
                    f"{MARKER}_REFUSED:{name}:{phase}:rc={proc.returncode}:"
                    + detail.replace("\n", " ").replace("\r", " ")
                )
            print(f"{MARKER}_{name.upper()}_{phase.upper().replace('-', '_')}=PASS",
                  flush=True)
    # Deliberately no claim of the Lua handler running on a real packet,
    # working ISP bypass, or a voice call: those need separate replay.
    print(MARKER + "=PASS_NATIVE_PARSE_AND_LUA_INIT_ONLY", flush=True)


def self_test() -> None:
    verify_catalog()
    require(UPSTREAM_COMMIT == "038c97e5819df10f8e8c22a2f1fffe57f2f7379b",
            "PINNED_TAG_CHANGED")
    require(engine_args(Path("/tmp/p4c2-native-fixture"), "http")[-1].startswith(
            "--lua-desync=multisplit"), "HTTP_HANDLER_LOST")
    require(engine_args(Path("/tmp/p4c2-native-fixture"), "quic")[-1].endswith(
            "fake_default_quic:repeats=5"), "QUIC_HANDLER_LOST")
    require(all(not any(x in arg for x in ("/conf/", "/usr/local/etc/", "ssh", "curl"))
                for name in PROFILES for arg in PROFILES[name]),
            "UNSAFE_PROFILE_SCOPE")
    print(MARKER + "_SELF_TEST=PASS_NO_NATIVE_CLAIM")


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--native":
        verify_catalog()
        root, engine = guest_guard(Path(sys.argv[2]))
        run_native(root, engine)
        return 0
    raise ValueError("usage: --self-test | --native /tmp/p4c2-native-...checkout")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
        print(MARKER + "=REFUSED:" + str(exc), file=sys.stderr)
        raise SystemExit(2)
