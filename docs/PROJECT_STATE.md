# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the current operational state needed to resume work quickly.

Updated when:
Current version, branch, phase, priority, last completed work, blockers, or next actions change.

Read after:
INDEX.md

Do not store here:
Decision history, permanent rules, detailed workflow, architecture details, or product requirements.

==================================================
QUICK CONTEXT
==================================================

Project:
os-zapret2-restyle

Repository:
https://github.com/Tolian82/os-zapret2-restyle

Branch:
main

Development tree:
/root/os-zapret2-restyle

Version source:
VERSION

Current version:
0.2.1

Current package revision:
9

Verified package:
os-zapret2-restyle-0.2.1_9

Current phase:
Milestone 7 — completion and live verification of approved functionality

Current priority:
Rebuild and live-verify the clean committed baseline, complete the remaining package lifecycle and GUI/API live tests, and remediate only findings already proven by the audit.

Known blockers:
None.

==================================================
AUTHORITATIVE CURRENT RESULT — 2026-07-30
==================================================

A complete package installation and runtime start has been verified on OPNsense.

Confirmed package chain:

1. the package installs through pkg;
2. +POST_INSTALL registers plugin files, reloads templates, and prints the explicit runtime setup command;
3. runtime preparation is started manually with:
   /usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install
4. setup installs required dependencies without making pkg installation perform nested package work;
5. setup obtains the pinned bol-van/zapret2 release v1.0.3;
6. setup builds executable binaries/my/dvtws2;
7. configd actions are registered and callable through configctl;
8. templates generate the runtime configuration;
9. Backend v2 parses, normalizes, resolves, validates, and generates runtime arguments;
10. lifecycle code installs the ipfw divert rule;
11. dvtws2 starts;
12. supervisor starts and monitors the configured process identity;
13. service status reaches ready/ok.

Live evidence from the installed system:

- package: os-zapret2-restyle-0.2.1_8;
- execution status: 13|13|ready|ok;
- dvtws2 process present;
- supervisor process present;
- expected PID files present;
- ipfw divert rule present;
- ipfw.ko and ipdivert.ko loaded;
- HOSTLIST and IPSET target files loaded by dvtws2;
- four runtime profiles generated from the tested strategy.

The final startup failure found during the test was not an installation defect. The preset requested shorthand blob name tls7, so the resolver correctly looked for files/fake/tls7.bin. After the preset was updated to use an available real blob filename, the service started successfully.

The public README strategy example is intentionally left unchanged for now by explicit project-owner instruction. It will be rewritten in a later dedicated documentation pass.

==================================================
CURRENTLY CONFIRMED
==================================================

Project and distribution:

- independent repository and package identity;
- package/plugin name os-zapret2-restyle;
- internal OPNsense service and configd namespace zapret;
- VERSION as the single version source;
- Makefile PLUGIN_NAME remains zapret2 as required by the OPNsense framework;
- GitHub Release assets and GitHub Pages pkg repository;
- FreeBSD:15:amd64 repository layout for supported OPNsense 26.7;
- repository configuration uses ordinary https:// and signature_type: none;
- generated package metadata and archive preflight validation.

Runtime and backend:

- modular Backend v2;
- unified Traffic Strategy;
- placeholders limited to <HOSTLIST:name> and <IPSET:name>;
- automatic one-selector-per-runtime-profile normalization;
- user-authored --new boundaries retained;
- Target Mode;
- global domain exclusions;
- strict domain and IP validation;
- candidate build and validation;
- transactional Apply;
- atomic runtime activation and rollback;
- launcher, firewall, dvtws2, and supervisor lifecycle;
- process identity validation for dvtws2 and supervisor;
- lockf-backed lifecycle serialization;
- supervisor-only runtime failure detection;
- runtime cleanup on launch or monitored-process failure;
- blob shorthand resolves directly to files/fake/<name>.bin;
- native upstream blob declarations containing ':' remain unchanged.

Package lifecycle:

- pkg installation does not download, compile, or install runtime dependencies;
- +POST_INSTALL prints the exact setup command;
- +PRE_DEINSTALL stops the service synchronously;
- +POST_DEINSTALL is a no-op and does not restart configd;
- package removal preserves runtime and shared dependencies;
- setup uses bol-van/zapret2 pinned to v1.0.3;
- setup backend remains reusable by a future GUI Maintenance action.

Live behavior:

