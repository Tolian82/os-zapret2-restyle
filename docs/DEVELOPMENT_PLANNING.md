# Development planning and functional-block execution

**Status:** CANONICAL · MANDATORY LEVEL 1
**Updated:** 2026-11-26

The normative home for general specification preparation, development planning, functional-block execution and progress. Existing DEV identifiers are preserved. See [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) for product architecture and safety, [TESTING_RULES.md](TESTING_RULES.md) for verification, [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) for delivery, [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) for documentation and [CHAT_RULES.md](CHAT_RULES.md) for owner communication.

## Functional outcomes and approved scope

DEV-007. **Correctness and an observable result define each logical increment.** Before implementation, name the user scenario, bounded change and evidence required to accept it. Prefer the smallest change that fully solves the confirmed problem and preserves required behavior. A discovered blocking defect remains the current task until corrected and checked; do not advance to an unrelated increment or declare the blocked scenario complete. If the required environment is unavailable, record the concrete boundary and leave acceptance open. Commit count, test count and internal component completion are not substitutes for the user-visible result.

**Functional-block principle (owner-approved 2026-11-26):** Plan backwards from an observable accepted result. All logically linked code, configuration, UI, test and documentation edits needed for that result form one functional block by default. Define before implementation: specification/requirement and outcome; linked changes and exact production paths/dependencies; explicit exclusions and boundaries; highest risk R0–R3 under DEV-072; existing tests and independently justified additions; objective acceptance and stop criteria; one logical PR and necessary CI under GH-010. The specification defines what and the ordered plan defines when. Private helpers and internal checkpoints are not independently deliverable results. Never combine unrelated work or cross a mandatory GO/compatibility/safety boundary.

DEV-017. **One logical engineering scope remains one logical change.** Same-root-cause repairs, tests, and documentation belong together; unrelated improvements wait for their own scope. GitHub same-scope handling is enforced by `GH-011`.

Implement linked edits together with quick local intermediate checks, then one targeted acceptance set, one logical source PR and applicable exact-head CI. Do not create a revision, PR, heavy CI cycle or handoff for every internal edit. Split only for a real independent outcome, mandatory dependency/compatibility gate, demonstrated safety/review necessity or concrete technical blocker; record why. At completion reconcile affected documents under DOC-036 and DOC-037. Fix same-block defects in the same block.

DEV-019. **Requirements or architecture changes require explicit rationale.** A change to approved user-visible behavior, safety semantics, ownership, or public contract is not smuggled in as an implementation cleanup.

Prepare a specification with purpose, observable behavior, constraints, interfaces, safety/non-goals, acceptance criteria and explicit owner decisions. Prepare the ordered implementation plan with the functional-block template in DEV-007, dependency order and existing evidence. Link general rules instead of copying them; do not quietly turn speculative details or unrelated tests into new requirements. Preserve approved requirements, GO boundaries and owner authorization.

DEV-047. **Progress is measured by accepted functionality.** A user-facing feature is complete only after its approved acceptance criteria are evidenced at the required source, CI/package, and installed-appliance levels. Commit counts, revision increments, test volume, and speculative hardening do not substitute for end-to-end acceptance. Once a usable implementation exists, prioritize its qualified delivery and owner-observed verification over unrelated internal expansion.

Measure progress by accepted functional blocks and outstanding acceptance criteria, not by internal implementation steps or test counts.

DEV-049. **Model initiative improves the approved plan, but does not silently extend it.** The model shall identify and propose demonstrably useful changes to decisions, requirements, design, or priorities, explaining evidence, expected benefit, cost, and risk. New, unapproved research directions are outside the mandatory current delivery scope; an initiative becomes a required workstream only after owner agreement. The model continues to execute already approved work without unnecessary reapproval.

DEV-063. **The approved specification, ordered plan, and canonical rules govern delivery; do not create side projects from technical difficulties.** The owner's current approved specification defines **what** to deliver, the approved plan defines **the sequence**, and the canonical rules govern **how** to implement and verify it. Work toward the observable accepted result using the existing architecture and the smallest necessary same-scope correction; a discovered obstacle is not permission to start a separate subsystem, speculative safety mechanism, open-ended test campaign, documentation project, or competing implementation. Propose an actually necessary change of scope or approach with its evidence and impact, but do not implement it as an assumed prerequisite. **If a decision, approach, or choice remains uncertain after checking the approved authority and evidence, ask the owner before acting on that uncertainty under `CHAT-014`; never silently guess or substitute a plausible personal preference.** Do not ask again for settled decisions or ordinary already-authorized steps.

Preserve stage order and GO boundaries; group linked edits within each stage. Replan only when direct evidence changes the block's scope; record the reason rather than recursively inventing micro-stages. Do not expand testing after the chosen gates pass except under DEV-061 and DEV-072.

## Cross-reference registry

<!-- RULE-XREF-OUT-BEGIN -->
| Source rule | Target rules |
|---|---|
| `DEV-007` | `DEV-072`, `GH-010` |
| `DEV-017` | `DOC-036`, `DOC-037`, `GH-011` |
| `DEV-063` | `CHAT-014`, `DEV-061`, `DEV-072` |
<!-- RULE-XREF-OUT-END -->

<!-- RULE-XREF-IN-BEGIN -->
| Target rule | Referenced by |
|---|---|
| `DEV-007` | `DEV-062`, `GH-010`, `GH-069` |
| `DEV-017` | `GH-010`, `GH-011` |
| `DEV-063` | `CHAT-014` |
<!-- RULE-XREF-IN-END -->

## Rule lifecycle

No cancelled or replaced rules in this book. IDs remain permanent.
