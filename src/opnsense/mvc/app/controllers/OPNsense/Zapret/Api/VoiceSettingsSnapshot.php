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
            // OPNsense BaseListField options include localized display labels
            // and unselected entries that can differ between web and root
            // configd PHP. Hash only the selected keys (stored semantics).
            if ($value !== []) {
                $optionList = true;
                foreach ($value as $option) {
                    if (!is_array($option) || !array_key_exists('selected', $option) ||
                        !array_key_exists('value', $option)) {
                        $optionList = false;
                        break;
                    }
                }
                if ($optionList) {
                    $selected = [];
                    foreach ($value as $key => $option) {
                        if (!in_array($option['selected'], [0, 1, false, true, '0', '1'], true)) {
                            throw new \InvalidArgumentException('Invalid shared model selection');
                        }
                        if ($option['selected'] == 1) {
                            $selected[] = (string)$key;
                        }
                    }
                    sort($selected, SORT_STRING);
                    return implode(',', $selected);
                }
            }
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

    /**
     * Read-only committed-owner inspection of the pre-v0.6.1 Config shape.
     * The native inspector must independently attest the sealed common
     * owner, release and IPFW. Never use this as a write/Apply baseline.
     *
     * Exactly one newly introduced, strictly empty optional field may be
     * omitted for comparison against the older committed digest. Every
     * previous tracked setting must retain the same canonical SHA-256.
     */
    public static function matchesCommittedDigest(array $model, string $sealedDigest): bool
    {
        if (!preg_match('/^[a-f0-9]{64}$/D', $sealedDigest)) {
            return false;
        }
        if (hash_equals($sealedDigest, self::digest($model))) {
            return true;
        }
        $hostlist = $model['hostlist'] ?? null;
        if (!is_array($hostlist) ||
            !array_key_exists('excludeipset', $hostlist) ||
            $hostlist['excludeipset'] !== ''
        ) {
            return false;
        }
        $oldShape = $model;
        unset($oldShape['hostlist']['excludeipset']);
        return hash_equals($sealedDigest, self::digest($oldShape));
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
