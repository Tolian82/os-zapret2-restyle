# Using Strategy Lab

Open **Services → Zapret2 → Diagnostics**.

Enter a domain that your ISP blocks. Use **Standard** for the primary TLS 1.3 search. Use **Extended** when TLS 1.2, plain HTTP, capability-gated QUIC, or a configured request-response UDP check is also needed.

The page shows the active stage and retains completed results. **Stop** requests cancellation; Zapret2 restoration continues and must finish before another lifecycle operation can run.

The stable-candidate table shows up to five candidates. Candidate number one is the default recommendation, but Strategy Lab does not write it to Settings automatically.

For a completed domain job with three to five candidates, **Temporary circular validation** starts one temporary target-scoped profile so browser or application behavior can be checked. Stop it when testing is complete. The saved Traffic Strategy remains unchanged.
