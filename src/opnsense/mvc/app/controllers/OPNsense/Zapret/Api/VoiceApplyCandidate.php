<?php

/**
 * Prepare a Voice-only configuration transition entirely in memory.
 *
 * NO file writes, native backend calls, model mutations or service restarts.
 * The caller must hold the OPNsense Config lock for the complete
 * snapshot+prepare phase; future Apply must also hold the shared lifecycle
 * lock across persistence, candidate validation and runtime handoff.
 */
namespace OPNsense\Zapret\Api;

require_once __DIR__ . '/VoiceCandidateValidator.php';
require_once __DIR__ . '/VoiceSettingsPayload.php';
require_once __DIR__ . '/VoiceSettingsSnapshot.php';
require_once __DIR__ . '/StrategySettingsPayload.php';

final class VoiceApplyCandidate
{
    private const SERVICES = ['telegram', 'discord', 'x', 'sip', 'custom'];

    private static function normalizeActiveIpSet(string $raw): string
    {
        $seen = [];
        $result = [];
        foreach (preg_split('/\r\n|\n|\r/', $raw) as $source) {
            $entry = trim(trim($source), ',;:');
            if ($entry === '') {
                continue;
            }
            // This is reached ONLY after VoiceCandidateValidator accepted
            // canonical IPv4 host/CIDR, including the prohibition of host
            // bits in network prefixes.
            if (!isset($seen[$entry])) {
                $seen[$entry] = true;
                $result[] = $entry;
            }
        }
        return implode("\n", $result);
    }

    public static function prepare(array $previous, array $submitted, $snapshot): array
    {
        VoiceSettingsSnapshot::requireFresh($previous, $snapshot);
        $errors = VoiceCandidateValidator::check($submitted);
        if ($errors !== []) {
            return [
                'result' => 'failed',
                'validations' => $errors,
            ];
        }
        $next = VoiceSettingsPayload::overlay($previous, $submitted);
        // The production dvtws2 instance and divert socket are shared.
        // Until per-profile incoming-WAN isolation is proven, the kernel
        // capture interface must be identical for Strategies and Voice.
        // This matches the authoritative Python compiler preflight.
        $strategyWan = (string)($previous['general']['waninterface'] ?? '');
        $selectedWan = (string)($next['voice']['waninterface'] ?? '');
        if ($strategyWan === '') {
            return [
                'result' => 'failed',
                'validations' => [
                    'zapret.voice.waninterface' => 'Strategies WAN must be configured before Voice',
                ],
            ];
        }
        if ($selectedWan !== '' && $selectedWan !== $strategyWan) {
            return [
                'result' => 'failed',
                'validations' => [
                    'zapret.voice.waninterface' =>
                        'Independent Voice WAN cannot be isolated by the shared engine yet; select the Strategies WAN',
                ],
            ];
        }
        $enabled = [];
        $targetCounts = [];
        foreach (self::SERVICES as $service) {
            $record = $next['voice'][$service];
            $active = $record['enabled'] === '1';
            if (!$active) {
                // OFF preserves drafts verbatim, even when they do not yet
                // meet native STUN syntax. Other shared pages must not
                // silently lose those settings.
                continue;
            }
            $name = $service . 'ips';
            $normalized = self::normalizeActiveIpSet($next['hostlist'][$name]);
            $next['hostlist'][$name] = $normalized;
            $enabled[] = $service;
            $targetCounts[$service] = count(explode("\n", $normalized));
        }
        $changed = [];
        foreach (['voice', 'hostlist'] as $group) {
            if ($group === 'voice') {
                $fieldNames = ['waninterface'];
                foreach (self::SERVICES as $service) {
                    $fieldNames[] = $service . '.enabled';
                    $fieldNames[] = $service . '.args';
                }
            } else {
                $fieldNames = array_map(
                    static fn($service) => $service . 'ips',
                    self::SERVICES
                );
            }
            foreach ($fieldNames as $field) {
                if (str_contains($field, '.')) {
                    [$name, $member] = explode('.', $field, 2);
                    $prior = (string)($previous['voice'][$name][$member] ?? '');
                    $final = (string)$next['voice'][$name][$member];
                } else {
                    $prior = (string)($previous[$group][$field] ?? '');
                    $final = (string)$next[$group][$field];
                }
                if (str_replace(["\r\n", "\r"], "\n", $prior) !==
                    str_replace(["\r\n", "\r"], "\n", $final)) {
                    $changed[] = $group . '.' . $field;
                }
            }
        }
        return [
            'result' => 'prepared',
            'candidate' => $next,
            'changed_fields' => $changed,
            'enabled_services' => $enabled,
            'target_counts' => $targetCounts,
            // This is a planning hint, NOT an authorisation to call
            // configctl or to skip authoritative Python release checks.
            'requires_runtime_handoff' => $changed !== [],
        ];
    }
}
