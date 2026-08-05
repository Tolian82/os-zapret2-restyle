# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_15.pkg`

Patches 1–13 are complete. Patch 13 activates Strategy Lab on the Diagnostics page and retires the synchronous Blockcheck integration.

Active Diagnostics architecture:

- domain connectivity remains a short synchronous probe;
- Strategy Lab starts an asynchronous job and returns `job_id`;
- the GUI polls status every second and renders stage progress;
- cancellation preserves partial results and cannot bypass stage 90 restoration;
- completed jobs expose a stable shortlist and recommendation number one;
- domain shortlists of three to five candidates can start temporary circular validation;
- circular validation never modifies the saved Traffic Strategy;
- the old `blockcheck.sh`, configd `blockcheck` action, API action, and ten-minute AJAX request are removed.

`VERSION=0.3.2`; `PLUGIN_REVISION=15`. No tag, release, release asset, or pkg-repository publication is authorized by this patch series.

Next action: owner-assisted live OPNsense verification of package candidate `0.3.2_15`, followed by a separately authorized release decision.
