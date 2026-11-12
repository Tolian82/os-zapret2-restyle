# #1052 P1 — canonical domain policy and packaged PSL

**Source boundary (13 November 2026):** P0 completed on merged `b29de5ca7e9dd3e499d0b7423a8524de90259209`; [generated native run 43327217834](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43327217834), [immutable #1052 receipt](https://github.com/Tolian82/os-zapret2-restyle/issues/1052#issuecomment-6838843832). P1 extends the existing [domain_policy.py](../../src/opnsense/scripts/OPNsense/Zapret/backend/domain_policy.py). It is a policy API/CLI and data-delivery increment, not activation of a production observer, queue worker or GUI. P2–P5 retain their gates in the [ordered plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).

## Observable scenario and evidence

A confirmed `video.example.co.uk` discovery must yield `example.co.uk`, while `a.user.github.io` must yield `user.github.io`. Multiple subdomains collapse to one plain root. Exclusions in any supplied HOSTLIST and global Exclude Domains suppress appropriate additions; ambiguous original sources go to the shared list. No guessed last-two-label root and no added `^`.

The pre-change [canonical policy test](../../scripts/test-domain-policy.py) genuinely failed because this entrypoint had no PSL/root API; the six existing normalizer/CLI tests passed. The extended suite now passes 22 cases using the complete packaged PSL, including actual ICANN/PRIVATE, wildcard/exception, IDNA2008, bounds/invalid/suffix-only/unknown names, all-list broad/exact exclusions, original-host plus normalized-candidate checks, batch and previous-owned conflicts, idempotency and rediscovery after ordinary deletion. Existing PHP and shell adapters remain the original semantic entrypoints. Native qualification must execute policy/data extracted from the actual `.pkg` with target Python and its declared IDNA package; source-only success is not package or owner-live acceptance.

## One offline PSL snapshot

Unmodified UTF-8 [public_suffix_list.dat](../../src/opnsense/scripts/OPNsense/Zapret/backend/data/public_suffix_list.dat) comes from official [publicsuffix/list commit aa004f90b4cbe1c54ea96375622eca83d76059f0](https://github.com/publicsuffix/list/tree/aa004f90b4cbe1c54ea96375622eca83d76059f0), 6,951 ICANN and 3,469 PRIVATE rules. Its adjacent [metadata](../../src/opnsense/scripts/OPNsense/Zapret/backend/data/public_suffix_list.json) records provenance, MPL-2.0 and SHA-256 `ebdedd64c8ee3807715f3257ffbb983e322352f7c9a14484102e5ec1245a627c`. The upstream license notice is retained. File/hash/metadata/section/rule validation is mandatory; missing, corrupt, ICANN-only or unknown suffix data cannot fall back to a broader guessed root. PSL exceptions take precedence over longest exact/wildcard matches, following the [official format](https://github.com/publicsuffix/list/wiki/Format).

Delivery and refresh use ordinary plugin packages. The minute worker has **no network fetch** or independent mutable PSL cache. Maintainers fetch an official upstream checkout, select a full immutable commit, then run:

```sh
python3 scripts/update-public-suffix-list.py --upstream-checkout /path/to/publicsuffix-list --commit FULL_COMMIT_SHA
python3 scripts/test-domain-policy.py
```

With no arguments, the updater checks the current packaged snapshot. It verifies the official origin and git object, reads exact committed bytes, validates both sections and representative ICANN/PRIVATE results, then writes tracked source/metadata. The selected commit and digest are data provenance, not a hardcoded component-version restriction. Updates receive the normal source review/native package gate; no separate appliance updater or scheduler is introduced.

IDNA uses the native `py${PLUGIN_PYTHON}-idna` dependency, derived from OPNsense's observed Python provider and official package catalog. No Python minor version or IDNA version is hardcoded. Strict IDNA2008 preserves `faß.de` as `xn--fa-hia.de`; Python's stdlib IDNA2003 conversion to `fass.de` is not used. Unicode/punycode syntax failures remain explicit; ordinary manual URL/wildcard compatibility and `!`, `^`, `!^`/`^!` semantics are retained by the existing normalizer.

## P2 caller contract

`plan_auto_additions(discoveries, hostlists, automatic, global_exclude)` and read-only CLI `auto-plan` share the same policy. `psl-status` reports the qualified packaged identity/counts. These commands do not write lists, Config or runtime state.

- Each discovery carries `hostname` and the **already generation-validated** sole `hostlist`, or `None` for unknown/stale/ambiguous. P2 must reject IPSET-only/mixed and Voice events using the map before calling this API. The policy never infers attribution from a root or IP address.
- `hostlists` must contain **all** manual HOSTLIST components and editable shared `auto`, even when empty. `automatic` contains only rows currently present in proven auto-owned components/ownership records; manual shared entries must not be falsely marked as owned. Global Exclude Domains is a separate string.
- Broad local negatives anywhere and separate globals are checked against both the original hostname and candidate root. Exact negatives match only those exact names. Native runtime exclusion locality is unchanged. Positive coverage is checked in the destination only.
- Original origins are grouped after validation/root resolution. Multiple sources, unknown plus known, or a previous auto-owned root in a different destination resolve to shared `auto`. The plan returns additions plus removal of **only proven auto-owned plain positive rows** from contradictory destinations. Manual rows and their modifiers are never rewritten/relocated. P2/P3 must durably apply every related addition/removal before acknowledging pending data.
- Malformed observations return indexed `unprocessed` diagnostics; damaged/missing policy or list snapshots fail the whole plan. The future worker must retain their pending input. No deletion blacklist/state is invented: a new detection can re-add a normally deleted positive. At-least-once retries use fresh complete list/ownership snapshots.

The existing [native package verifier](../../scripts/native-opnsense-package.py) now validates the additional observed official provider and runs extracted archive policy/PSL on `example.co.uk`, PRIVATE `github.io` and IDNA `faß.de`. This qualifies delivery without installing the product or restarting a service. Historical running-upgrade/unsafe-owner VM campaigns no longer trigger on this archive/provider-only builder path; their actual lifecycle source triggers and manual dispatch remain, with a budget regression check. No test package is published by this increment; stable owner-installed `0.6.5_1.pkg` stays immutable.
