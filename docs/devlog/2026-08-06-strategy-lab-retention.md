# 2026-08-06 — Strategy Lab retention

Revision 44 adds lock-protected count-based cleanup for automated jobs and circular sessions. Only excess verified terminal artifacts are deleted. Active/latest, nonterminal, restoration-failed, unverified, and malformed evidence remains preserved regardless of the configured limit.
