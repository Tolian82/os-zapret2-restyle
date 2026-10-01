# 2026-10-01: owner-live Squid, sing-box, Zapret2, SSH and TNAS route inventory

**Type:** dated owner-provided appliance evidence; **not** a post-reboot test, a new media pass, or an action performed by the documentation writer.
**Operational recovery:** [Telegram lab operations](../../architecture/TELEGRAM_LAB_OPERATIONS.md).
**Underlying traffic design/history:** [Telegram traffic policy](../../architecture/TELEGRAM_TRAFFIC_POLICY.md).

The owner executed the listed commands on a live OPNsense installation and TOS 7 TNAS. The owner also copied the **full current sing-box JSON from its own GUI**. This evidence fixes provenance: the JSON is not a hypothetical suggested template, and the original one-time TCP policy installer is not the authority for the most recently owner-displayed GUI snapshot. No password or private SSH key is recorded here.

## OPNsense paths, processes and current UDP status

- The interactive root console is `csh/tcsh`; owner deliberately entered `/bin/sh` for the earlier POSIX key/script creation and `echo "$0"` confirmed `/bin/sh`. Prior shell errors arose from POSIX syntax pasted into csh; the installed POSIX route **file** is correct. `command -v ssh` printed `/usr/local/bin/ssh`; `command -v logger` printed `/usr/bin/logger`.
- `service -e | grep -E 'squid|sing-box'` printed `/usr/local/etc/rc.d/sing-box` and `/usr/local/etc/rc.d/squid`.
- `configctl proxy status`: `squid is running as pid 3976.` Multiple Squid processes listened at `127.0.0.1:3128`, `:3129`, `192.168.1.2:3128`, `127.0.0.1:3130`.
- `service sing-box rcvar`: `sing_box_enable="YES"`. Current sing-box process was listening at `*:1080`.
- `/usr/local/etc/rc.d/sing-box` exposes `# PROVIDE: sing_box`, `# REQUIRE: NETWORKING`, `rcvar="sing_box_enable"`, `command="/usr/local/bin/sing-box"`, `config="/usr/local/etc/sing-box/config.json"`.
- `pkg which /usr/local/etc/sing-box/config.json` and `pkg which /usr/local/etc/rc.d/sing-box` identified `os-sing-box-1.0.2`. Its package also ships `/usr/local/www/sing-box.php`, `/usr/local/www/sing-box_sub.php`, `/usr/local/etc/sing-box/sub/env`, `.../sub/template.json` and `/usr/local/opnsense/service/conf/actions.d/actions_sing-box.conf`. The latter has start/stop/restart/status and subscription-update; `/usr/bin/sing_box_sub` delegates to `/usr/local/etc/sing-box/sub/sub.sh`.
- Existing `/usr/local/etc/rc.syshook.d/start/20-zapret` is present. The repository source invokes `configctl zapret start`, not a persisted Voice request.
- Owner-live `configctl zapret status`: `zapret is running as pid 50205`.
- Owner-live Voice status **ON** (do not generalize this to after reboot):

```text
telegram_voice_poc.requested=on
telegram_voice_poc.effective=on
telegram_voice_poc.service=running
telegram_voice_poc.active_profile=on
telegram_voice_poc.strategy=stun-zero-fake-repeats-2
telegram_voice_poc.scope=telegram-ipv4-all-udp-ports
telegram_voice_poc.table=zapret2_tgvoice
telegram_voice_poc.table_present=yes
telegram_voice_poc.table_entries=14
telegram_voice_poc.stage_table=zapret2_tgvoice_stage
telegram_voice_poc.stage_table_present=no
telegram_voice_poc.rule=19000
telegram_voice_poc.rule_packets=60
telegram_voice_poc.rule_bytes=4080
```

Observed IPFW list:

```text
19000     60     4080 divert 989 udp from any to table(zapret2_tgvoice) out not diverted not sockarg xmit vtnet1
19001   1280    96712 divert 989 tcp from any to any 80,443,5222,8888 out not diverted not sockarg xmit vtnet1
19002      0        0 divert 989 udp from any to any 80,443,5222,8888 out not diverted not sockarg xmit vtnet1
```

**Crucial observed/implemented distinction:** Current Voice PoC ON is requested by `/var/run/zapret2-telegram-voice-poc.enabled`; on OPNsense reboot the file disappears and Voice ON is not restored by the existing ordinary Zapret boot hook. Source corroboration: [Voice helper](../../../src/opnsense/scripts/OPNsense/Zapret/backend/telegram_voice.sh), [native hook](../../../src/etc/rc.syshook.d/start/20-zapret). The October 1 actual current non-STUN reflector control did **not** establish media despite rule counters.

