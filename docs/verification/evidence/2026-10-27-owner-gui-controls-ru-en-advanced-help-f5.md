# Owner report — RU/EN, Advanced, Help and F5 controls

**Date:** 27 October 2026. **Evidence class:** owner-reported successful manual UI observations, without supplied screenshot, CLI package inventory or independent API/transaction trace for this particular report.

The owner explicitly reported: **"RU/EN, Advanced и Help, F5 - отлично работают."**

**Accepted limited observation:** Russian/English language selection, the native Advanced UI toggle, the Help UI toggle, and page refresh (F5) behaved correctly in the owner's browser. This is a positive manual observation for existing interface controls; it is not a new controlled test of the destructive Remove button.

**Identity boundary:** The owner did **not** provide `pkg info -x os-zapret2-restyle` in this report. The last independently supplied appliance package identity remains `os-zapret2-restyle-0.5.9_44`; package `v0.5.9_45` is merged and CI-qualified in source but was **not** published as a persistent GitHub prerelease asset at the time this report was recorded. Do not attribute this user report to installed `_45` without new evidence; the owner might have independently built a different version.

**Not established:** Actual new `_45` typed `REMOVE N` modal, one correlated destructive GUI POST, native Stop/quarantine/Apply/restart, rollback, inventory after GUI Remove, cache and Strategy Lab Job. Those remain explicit Stage 7 / Stage 8 owner-installed acceptance gates. Do not authorize or submit a destructive Remove based on this UI report.

**Next gate:** Verify installed-package identity once a testing `v0.5.9_45` asset has been published and installed, then repeat these UI observations against that exact candidate alongside the separately approved Stage 7 GUI Remove acceptance.
