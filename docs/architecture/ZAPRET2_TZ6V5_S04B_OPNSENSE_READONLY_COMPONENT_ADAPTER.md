# TZ6v5 S04b — OPNsense bounded read-only component adapter (candidate)

**23 November 2026.** Base accepted main \`v0.6.5_151\` / \`aac77c8a7\`. Candidate \`v0.6.5_152\`, private CI-only package, **not** released or installed on the operator's OPNsense.

## Change boundary

\`backend/component_inventory_opnsense.py\` is a private, explicit, five-axis reader calling the existing S04a pure \`classify()\`. It reads only:

* Installed \`/usr/local/sbin/pkg info -e os-zapret2-restyle\`, never the FreeBSD \`/usr/sbin/pkg\` bootstrap shim;
* Fixed native \`dvtws2\` path, owner/mode/size/64-byte FreeBSD amd64 ELF structure (**not** a functional version or checksum provenance claim);
* Bounded root-owned \`/conf/config.xml\`, checking parse and initialized \`OPNsense/Zapret/general/enabled\`; no \`Config::save\`;
* Original \`SharedApplyOperation.read()\`, existing \`shared_apply_seal.verify_seal()\` and \`voice_ipfw_adapter.shared_release_manifest()\`;
* The existing \`voice_live_inspect.examine_shared()\` (one Common runtime/PID/IPFW inspector), and its existing conservative cold/no-kernel witness.

Never acquire the original FD9, create/repair any lock/journal, save Config, run a service command, enumerate new owner PID signatures, touch IPFW, or grant physical authority. All output fields are bounded enum-only. A reported RUNNING is **not** permission to Stop, and missing Config/manifest never grants a Start. Races or invalid original records return invalid/INCOMPLETE rather than a new owner interpretation. No public \`status --json\` has been implemented.

## Qualified and unqualified evidence

Source tests check the five requested *fact combinations*, bounded read-only ELF/XML reading and no file byte/mode/mtime changes, explicit non-bootstrap pkg query, and reuse of original journal/seal/manifest/runtime API. **These are synthetic/source tests, not real OPNsense physical five-scenario qualification.** The next native step must run actual adapter on disposable FreeBSD OPNsense in five independent controlled states, with before/after root Config bytes, original journal/seal, PID/epoch, IPFW exact rule table readback, foreign rules, and file tree inventory. Use existing original workflow setup, and stop at the first unqualified real native result; do not create a second service controller or simulate a foreign owner as if native.

S04 **NO-GO** and S05 blocked until the actual five native states/no-write witness and any read-only race errors are proven. #1223/#1224/#1225 remain open, no owner device work or public package.
