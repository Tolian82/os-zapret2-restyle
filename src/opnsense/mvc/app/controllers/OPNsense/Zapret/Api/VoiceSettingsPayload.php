<?php

/**
 * Restrict the future Voice Apply to Voice-owned persisted model fields.
 * This is deliberately pure: no Config writes, configd invocation or
 * runtime changes. The backend must validate the complete Voice candidate
 * and the shared Telegram-IPSET baseline before committing this overlay.
 */
namespace OPNsense\Zapret\Api;

final class VoiceSettingsPayload
{
    private const SERVICES = ['telegram', 'discord', 'x', 'sip', 'custom'];

    public static function overlay(array $current, array $submitted): array
    {
        foreach (array_keys($submitted) as $section) {
            if (!in_array($section, ['voice', 'hostlist'], true)) {
                throw new \InvalidArgumentException('Unexpected Voice configuration group');
            }
        }
        $result = $current;
        if (array_key_exists('voice', $submitted)) {
            if (!is_array($submitted['voice'])) {
                throw new \InvalidArgumentException('Voice configuration must be an object');
            }
            foreach ($submitted['voice'] as $key => $value) {
                if ($key === 'waninterface') {
                    if (!is_scalar($value)) {
                        throw new \InvalidArgumentException('Voice WAN must be a string');
                    }
                    $result['voice']['waninterface'] = (string)$value;
                    continue;
                }
                if (!in_array($key, self::SERVICES, true) || !is_array($value)) {
                    throw new \InvalidArgumentException('Unexpected Voice service');
                }
                foreach ($value as $field => $text) {
                    if (!in_array($field, ['enabled', 'args'], true) || !is_scalar($text)) {
                        throw new \InvalidArgumentException('Unexpected Voice service field');
                    }
                    if ($field === 'enabled' && !in_array((string)$text, ['0', '1'], true)) {
                        throw new \InvalidArgumentException('Voice service checkbox must be 0 or 1');
                    }
                    $result['voice'][$key][$field] = (string)$text;
                }
            }
        }
        if (array_key_exists('hostlist', $submitted)) {
            if (!is_array($submitted['hostlist'])) {
                throw new \InvalidArgumentException('Voice IPSET group must be an object');
            }
            foreach ($submitted['hostlist'] as $key => $text) {
                if (!is_scalar($text) ||
                    !in_array($key, array_map(static function ($s) { return $s . 'ips'; }, self::SERVICES), true)
                ) {
                    throw new \InvalidArgumentException('Unexpected Voice IPSET field');
                }
                $result['hostlist'][$key] = (string)$text;
            }
        }
        return $result;
    }

    /**
     * Both pages edit the same Telegram IPSET, so both must compare the
     * exact original field value while Config is locked before any mutation.
     */
    public static function requireFreshTelegram(array $current, $baseline): void
    {
        StrategySettingsPayload::requireFreshTelegram($current, $baseline);
    }
}
