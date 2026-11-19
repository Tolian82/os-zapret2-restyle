# Strategies list API v1 — portable core boundary (OPNsense only for now)

**Статус: технический контракт для текущего [ТЗ_6v3](TZ_6v3.md), утверждено 19 ноября 2026; реализация пока не выполнена.**

Scope: `os-zapret2-restyle`, Strategies page only, initial five sources and future **six to eight sources in total**, with approximately unchanged total manual-domain volume. Voice/Передача Голоса, Strategy Lab, generic forms framework, pfSense product or a new service are OUT OF SCOPE. См. [ТЗ_6v3](TZ_6v3.md) — активный scope, [ТЗ_6v2](TZ_6v2.md) — сохраняемая часть GUI/FD9. Дальние вопросы — [Future](STRATEGIES_LIST_FUTURE.md) и [Feature #1192](https://github.com/Tolian82/os-zapret2-restyle/issues/1192). This design narrows the transport/registry implementation and does not cancel TZ6v2 acceptance.

## Why `FormData` alone does not fix the installed issue

- `FormData`/multipart is a **GUI -> HTTP** transport. It does not fix **root -> configd -> API -> GUI** rereading, or PHP application-side per-list checks, or the native `configd` argv bound.
- Today the manual OPNsense fields are loaded into native form controls; root `read-editors` repeats their whole text in a second JSON response. The production 1,774,109-byte User Domains exceeds `AutoDetectConfigSnapshot::MAX_MODEL_TEXT` (1 MiB), so the entire five-source response is refused even though the shared `auto-domains.txt` is valid and empty.
- Existing `general.volt` constructs `FormData` **conditionally**, for a single `found-intent.json` Blob containing the three automatic sources' baseline/drafts. Manual edited values remain actual native form fields, with `SharedApplyEnvelope::compactStrategies()` supplying SHA-checked deltas for large values. This existing, safety-qualified behavior must not be broken.
- A single new giant JSON Blob with all manual, automatic and unchanged content would duplicate bytes and could still exceed PHP's `post_max_size` / `upload_max_filesize`. Global PHP settings MUST NOT be raised for this change.

## Registry and portable core

One canonical, versioned **Strategies list catalog** describes current source identities and their contracts. The initial entries, in display order:

| ID | Editing owner | Storage adapter | Current target |
| --- | --- | --- | --- |
| `youtube_manual` | user/manual | OPNsense Config `hostlist.youtubedomains` | `youtube` |
| `youtube_found` | auto-owned, user-editable draft | root-private `auto-detect-owned/youtube.txt` | `youtube` |
| `user_manual` | user/manual | OPNsense Config `hostlist.userdomains` | `user` |
| `user_found` | auto-owned, user-editable draft | root-private `auto-detect-owned/user.txt` | `user` |
| `shared_found` | shared-auto, user-editable draft | `ipset/auto-domains.txt` | explicit `auto` |

Catalog fields include stable `id`, `owner`, `storage_kind`, platform binding (`model_field` or protected file key), editor kind, validation policy, semantic target and limits; the initial visible GUI order remains unchanged. Do not create a *second* runtime HOSTLIST writer registry: map catalog target IDs to the existing native target registry and reject disagreement. Future entries must be explicitly registered, validated and mapped to engine target ownership; count is data-driven, never assumed to be five in transport/UI iteration. This does NOT authorize additional targets or auto-attribution now.

Platform-neutral core owns list identity, semantic validation (existing Python domain policy), revisions, CAS/conflict decisions, changed-content semantics and candidate planning. The **OPNsense adapter** owns `Config::lock`, OPNsense Model, configd and native one-FD9 Shared Apply. A future pfSense adapter would implement its own platform-native config, locking, UI and lifecycle integration. No pfSense code now; do not emulate OPNsense FD9 blindly.

## Read API (first implementation target)

Expose a registry-driven read response via the existing authenticated Strategies endpoint, versioned to avoid interpreting old/new shapes interchangeably. Read must remain read-only, with original Config lock + existing protected file destination lock and stable per-source status. It must not initialize, repair, delete or save.

- **Manual** sources: their *full saved content* is already loaded by the native OPNsense Model form; do not return a duplicate megabyte-scale `content` through configd. Return `id`, `owner`, `status`, byte length and SHA-256 of the saved authoritative bytes, as well as the coherent Config revision. The frontend captures the original saved textarea baseline separately from the mutable draft before edits. It verifies UTF-8 bytes and the agreed `present\0` SHA-256 against this read before declaring that source ready. If browser/native textarea normalization makes exact proof impossible, refuse the snapshot and diagnose; never silently accept a mismatch or overwrite an unsaved edit.
- **Found-only** sources: return actual authenticated, bounded content, owner, status and revision from the existing protected P2 reader; distinguish safe empty, safe missing and uninitialized from corruption. Their storage remains in existing plaintext files.
- Each individual editor may show its *own verified* safe empty/content status even if a different source is unreadable; this is a display rule, not permission to Apply an unverified mixed snapshot.
- Cross-source Apply readiness remains **fail closed** unless all registered sources were qualified from the same agreed baseline. Preserve unsaved edits and report which read/stage failed without printing any private domains to logs.
- The current legacy `hostlistEditorsRead` JSON contract and browser tests must be versioned together. Do not ship a backend-only contract change that strands the installed frontend.

## Saving (preserve one existing authority)

- The full current *user-edited* text, or a verified byte-exact delta that reconstructs it, MUST reach the server when a manual list changed. A SHA or metadata alone is not user content.
- Unchanged manual fields are not redundantly sent through configd. Keep the existing bound SHA-delta path and original native Config re-read. Found-only edits continue through the existing `found-intent` PHP multipart upload and one original FD9 staging path.
- **Обязательно в ТЗ_6v3:** один Strategies `FormData + JSON` манифест для **всех пяти** источников, включая оба ручных YouTube/User и три найденных. В нём обычные неизменяемые поля формы, версии/ID и реальные данные **только изменённых** списков (текст/Blob или проверенная SHA-дельта). Повторно используем `found-intent.json`/`SharedApplyEnvelope`; метаданные не заменяют новый текст. Не делаем отдельный новый writer или обязательную chunk-систему.
- Any new whole-list Blob transport must be bounded by measured application/request budgets; no arbitrary PHP global limit increase. Chunking is **not in this initial scope** and needs a measured blocker and an explicit atomic-staging design if subsequently justified.
- Validation and conflict checks must be extended **only as necessary** to keep the current one-bottom-Apply safe. Do not undertake a separate project to rewrite all user-edit tracking or all concurrency checks now. A stale source must never overwrite a newer source silently.
- All edits remain ONE existing bottom Strategies Apply with the existing original FD9 authority, Config writer, rollback journal, P2 destination locking, service lifecycle and cross-source policy. No independent Auto Save/Reload, separate Config writer, SQLite, extra daemon or off-path target mutation.

## Storage, limits and future capacity

- **No mandatory migration out of `config.xml`**. Existing manual lists continue in its native OPNsense fields for the current scope. Existing discovered lists remain ordinary managed text files. The catalog may support `config` and `file` storage kinds, but any future decision to change the actual owner of a saved manual list requires explicit migration/backup/rollback acceptance.
- User expects 6–8 lists *total*, not 17, with little or no increase in aggregate domain count. Do not create a new file database or elaborate chunk subsystem based on invented capacity assumptions.
- Preserve finite product-level safety bounds (existing domain validator and transport budgets). Removing a redundant 1 MiB **product field guard** in favor of the already-supported domain policy is not the same as raising PHP `php.ini` limits. Determine any actual Config/render capacity blockers before changing them.

## Smallest effective implementation sequence

**S0/S1 code status (`_98` candidate):** `StrategiesHostlistCatalog` installed in the existing PHP API namespace and imported by root native snapshot and Settings controller for original five source IDs/owners and manual/auto target bindings. No new target registry, engine writer, `FormData` transport or root read schema yet. The known 1.77 MiB failure remains intentionally reproducible. **Next: S2 read/API/browser**, then S3 unified five-source multipart/JSON. [ТЗ_6v3](TZ_6v3.md).

1. Introduce the canonical Strategies catalog and a portable parser/validator with unit coverage; current five entries only and stable GUI IDs. No Voice or runtime target additions.
2. Reproduce the actual 1,774,109-byte saved User Domains + safe empty shared-list read failure on the old code. Adapt root read and authenticated API to metadata-only **for saved manual data**, retaining full found-only content and exact revisions; fix only directly applicable per-field product guards.
3. Update the Strategies frontend to capture manual saved baselines and verify the new read contract, preserve unsaved drafts and independent empty-list display. Keep native GUI geometry and one bottom Apply. Test F5 and a changed manual list rather than only a mocked positive read.
4. Подключить оба ручных и три найденных списка к одному `FormData + JSON` при сохранении существующих `found-intent.json`, SHA-дельт и одного original FD9 Apply. Реальные отредактированные байты должны доходить; большие Blob-части — по фактической необходимости и в пределах проверенных лимитов. Voice Apply не менять.
5. Fast red->green owner-sized regression and narrow relevant native OPNsense GUI/FD9 test; then source PR merge under current GitHub rules. Any test `.pkg` must be published separately only when authorized/requested and qualified. Owner appliance evidence remains separate.

## Explicit non-goals

IPSET Telegram, остальные IPSET, Exclude Domains, Exclude IPSet не входят в текущий HOSTLIST реестр и сохраняют свои валидаторы, правила и штатный Apply. Возможный отдельный тип `ipset`/исключения в будущем — [Future #1192](https://github.com/Tolian82/os-zapret2-restyle/issues/1192), не ТЗ_6v3.

Full pfSense implementation, altering the Voice page, adding 6–8 *new* lists now, changing the GUI design, global PHP tuning, mandatory move of manual data to text files, a second Config writer, independent list-save buttons, and comprehensive rewriting of unrelated user-change/concurrency logic.
