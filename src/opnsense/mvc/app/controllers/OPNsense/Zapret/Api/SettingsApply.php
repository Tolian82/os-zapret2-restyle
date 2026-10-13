<?php

/**
 * Shared, side-effect-free candidate boundary for the Strategies and Voice
 * forms. The public controllers keep their own field whitelists, but both
 * must submit a whole-model candidate to the same future native Apply worker.
 *
 * A dependency token is a witness for the generation used to prepare the
 * candidate, never an authorization to save or activate it. The privileged
 * worker must re-read the native Config under FD9 and a fresh Config lock,
 * repeat this comparison, then revalidate its full runtime before mutation.
 */
namespace OPNsense\Zapret\Api;

require_once __DIR__ . '/StrategySettingsPayload.php';
require_once __DIR__ . '/VoiceApplyCandidate.php';
require_once __DIR__ . '/VoiceSettingsSnapshot.php';

final class SettingsApply
{
    private static function sameText(string $left, string $right): bool
    {
        return str_replace(["\r\n", "\r"], "\n", $left) ===
            str_replace(["\r\n", "\r"], "\n", $right);
    }

    /**
     * Build a full Strategies candidate without changing Voice or any other
     * fields outside the Strategies whitelist. The shared Telegram IPSET
     * requires the existing browser baseline as an additional stale-tab guard.
     */
    public static function prepareStrategies(array $previous, array $submitted, $telegramBaseline): array
    {
        StrategySettingsPayload::requireFreshTelegram($previous, $telegramBaseline);
        $candidate = StrategySettingsPayload::overlay($previous, $submitted);
        $changed = [];
        foreach ($submitted as $group => $fields) {
            foreach ($fields as $name => $_) {
                $before = (string)($previous[$group][$name] ?? '');
                $after = (string)$candidate[$group][$name];
                if (!self::sameText($before, $after)) {
                    $changed[] = $group . '.' . $name;
                }
            }
        }
        return [
            'result' => 'prepared',
            'candidate' => $candidate,
            'changed_fields' => $changed,
            'dependencies' => VoiceSettingsSnapshot::digest($previous),
        ];
    }

    /** All five Voice services, with the original full-model snapshot gate. */
    public static function prepareVoice(array $previous, array $submitted, $snapshot): array
    {
        $plan = VoiceApplyCandidate::prepare($previous, $submitted, $snapshot);
        if (($plan['result'] ?? null) === 'prepared') {
            $plan['dependencies'] = VoiceSettingsSnapshot::digest($previous);
        }
        return $plan;
    }

    /**
     * Re-check the entire relevant shared Zapret generation immediately
     * before the future runtime switch. An unrelated OPNsense subsystem edit
     * is not included, but changed ordinary, WAN, Voice or shared IPSET input
     * requires a fresh candidate. Never write the older full Config XML.
     */
    public static function requireUnchanged(array $plan, array $live): void
    {
        if (($plan['result'] ?? null) !== 'prepared' ||
            !isset($plan['dependencies']) || !is_string($plan['dependencies'])) {
            throw new \InvalidArgumentException('Incomplete shared Apply candidate');
        }
        VoiceSettingsSnapshot::requireFresh($live, $plan['dependencies']);
    }
}
