# Archived legacy branch refs — 8 November 2026

This immutable audit record captures the **88** retired original branch ref names and exact tip commits before cleanup. The release `v0.6.3` and `main` are NOT rewritten.

- Source main SHA: `be25e7fc297696a40404bf832f943e9bf22a5c7f`.
- Stable tag: `v0.6.3` (GitHub annotated tag ref SHA `9c20f014d7a0be745ed2a33cdc881bb68b097fd7`).
- Total original branches: **89**, of which **54** `publish/*` refs and **4** other refs were independently verified to be ancestors of `main` with zero ahead commits.
- The archival commit uses `main` as its first Git parent and **34 additional parent commits** (all non-publish source branch heads, including the four already-merged ones), preserving otherwise-unmerged branch history without introducing their files into `main`.
- All refs were non-protected and there were zero open pull requests at audit time; no branch containing post-audit changes may be deleted.
- This branch is intentionally *not* a source branch for normal merges. Check out `main` for production; the archive is for forensic recovery only.

| Retired ref | Original commit SHA | History preserved through |
|---|---|---|
| `audit/stage0-tests-ci-scenarios-v0.6.2_19` | `f8c0102029ce318239b0fe1d7e9be749c058f768` | archive additional parent |
| `dev/remove-engine-path-identity-v0.5.9-12` | `95a40647ab5df01729ef99a8c691c5c5c9c8f67d` | archive additional parent |
| `dev/remove-inert-jail-direct-argv-v0.5.9-17` | `eba2ecd9e574ad3d3c1df8b758ac7bb6f12c761f` | archive additional parent |
| `dev/remove-jail-shim-composition-v0.5.9-15` | `9ac645b2419be60856a0a33b0abd5b8ce50bfca7` | archive additional parent |
| `docs/add-readme-star-request` | `261ce3e003ac71e6389feaf5c26e6fa32cf65efe` | archive additional parent |
| `docs/decisions-zapret2-fork-ideas-20261023` | `49a7cb82e435fe16f61cb9be01aa4e366eac7e41` | archive additional parent |
| `docs/installed-lua-ttl-capability-20261019` | `f488ace4d057b3ccce46b1bda9ea2f6f6b9575d5` | archive additional parent |
| `docs/v0.5.5_7-nofake-reflector-owner-live` | `8853318bde3518fd1776a42e5572a89b9c8a6885` | archive additional parent |
| `docs/v0.5.9-34-ci-build-evidence` | `006e48256710b8f16d09915c806a5099562f9ed0` | main ancestry |
| `docs/v0.5.9_37-remove-r2-owner-proof` | `2961c6cff8dc19f966604ce6326f8bf0324a3d63` | main ancestry |
| `docs/v0565-owner-native-gate-diagnosis` | `c4a5d0a950a43b3c4e6eeb51b12ef7db77b036d2` | archive additional parent |
| `docs/v0567-stage2-v2-ci-accepted` | `32a9148cf02cc9709b42c8e8bde53ce0ac45af2c` | archive additional parent |
| `feat/strategy-lab-stage1-private-curl-impersonate` | `406d25c46fe61623db97c901f74bf09cbb719ca0` | archive additional parent |
| `feature/remove-owner-live-acceptance-037` | `50e4843d429530d2ae3f1f769f10fdfeced3b220` | archive additional parent |
| `feature/v0.6.1-13-python-runtime-contract` | `55718c80b40e11abded40427df04e80f24a7f6c2` | archive additional parent |
| `fix/main-diff-check-043` | `e805a5431b27f4d8385d293773ecf119f6e50197` | archive additional parent |
| `fix/remove-original-inode-rollback-035` | `42b0192f4b9da96089ab67bd4736850022cea91a` | archive additional parent |
| `fix/strategy-lab-native-owner-v0566` | `ec3e86a44578f5ab12ac49a920dfb32a7be06603` | archive additional parent |
| `fix/v05618-lab-result-summary-l10n` | `aab94d898ee06a8730f97f50d17d077c3183c2c4` | archive additional parent |
| `fix/v05619-strategy-apply-spinner` | `35c8121e5071c8be5131aa2b99eea708b39d61d5` | archive additional parent |
| `fix/voice-legacy-cli-preflight-v0.5.3_15` | `ab6cb2a486775b2a5aa8b744edd0152014e94d41` | archive additional parent |
| `publication-record/v0.5.3_8` | `3b2310ef017aff839920ccd5648c40bf325f8d2c` | archive additional parent |
| `publish/v0.4.1_14` | `df20ed2ebe7f6c37c4189008e06e80700ae89ce4` | main ancestry |
| `publish/v0.4.1_16` | `1a7baa7d1afee032170e654c6840cfb4e3b55ea2` | main ancestry |
| `publish/v0.4.1_17` | `ebf071122b2613c4fe56b5af4e5e9f07c99e9122` | main ancestry |
| `publish/v0.4.1_18` | `fa1b924a5c1d646f0daec13aff6e7406a534c6a3` | main ancestry |
| `publish/v0.4.1_19` | `6d06f0c3dfc7a76f0dc7b43ca6ba8cc0d0f83758` | main ancestry |
| `publish/v0.4.1_20` | `d732965c143563352e18ac58c209aeb30a6d4feb` | main ancestry |
| `publish/v0.4.1_22` | `71baa9d0e7cd3e04535ff9b9ba87aefe8f4e8cfe` | main ancestry |
| `publish/v0.4.1_23` | `3cd3ecc8b9976b1ec8000e2eccfa48f6898d1e73` | main ancestry |
| `publish/v0.5.3_4` | `449e777b0990bd87a7dc5bcce1377a40fb4e4a97` | main ancestry |
| `publish/v0.5.3_5` | `d91c8cb9ff957ef71545cb8d8bcca26638101f77` | main ancestry |
| `publish/v0.5.3_6` | `aa5a5fc867ef229e95ef017f337d08571366aa04` | main ancestry |
| `publish/v0.5.3_7` | `e402d896f1323c03bb89dbdb39a350f79fb0f596` | main ancestry |
| `publish/v0.5.3_8` | `2c8e2dacad45115ad0bcfd567344c567227d48e2` | main ancestry |
| `publish/v0.5.3_9` | `e979517ad38eaef6285fca49582ba9ca84bb8b7b` | main ancestry |
| `publish/v0.5.3_10` | `30e71804f50d2fad9bededcf1b8ff1863937753f` | main ancestry |
| `publish/v0.5.3_11` | `449d614cee030090bb8179f89b830b2919cd6fec` | main ancestry |
| `publish/v0.5.3_12` | `5bfafc01de2183392b325de6538d4fb943b50ea5` | main ancestry |
| `publish/v0.5.3_13` | `b8c5c35635a472e2b642c373f8fc724811a18ce8` | main ancestry |
| `publish/v0.5.3_14` | `be6669469049279713128d290cd649ba4fa96462` | main ancestry |
| `publish/v0.5.3_15` | `64ca0e4f46253aa52c78a7311125e985ef9e72df` | main ancestry |
| `publish/v0.5.3_16` | `8c50c401f4494d76a674cfa80d1b7150193eeb61` | main ancestry |
| `publish/v0.5.3_17` | `6501b0fbc4f3b678b4c9fe4b8a20229e9bdc0184` | main ancestry |
| `publish/v0.5.3_19` | `ff43ed56d0a348d8558bceb7a05151cd2bc23646` | main ancestry |
| `publish/v0.5.3_22` | `22fbbed3fa8e5bb223ba1e4b87577b7aeb6fa87a` | main ancestry |
| `publish/v0.5.3_26` | `53485762181de25e1da823019e979c9af591b06a` | main ancestry |
| `publish/v0.5.3_28` | `93c8510f1f7b28aa5d19e0a460db375d9791c8a7` | main ancestry |
| `publish/v0.5.5_3` | `437472c2030a5110f2224905e30feaedc54160c5` | main ancestry |
| `publish/v0.5.5_4` | `fdfa3b8dbb0ab30d4bffa9cb4bb2ee9a5bd2f521` | main ancestry |
| `publish/v0.5.5_6` | `4fe557b94205118f98888c4936f7f11574cde128` | main ancestry |
| `publish/v0.5.5_7` | `79270c52b46fc226caacefb02b4b65d06148e3cf` | main ancestry |
| `publish/v0.5.6_13` | `1980e0a0f83cb5245ad904b4cdcbead4c4a26341` | main ancestry |
| `publish/v0.5.6_14` | `a8a658f0ed85f9363a6cc040067ea061cdab3e4f` | main ancestry |
| `publish/v0.5.6_15` | `17fd1e07dee403f8b8911ba17be45e2041e7feda` | main ancestry |
| `publish/v0.5.6_16` | `253aa4c9a88192e2bd9f86161acebe6e4001d213` | main ancestry |
| `publish/v0.5.6_17` | `b735b0bb55933f0abab007f3165cbb733ceb6d33` | main ancestry |
| `publish/v0.5.7_30` | `f852f3cdc35fe62c47b943e3a01ccdf56fbb81e1` | main ancestry |
| `publish/v0.5.7_46` | `065280eef9a03d540c220820380e7103993a07eb` | main ancestry |
| `publish/v0.5.7_47` | `fabed3a5fb8a0ece2f64966c243bd62dc8150275` | main ancestry |
| `publish/v0.5.7_48` | `4a556a89e33411fde9a5bc3e448a8a8d242d4c48` | main ancestry |
| `publish/v0.5.9_37` | `fdc67d667e18c36552986b3482049371401491a2` | main ancestry |
| `publish/v0.5.9_38` | `1266917215548f86455c9ed984d5e79ccdf7c3bc` | main ancestry |
| `publish/v0.5.9_40` | `a3b6a140a5ebe253f67958f4cc6abbd1747acb94` | main ancestry |
| `publish/v0.5.9_41` | `379139552eb47c0faa77db0496a0c66f9970cb28` | main ancestry |
| `publish/v0.5.9_42` | `6d79349ead6fca0a563e7854f17fc663b25ad4aa` | main ancestry |
| `publish/v0.5.9_43` | `a58be7048662e47f37568677197ed8d1096c5472` | main ancestry |
| `publish/v0.5.9_44` | `656bbaaeeb4cfd699feaef6a4de33f03791e57fa` | main ancestry |
| `publish/v0.5.9_47` | `88a865765805c3b73829137713353c1648d96264` | main ancestry |
| `publish/v0.6.1_9` | `931ba3e8341d26800e3cac0374ae38b54a1b5ffe` | main ancestry |
| `publish/v0.6.1_10` | `450485597f0ff9e0a722f061df1485d2a191e62b` | main ancestry |
| `publish/v0.6.1_11` | `e7e102ad68829c3f1c79aa49307ef2b04cabae80` | main ancestry |
| `publish/v0.6.1_12` | `acfd77bd2e1a8bca5e8d0fd5a9d35ef54d31dfd5` | main ancestry |
| `publish/v0.6.1_30` | `722084d42d66ac4db8b22368cba0fcd0c5588ebf` | main ancestry |
| `publish/v0.6.2_181` | `e7ca383d126da236b0630822fb04acefe7a9f641` | main ancestry |
| `publish/v0.6.2_183` | `3ce52de6386f308c7b873494000de6e90cb090ee` | main ancestry |
| `recovery/base` | `d6067b78ee4fc4e60865dbf5a7eb9368c6e4e2b6` | main ancestry |
| `stage2/held-fd9-native-pkg-v0.6.2_79` | `4d64c04e3f234ce3c743e0d2da49e648cbb91469` | archive additional parent |
| `stage2/locked-real-unsafe-owner-v0.6.2_76` | `3804e74b0491d88e9c75140cf1a3a832335f4dd4` | archive additional parent |
| `stage2/native-package-ci-path-classifier-v0.6.2_63` | `f00da41336a16d9a4be584939bfd0545f71cb498` | archive additional parent |
| `stage2/old-fd9-recursion-v0.6.2_80` | `3ca56bcc7a100e2de21341707a267dec59ff91d7` | archive additional parent |
| `stage2/real-configd-unlock-v0.6.2_78` | `1255066ea4ce3d62192ab199eb519a6d08d9db04` | archive additional parent |
| `test/v0567-stage2-chrome-v2` | `4031d8fac575116b8cc54083e29e860919fc7d63` | archive additional parent |
| `test/v0568-chrome-v2-qualified` | `1fd0b141ac7e904e3fc1960f2048a779fb14089a` | archive additional parent |
| `v0.5.0_3-docs-20261002-ice-timeout-evidence-v2` | `c2e767a5de08469e605ffb201409226dcdb3c9cb` | archive additional parent |
| `v0.5.0_4-telegram-voice-ipfrag` | `3ecdd1b3326fe7655e1d7df9edd51808e2a68dc9` | archive additional parent |
| `work/v0.6.2_136-offguest-host-checkpoint-ci` | `2289f2c680e76a516cf272cf48d8d7c1f9db650b` | archive additional parent |
| `work/v0.6.2_145-native-syshook-installed-lifecycle` | `61d4033103d6a4c4012d000b65b36449d875f711` | main ancestry |

