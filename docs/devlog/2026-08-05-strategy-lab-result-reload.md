# 2026-08-05 — Persisted result reload

Revision 40 adds an atomic latest-job pointer, migration fallback for existing job directories, and Diagnostics startup logic that immediately restores a terminal result or resumes a nonterminal job. No new lifecycle transaction is started by page reload.
