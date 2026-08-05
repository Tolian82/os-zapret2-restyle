# 2026-08-05 — Strategy Lab Patch 13

Activated the asynchronous Strategy Lab on the Diagnostics page and retired the synchronous Blockcheck integration.

The GUI now starts jobs, polls once per second, renders stages and shortlists, cancels safely, and controls temporary circular validation. The legacy wrapper, configd action, API method, and ten-minute AJAX request were removed rather than retained as a hidden fallback.

Added focused regression coverage for API endpoints, polling, stage and shortlist rendering, circular controls, removal of every legacy entry point, localization, and package revision 15. Live appliance verification remains a separate owner-assisted gate.
