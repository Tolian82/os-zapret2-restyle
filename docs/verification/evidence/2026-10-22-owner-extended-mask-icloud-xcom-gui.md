# Owner Extended GUI: mask.icloud.com and x.com (post-v0.5.6_11 publication)

**Date:** 22 October 2026. **Source:** two owner-provided screenshots of the installed Strategy Lab after publishing the `v0.5.6_11` testing prerelease. Screenshots themselves do **not** include `pkg info`; the observed frontend matches the new `_11` scope display, but exact installed binary package identity remains unverified.

## Screenshot 1 — mask.icloud.com

- Target `mask.icloud.com`; Extended; Enable QUIC ON; generic UDP port 443 with a selected UTF-8 text file, `Эссе о гневе и мести.txt`, 114 bytes.
- Job COMPLETE, SUCCESS, 100%. Stage20 managed Zapret2 stopped, Stage30 reported IPv4 and generic control-host QUIC/IPv4 available, Stage40 direct TLS1.3 not established, Stage50 no working TLS1.3 family, Stage60 0 working / 16 checked, Stage70 0 stable / 0 checked.
- Stage85 one final stable candidate; Stage90 explicitly PASS, original Zapret2 service and rules restored; Stage99 SUCCESS with 1 profile.
- The new `v0.5.6_11` verified-protocol notice is visible: **TLS/TCP443 0; HTTP/TCP80 1; QUIC/UDP443 0; other UDP 0**. One visible replayed HTTP/TCP80 `multisplit` profile, pinned IPv4 `17.248.248.120`, `1/1` final replay. No confirmed UDP443/QUIC success.
- Stage80 text is partially covered by the screenshot's OPNsense shell/header overlay. Do not infer exact QUIC attempt exit codes, IPFW counters, direct target outcome or generic UDP reply from this cropped row; persisted job `quic.json`/UDP artifacts were not supplied.

## Screenshot 2 — x.com

- `x.com`, Extended, QUIC ON, same arbitrary 114-byte text file and generic UDP port 443.
- Job SUCCESS and two stable working profiles total as displayed; Stage40 direct TLS1.3 not established, Stage50 found at least one TLS1.3 family, Stage60 3 working / 7 checked, Stage70 2 stable / 4 checked.
- Stage80: QUIC four strategies tested (`quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`) — **none working**. Generic UDP443 payload 114 bytes, pinned selected IPv4 `172.66.0.227`, direct control reply **not received** (GUI explicitly notes this does not imply a closed port); three strategies tested (`udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`) — none working.
- Screenshot stops at Stage80; it does not show Stage90 or shortlist detail. Therefore do not assert from *this new screenshot* which two protocols won final replay, or that restoration succeeded, solely based on the overall SUCCESS label. Older x.com results are separate executions and cannot substitute.
 
## Protocol validity and interpretation

Apple [documents](https://support.apple.com/en-ie/101555) `mask.icloud.com` as iCloud Private Relay **UDP/443** and `mask-h2.icloud.com` as its **TCP/443 fallback**. Apple [also states](https://developer.apple.com/icloud/prepare-your-network-for-icloud-private-relay/) that Private Relay validates eligible Apple devices and iCloud+ accounts, using single-use authentication tokens and related abuse protections. It is therefore **not a generic unauthenticated HTTP/3 webpage**. A browser-profile `curl --http3-only https://mask.icloud.com/` can be useful as a low-level QUIC/TLS probe, but a failed HTTP/3 URL attempt is **not sufficient to prove DPI blocking or bypass failure for the authenticated Private Relay service**. A positive, pinned, CA-verified QUIC handshake would still be transport evidence, not a working authenticated Private Relay session.

The uploaded `Эссе о гневе и мести.txt` contains 114 bytes of ordinary text. Strategy Lab generic UDP mode sends the bytes supplied; it does not transform arbitrary text into a valid QUIC Initial, MASQUE request, or an authenticated Apple Private Relay command. Generic UDP direct control replies and arbitrary-payload IPFW interceptions must not be merged into QUIC protocol outcomes.

**Acceptance:** Owner-visible frontend semantics for one replay-verified HTTP/TCP80 profile and zero verified TLS/QUIC/UDP profiles **PASS** on `mask.icloud.com`; source CI had independently passed in PR #467. This is not installed-package identity attestation or Stage3 QUIC bypass acceptance. No new runtime bug or new desynchronization strategy follows from these screenshots alone.

**Next meaningful network acceptance:** use a target independently documented to serve **ordinary unauthenticated HTTP/3**, with evidence that it is unavailable directly on the owner's route and a compatible authenticated endpoint identity; retain the established QUIC-only no-TCP fallback, real returned remote IPv4, CA, UDP IPFW, 3/3 candidate stability, exact replay and Stage90 restoration. Avoid further speculative Apple `mask` tests and arbitrary UDP text files for QUIC validation.
