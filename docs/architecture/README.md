# Architecture and requirement contracts

**Role:** specialist navigation, not a parallel state/plan owner. Completed feature requirements remain current contracts; completed execution plans and closed campaigns belong in history. [Current state](../PROJECT_STATE.md) owns proof levels.

## Active work and retained long-term design

- **MANDATORY UPSTREAM CANON:** [официальный manual.en.md](https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md) → [правило DEV-069: не проверять описанное поведение движка](ZAPRET2_UPSTREAM_MANUAL_CANON.md).
- **CLI Emergency Contract:** [ТЗ_6v5 §5.5–5.6: guarded `--force` и read-only `--help`](TZ_6v5.md), [DEV-070](../PROJECT_PRINCIPLES.md); новая регрессия V5-15/16 в [S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md).
- **IPFW Allocation:** [Normal 19000–19099, current Lab 19100–19131, future comparative 19140–19200](TZ_6v5.md) — [DEV-071](../PROJECT_PRINCIPLES.md), numbers outside these are not ours.
- **S01 reconciliation (23.11.2026):** [12 файлов старого #1228 — KEEP/REWORK/DROP; текущая ветка `_130`, следующая задача S02](ZAPRET2_TZ6V5_S01_PR1228_DISPOSITION.md). Это исходная инвентаризация, не product-acceptance.
- **CURRENT:** [ТЗ_6v5 — единая конфигурация и исполнитель](TZ_6v5.md) → [пошаговый исполнимый план S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md); [подробный JSON-контракт](ZAPRET2_DECLARATIVE_RUNTIME_MANIFEST.md) и [FD9 route audit](ZAPRET2_CANONICAL_SERVICE_LIFECYCLE.md).
- [#1052 specification](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) и [исторический P0–P5 план](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).
- [Voice UDP ports, extra IPv6 checkbox and P2P](VOICE_PORTS_IPV6_P2P_FUTURE.md) — retained long-term plan, per the latest owner instruction; detailed proposals remain distinct from implemented behavior.

## Current technical contracts

- [OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md](OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md)
- [OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md)
- [STRATEGY_LAB.md](STRATEGY_LAB.md)
- [STRATEGY_LAB_ACTIVATION.md](STRATEGY_LAB_ACTIVATION.md)
- [STRATEGY_LAB_ADAPTIVE_BUDGET.md](STRATEGY_LAB_ADAPTIVE_BUDGET.md)
- [STRATEGY_LAB_ADAPTIVE_SEARCH.md](STRATEGY_LAB_ADAPTIVE_SEARCH.md)
- [STRATEGY_LAB_BROWSER_HTTP.md](STRATEGY_LAB_BROWSER_HTTP.md)
- [STRATEGY_LAB_CIRCULAR_ISOLATION.md](STRATEGY_LAB_CIRCULAR_ISOLATION.md)
- [STRATEGY_LAB_CIRCULAR_OWNERSHIP.md](STRATEGY_LAB_CIRCULAR_OWNERSHIP.md)
- [STRATEGY_LAB_CORRECTIVE_CONTRACT.md](STRATEGY_LAB_CORRECTIVE_CONTRACT.md)
- [STRATEGY_LAB_CORRECTIVE_MATRIX.md](STRATEGY_LAB_CORRECTIVE_MATRIX.md)
- [STRATEGY_LAB_MODEL_C.md](STRATEGY_LAB_MODEL_C.md)
- [STRATEGY_LAB_OBSOLETE_SURFACES.md](STRATEGY_LAB_OBSOLETE_SURFACES.md)
- [STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md](STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md)
- [STRATEGY_LAB_PROFILE_OUTPUT.md](STRATEGY_LAB_PROFILE_OUTPUT.md)
- [STRATEGY_LAB_PROGRESS_LOCALIZATION.md](STRATEGY_LAB_PROGRESS_LOCALIZATION.md)
- [STRATEGY_LAB_PYTHON_MIGRATION.md](STRATEGY_LAB_PYTHON_MIGRATION.md)
- [STRATEGY_LAB_QUIC_CONTROL.md](STRATEGY_LAB_QUIC_CONTROL.md)
- [STRATEGY_LAB_RETENTION.md](STRATEGY_LAB_RETENTION.md)
- [STRATEGY_LAB_SETTINGS_GUARD.md](STRATEGY_LAB_SETTINGS_GUARD.md)
- [STRATEGY_LAB_STRUCTURED_RESULTS.md](STRATEGY_LAB_STRUCTURED_RESULTS.md)
- [STRATEGY_LAB_UDP_INPUT.md](STRATEGY_LAB_UDP_INPUT.md)
- [STRATEGY_LAB_UNIFIED_SHORTLIST.md](STRATEGY_LAB_UNIFIED_SHORTLIST.md)
- [VOICE_TRANSMISSION_GUI.md](VOICE_TRANSMISSION_GUI.md)
- [ZAPRET2_EXCLUDE_IPSET_SPEC.md](ZAPRET2_EXCLUDE_IPSET_SPEC.md)
- [ZAPRET2_EXTRA_RESOURCES_GUI.md](ZAPRET2_EXTRA_RESOURCES_GUI.md)
- [ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md](ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md)
- [ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md](ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md)
- [ZAPRET2_SERVICE.md](ZAPRET2_SERVICE.md)
- [ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md](ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md)

## Historical plans and measurements

[Stage archive map](../history/README.md). Old acceptance/pending/version statements there are dated evidence, not the immediate task. The [review inventory](../audit/DOCS-2026-11-13-INVENTORY.md) records every original file's disposition.
