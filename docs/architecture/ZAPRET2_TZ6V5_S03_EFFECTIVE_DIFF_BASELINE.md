# ТЗ_6v5 — S03b: baseline реальных effective-diff изменений старого генератора

**Срез:** исходный `main v0.6.5_132` / `88425da7fa47a4c519500866e3964f5dbae9304d` после [S03a actual RED 6/6](ZAPRET2_TZ6V5_S03_ORIGINAL_GENERATOR_RED.md). Продолжение того же S03, source candidate `v0.6.5_133` (только тесты/CI/документы), **пакет `os-zapret2-restyle-0.6.5_133.pkg` NOT BUILT/NOT PUBLISHED**, owner OPNsense (last-confirmed `_117.pkg`) не тронута.

## Проверяемая задача

До создания будущего S07–S14 `pure compiler / diff planner` фиксируем **фактический неизменённый old renderer**, не имитируя его Python-моделью. Новый [исполняемый S03b тест](../../scripts/test-tz6v5-s03-effective-diff-baseline.py) повторно использует `scripts/test-p2e-original-shared-build.py::OriginalSharedGeneration`; каждый case вызывает **настоящий** `orchestrator_build_release` со всеми штатными `profile_pipeline / target_mode / targets / Voice / global exclusions` и читает настоящий staged `dvtws.args` плюс хеши `managed/hostlist-{youtube,user,exclude}.txt` и source-map.

Случайный временный корень заменяется только при сравнении двух реальных argv; сами CLI-параметры, порядок, canonical активные ссылки, staged managed SHA-256 не меняются. Домены синтетические; секреты/содержимое hostlist/Config не выводятся.

## Сценарии и строго ограниченные доказательства

| Case | Сравнение реального old/next | Наблюдение / будущий критерий |
| --- | --- | --- |
| `same_input` | одинаковая стратегия, managed contents, режим | `NO_CHANGE_SOURCE_EQUAL`; будущий planner не должен трогать PID/IPFW/FD9 |
| `youtube_contents` | тот же `<HOSTLIST:youtube>`, добавлена синтетическая запись | `CONTENT_ONLY_CANDIDATE_UNPROVEN_RELOAD`: refs/argv идентичны, managed SHA меняется |
| `user_contents` | тот же `<HOSTLIST:user>`, изменён текст | Аналогично: только кандидат на live reload, не автоматическое разрешение |
| `exclude_contents` | global Exclude уже существует; nonempty→different nonempty | Аргументы не меняются, managed exclusion SHA меняется; нужен настоящий multi-ref seal/rollback |
| `profile_order` | изменён порядок User / YouTube | `STRUCTURAL_DIFFERENCE`, обязательное сохранение first-match |
| `dpi_args` | изменён `--lua-desync` | `STRUCTURAL_DIFFERENCE`, будущий Restart |
| `voice_enabled` | Voice OFF→ON | `STRUCTURAL_DIFFERENCE`, future guard и проверка IPFW |
| `divert_port` | 19899→19900 | `STRUCTURAL_DIFFERENCE`, future Restart |
| `target_mode` | `auto`→`list` на *одинаковом старом native argv* | `SEMANTIC_MODE_CHANGE_EVEN_IF_ARGV_EQUAL`: argv-only diff опасен; future source-map/Target Mode semantic fingerprint обязателен |
| `exclude_presence` | global Exclude пустой→непустой | `STRUCTURAL_DIFFERENCE`: появился новый native reference |

**Важный вывод:** одинаковый `dvtws.args` НЕ означает `NO_CHANGE` при отличающихся staged list bytes и НЕ означает `RELOAD_SAFE` при Target Mode `auto`→`list`. Классы `CONTENT_ONLY_CANDIDATE_UNPROVEN_RELOAD` — аналитические метки теста, а **не** настоящий `Apply planner` и не подтверждённый live reload.

## Натуральные границы свидетельства

Проводится в существующей **одноразовой OPNsense 26.7/P2e** на точном SHA PR, после старого P2e и перед S03a. Shell/Python используют реальные production модули, но со строго тестовыми входами. Службу не запускают, FD9/Config.xml/installer/действующий IPFW не меняют, upstream `manual.en.md` auto-reread/SIGHUP не тестируют. `--lua-desync=fake` в **тексте стратегии** не означает фактический fake engine: это обычный вход old compiler без установленного dvtws2.

Для запуска:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-tz6v5-s03-effective-diff-baseline.py
```

Ожидаемые свидетели: `TZ6V5_S03B_REAL_ORIGINAL_EFFECTIVE_DIFF_BASELINE={...}`, `S03B_ACTUAL_OLD_GENERATOR_BASELINE=PASS`, `S03B_RELOAD_SAFE_NATIVE_NOT_CLAIMED=1`.

**S03b gate:** evidence/CI на exact-head должен подтвердить 10 производственных сравнений, включая контрпример Auto→List. Если любое отличие меняет native argv неожиданно — разбираем реальный генератор, а не подгоняем ожидаемый класс. После GO S03b **весь S03 остаётся NO-GO**, поскольку не закрыты реальные WAN-only G05→G08, force/PID/FD9, terminal diagnostics/RU+EN, полноценные Help/Reload negative с guard, Lab/Auto physical source negative и native V5-17 интеграция. S04 до полного S03 не начинать.
