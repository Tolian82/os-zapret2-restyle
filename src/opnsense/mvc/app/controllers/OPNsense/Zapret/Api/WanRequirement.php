<?php
/** Shared pure WAN-first contract, independent of engine and Config writes. */
namespace OPNsense\Zapret\Api;

final class WanRequirement
{
    public static function value($raw): string
    {
        if (is_array($raw)) $raw = $raw['selected'] ?? null;
        return is_string($raw) ? trim($raw) : '';
    }

    public static function effectiveWan(array $current, array $fields = []): string
    {
        return self::value($fields['general']['waninterface']
            ?? $current['general']['waninterface'] ?? null);
    }

    public static function runtimeRequested(array $current, array $fields = []): bool
    {
        if (self::value($fields['general']['enabled']
            ?? $current['general']['enabled'] ?? null) === '1') return true;
        foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $name) {
            if (self::value($fields['voice'][$name]['enabled']
                ?? $current['voice'][$name]['enabled'] ?? null) === '1') return true;
        }
        return false;
    }

    public static function missingBeforeActivation(array $current, array $fields = []): bool
    {
        return self::runtimeRequested($current, $fields)
            && self::effectiveWan($current, $fields) === '';
    }
}