## Squid effective files, GUI provenance and firewall

The owner confirmed the parent `185.203.117.88:33128` is shown/configured in OPNsense Proxy GUI. Separately the effective config scan found the **only** `cache_peer` at `/usr/local/etc/squid/pre-auth/parentproxy.conf:1`, followed by `cache_peer_access` and `never_direct` lines 2–3. The GUI-to-file generation path has **not** been proven; keep that file. The main `squid.conf` contained `include /usr/local/etc/squid/pre-auth/*.conf` on line 84, `auth` line 119, `post-auth` line 136. `pkg which` did not identify the main or custom `pre-auth` files as package-owned. Live file list: `pre-auth/40-snmp.conf` (empty), `pre-auth/90-singbox-lan-v1.conf`, `pre-auth/dummy.conf`, `pre-auth/parentproxy.conf`, `post-auth/dummy.conf`.

The owner-provided PF NAT scan listed `rdr pass` for two PF alias tables `<Telegram>`, `<Telegram_IPs>` on **both** `vtnet0` and `tun_singbox`, TCP `http`→`127.0.0.1:3128`, TCP `https`→`127.0.0.1:3129`. The existing sing-box JSON has only SOCKS inbound, not an active demonstrated TUN mode. Successful earlier transparent LAN and SOCKS TCP/parent tests remain historical evidence; no new reboot or TCP probes were run for this inventory.

### Configuration file fingerprints

Owner-direct `sha256` snapshot; use to detect drift after planned reload/reboot rather than assuming the current system was reboot-tested:

| Path | SHA-256 |
|---|---|
| `/usr/local/etc/squid/pre-auth/parentproxy.conf` | `e396a20165f4d3b005cc6601c499382220ccd5470a56b0d0747e3bd7e20a5b34` |
| `/usr/local/etc/squid/pre-auth/90-singbox-lan-v1.conf` | `361f1512a99bf8786af045aec0588ccebd4801cc257827db4c6d83e110ac1fd0` |
| `/usr/local/etc/squid/singbox-lan-v1-ipv4.acl` | `1cc96aaa582f6fc1e3ce417f3c090881a3ad95c2b6bc25d6702ba0016ee52840` |
| `/usr/local/etc/sing-box/config.json` | `66d5c6f46b0e6ffaf3e5b03a3c94bece043aa7af811fc8e0ec883a173aeb3aa3` |

## Sing-box full GUI JSON

**Exact user-provided current GUI JSON**, including the dated `ip_cidr` values. This is a static snapshot, not a guaranteed current Telegram allocation or a subscription-refresh mechanism. Avoid independently altering/removing entries while documenting the lab.

```json
{
  "log": {
    "disabled": false,
    "level": "info",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "socks",
      "tag": "socks-in",
      "listen": "0.0.0.0",
      "listen_port": 1080
    }
  ],
  "outbounds": [
    {
      "type": "http",
      "tag": "squid-lan-v1",
      "server": "127.0.0.1",
      "server_port": 3130
    },
    {
      "type": "direct",
      "tag": "direct"
    }
  ],
  "route": {
    "default_domain_resolver": "lan-dns-v1",
    "rules": [
      {
        "inbound": ["socks-in"],
        "network": "tcp",
        "port": [80, 443],
        "action": "resolve",
        "server": "lan-dns-v1",
        "strategy": "prefer_ipv4"
      },
      {
        "inbound": ["socks-in"],
        "network": "tcp",
        "port": [80, 443],
        "ip_cidr": [
          "3.33.224.147/32",
          "5.22.249.99/32",
          "5.28.128.0/17",
          "8.6.112.0/32",
          "8.47.69.0/32",
          "13.248.169.48/32",
          "44.232.173.249/32",
          "45.43.186.0/24",
          "52.20.84.62/32",
          "52.40.42.113/32",
          "62.122.170.171/32",
          "65.49.214.20/32",
          "70.120.32.58/32",
          "76.223.54.146/32",
          "77.74.50.198/32",
          "79.170.40.4/32",
          "91.105.192.0/23",
          "91.108.4.0/22",
          "91.108.8.0/21",
          "91.108.16.0/21",
          "91.108.56.0/22",
          "95.161.64.0/20",
          "95.216.41.0/24",
          "95.216.186.40/32",
          "103.45.244.131/32",
          "103.224.212.210/32",
          "104.16.132.229/32",
          "104.16.133.229/32",
          "104.16.248.249/32",
          "104.16.249.249/32",
          "104.21.66.37/32",
          "104.21.68.64/32",
          "104.21.85.75/32",
          "104.196.2.43/32",
          "149.154.160.0/20",
          "151.101.246.62/32",
          "162.159.128.233/32",
          "162.159.129.233/32",
          "162.159.130.233/32",
          "162.159.130.234/32",
          "162.159.133.233/32",
          "162.159.133.234/32",
          "162.159.134.233/32",
          "162.159.134.234/32",
          "162.159.135.232/31",
          "162.159.135.234/32",
          "162.159.136.232/32",
          "162.159.136.234/32",
          "162.159.137.232/32",
          "162.159.138.232/32",
          "170.249.238.146/32",
          "172.67.155.218/32",
          "172.67.191.37/32",
          "172.67.203.133/32",
          "173.194.222.0/24",
          "185.76.151.0/24",
          "188.166.3.205/32",
          "202.146.223.58/32",
          "207.207.210.23/32",
          "207.207.210.36/32",
          "207.207.210.50/32"
        ],
        "action": "route",
        "outbound": "squid-lan-v1"
      },
      {
        "inbound": ["socks-in"],
        "network": "udp",
        "action": "route",
        "outbound": "direct"
      }
    ],
    "final": "direct"
  },
  "dns": {
    "servers": [
      {
        "type": "local",
        "tag": "lan-dns-v1"
      }
    ],
    "strategy": "prefer_ipv4"
  }
}
```

