#!/usr/bin/env python3
"""Bounded FreeBSD IPFW adapter for shared Strategies/Voice firewall work.

The common firewall invokes the shared release path only under the existing
lifecycle FD9. The caller retains the previously installed release and table
snapshots until its whole-runtime commit. Public Apply is integrated separately.
The class still defaults to read-only; importing the module touches no kernel.

No shell execution, arbitrary table/rule names, unbounded subprocess output,
or automatic adoption of existing/foreign rule numbers is permitted.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
from typing import Callable, Sequence

from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, VoiceFirewallError,
    prepare_desired, apply_transaction, rollback_uncommitted,
    cleanup_committed, verify_prior_state,
)

MAX_IPFW_OUTPUT = 2 * 1024 * 1024
MAX_LINES = 8192
MAX_TABLE_ENTRIES = 4096
MAX_ARGS = 24
RULE_LINE = re.compile(r"^\s*([0-9]{1,5})\s+(.+?)\s*$")
TABLE_ENTRY = re.compile(r"^\s*(\S+)(?:\s+([0-9]+))?\s*$")
INTERFACE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
NUMERIC_PORTS = re.compile(r"^[0-9,-]{1,1024}$")
# FreeBSD ipfw table info for an absent table varies across versions.
# Only these explicit errors mean nonexistence; any other error fails closed.
MISSING_TABLE = re.compile(
    r"(table.+(?:does not exist|not found|no such table)|"
    r"(?:does not exist|no such table).+table)",
    re.IGNORECASE,
)


class IPFWAdapterError(VoiceFirewallError):
    pass


def require_lifecycle_lock() -> None:
    """Attest the existing common FD9; never acquire a separate lock."""
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        raise IPFWAdapterError("native IPFW actions require FreeBSD root")
    lock = "/var/run/zapret2-lifecycle.lock"
    try:
        held, actual = os.fstat(9), os.stat(lock, follow_symlinks=False)
    except OSError as error:
        raise IPFWAdapterError("existing lifecycle FD9 is required") from error
    if not stat.S_ISREG(actual.st_mode) or actual.st_uid != 0 or \
       actual.st_dev != held.st_dev or actual.st_ino != held.st_ino:
        raise IPFWAdapterError("FD9 is not the existing Zapret2 lifecycle lock")
    probe = os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
        else:
            fcntl.flock(probe, fcntl.LOCK_UN)
            raise IPFWAdapterError("FD9 is open but the lifecycle lock is not held")
    finally:
        os.close(probe)


def checked_table_name(name: str) -> str:
    if name not in (
        TABLE_PREFIX + service + suffix
        for service in SERVICES
        for suffix in ("", "_stage")
    ):
        raise IPFWAdapterError("table is outside Voice-owned name allowlist")
    return name


def checked_rule_number(number: int, first: int, last: int) -> int:
    if type(number) is not int or not first <= number <= last <= 65534:
        raise IPFWAdapterError("rule number outside plugin-owned interval")
    return number


def checked_ipv4(value: str) -> str:
    if not isinstance(value, str):
        raise IPFWAdapterError("IPFW address must be a string")
    try:
        net = ipaddress.IPv4Network(
            value if "/" in value else value + "/32", strict=True
        )
    except ValueError as error:
        raise IPFWAdapterError("invalid Voice IPv4/CIDR") from error
    canon = str(net) if "/" in value else str(net.network_address)
    if value != canon:
        raise IPFWAdapterError("noncanonical Voice IPv4/CIDR")
    return canon


def checked_rule_argv(argv: Sequence[str]) -> list[str]:
    if not isinstance(argv, (list, tuple)) or not 14 <= len(argv) <= 15 or any(
        not isinstance(token, str) for token in argv
    ):
        raise IPFWAdapterError("unexpected owned rule structure")
    if argv[:6] != ["divert", argv[1], argv[2], "from", "any", "to"] or \
       not argv[1].isdecimal() or not 1 <= int(argv[1]) <= 65535 or \
       argv[2] not in ("udp", "tcp"):
        raise IPFWAdapterError("invalid IPFW divert/protocol")
    if argv[-7:-1] != ["out", "not", "diverted", "not", "sockarg", "xmit"] or \
       not INTERFACE.fullmatch(argv[-1]):
        raise IPFWAdapterError("unsafe WAN or missing divert loop guard")
    if argv[6] == "any":
        if len(argv) != 15:
            raise IPFWAdapterError("ordinary rule requires a port selector")
    elif argv[6] not in (f"table({TABLE_PREFIX}{service})" for service in SERVICES) or \
         argv[2] != "udp":
        raise IPFWAdapterError("destination scope outside Voice IPv4 tables")
    if len(argv) == 15:
        selector = argv[7]
        if not NUMERIC_PORTS.fullmatch(selector):
            raise IPFWAdapterError("unsafe UDP/TCP port selector")
        for token in selector.split(","):
            terms = token.split("-")
            if not 1 <= len(terms) <= 2 or any(
                not part.isdecimal() or not 1 <= int(part) <= 65535 for part in terms
            ) or int(terms[0]) > int(terms[-1]):
                raise IPFWAdapterError("invalid UDP/TCP port interval")
    return list(argv)


class FreeBSDIPFWAdapter:
    """Narrow IPFW process adapter with injectable runner for CI fixtures."""

    def __init__(self, rule_base: int, rule_max: int,
                 ipfw_binary: str = "/sbin/ipfw",
                 *, allow_mutations: bool = False,
                 runner: Callable | None = None):
        if type(rule_base) is not int or type(rule_max) is not int or \
           not 1 <= rule_base <= rule_max <= 65534:
            raise IPFWAdapterError("invalid Voice owned rule interval")
        if ipfw_binary != "/sbin/ipfw":
            raise IPFWAdapterError("unsupported IPFW executable path")
        self.rule_base, self.rule_max = rule_base, rule_max
        self.binary = ipfw_binary
        self.allow_mutations = allow_mutations
        self.runner = runner or subprocess.run

    def _run(self, *args: str, modifying: bool = False, allow_missing: bool = False):
        if modifying and not self.allow_mutations:
            raise IPFWAdapterError("Voice adapter is read-only until lifecycle preflight")
        if len(args) > MAX_ARGS or any(
            not isinstance(x, str) or not x or "\x00" in x for x in args
        ):
            raise IPFWAdapterError("invalid IPFW command tokens")
        result = self.runner(
            [self.binary, *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15, check=False
        )
        if len(result.stdout) + len(result.stderr) > MAX_IPFW_OUTPUT:
            raise IPFWAdapterError("IPFW command output exceeds bound")
        if result.returncode != 0:
            if allow_missing and MISSING_TABLE.search(result.stderr):
                return None
            raise IPFWAdapterError("IPFW command failed: operation not completed")
        return result.stdout

    def _parse_rule_listing(self, text: str) -> dict[int, list[str]]:
        lines = text.splitlines()
        if len(lines) > MAX_LINES:
            raise IPFWAdapterError("IPFW rule listing is too large")
        rules: dict[int, list[str]] = {}
        for line in lines:
            if not line.strip():
                continue
            match = RULE_LINE.fullmatch(line)
            if match is None:
                raise IPFWAdapterError("unexpected IPFW list format")
            number, body = int(match.group(1)), match.group(2)
            if not self.rule_base <= number <= self.rule_max:
                continue
            if number in rules:
                raise IPFWAdapterError("duplicate IPFW rule number")
            # FreeBSD normalizes rules in 'ipfw list'; unsupported syntax
            # must NOT be accepted as plugin-owned or silently discarded.
            words = body.split()
            rules[number] = checked_rule_argv(words)
        return rules

    def list_rules(self, first: int, last: int) -> dict[int, list[str]]:
        if first != self.rule_base or last != self.rule_max:
            raise IPFWAdapterError("Voice requested rules outside owned range")
        output = self._run("-q", "list")
        return self._parse_rule_listing(output)

    def get_table(self, name: str) -> list[str] | None:
        name = checked_table_name(name)
        info = self._run("table", name, "info", allow_missing=True)
        if info is None:
            return None
        # Different installed table kinds (flow, iface, number) must not be
        # adopted as Voice IPv4 destination tables.
        if not re.search(r"(?im)\btype\s*:\s*addr\b", info):
            raise IPFWAdapterError("existing IPFW table is not address type")
        output = self._run("table", name, "list")
        values: list[str] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            match = TABLE_ENTRY.fullmatch(line)
            if not match:
                raise IPFWAdapterError("unexpected IPFW table listing format")
            raw_address = match.group(1)
            # FreeBSD often prints single-host keys as A.B.C.D/32 even
            # if the plugin's normalized managed file stores A.B.C.D.
            address = (raw_address[:-3] if raw_address.endswith("/32") else raw_address)
            address = checked_ipv4(address)
            if address in values:
                raise IPFWAdapterError("duplicate IPv4 in IPFW table")
            values.append(address)
            if len(values) > MAX_TABLE_ENTRIES:
                raise IPFWAdapterError("IPFW table exceeds configured bounds")
        return values

    def create_table(self, name: str) -> None:
        self._run("-q", "table", checked_table_name(name), "create", "type", "addr",
                  modifying=True)

    def destroy_table(self, name: str) -> None:
        self._run("-q", "table", checked_table_name(name), "destroy", modifying=True)

    def add_table_entry(self, name: str, address: str) -> None:
        self._run("-q", "table", checked_table_name(name), "add",
                  checked_ipv4(address), modifying=True)

    def swap_tables(self, active: str, stage: str) -> None:
        if not (active.startswith(TABLE_PREFIX) and stage == active + "_stage" and
                active in (TABLE_PREFIX + service for service in SERVICES)):
            raise IPFWAdapterError("invalid Voice table swap pair")
        self._run("-q", "table", active, "swap", stage, modifying=True)

    def delete_rule(self, number: int) -> None:
        number = checked_rule_number(number, self.rule_base, self.rule_max)
        self._run("-q", "delete", str(number), modifying=True)

    def add_rule(self, number: int, argv: Sequence[str]) -> None:
        number = checked_rule_number(number, self.rule_base, self.rule_max)
        arguments = checked_rule_argv(argv)
        self._run("-qf", "add", str(number), *arguments, modifying=True)


def _verify_shared_voice_engine(release: Path, plan: dict, read) -> None:
    """Bind destination-scoped Voice IPFW to the ACTUAL single-engine argv.

    Voice STUN has its own table-scoped UDP divert rules. The ordinary
    tcp/udp-ports artifacts intentionally exclude Voice: adding wildcard
    STUN there would divert ALL UDP destinations. Before any IPFW mutation,
    prove each saved Voice profile occurs first and unchanged in both the
    merged traffic and the generated one-engine argument file.
    """
    from voice_traffic_merge import profile_tokens
    from voice_profile_compiler import parse_ports

    profiles = plan.get("profiles")
    capture = plan.get("capture")
    if not isinstance(profiles, list) or len(profiles) > len(SERVICES) or (
        not isinstance(capture, dict)
        or not isinstance(capture.get("voice"), list)
        or len(capture["voice"]) != len(profiles)
    ):
        raise IPFWAdapterError("invalid Voice profiles/capture in common release")
    traffic = read("traffic.conf").decode("utf-8")
    argv = read("dvtws.args").decode("utf-8")
    if not traffic.strip() or not argv.strip() or traffic not in argv:
        raise IPFWAdapterError("common engine argv differs from merged Voice traffic")
    # ipfw's divert port is a SOCKET target, distinct from the UDP service
    # selectors checked below. The single native engine must listen on the
    # EXACT socket into which all Voice and Strategies rules divert.
    divert = capture.get("divert_port")
    source = plan.get("source")
    if type(divert) is not int or not 1 <= divert <= 65535 or (
        not isinstance(source, dict)
        or capture.get("logical_wan") != source.get("logical_wan")
        or capture.get("wan") != source.get("resolved_wan")
    ):
        raise IPFWAdapterError("common Voice capture WAN/divert evidence differs")
    argv_tokens = argv.split()
    socket_tokens = [token for token in argv_tokens if token.startswith("--port=")]
    if not argv_tokens or argv_tokens[0] != f"--port={divert}" or (
        socket_tokens != [f"--port={divert}"]
    ):
        raise IPFWAdapterError("common engine divert socket differs from shared IPFW")
    tokens = profile_tokens(traffic)
    if len(tokens) < len(profiles) + 1:
        raise IPFWAdapterError("missing ordinary Strategy after Voice profiles")
    for index, row in enumerate(profiles):
        if not isinstance(row, dict) or row.get("service") not in SERVICES or (
            row.get("enabled") is not True
            or not isinstance(row.get("profile_sha256"), str)
        ):
            raise IPFWAdapterError("untrusted Voice profile evidence")
        profile = tokens[index]
        service = row["service"]
        if index and SERVICES.index(service) <= SERVICES.index(profiles[index - 1]["service"]):
            raise IPFWAdapterError("out-of-order or duplicate Voice profile")
        if not profile or profile[0] != "--name=voice-" + service or (
            "--filter-l7=stun" not in profile
            or "--payload=stun" not in profile
            or "--filter-l3=ipv4" not in profile
            or "--ipset=" + str(row.get("ipset_path", "")) not in profile
        ) or hashlib.sha256("\n".join(profile).encode("ascii")).hexdigest() != (
            row["profile_sha256"]
        ):
            raise IPFWAdapterError("Voice kernel capture differs from common engine profile")
        # The _83 identity/hash witness alone is insufficient: a coherent
        # replacement of the engine profile and its hash must NOT retain
        # stale IPFW UDP ports or destination tables from the capture plan.
        owned = capture["voice"][index]
        if not isinstance(owned, dict) or owned.get("service") != service or (
            row.get("ipset_path") !=
            f"/usr/local/etc/zapret2/runtime-v2/managed/ipset-{service}.txt"
            or row.get("wan") != capture.get("logical_wan")
            or row.get("ports") != owned.get("ports")
            or row.get("targets") != owned.get("destinations")
            or row.get("target_count") != owned.get("destination_count")
            or row.get("target_count") != len(owned.get("destinations", []))
        ):
            raise IPFWAdapterError("Voice engine/IPFW port or destination scope differs")
        udp = [item.partition("=")[2] for item in profile
               if item.startswith("--filter-udp=")]
        if len(udp) != 1:
            raise IPFWAdapterError("Voice engine must have one UDP selector")
        try:
            parsed = [list(port) for port in parse_ports(udp[0], service)]
        except ValueError as error:
            raise IPFWAdapterError("Voice engine contains untrusted UDP ports") from error
        if parsed != owned["ports"]:
            raise IPFWAdapterError("Voice engine/IPFW UDP selector differs")
    for other in tokens[len(profiles):]:
        if any(arg.startswith("--name=voice-") for arg in other):
            raise IPFWAdapterError("ordinary Strategies reuse a Voice profile identity")
    if argv.count("--name=voice-") != len(profiles):
        raise IPFWAdapterError("unowned or duplicated Voice profile in common engine argv")


def shared_release_manifest(release: Path) -> dict:
    """Derive ownership from one trusted common release, without a second ledger.

    The lifecycle supplies the previously installed release or its retained
    backup. Directory names alone do not prove live ownership: every kernel
    object is compared with this manifest before mutation.
    """
    release = Path(release)
    if not release.is_absolute() or release.resolve() != release or not release.is_dir():
        raise IPFWAdapterError("shared firewall requires a regular absolute release")
    if release.stat().st_mode & 0o022:
        raise IPFWAdapterError("shared release is writable by another user")

    def read(name: str) -> bytes:
        path = release / name
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or \
           info.st_uid != release.stat().st_uid or info.st_size > 1_048_576 or \
           path.resolve() != path:
            raise IPFWAdapterError("unsafe shared firewall artifact")
        return path.read_bytes()

    plan = json.loads(read("voice-plan.json"))
    if not isinstance(plan, dict) or plan.get("schema") != 1:
        raise IPFWAdapterError("unsupported shared release plan")
    _verify_shared_voice_engine(release, plan, read)
    tcp = read("tcp-ports.txt").decode("utf-8").strip()
    udp = read("udp-ports.txt").decode("utf-8").strip()
    manifest = prepare_desired(plan.get("capture"), tcp, udp)
    hashes = plan.get("source", {}).get("ipset_sha256", {})
    for service in SERVICES:
        table = TABLE_PREFIX + service
        if table not in manifest["tables"]:
            continue
        raw = read(f"managed/ipset-{service}.txt")
        if raw.decode("utf-8") != "".join(value + "\n" for value in manifest["tables"][table]) or \
           hashlib.sha256(raw).hexdigest() != hashes.get(service):
            raise IPFWAdapterError("shared capture differs from managed IPSET")
    return manifest


def shared_firewall_action(adapter, action: str, previous: dict, desired: dict) -> None:
    """Common lifecycle's reversible firewall boundary; caller holds FD9.

    Install retains table snapshots until the whole runtime commits. A
    launcher/Config failure calls rollback before commit. Stop uses an empty
    desired manifest with the same rule interval. No Config, process, runtime
    writer or independent persistent operation is created here.
    """
    actions = {"install": apply_transaction, "rollback": rollback_uncommitted,
               "commit": cleanup_committed, "verify": verify_prior_state}
    if action == "verify-cleanup":
        # Read-only exact snapshot of partial post-COMMIT IPFW cleanup.
        # Missing stage tables are permitted, but any surviving stage
        # must match the sealed previous state. No foreign rule/table.
        from voice_firewall_transaction import plan_postcommit_cleanup
        plan_postcommit_cleanup(adapter, previous, desired)
    elif action == "verify-staged":
        # The new rules are installed but old IPSET contents MUST survive in
        # stage tables until the native Config save succeeds. Final verify
        # intentionally rejects these uncommitted rollback artifacts.
        from voice_firewall_transaction import plan_postcommit_cleanup
        plan_postcommit_cleanup(adapter, previous, desired)
        for name in desired["tables"]:
            if adapter.get_table(name + "_stage") is None:
                raise IPFWAdapterError("missing shared IPFW rollback stage table")
    elif action == "verify":
        actions[action](adapter, desired, desired)
    elif action in actions:
        actions[action](adapter, previous, desired)
    else:
        raise IPFWAdapterError("unknown shared firewall action")


def main(argv: list[str]) -> int:
    if len(argv) != 5 or argv[1] != "shared" or argv[2] not in {
        "install", "rollback", "commit", "verify", "verify-staged", "verify-cleanup"
    }:
        print("usage: voice_ipfw_adapter.py shared ACTION PREVIOUS_RELEASE DESIRED_RELEASE",
              file=sys.stderr)
        return 64
    try:
        require_lifecycle_lock()
        for argument in argv[3:]:
            if argument != "-" and Path(argument).stat().st_uid != 0:
                raise IPFWAdapterError("shared firewall requires root-owned releases")
        previous = None if argv[3] == "-" else shared_release_manifest(Path(argv[3]))
        desired = None if argv[4] == "-" else shared_release_manifest(Path(argv[4]))
        reference = desired if desired is not None else previous
        if reference is None:
            raise IPFWAdapterError("shared firewall requires a trusted release")
        empty = {"rule_base": reference["rule_base"], "rule_max": reference["rule_max"],
                 "rules": {}, "tables": {}}
        previous = empty if previous is None else previous
        desired = empty if desired is None else desired
        adapter = FreeBSDIPFWAdapter(reference["rule_base"], reference["rule_max"],
                                     allow_mutations=argv[2] in {"install", "rollback", "commit"})
        shared_firewall_action(adapter, argv[2], previous, desired)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
