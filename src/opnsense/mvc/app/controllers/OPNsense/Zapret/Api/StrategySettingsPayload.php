<?php

/**
 * Scopes the existing Strategies Apply request to fields owned by that page.
 * Voice state and named Voice IPSETs must never be overlaid by a stale
 * Strategies form, even when an HTTP client sends an unexpected payload.
 *
 * Telegram IPSET is deliberately shared. A separate optimistic-concurrency
 * token is still required before enabling the new Voice Apply endpoint.
 */
namespace OPNsense\Zapret\Api;

final class StrategySettingsPayload
{
    private const FIELDS = [
        'general' => ['enabled', 'waninterface', 'divertport'],
        'strategy' => ['trafficargs', 'extraargs'],
        'hostlist' => [
            'mode', 'youtubedomains', 'telegramips',
            'userdomains', 'excludedomains',
        ],
    ];

    public static function overlay(array $current, array $submitted): array
    {
        $result = $current;
        foreach ($submitted as $group => $fields) {
            if (!array_key_exists($group, self::FIELDS) || !is_array($fields)) {
                throw new \InvalidArgumentException('Unexpected Strategies configuration group');
            }
            foreach ($fields as $field => $value) {
                if (!in_array($field, self::FIELDS[$group], true) || !is_scalar($value)) {
                    throw new \InvalidArgumentException('Unexpected Strategies configuration field');
                }
                if (!isset($result[$group]) || !is_array($result[$group])) {
                    $result[$group] = [];
                }
                $result[$group][$field] = (string)$value;
            }
        }
        return $result;
    }
}
