# Telegram laboratory: exact live configuration, boot and operator runbook

**Status:** owner-live inventory, 2026-10-01; separate laboratory, not plugin code.
**October 2 continuation:** [Matched real Windows/Android call PCAP/counter evidence](../verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md) records both clients P2P-disabled, clean owner-reported audio, Voice rule +99/+6624 and 18 extra WAN zero16 fakes, **but no inbound Telegram UDP and no proven UDP media**. This does not change startup or routing requirements. Owner-live outbound IPv4 PFIL order for that capture was **IPFW→PF**; re-check after later boots.

**Read first:** [dated owner evidence](../verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md) (including full sing-box JSON and file hashes); [traffic and recovery policy](TELEGRAM_TRAFFIC_POLICY.md); [current handoff](../START_HERE.md).

**Preserve existing working TCP configuration.** No reboot, Squid/sing-box reload, GUI Apply, plugin change or new automation was performed as part of this documentation work. Explicitly distinguish observed live state from unverified post-reboot behavior.

## Important shell and responsibility boundaries

**OPNsense interactive root console uses csh/tcsh by default.** Owner-facing console commands must be single-line **csh-compatible**. For deliberate multi-line POSIX scripting first enter `/bin/sh` (present and successfully used on this specific appliance: `echo "$0"` returned `/bin/sh`), and afterwards return with `exit`. Do not paste POSIX `KEY=...`, `if [ ... ]; then ... fi` or heredocs into csh. Repository source scripts use `#!/bin/sh` by project convention, a *different execution context*. Critical tested FreeBSD-specific executable locations: **`/usr/local/bin/ssh`**, NOT `/usr/bin/ssh`; `/usr/bin/logger` is correct.

**Separate ownership:** code/config model/GUI/service lifecycle of `os-zapret2-restyle` changes only via GitHub branch/PR/CI/merge. Independent lab Squid/sing-box/PF/SSH/routes may be maintained through OPNsense's native configuration or GUI where verified. Do not add an ad-hoc Zapret2 boot hook or a separate plugin TCP/Voice controller. The approved plugin product plan remains only the three sequential UDP stages.

## Verified live OPNsense components and startup

