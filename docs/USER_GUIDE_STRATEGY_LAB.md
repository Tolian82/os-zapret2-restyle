# Using Strategy Lab

This guide describes the current packaged client. The approved [Chrome HTTP development plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) is not implemented yet; its future behavior must not be inferred from an old QUIC result.

Open **Services → Zapret2 → Diagnostics**.

Enter a domain that your ISP blocks. Use **Standard** for the primary TLS 1.3 search, with a finite adaptive budget whose configured Standard base is 150 seconds. Use **Extended** when TLS 1.2, plain HTTP, optional QUIC bypass testing, or a configured request-response UDP check is also needed; Extended has a configured additional 120-second base; actual finite budgets depend on eligible work.

## Enable QUIC

Extended mode shows **Enable QUIC** directly below **Generic UDP (optional)**.

- It is unchecked by default.
- Its checked/unchecked state is saved and survives a page reload.
- Unchecked means QUIC candidates are not tested.
- Checked means QUIC candidates are tested even when the Stage-30 control probe reports ordinary QUIC/IPv4 as blocked.

If every required endpoint already passes the direct HTTPS baseline, the job finishes without candidate or Extended testing, including QUIC. A bare IPv4 target requires Host/SNI for QUIC.

The control probe remains diagnostic information only. It no longer decides whether QUIC testing runs. This allows Strategy Lab to search for a QUIC bypass specifically when the provider blocks ordinary QUIC.

## Generic UDP

Generic UDP is optional and available only in Extended mode. To enable it for a job, provide both:

- a destination UDP port from `1` to `65535`;
- a payload file containing `1..4096` bytes.

Both values are required together. A file larger than 4096 bytes is rejected with a visible validation message before a new job starts; multi-megabyte files are intentionally not accepted as request payloads.

The page shows State, Outcome, and stages 00–99 and retains completed evidence. **Stop** persists cancellation, terminates the active bounded runner, and still completes cleanup and Zapret2 restoration before another lifecycle operation can run. Reloading Diagnostics recovers the active or newest completed job.

The stable-candidate table shows up to three candidates. Candidate number one is the default recommendation, but Strategy Lab never writes it to Settings automatically.

**Temporary circular validation** is offered only after a completed successful domain job has a valid three-to-five-item shortlist and verified restoration. It starts one temporary target-scoped profile for browser or application testing. Stop it when testing is complete. The saved Traffic Strategy remains unchanged.
