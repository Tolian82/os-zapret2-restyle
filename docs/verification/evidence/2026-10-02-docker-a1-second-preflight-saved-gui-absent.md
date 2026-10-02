# 2026-10-02 — A1 second preflight: persisted GUI Strategy lacks A1

**Status:** OWNER-LIVE CONFIGURATION DIAGNOSIS · `A1_NOT_IN_SAVED_GUI` · **NO DOCKER RUN / NO WIRE VERDICT**. Complements the [first preflight](2026-10-02-docker-a1-preflight-absent-effective-profile.md); this second archive resolves its previously missing saved-vs-effective boundary.

## Private source and measured outcome

The owner downloaded the pinned GitHub one-command v2 runner through their *already configured* OPNsense Squid listener `192.168.1.2:3128` after `127.0.0.1:3128` returned `Proxy CONNECT aborted`; no proxy configuration changes are requested. One run started **2026-10-02 19:08:19 UTC** and produced owner-supplied private archive `a1-20261002T190819Z-gWjrnb.tgz` (uploaded with filename suffix `(1)`; **2,633 bytes**, SHA-256 `3b9f62b6ced5e0fe6d251edd59925c910019c061f0691741cf718c4bb9ec361e`). Raw archive, full effective traffic configuration and private network logs remain private.

The included `a1-saved-diagnostics.txt` confirms the `/conf/config.xml` GUI model was **successfully read**. The diagnostics deliberately captured **only presence flags**, not the XML itself:

```text
saved_gui_model=READ_OK
saved_gui_A1=NO
saved_gui_A1_port=NO
saved_gui_A1_payload=NO
saved_gui_A1_fake=NO
saved_gui_A1_ipset=YES
```

`saved_gui_A1_ipset=YES` refers to the existing Telegram IPSET marker **elsewhere in the saved Strategy**, and is **not** evidence that any A1 line persisted. Both the specific UDP/596–599 port and the `payload=unknown`/16-byte-badsum fake terms are **absent from saved Strategy**. The actual effective `traffic.conf` likewise contains only existing YouTube, Telegram MTProto, user TLS and injected STUN helper profiles, **no A1**. Live `ipfw -a list` includes the destination-scoped Voice `19000` rule and ordinary `19002` UDP capture limited to `80,443,5222,8888`; no numeric `596–599` capture. Zapret2 reports running, Voice requested/effective ON with 14 managed entries. The runner returned `A1_NOT_IN_SAVED_GUI` and **intentionally never started Docker**, so this is neither `WIRE_FAIL` nor a failed DPI strategy.

**Meaning and limit:** this proves the A1 block was not present in the **saved ordinary Strategy** by the time of the second run. It does **not** prove why the prior owner-reported Apply did not persist it: the text could have been entered in Strategy Lab rather than the ordinary persistent Strategy editor, a save could have failed or been reverted, or an intervening configuration operation could have replaced it. Do not claim a UI bug, operator error or runtime normalization failure without appropriate evidence. Unlike the first archive, **absence from saved GUI is measured**.

## Next one-factor corrective action and automatic validation

The current source [SettingsController.php](../../../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php) persists ordinary settings through a guarded `applyAction` and then invokes `zapret reconfigure`; on failed activation it can restore the previous model. The owner must first **place A1 in the main persistent Services → Zapret DPI Bypass → Strategy editor, not Strategy Laboratory / candidate replay**, preserving all existing profiles. Insert the exact previously documented A1 block as an independent `--new`-delimited profile, click the **ordinary Settings Apply**, and confirm it reports success. Avoid a second Apply if there is an error: preserve its displayed validation/reconfigure message instead. Do not write `/conf/config.xml`, `traffic.conf` or firewall rules directly or blindly restart Squid/sing-box/PF to make the diagnosis disappear.

Then execute **only the existing** GitHub-tracked [one-command OPNsense A1 runner](../../../tools/telegram-voice-lab/run-a1-opnsense.sh), already downloaded to `/root/tgvoice-lab/run-a1-opnsense.sh` and SHA-pinned in its previous handoff. It will automatically differentiate `A1_NOT_IN_SAVED_GUI` / `A1_SAVED_BUT_NOT_EFFECTIVE` / missing numeric IPFW rule. If and only if preflight is successful, it calls existing manual route guard, existing SSH key, pinned 15-second Docker reflector on TNAS and collects both LAN/WAN PCAPs and CLI results in **one private TGZ archive**. No separate TNAS login, consoles, human call or new desync candidate. If A1 is saved but ineffective, analyze that new archived state before considering plugin corrective code through GitHub.

The existing fixed reflector `91.108.13.10:596`, tgcalls identity, IPFW destination-scoped helper and working Telegram TCP proxy remain unchanged. **Current gates:** A1 GUI persisted **NO**, A1 effective **NO**, Docker A1 **NOT RUN**, `REFLECTOR_READY` and `MEDIA_PASS` **OPEN**.
