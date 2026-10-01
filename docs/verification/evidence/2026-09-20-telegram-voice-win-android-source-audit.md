# Historical Telegram Voice client-source audit (corrected)

**Status:** Historical evidence reconciled on 2026-10-01 from [PR #287](https://github.com/Tolian82/os-zapret2-restyle/pull/287). This is not a statement about current Windows/Android client parity.

## Independently checked source identities

At the exact historical [Telegram Desktop commit `4d4da471fbee771c10e173a83c003ba1728989f1`](https://github.com/telegramdesktop/tdesktop/tree/4d4da471fbee771c10e173a83c003ba1728989f1), the `Telegram/ThirdParty/tgcalls` submodule actually points to **`2faee3b5524f54d56c91c2058c00e11c656a74b3`**. PR #287 incorrectly called its submodule `24694f64b03e301ec2c90792566046e61a2c4967`.

For the historical [Android commit `9552e5541e1274b9557c9832b204dbfcaf44b3dc`](https://github.com/DrKLO/Telegram/tree/9552e5541e1274b9557c9832b204dbfcaf44b3dc), an independent exact-commit content comparison found:

| Audited `tgcalls` file | Android vs upstream `24694f64...` | Android vs actual Desktop `2faee3b...` |
|---|---|---|
| `v2/ReflectorPort.cpp` | Identical | Different |
| `v2/NativeNetworkingImpl.cpp` | Identical | Different |
| `EncryptedConnection.cpp` | Identical | Different |

This preserves the valuable historical Android/upstream match but **does not** establish the original PR's claimed exact Windows/Android parity. Different source bytes do not, by themselves, prove different runtime behaviour either.

## Integration decision

The source identities and the corrected limitation belong in this historical evidence, not in the active TOS build recipe. The proposal in PR #287 to pin the earlier `e3069322...` test binary and its corresponding lexical CI checks is superseded: the project has since qualified the active `efd330ca...` binary. See [current build evidence](2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md), the [research](../../research/TELEGRAM_VOICE_UDP.md) and the [current handoff](../../START_HERE.md).

Do not infer parity for the currently distributed Windows/Android clients from this historical comparison. Future client-parity work requires newly resolved source and actual client/configuration identities.
