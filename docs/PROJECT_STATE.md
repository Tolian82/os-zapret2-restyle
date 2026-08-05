# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current hardening source candidate: `os-zapret2-restyle-0.3.2_25.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–11 are complete in source. A second owner-approved hardening series is now active following the repository-wide audit of candidate runtime, lifecycle, result fidelity, circular validation, GUI recovery, and CI coverage.

Accepted hardening authority:

- `docs/patches/v0.3.2_25.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-hardening-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`.

Permanent decisions for this series:

- IPFW `19100–19131` is reserved exclusively for Strategy Lab and is cleaned destructively; no occupancy, ownership, snapshot, or foreign-rule restoration logic is required.
- every published working candidate must contain the tested domain or IP and a complete replay-verified profile ready for the Traffic Strategy field;
- the displayed profile must use static target selectors (`--hostlist-domains=` or `--ipset-ip=`) and must not include global runtime-only arguments;
- each logical correction is delivered as a separate revisioned patch with focused tests and synchronized documentation;
- GitHub publication is strictly serialized: the task branch may contain only one new unverified commit at a time, and the next patch may not be prepared or published until all required checks for the current commit have completed successfully and the remote commit has been verified;
- when a check fails, only the current patch is corrected; later patches are not stacked behind it.

`VERSION=0.3.2`; `PLUGIN_REVISION=25`.

Next action: complete verification of Patch `_25`. Patch `_26` must not begin until `_25` has passed all required GitHub checks.
