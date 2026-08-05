# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current hardening source candidate: `os-zapret2-restyle-0.3.2_28.pkg`

Patches 1–13 of the initial Strategy Lab delivery are complete. Corrective Patches 1–11 are complete in source. The second owner-approved hardening series is active.

Hardening series status:

- Patch `_25` — hardening contract and serialized GitHub publication rule: required GitHub checks completed successfully;
- Patch `_26` — proof-based temporary candidate runtime cleanup: required GitHub checks and FreeBSD package build completed successfully;
- Patch `_27` — cleanup of reserved Strategy Lab residue before baseline collection: required GitHub checks and FreeBSD package build completed successfully;
- Patch `_28` — hard whole-worker deadline with child cancellation and restoration path: current source candidate awaiting its own required GitHub checks;
- Patch `_29` and later work must not begin until `_28` is fully verified.

Accepted hardening authority:

- `docs/decisions/DEC-2026-08-05-strategy-lab-hardening-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`;
- revisioned records under `docs/patches/`.

Permanent decisions for this series:

- IPFW `19100–19131` is reserved exclusively for Strategy Lab and is cleaned destructively; no occupancy, ownership, snapshot, or foreign-rule restoration logic is required.
- every published working candidate must contain the tested domain or IP and a complete replay-verified profile ready for the Traffic Strategy field;
- the displayed profile must use static target selectors (`--hostlist-domains=` or `--ipset-ip=`) and must not include global runtime-only arguments;
- GitHub publication is strictly serialized: only one new unverified commit may exist at a time; all required checks and remote verification must complete successfully before the next patch begins;
- a failed check is corrected within the current patch without stacking later commits.

`VERSION=0.3.2`; `PLUGIN_REVISION=28`.

Next action: complete required GitHub checks and remote verification for Patch `_28`. Patch `_29` remains blocked until that succeeds.
