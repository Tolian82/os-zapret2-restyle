# Owner decision — GitHub testing packages are .pkg-only (2026-11-10)

**Binding instruction:** deliver a persistent immutable GitHub `.pkg` test package. NO external SH companion installers may be created, uploaded, linked or recommended for new testing candidates. Earlier contradictory installation instructions in CHAT-027, GH-060, GH-061 and LC-16 are cancelled. Old published assets and prior evidence are not rewritten.

**Owner command:** `fetch -o /root/os-zapret2-restyle-<version>.pkg <direct-pkg-url>` then `pkg add -f /root/os-zapret2-restyle-<version>.pkg`, then `pkg info -x os-zapret2-restyle`. Before `pkg add -f`, resolve any missing/outdated manifest dependencies through interactive official `pkg install -r OPNsense`; review the transaction. No testing pkg repo, FreeBSD stock repositories, `pkg add -M`, hooks bypass, external install wrappers or `pkg install -f <local.pkg>` (known solver fault).

**Implementation:** publisher uploads/verifies ONLY a `.pkg`; publication-record PR records only physical package SHA/source/tag and direct URL. Delete legacy installer template; Guest D tests no-git clean physical `.pkg` by resolving actual manifest dependencies only through official OPNsense, then `pkg add -f`. Full native pkg hooks and upstream runtime remain unchanged.

**Limits:** Installed G01 full purge maintenance script is not an installer and keeps its independent safety contract. Historical release assets remain immutable. A source-only governance revision is not a new released pkg. G10A full acceptance and GUI issue #1013 remain open.

Sources: [CHAT-027](../CHAT_RULES.md), [GH-060/GH-061](../GITHUB_PUBLICATION.md), [LC-16](../architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md).