| Component | Source, startup, files | Exact live observation; limitation |
|---|---|---|
| Squid | Native OPNsense Proxy GUI is used, including the parent's GUI entry (owner-confirmed). Main effective `/usr/local/etc/squid/squid.conf`; rc `/usr/local/etc/rc.d/squid`; `configctl proxy status`. | Running (status reported pid 3976). `service -e` listed Squid. The main config includes `pre-auth/*.conf` line 84, `auth/*.conf` line 119, `post-auth/*.conf` line 136. Not package-owned per `pkg which`. GUI regeneration/reboot of all custom extensions **not tested**. |
| Parent proxy | `/usr/local/etc/squid/pre-auth/parentproxy.conf` | Owner confirmed parent configured in GUI, but its relationship to this particular file's **generation** is not established. The *only* `cache_peer` in recursive owner scan of Squid `*.conf`: `185.203.117.88 parent 33128`; also `cache_peer_access` and `never_direct`. **Do not remove this file** based on GUI appearance alone. |
| Squid TCP LAN/interception | Main `squid.conf` + existing PF redirects | Actual listening ports: `127.0.0.1:3128`, `127.0.0.1:3129`, `192.168.1.2:3128`. |
| sing-box→Squid | Independent lab file `/usr/local/etc/squid/pre-auth/90-singbox-lan-v1.conf` and ACL snapshot `/usr/local/etc/squid/singbox-lan-v1-ipv4.acl` | Actual loopback CONNECT listener `127.0.0.1:3130` present in Squid; additional ACL is a **static snapshot**, not an automatically refreshed PF alias list. GUI/reboot persistence not yet tested. |
| Additional Squid snippets | `pre-auth/40-snmp.conf` (0 bytes), `pre-auth/dummy.conf`, `post-auth/dummy.conf` | Observed present; no deletion/change intended. |
| sing-box | Existing `os-sing-box-1.0.2` GUI `/usr/local/www/sing-box.php` edits/views `/usr/local/etc/sing-box/config.json`; rc `/usr/local/etc/rc.d/sing-box`; configd `/usr/local/opnsense/service/conf/actions.d/actions_sing-box.conf`. | `service sing-box rcvar` = `sing_box_enable="YES"`, service appears in `service -e`, process listens `*:1080`. Package owns both `config.json` and rc script. GUI owner displayed the exact JSON preserved in [evidence](../verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md#sing-box-full-gui-json). |
| PF/NAT | Effective `pfctl -sn` | `rdr pass` for `<Telegram>` and `<Telegram_IPs>`, TCP 80→3128 and TCP 443→3129, on LAN `vtnet0` and legacy `tun_singbox`. Today's sing-box is **SOCKS**, not a proven active TUN; legacy rules do not prove TUN traffic. Exact GUI persistence of rules not yet measured. |
| Zapret2 normal service | Package boot hook `/usr/local/etc/rc.syshook.d/start/20-zapret` → `configctl zapret start`; existing `configctl zapret status`. | Live status: `zapret is running as pid 50205`. Existing hook starts ordinary service, **not** the experimental Voice-helper ON request. |
| Telegram Voice UDP | `configctl zapret telegram_voice_enable|disable|status`; ephemeral `/var/run/zapret2-telegram-voice-poc.enabled` | Owner directly measured **requested=on, effective=on, active_profile=on**, current `stun-zero-fake-repeats-2`, 14 Telegram IPSET entries, rule 19000, 60 packets / 4080 bytes. Only interception proven; media **not** established. **Reboot loses the marker: helper will be OFF despite ordinary Zapret starting.** |

Squid parent snippet from prior effective config (and currently verified directive inventory):

```squidconf
cache_peer 185.203.117.88 parent 33128 0 no-query default
cache_peer_access 185.203.117.88 allow all
never_direct allow all
```

sing-box `config.json` is **not absent from GUI**: the owner furnished its full JSON directly from the installed GUI. The inbounds are SOCKS `0.0.0.0:1080`; matching TCP 80/443 resolves with `lan-dns-v1` and routes if `ip_cidr` matches the dated list to HTTP outbound `127.0.0.1:3130`; the remaining TCP/UDP use `direct`. UDP `direct` still traverses applicable WAN IPFW rules; SOCKS UDP ASSOCIATE remains **unverified**. The GUI/subscription package also owns `/usr/local/www/sing-box_sub.php`, `/usr/bin/sing_box_sub` (wrapper to `/usr/local/etc/sing-box/sub/sub.sh`), `.../sub/env` and `.../sub/template.json`. Its configd actions are start/stop/restart/status/sub-update. **Effects of Save, subscription update and package replacement on this particular edited config have not been tested**. Never blindly press Apply/update as a persistence test.

The Squid ACL file and sing-box inline `ip_cidr` arose from the same past snapshot of PF `Telegram`+`Telegram_IPs` and **require deliberate resynchronization after alias changes**; no daemon, GUI or automatic synchronization has been verified. One-time installer `singbox_squid_lan_policy_20260930_v2.py` originally lived in `/tmp` and is not a boot mechanism. Successful backups/manifest are in `/root/singbox-lan-policy-20261001T034734Z-33814uhu`; see the traffic policy for its detailed earlier rollback warning.

### The Voice ON-after-reboot trap — one-shot requirement, implementation pending

The appliance already has the package's *single* native start hook `start/20-zapret`. Its boot start does not imply Voice ON. Current temporary Voice marker resides under `/var/run` and is not persisted in the OPNsense config. On reboot, the selected **ON** experiment will revert **OFF** unless someone explicitly restores it. Do **not** deduce Voice ON solely from `configctl zapret status`, `service -e`, generic IPFW divert activity or the numeric identity 19000 (rule positions can be reused).

**Temporary operator recovery after OPNsense reboot, one csh-compatible command per line:**

```sh
configctl zapret status
configctl zapret telegram_voice_status
configctl zapret telegram_voice_enable
configctl zapret telegram_voice_status
ipfw -a list
```

Only run `telegram_voice_enable` if the selected experiment actually requires ON and ordinary service is healthy. Verify requested/effective/profile, rule scope/IPSET and firewall counters; invoking a command alone is not proof of intended state. The owner **explicitly rejected Cron and repeated/periodic activation**. A [source-verified comparison of GUI and Voice IPFW interception, PF/NAT hook order, and the one-shot boot boundary](TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) now explains why merely pasting the helper profile into GUI is not equivalent. No new one-shot startup action is installed or reboot-tested. Until an independent one-shot approach is approved/implemented and live-qualified, the earlier manual recovery above remains necessary. Future native product GUI-backed persistence remains stage 3 after the existing media acceptance gates.

The measured live IPFW data for this inventory:

```text
19000     60     4080 divert 989 udp from any to table(zapret2_tgvoice) out not diverted not sockarg xmit vtnet1
19001   1280    96712 divert 989 tcp from any to any 80,443,5222,8888 out not diverted not sockarg xmit vtnet1
19002      0        0 divert 989 udp from any to any 80,443,5222,8888 out not diverted not sockarg xmit vtnet1
```

## Verified SSH from OPNsense to TNAS

| Item | Actual value |
|---|---|
| Target | `tolian@192.168.1.100`, SSH **port 9222**, expected source OPNsense LAN `192.168.1.2` |
| SSH on OPNsense | **`/usr/local/bin/ssh`**. An earlier script incorrectly assumed `/usr/bin/ssh`, failed with executable not found and was repaired. |
| OPNsense secret key | `/root/.ssh/id_ed25519_tgvoice_lab`, generated Ed25519 without passphrase, observed permissions 0600. **Never store private contents in GitHub or chat.** |
| Public key | `/root/.ssh/id_ed25519_tgvoice_lab.pub`; fingerprint `SHA256:ymEtvjjSkD82sORfc3k5nVFJ0ZgmzFE0JaFard2b8zk` |
| Verified TNAS server key | Ed25519 fingerprint `SHA256:TmtT2KOiPHelGGUoOhwFxaF7DsdBBdgFxCTQdj0SVUQ`, checked against `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` on TNAS. |
| Host trust | OPNsense root `known_hosts` accepted `[192.168.1.100]:9222` after comparison; route script requests `StrictHostKeyChecking=yes`. |
| Authorized key | TNAS login's `$HOME/.ssh/authorized_keys`, installed without replacing existing keys; prefixed `from="192.168.1.2",restrict` (source restriction; disable PTY/forwarding). **The absolute TNAS home directory was not measured; do not invent it.** |
| Access | Owner-live BatchMode/identity-only SSH succeeded **without password**; remote `id` says `uid=0(tolian) gid=0(tolian)`: effectively root-equivalent. Securely back up the private key and trust material **outside the repository**, and treat access accordingly. |

One-line SSH test from OPNsense's default csh:

```sh
/usr/local/bin/ssh -T -p 9222 -i /root/.ssh/id_ed25519_tgvoice_lab -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes tolian@192.168.1.100 'id'
```

A post-quantum KEX warning was observed and is distinct from a failed login. TNAS interactive `docker` is `/Volume1/@apps/DockerEngine/dockerd/bin/docker`; **noninteractive SSH PATH does not contain that directory**. If a *future optional* SSH test needs Docker, use its absolute path. The route script never uses Docker.

## TNAS host routing and manually operated Docker lab

- TNAS `192.168.1.100`, interface `ovs_eth1`; owner observed `systemd-networkd enabled`, network file `/etc/systemd/network/10-eth1.network`, and default DHCP gateway **`192.168.1.140`**. That is still its ordinary **default** gateway; it is **retired as the Telegram Voice test exit**. Do not change the default or restore old Voice tests through it.
- Two current **specific** routes: `91.108.13.10/32` (reflector) and `149.154.167.99/32` (HTTPS test), each `via 192.168.1.2 dev ovs_eth1 src 192.168.1.100`; both owner-verified.
- Container `tgvoice-lab`: owner measured `status=running network=host restart=no` at this epoch. **Manual startup when needed is intentional**; no container autostart. Host-network container uses TNAS host routes.
- TOS regenerates `/etc/systemd/network/*` on reboot. The owner explicitly decided **not to automate TNAS route repair**: after TNAS reboot, manually run the already-tested script below from OPNsense. **No Cron, configd action, automatic boot hook or polling job** for these routes.

### Exact OPNsense route script and invocation

The owner has installed **`/root/tgvoice-lab/ensure-tnas-routes.sh`** (chmod 0700). After the originally mistaken SSH path was changed to `/usr/local/bin/ssh`, the script passed `/bin/sh -n` and a real owner-live run: both routes reported `OK`, `EXIT=0`. It does not restart services, alter TNAS's default route or call Docker.

Here is the **full recovered installed script** for disaster recovery (do not paste its `if`/heredoc content into csh; deploy as a file from an explicitly entered POSIX shell if ever necessary):

```sh
#!/bin/sh

# Independent laboratory script. Does not modify os-zapret2-restyle.
set -u

BASE=/root/tgvoice-lab
KEY=/root/.ssh/id_ed25519_tgvoice_lab

if [ -e "$BASE/route-watch.disabled" ]; then
    echo "SKIPPED: route automation is paused"
    exit 0
fi

if /usr/local/bin/ssh -T -p 9222 \
    -i "$KEY" \
    -o IdentitiesOnly=yes \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=yes \
    -o ConnectTimeout=7 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    tolian@192.168.1.100 /bin/sh -s <<'REMOTE'
set -eu

DEV=ovs_eth1
SRC=192.168.1.100
GW=192.168.1.2

# Never modify routes if the expected network is not present.
ip -4 -o addr show dev "$DEV" |
    awk '{print $4}' |
    grep -Fq "$SRC/" || {
        echo "ERROR: expected TNAS address/interface not found"
        exit 1
    }

GWR=$(ip -4 route get "$GW" from "$SRC")

case " $GWR " in
    *" dev $DEV "*) ;;
    *)
        echo "ERROR: gateway is not reachable on expected interface"
        exit 1
        ;;
esac

case " $GWR " in
    *" via "*)
        echo "ERROR: gateway is not directly connected"
        exit 1
        ;;
esac

for DST in 91.108.13.10 149.154.167.99
do
    CURRENT=$(ip -4 route get "$DST" from "$SRC")

    case " $CURRENT " in
        *" via $GW dev $DEV "*)
            echo "OK: $DST already uses $GW"
            continue
            ;;
    esac

    echo "RESTORING: $DST via $GW"

    ip -4 route replace "$DST/32" \
        via "$GW" dev "$DEV" src "$SRC"

    CURRENT=$(ip -4 route get "$DST" from "$SRC")

    case " $CURRENT " in
        *" via $GW dev $DEV "*)
            echo "RESTORED: $DST"
            ;;
        *)
            echo "ERROR: route verification failed for $DST"
            exit 1
            ;;
    esac
done
REMOTE
then
    exit 0
else
    /usr/bin/logger -t tgvoice-lab-routes \
        "TNAS SSH connection or route verification failed"
    exit 1
fi
```

**Only command needed after a TNAS reboot**, from OPNsense csh (do not switch shells):

```sh
/bin/sh /root/tgvoice-lab/ensure-tnas-routes.sh
```

On the owner-live test with routes already present:

```text
OK: 91.108.13.10 already uses 192.168.1.2
OK: 149.154.167.99 already uses 192.168.1.2
EXIT=0
```

If a route is missing, the script checks source/interface and direct gateway first, selectively uses `ip -4 route replace`, then verifies each route. If expected source or gateway is absent, it fails rather than guessing. The optional file `/root/tgvoice-lab/route-watch.disabled` pauses execution; remove it to resume. From the **default csh** the exit status is `echo $status`; in **sh** the owner demonstrated `echo "$?"`. Neither means an automatic reboot test was performed. If a previously suggested `actions_tgvoice_lab_routes.conf` exists, that was **never confirmed**; do not assume or schedule it.

## Reboot risk register and next operator action

| After reboot | What is established | Operator recovery / gap |
|---|---|---|
| OPNsense regular Zapret2 | Package has existing `start/20-zapret` hook | Check `configctl zapret status`; never use it as a substitute for `telegram_voice_status`. |
| OPNsense **Voice ON** | Present before reboot; **not persistent yet** because `/var/run` marker is transient | [GUI-versus-helper firewall/NAT audit and **one-shot-only** boot design](TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) is documented; **no recurring Cron and no actual reboot acceptance**. Until proven, check `telegram_voice_status`; if chosen ON, manually call `telegram_voice_enable` and recheck. |
| Squid/parent/3130 | Current running listeners and included files verified | Before/after controlled reboot compare effective listeners, parent tunnel, files and hashes (see dated evidence); don't assert GUI-generated persistence not yet measured. |
| sing-box | RC enabled and GUI JSON provided | Verify actual `*:1080`, JSON + static IP set unchanged, LAN/SOCKS parent probes. Updating subscription or GUI Save may need separate qualification. |
| PF/IPFW | Rules currently present | Inspect `pfctl -sn`, `ipfw -a list`; current helper UDP rule 19000 is epoch-specific. |
| TNAS routes | Correct now; owner chooses **manual** restoration after reboot | Manually run `/bin/sh /root/tgvoice-lab/ensure-tnas-routes.sh` from OPNsense; start Docker container separately only when needed. |

**Backups:** OPNsense export alone is *not proved* to preserve manually created SSH private/public keys, `known_hosts`, `/root/tgvoice-lab/`, custom Squid snippets or experimental installer manifests. Make a protected **off-repository** backup before any destructive operation; never publish keys, secrets or personal auth files. Full live fingerprints/hashes and sing-box GUI snapshot are in the dated evidence document.
