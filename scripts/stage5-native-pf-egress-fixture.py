#!/usr/bin/env python3
"""Native PF egress on ONE disposable OPNsense Stage 5 guest, never an owner device.

A stock single-vtnet0 VM can acquire an unscoped antispoof host block after
Apply. This test-only fixture uses OPNsense Config/MVC Filter and official
filter reload; pinned host TCP/UDP 53/443, including the loopback-arrival
check, are verified. No pfctl edits, PF disable or production code changes.
"""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

IP = "192.168.122.10"
HERE = Path(__file__).resolve().parent
PHP = r'''require_once('script/load_phalcon.php');
$config = \OPNsense\Core\Config::getInstance();
$config->lock();
try {
    $root = $config->object();
    $iface = null; $matches = 0;
    foreach ($root->interfaces->children() as $key => $detail) {
        if ((string)$detail->if === 'vtnet0') { $iface = (string)$key; $matches++; }
    }
    if ($matches !== 1 || !in_array($iface, ['lan','wan'], true)) {
        throw new \RuntimeException('UNQUALIFIED_TEST_NIC_MAPPING');
    }
    $model = new \OPNsense\Firewall\Filter();
    foreach ($model->rules->rule->iterateItems() as $item) {
        if (strpos((string)$item->description, 'ZAPRET2-CI-STAGE5-EGRESS') !== false) {
            throw new \RuntimeException('DUPLICATE_TEST_RULE');
        }
    }
    foreach (['443','53'] as $port) {
        foreach (['in','out'] as $direction) {
        $rule = $model->rules->rule->add();
        $rule->enabled = '1';
        $rule->action = 'pass';
        $rule->quick = '1';
        $rule->direction = $direction;
        $rule->ipprotocol = 'inet';
        $rule->protocol = 'TCP/UDP';
        // The host can enter PF via lo0 before outbound vtnet0.
        // OPNsense InterfaceField excludes lo0: float only the exact CI
        // source and two destination ports for the inbound direction.
        $rule->interface = $direction === 'out' ? $iface : '';
        $rule->source_net = '192.168.122.10';
        $rule->destination_net = 'any';
        $rule->destination_port = $port;
        $rule->description = 'ZAPRET2-CI-STAGE5-EGRESS-' . $port . '-' . $direction;
        }
    }
    if (!$model->serializeToConfig()) {
        throw new \RuntimeException('MODEL_SERIALIZE_REFUSED');
    }
    $config->save(['description'=>'Disposable Stage 5 PF egress']);
    echo 'PASS_DISPOSABLE_PF_MODEL_SAVED';
} catch (\Throwable $e) {
    fwrite(STDERR, 'CI_PF_FIXTURE_REFUSED:' . get_class($e) . "\n");
    exit(73);
} finally { $config->unlock(); }
'''


class Refusal(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Refusal(why)


def cmd(argv, timeout=30):
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Refusal("CI_PF_COMMAND_UNAVAILABLE:" + argv[0]) from None
    need(p.returncode == 0, "CI_PF_COMMAND_REFUSED:" + argv[0])
    return p.stdout


def validate_scope(env, nic, routes, identity):
    for key, value in (
        ("GITHUB_ACTIONS", "true"),
        ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK", "1"),
        ("ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE", "1"),
        ("ZAPRET2_STAGE5_RUNNING_VOICE_ARTIFACT", "1"),
    ):
        need(env.get(key) == value, "CI_PF_DISPOSABLE_OPTIN_MISSING:" + key)
    need("PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY" in identity,
         "CI_PF_NOT_FRESH_GUEST")
    need(re.search(r"(?m)^\s*inet\s+192\.168\.122\.10\s+netmask\s+", nic),
         "CI_PF_NOT_PINNED_VTNET0_IP")
    need(re.search(r"(?m)^default\s+192\.168\.122\.2\s+\S+\s+vtnet0\b", routes),
         "CI_PF_NOT_PINNED_DEFAULT_ROUTE")


def verify_pf_rules(rules):
    for direction in ("in", "out"):
        prefix = ("pass out quick on vtnet0 " if direction == "out"
                  else "pass in quick ")
        rows = [x for x in rules.splitlines()
                if x.startswith(prefix) and IP in x]
        need(any(re.search(r"\b(443|https)\b", x) for x in rows),
             "CI_PF_NO_NATIVE_443_" + direction.upper())
        need(any(re.search(r"\b(53|domain)\b", x) for x in rows),
             "CI_PF_NO_NATIVE_53_" + direction.upper())


def ipv4_dns(host):
    """Read-only resolver observation; never substitute IPs for worker DNS."""
    try:
        rows = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)
        ips = sorted({row[4][0] for row in rows})
        return {"status": "resolved", "ipv4": ips[:5]}
    except OSError as exc:
        return {"status": "failure", "error_class": type(exc).__name__,
                "error_number": exc.errno}