**Safety:** Deleting a Git branch ref does not erase its Git commits when reachable from another ref. The archive is a preservation mechanism, not an assertion that abandoned experimental code should be merged. This file is a snapshot, not an executable deletion instruction.


## Follow-up archive before stale-branch cleanup — 11 November 2026

After the owner accepted the main lifecycle specification v1.3 and published stable `v0.6.4_1`, a read-only audit found 11 live refs (one `main`, this intentional archive, two stale unmerged experiments, and seven obsolete testing publisher refs). There were **no open pull requests**.

The two divergent and no-longer-active experiment histories below are **preserved as additional Git parents of this new archival commit**, rather than force-merged into active product `main`. Their source-specific test claims are historical, not current acceptance or new work.

| Retired branch | Audited exact tip SHA | Disposition |
|---|---|---|
| `diagnostics/g01-process-attestation` | `72371096dadbb74d7bcf0b9ba9a6c06343f4f9d3` | Old G01 process-owner diagnostic experiment; superseded by accepted G01 and stable v0.6.4; history preserved by archive parent |
| `feature/g10a-two-pass-native-https-regression-20261110` | `1111cab59cb87fd79373148256d27347556f4f0f` | Old G10A Useful Links/Volt-render native diagnostic sequence; GUI Useful Links section deliberately removed under owner's v1.3, history preserved by archive parent |

