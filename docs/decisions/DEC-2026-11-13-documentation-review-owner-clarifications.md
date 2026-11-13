# 13 November 2026 — documentation review owner clarifications

**Status:** ACCEPTED OWNER DECISIONS. **Source:** explicit answers during the owner-requested documentation review. These are specific policy/scope decisions, not a fifth general rule book.

## Supported versions

Question: SECURITY named only the latest prerelease and main despite published stable releases. The owner selected **«Добавить стабильную»**: support the latest published stable release, latest testing prerelease and main. [SECURITY](../SECURITY.md) owns the resulting current support policy. The [former page](../history/stages/documentation-2026-11-13/snapshots/SECURITY.md) preserves the replaced wording.

## Voice ports, extra IPv6 checkbox and P2P

The owner initially selected «Всё в архив», then explicitly changed that decision during the same review: **«Я передумал. Voice с портами UDP, дополнительной галочкой IPv6 и P2P. Оставляем в дальних планах. Не убираем в архив.»** The latest instruction supersedes the initial archival choice. Keep the entire direction in the long-term roadmap, outside the archive; do not implement it as part of this documentation review or the immediate #1052 increment.

Primary retained design: [Voice UDP ports / extra IPv6 / P2P long-term plan](../architecture/VOICE_PORTS_IPV6_P2P_FUTURE.md). It contains the original section 13 and P2P engineering discussion. Existing managed-IPSET dual-stack support is already current; detailed P2P proposals retain their original proposal status pending the future specification. Current routes: [Voice contract](../architecture/VOICE_TRANSMISSION_GUI.md), [requirements](../REQUIREMENTS.md), [roadmap](../ROADMAP.md).

## Preservation boundary

Original information, contradictory older statuses, engineering details and rejected proposals are retained. Canonical DOC/DEV/CHAT/GH rule IDs are unchanged. Source snapshots are stage history within the still-active v0.6.x line, not a fabricated version-line closure or a new release.