The array, structure and values above match the owner's GUI input; whitespace inside short single-line JSON arrays is normalized for readability and therefore the Markdown code fence is not claimed to have an identical byte-for-byte hash to the on-device JSON.

## Owner-live SSH setup and TNAS state

The owner generated an Ed25519 key on OPNsense `/root/.ssh/id_ed25519_tgvoice_lab` (0600) with public key `...pub`, fingerprint `SHA256:ymEtvjjSkD82sORfc3k5nVFJ0ZgmzFE0JaFard2b8zk`. On the first TNAS SSH `9222` connection OPNsense saw `SHA256:TmtT2KOiPHelGGUoOhwFxaF7DsdBBdgFxCTQdj0SVUQ`; owner later independently confirmed the same server fingerprint from TNAS `/etc/ssh/ssh_host_ed25519_key.pub`. Authorized key was appended without replacing existing keys at TNAS `$HOME/.ssh/authorized_keys`, prefixed `from="192.168.1.2",restrict`. A subsequent identity-only BatchMode SSH printed `uid=0(tolian) gid=0(tolian)` **without password**. Guard the private key as root-equivalent; do not publish or assume OPNsense configuration backups contain it.

An optional Docker command failed over SSH because its noninteractive PATH lacked the TNAS Docker directory. Owner interactive `type -a docker` and `readlink -f` confirmed `/Volume1/@apps/DockerEngine/dockerd/bin/docker`; the SSH failure was **not** evidence that the container was down. The route script needs no Docker.

TNAS owner-live:
- `ip -4 route get 91.108.13.10 from 192.168.1.100` → via `192.168.1.2 dev ovs_eth1`.
- `ip -4 route get 149.154.167.99 from 192.168.1.100` → via `192.168.1.2 dev ovs_eth1`.
- `docker inspect`: `status=running network=host restart=no`; **manual container start intended**.
- `systemctl is-enabled systemd-networkd` → `enabled`. `networkctl status ovs_eth1` → `Network File: /etc/systemd/network/10-eth1.network`, `192.168.1.100` via DHCP, ordinary default gateway `192.168.1.140`. Do not confuse it with the retired Telegram test exit; no default change authorized.
- After correcting `/usr/bin/ssh` to **`/usr/local/bin/ssh`** in the already-written 89-line route script and passing `/bin/sh -n`, the manual command `/bin/sh /root/tgvoice-lab/ensure-tnas-routes.sh` returned:

```text
OK: 91.108.13.10 already uses 192.168.1.2
OK: 149.154.167.99 already uses 192.168.1.2
EXIT=0
```

**Owner's later explicit decision:** This script is **manual-only after TNAS reboot**. Do not implement the previously proposed 5-minute Cron job, configd action, boot hook or container autostart; the existence of any exploratory action file was not confirmed. A current, still-open and different issue is auto-restoring OPNsense's selected **Voice ON** state after *OPNsense* reboot. The owner's demonstrated ON status is **not** persistent and **must** be rechecked/recovered manually until a separately verified solution exists.