Publisher-only branch refs are safe to retire without extra parents: the seven immutable testing tags below independently point to the **exact same source commit SHA** as their respective publish branch, and each GitHub Release contains the matching native `.pkg` asset. Removing only a branch ref does not change any tag/asset.

| Published tag / former branch | Exact source SHA | Protected proof |
|---|---|---|
| `v0.6.3_29` / `publish/v0.6.3_29` | `0ba0c5fcf041201465c647b94597e51c2a1ac40a` | immutable tag + published package |
| `v0.6.3_33` / `publish/v0.6.3_33` | `48564cde7910f0c3bb463aed9db65d2d6fbaf42f` | immutable tag + published package |
| `v0.6.3_40` / `publish/v0.6.3_40` | `698cb7f219a729cfd0423b13a009489538038199` | immutable tag + published package |
| `v0.6.3_43` / `publish/v0.6.3_43` | `41bd7d5cd70f6cef12928ee264613ee8af2f2e70` | immutable tag + published package |
| `v0.6.3_47` / `publish/v0.6.3_47` | `f47eb7dbdf37fde1a3a99aaf048bed28e373c25f` | immutable tag + published package |
| `v0.6.3_50` / `publish/v0.6.3_50` | `ba0d14d5a8d1d35913d8a0549473ea69630f1687` | immutable tag + published package |
| `v0.6.3_52` / `publish/v0.6.3_52` | `92a883b50466cb33da7ed062f821b743c45c485f` | immutable tag + published package |

**Retention policy:** Keep `main` as the only production branch and `archive/retired-branches-2026-11-08` as the **only historical preservation branch**. The archive itself is NOT a candidate for merger to `main`. Its current Git tip has its previous archival commit as first parent and the above two unmerged branch tips as additional parents; the 34 older retired branch heads remain reachable through the first parent. Temporary cleanup job/workflow is meant to reside on an ephemeral ref only, not persist in `main`. Do not delete/rewrite any historical stable or prerelease tags or GitHub Release assets.
