# Using Strategy Lab

Open **Services → Zapret2 → Diagnostics**.

Enter a domain that your ISP blocks. Use **Standard** for the primary TLS 1.3 search, with an enforced 150-second search budget. Use **Extended** when TLS 1.2, plain HTTP, capability-gated QUIC, or a configured request-response UDP check is also needed; Extended may use one additional shared 120-second allowance.

The page shows State, Outcome, and stages 00–99 and retains completed evidence. **Stop** persists cancellation, terminates the active bounded runner, and still completes cleanup and Zapret2 restoration before another lifecycle operation can run. Reloading Diagnostics recovers the active or newest completed job.

The stable-candidate table shows up to five candidates. Candidate number one is the default recommendation, but Strategy Lab never writes it to Settings automatically.

**Temporary circular validation** is offered only after a completed successful domain job has a valid three-to-five-item shortlist and verified restoration. It starts one temporary target-scoped profile for browser or application testing. Stop it when testing is complete. The saved Traffic Strategy remains unchanged.