def resolver_nameservers():
    # Report only numeric resolver addresses; no search domains or tokens.
    try:
        lines = Path("/etc/resolv.conf").read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return ["unavailable"]
    return [part[1] for line in lines[:40]
            if (part := line.strip().split()) and len(part) == 2
            and part[0] == "nameserver" and
            re.fullmatch(r"[0-9a-fA-F:.]+", part[1])][:6]


def direct_ipv4_tcp(ip):
    """Diagnostic only: DOES NOT satisfy worker DNS/HTTPS acceptance."""
    try:
        with socket.create_connection((ip, 443), timeout=5):
            return "tcp_connected"
    except OSError as exc:
        return type(exc).__name__ + ":errno=" + str(exc.errno)


def select_scoped_pf_counters(output):
    """PF verbose output prefixes rule lines with @NN; preserve nearby counters."""
    rows = output.splitlines()
    selected = []
    for i, line in enumerate(rows):
        if IP not in line:
            continue
        if not re.match(r"^\s*(?:@\d+\s+)?(?:pass|block)\s", line):
            continue
        selected.append(" ".join(rows[i:i + 4])[:600])
    return selected[:12]


def scoped_pf_rule_counters():
    """Read-only selected PF rule/counter headers; no full config or packet data."""
    try:
        p = subprocess.run(["/sbin/pfctl", "-vvsr"], capture_output=True,
                           text=True, check=False, timeout=8)
        if p.returncode != 0:
            return ["pfctl_return_code=" + str(p.returncode)]
        return select_scoped_pf_counters(p.stdout)
    except (OSError, subprocess.TimeoutExpired):
        return ["pfctl_unavailable"]


def execute():
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD",
         "CI_PF_NOT_FREEBSD_ROOT")
    identity = cmd([sys.executable, str(HERE / "stage0-opnsense-guest-readonly.py")])
    validate_scope(os.environ, cmd(["/sbin/ifconfig", "vtnet0"]),
                   cmd(["/usr/bin/netstat", "-rn", "-f", "inet"]), identity)
    baseline = {host: ipv4_dns(host)
                for host in ("api.github.com", "codeload.github.com")}
    need(all(row["status"] == "resolved" and row["ipv4"]
             for row in baseline.values()), "CI_PF_PRE_RELOAD_DNS_BASELINE_UNAVAILABLE")
    need("PASS_DISPOSABLE_PF_MODEL_SAVED" in
         cmd(["/usr/local/bin/php", "-r", PHP], timeout=90),
         "CI_PF_MODEL_NOT_SAVED")
    cmd(["/usr/local/sbin/configctl", "filter", "reload"], timeout=120)
    need(cmd(["/sbin/pfctl", "-s", "info"]).startswith("Status: Enabled"),
         "CI_PF_NOT_ENABLED")
    verify_pf_rules(cmd(["/sbin/pfctl", "-sr"]))
    # DNS + TCP are both mandatory. Direct pre-resolved-IP TCP is only a
    # bounded diagnostic when native DNS fails, NEVER an Install substitute.
    post = {host: ipv4_dns(host) for host in baseline}
    if any(row["status"] != "resolved" or not row["ipv4"]
           for row in post.values()):
        diag = {"dns_before_reload": baseline, "dns_after_reload": post,
                "numeric_resolvers": resolver_nameservers(),
                "tcp_pre_resolved": {
                    host: direct_ipv4_tcp(row["ipv4"][0])
                    for host, row in baseline.items()}}
        print("STAGE5_CI_PF_DNS_DIAGNOSTICS=" + json.dumps(diag, sort_keys=True),
              file=sys.stderr, flush=True)
        raise Refusal("CI_PF_POST_RELOAD_DNS_UNAVAILABLE")
    for host in post:
        try:
            with socket.create_connection((host, 443), timeout=8):
                pass
        except OSError as exc:
            diag = {
                "hostname": host, "dns_before_reload": baseline[host],
                "dns_after_reload": post[host],
                "raw_ipv4_tcp": direct_ipv4_tcp(post[host]["ipv4"][0]),
                "native_pf_rule_counters": scoped_pf_rule_counters(),
            }
            print("STAGE5_CI_PF_TCP_DIAGNOSTICS=" +
                  json.dumps(diag, sort_keys=True), file=sys.stderr, flush=True)
            raise Refusal("CI_PF_NETWORK_UNAVAILABLE:" + host +
                          ":errno=" + str(exc.errno) +
                          ":class=" + type(exc).__name__) from None
    print("STAGE5_CI_NATIVE_PF_EGRESS=" + json.dumps({
        "status": "PASS_DISPOSABLE_STOCK_PF_SCOPED_EGRESS",
        "host": IP, "ports": [53, 443], "native_filter": True,
        "pf_enabled": True, "owner_appliance_modified": False,
    }, sort_keys=True))


