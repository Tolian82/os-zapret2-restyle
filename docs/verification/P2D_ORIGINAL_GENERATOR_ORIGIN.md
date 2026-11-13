# #1052 P2d — provenance captured inside original common generator, not active observation

**Source candidate:** `v0.6.5_13`, next increment after [P2c common read-only owner](P2C_AUTO_DETECT_OWNER_GENERATION.md) and prior [P0 original full-generator attribution](P0_NATIVE_AUTO_DETECT_FEASIBILITY.md). P2 remains OPEN.

## Concrete source change

The unique previously detached P0 `build_map()` / `lookup()` implementation has moved into installed `backend/auto_detect_origin_map.py`. The old `docs/verification/p0_profile_attribution.py` now imports that same canonical function, so there is **no divergent duplicate parser or inference by filename**. This code already proves that a mixed original `<HOSTLIST:...>` + `<IPSET:...>` source, even after normalization splits it into a HOSTLIST-looking final profile, remains IPSET-ancestry excluded.

The **existing** `orchestrator_build_release()` for **`shared-candidate` with Target Mode `auto` only** snapshots the authentic original stages into the private shared-work directory:
- original `traffic.input`, source Target Mode `effective`, Python normalizer `normalized`, per-profile canonical resolver `resolved`;
- selector→native binding through the **same original registry/storage mapping**, not by scanning final filenames;
- `traffic-user.conf`, explicit `voice.conf` from the original shared Voice compiler, `extra.conf`, preamble, `assembled` before global policy and `dvtws.args` after it, and only approved global exclusion overlay identities.

The new `publish_origin_map()` calls the canonical P0 map validator against those **same-generation staged file bytes**, validates regular unlinked stage file identity, order/count and final argv digest, then creates `auto-detect-source-map.json` in the private release with mode `0600` and file+directory fsync **before original FD9 `shared_apply_seal`**. The existing atomic release copier and seal inventory already own any resulting file. All raw/intermediate data remain in private shared-work; the sealed/installed artifact contains only original source hashes/roles/profile numbers and hostlist labels. Unexpected stage transformations or write failures omit the optional source map and do **not** block working shared Apply.

**Deliberate fail-closed boundary:** `auto-detect-source-map.json` is schema=1 `ORIGINAL_SHARED_GENERATOR_CAPTURE_NONACTIVATING` and explicit `observer_attached=false`, `activation_authorized=false`. It cannot pass the separate P2c requirement for `auto-detect-generation.json` schema=2 with actual trailing native observer, raw/debug path and confirmed original owner/command. The native engine argv and existing Target Mode/Hostlists/IPSET modes are **not modified**. No raw writer, no debug parser, no 60-second worker, no `pending` acknowledgement, no GUI or list mutation.

## Scoped verification

S0: `python3 scripts/test-auto-detect-origin-producer.py` uses the prior **full real P0 generated pipeline fixture** rather than independently manufactured final profiles, covering a known explicit source, mixed HOSTLIST+IPSET with Voice, tampered resolved source, malicious symlinked staged file, wrong mode and duplicate publication. It also runs the unchanged P0 fixture through the now unique installed mapper. S1: native shell syntax, current identity/docs/budget and full focused source checks. S2: existing qualified native OPNsense 26.7 package build for changed installed Python/Orchestrator/Voice staging; **no separate installed-user, Voice-call or Strategy Lab VM suite is warranted**, and passing build is not live source acceptance.

**Do not promote a synthetic test source map to a genuine P2c owner token.** Native genuine dvtws2/FD9 generation-source, producer raw/debug events and accepted append correlation, hot reload, durable destination ownership, cron, GUI and owner appliance tests remain outstanding P2/P3–P5. The stable installed `0.6.5_1.pkg` is unchanged and no `0.6.5_13.pkg` is published.

## Next step

Qualify a true shared `auto` common build with normal/restart and Voice enabled/disabled on native FreeBSD, confirm sealed map before activating any observer; then append only approved trailing no-action native observer and produce the **same-generation authorized schema=2** map with confirmed raw/debug linkage under the original FD9 lifecycle. Only after that integrate crash-safe pending FD clearance, committed auto-owned results and minute configd/cron without altering user Config or the Strategy Lab.

**Evidence status:** source implementation and focused fixture; exact-head CI/native archive outcome to be recorded separately in #1052. P2 NOT completed.
