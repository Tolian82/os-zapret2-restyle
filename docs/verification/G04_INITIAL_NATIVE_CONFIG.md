# G04 — first-install settings are saved native Config, not UI defaults

**Source candidate:** v0.6.3_8. Published stable remains v0.6.3_1. Exact scope: LC-05, A05 and saved-empty non-backfill guard from A08. A06 actual live DPI strategy/Start qualification is a separate remaining native/owner-live gate; do not mark it PASS from a Config-only witness.

## Owner decision (8 November 2026)

On the very first genuine package installation, only if **the whole native /opnsense/OPNsense/Zapret subtree is absent**, populate exactly two native model fields and persist them once with OPNsense Config::save() under the normal Config lock. These are the same strategy.trafficargs and hostlist.youtubedomains fields the user edits in the GUI. The authoritative strings and ordering are in the [LC-05 specification](../architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md#4-стартовые-значения-полей-после-истинно-чистой-установки) and native initialize_config.php.

The installed pkg/+POST_INSTALL calls the initializer immediately after official firmware registration, before the existing configd/template refresh. An existing Zapret subtree is the **authoritative user setting**, even if the whole subtree is empty, one field is missing, both were deliberately cleared or they contain non-default values. In these cases the initializer is a read-only no-op: not even an extra Config::save() is permitted.

Do not introduce XML model defaults for these fields, an init() model getter fallback, a first-run flag in another file, alternative config storage, a second Config writer or GUI-side injection. Disabled service/WAN-unselected must remain unchanged. The pkg hook must not start dvtws2, fetch resources, touch IPFW/PF or compile upstream.

## Exact tests

**SOURCE**: PHP test-g04-initial-config.php, shell test-package-lifecycle-restart.sh, and Python test-stage2-opnsense-real-native-clean-install.py assert exact lines, one Config save, no save for saved/empty/partial Config, safe abort on validation/uncertain save before templates, and unchanged lifecycle order.

**INSTALLED-CI**: one disposable OPNsense 26.7 guest uses stock Mk and genuine pkg add; stage2-opnsense-real-native-clean-install.py verifies the two fields on /conf/config.xml, unrelated OPNsense Config unchanged, Enabled OFF, WAN empty, no runtime start. stage2-opnsense-g04-native-config.py creates a fresh PHP model to prove saved fields read back (like GUI F5), then saves empty values through the normal model and reinstalls the **same physical .pkg**. POST_INSTALL must report zapret-config=preserved, and the saved empty Zapret subtree must remain unchanged.

**OWNER-LIVE (G11)**: after an approved G10 testing package, initial page shows saved values; refresh, clear fields, save, refresh, reinstall and verify empties remain. Actual dvtws2 dry-run, TCP+QUIC and WAN-dependent runtime acceptance require separate installed/live proof. The source branch does **not** authorize a release.
