# Strategy Lab structured final results

Terminal results are rendered as structured evidence rather than only raw JSON.

The summary shows target, mode, outcome, and verified restoration. Every shortlist row shows protocol, port, family, selected/remote endpoint addresses, replay pass count, and the complete replay-verified Traffic Strategy profile.

The copy control copies the complete `profile` field, falling back to `strategy` only for historical result compatibility. Profile bytes remain in an in-memory JavaScript array and are never embedded into HTML attributes. Clipboard API is preferred; a temporary off-screen textarea is the compatibility fallback.

All displayed values are escaped before HTML insertion. Raw JSON remains available only under the advanced disclosure.

The same renderer is used for live completion and the persisted result restored after page reload.