def self_test():
    env = dict(GITHUB_ACTIONS="true",
               ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK="1",
               ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE="1",
               ZAPRET2_STAGE5_RUNNING_VOICE_ARTIFACT="1")
    nic = "vtnet0:\n inet 192.168.122.10 netmask 0xffffff00\n"
    route = "default 192.168.122.2 UGS vtnet0\n"
    identity = "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY"
    validate_scope(env, nic, route, identity)
    for inp, n, r in (({**env, "GITHUB_ACTIONS": "false"}, nic, route),
                      (env, nic.replace(IP, "192.168.122.11"), route),
                      (env, nic, route.replace("192.168.122.2", "10.0.0.1"))):
        try:
            validate_scope(inp, n, r, identity)
            raise AssertionError("unqualified CI guest accepted")
        except Refusal:
            pass
    verify_pf_rules("pass out quick on vtnet0 inet proto tcp "
                    "from 192.168.122.10 to any port = https\n"
                    "pass out quick on vtnet0 inet proto udp "
                    "from 192.168.122.10 to any port = domain\n"
                    "pass in quick inet proto tcp from 192.168.122.10 "
                    "to any port = https\n"
                    "pass in quick inet proto udp from 192.168.122.10 "
                    "to any port = domain\n")
    try:
        verify_pf_rules("block drop in log inet from 192.168.122.10 to any")
        raise AssertionError("missing native rules accepted")
    except Refusal:
        pass
    assert "serializeToConfig()" in PHP and "config->save" in PHP
    assert ipv4_dns is not None and direct_ipv4_tcp is not None
    assert resolver_nameservers is not None
    assert scoped_pf_rule_counters is not None
    assert len(select_scoped_pf_counters(
        "@6 block drop in log inet from 192.168.122.10 to any\n"
        "  [ Evaluations: 10 Packets: 2 Bytes: 128 ]\n"
        "@18 pass in quick inet proto tcp from 192.168.122.10 to any port = https\n"
        "  [ Evaluations: 10 Packets: 1 Bytes: 64 ]\n"
    )) == 2
    print("PASS_STAGE5_CI_NATIVE_PF_EGRESS_NEGATIVE_SCOPE_AND_SHAPE")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif not sys.argv[1:]:
            execute()
        else:
            raise Refusal("CI_PF_BAD_ARGUMENTS")
    except Refusal as e:
        print("STAGE5_CI_NATIVE_PF_EGRESS=REFUSED:" + str(e), file=sys.stderr)
        sys.exit(2)
