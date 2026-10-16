<?php

/**
 * Deterministic snapshot of the Zapret fields which influence Voice.
 *
 * Token covers every general/strategy/voice/hostlist model field, including
 * the Telegram IPSET shared with Strategies. It is not an authentication
 * secret; it detects legitimate concurrent edits by other browser tabs.
 * The future transaction must repeat the comparison under Config lock before
 * any mutation; validating the token alone does NOT authorize Apply.
 */
namespace OPNsense\Zapret\Api;

final class VoiceSettingsSnapshot
{
    private const GROUPS = ['general', 'strategy', 'voice', 'hostlist'];

    private static function canonicalize($value)
    {
        if (is_array($value)) {
            ksort($value, SORT_STRING);
            $result = [];
            foreach ($value as $key => $member) {
                $result[(string)$key] = self::canonicalize($member);
            }
            return $result;
        }
        if (is_string($value)) {
            return str_replace(["\r\n", "\r"], "\n", $value);
        }
        if (is_bool($value) || is_int($value) || $value === null) {
            return $value;
        }
        throw new \InvalidArgumentException('Unexpected non-scalar Zapret settings');
    }

    public static function digest(array $model): string
    {
        $tracked = [];
        foreach (self::GROUPS as $group) {
            $value = $model[$group] ?? [];
            if (!is_array($value)) {
                throw new \InvalidArgumentException('Malformed Zapret configuration group');
            }
            $tracked[$group] = self::canonicalize($value);
        }
        $json = json_encode($tracked, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        return hash('sha256', $json);
    }

    public static function requireFresh(array $model, $token): void
    {
        if (!is_string($token) || !preg_match('/^[a-f0-9]{64}$/D', $token)) {
            throw new \InvalidArgumentException(
                'Voice configuration baseline is missing. Reload the Voice page.'
            );
        }
        if (!hash_equals(self::digest($model), $token)) {
            throw new \InvalidArgumentException(
                'Voice or shared Strategies settings changed in another tab. Reload the Voice page.'
            );
        }
    }
}