- valid configuration reached 13|13|ready|ok;
- HOSTLIST:youtube, HOSTLIST:user, IPSET:telegram, and hostlist exclusion data were loaded;
- invalid candidate data preserves the active runtime, service PID, and ipfw rules;
- invalid IP input fails during target validation;
- corrected preset using an existing blob starts successfully.

==================================================
OPEN VERIFICATION WORK
==================================================

The following are not yet classified as fully live verified:

1. package upgrade from an earlier revision to 0.2.1_8;
2. package removal while the service is running;
3. preservation of runtime and dependencies after package removal;
4. package reinstall over preserved runtime;
5. full OPNsense reboot and automatic service-start behavior;
6. controlled dvtws2 crash and supervisor cleanup/recovery behavior;
7. direct diagnostics route behavior;
8. complete GUI → MVC → configd → backend API live matrix;
9. blockcheck behavior across the complete browser/PHP/configd/script timeout chain;
10. classification of the currently unused reconfigure API endpoint.

These are remaining tests, not evidence that the implemented architecture is broken.

==================================================
CURRENT AUDIT FINDINGS
==================================================

Authoritative detailed records are in AUDIT.md.

Still open or requiring live verification:

- API diagnostics route duplication and direct-route behavior;
- stale GUI help text referring to removed HTTP/HTTPS strategy fields;
- blockcheck timeout inconsistency;
- unused reconfigure endpoint classification;
- rc.d enable-source behavior;
- remaining package upgrade/remove/reinstall/reboot tests;
- focused supervisor failure-path verification.

Closed or implementation-complete findings include:

- duplicate firewall_rules_present() declaration;
- disconnected inherited watchdog removal;
- PID identity hardening;
- conditional supervisor kill escalation;
- lifecycle serialization;
- setup launcher executable mode;
- wrong upstream zapret repository;
- nested package-managed runtime lifecycle;
- GitHub Pages repository URL scheme;
- release workflow catalogue filename;
- native ABI artifact staging.

==================================================
IMMEDIATE NEXT ACTIONS
==================================================

1. Build package revision 9 from the clean committed baseline and verify that its runtime behavior matches the tested 0.2.1_8 baseline.
2. Live-verify the corrected unified Traffic Strategy guidance on Settings and Diagnostics pages.
3. Execute upgrade → remove → reinstall live tests and record exact evidence.
4. Reboot the OPNsense test system and verify service startup, PID ownership, supervisor, and ipfw state.
5. Complete the remaining GUI/API live-test matrix, including the duplicate diagnostics route and service reconfigure classification.
6. Resolve only findings proven by the audit; do not redesign working architecture without evidence.
7. Resume completion of remaining approved REQUIREMENTS.md functionality.

==================================================
WORKING RULES FOR RESUMPTION
==================================================

Before changing code:

1. read docs/INDEX.md;
2. follow the mandatory reading order;
3. inspect the actual repository tree;
4. check branch, HEAD, tags, and working tree;
5. use AUDIT.md Finding IDs for remediation work;
6. record approved concepts in DECISIONS.md;
7. update every affected document in the same logical commit;
8. never infer current state from chat history alone.

The live-verified source and synchronized Engineering Memory were committed and published as efff7b5. Package revision 9 is the first follow-up candidate that must be built from the clean committed baseline and compared with the verified 0.2.1_8 runtime behavior.


==================================================
2026-07-30 — GIT-FIRST PATCH WORKFLOW APPROVED
==================================================

Current development policy:

- repository changes are prepared as reviewable unified Git patches;
- patches must include file-mode changes when required;
- the project owner applies supplied patches through Git;
- repository files are not edited directly in the OPNsense console;
- every applied change remains inspectable through Git diff and is committed as one
  logical change after validation;
- temporary files, logs, diagnostics, installed-system configuration, and other files
  outside the repository are not restricted by this rule.

The release-package verification script was confirmed functionally correct when invoked
through sh. Its missing executable mode is corrected from 100644 to 100755 in the same
logical infrastructure and documentation change.

Current patch-baseline rule:
The project owner's archive of the actual working tree is the authoritative base
for multi-file patch preparation. It is supplied after changes are agreed, named
`os-zapret2-restyle-<short_commit_sha>.tar.gz`, and becomes obsolete after the
resulting patch is committed. Delivered patches must first pass
`git apply --check` against an unchanged copy of that archive.
