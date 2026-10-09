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

    /**
     * Optimistic guard for the Telegram IPSET shared by both GUI pages.
     * Reject an old Strategies tab before any model or runtime mutation.
     * The baseline is raw form content, not a request to change the IPSET.
     */
    public static function requireFreshTelegram(array $current, $baseline): void
    {
        if (!is_string($baseline)) {
            throw new \InvalidArgumentException('Telegram IPSET baseline is missing. Reload the Strategies page.');
        }
        $saved = (string)($current['hostlist']['telegramips'] ?? '');
        // Browser textareas normalize line endings. Compare the same data,
        // while keeping all address/content validation with the model.
        $normalize = static function (string $value): string {
            return str_replace(["\r\n", "\r"], "\n", $value);
        };
        if (!hash_equals($normalize($saved), $normalize($baseline))) {
            throw new \InvalidArgumentException(
                'Telegram IPSET changed in another page. Reload the Strategies page before applying.'
            );
        }
    }

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
