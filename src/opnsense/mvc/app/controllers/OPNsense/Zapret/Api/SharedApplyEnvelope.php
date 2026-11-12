<?php
/**
 * One bounded, canonical transport envelope for the native common Apply.
 *
 * This is NOT a second Config writer. Form validation and the authoritative
 * model snapshot are repeated by the original-FD9 root backend.
 */
namespace OPNsense\Zapret\Api;

final class SharedApplyEnvelope
{
    private const LIMIT = 65536;

    /**
     * A changed large form value must not require a huge configd argv.
     * Encode the minimal single-splice edit against the saved Model value.
     * Nothing is stored by the GUI. Root expands this under FD9 against a
     * fresh, SHA-256 checked Config snapshot before normal validation.
     */
    private const MAX_LIST_BYTES = 4 * 1024 * 1024;
    private const LISTS = [
        'youtubedomains', 'userdomains', 'excludedomains', 'telegramips',
        'discordips', 'xips', 'sipips', 'customips', 'excludeipset',
    ];

    public static function compactStrategies(array $fields, array $saved): array
    {
        foreach (($fields['hostlist'] ?? []) as $name => $updated) {
            if (!in_array($name, self::LISTS, true) || !is_string($updated) ||
                strlen($updated) < 4096) {
                continue;
            }
            $old = $saved['hostlist'][$name] ?? null;
            if (!is_string($old)) {
                continue;
            }
            $before = strlen($old);
            $after = strlen($updated);
            if ($before > self::MAX_LIST_BYTES || $after > self::MAX_LIST_BYTES) {
                throw new \InvalidArgumentException('Changed domain list exceeds safe size');
            }
            $prefix = 0;
            $common = min($before, $after);
            while ($prefix < $common && $old[$prefix] === $updated[$prefix]) {
                ++$prefix;
            }
            $suffix = 0;
            $remaining = $common - $prefix;
            while ($suffix < $remaining &&
                $old[$before - $suffix - 1] === $updated[$after - $suffix - 1]) {
                ++$suffix;
            }
            $delta = ['__zapret_list_delta' => [
                'base' => hash('sha256', $old),
                'prefix' => $prefix,
                'delete' => $before - $prefix - $suffix,
                'insert' => substr($updated, $prefix, $after - $prefix - $suffix),
            ]];
            // Small/unchanged fields use the established ordinary envelope.
            if (strlen(json_encode($delta, JSON_THROW_ON_ERROR)) < $after) {
                $fields['hostlist'][$name] = $delta;
            }
        }
        return $fields;
    }

    public static function expandStrategies(array $fields, array $saved): array
    {
        foreach (($fields['hostlist'] ?? []) as $name => $value) {
            if (is_string($value)) {
                continue;
            }
            if (!in_array($name, self::LISTS, true) || !is_array($value) ||
                array_keys($value) !== ['__zapret_list_delta'] ||
                !is_array($delta = $value['__zapret_list_delta']) ||
                array_keys($delta) !== ['base', 'prefix', 'delete', 'insert'] ||
                !is_string($delta['base']) ||
                !preg_match('/^[a-f0-9]{64}$/D', $delta['base']) ||
                !is_int($delta['prefix']) || $delta['prefix'] < 0 ||
                !is_int($delta['delete']) || $delta['delete'] < 0 ||
                !is_string($delta['insert'])) {
                throw new \InvalidArgumentException('Invalid changed domain delta');
            }
            $old = $saved['hostlist'][$name] ?? null;
            if (!is_string($old) || strlen($old) > self::MAX_LIST_BYTES ||
                !hash_equals(hash('sha256', $old), $delta['base'])) {
                throw new \InvalidArgumentException('Stale domain edit; reload the page');
            }
            $oldLength = strlen($old);
            if ($delta['prefix'] > $oldLength ||
                $delta['delete'] > $oldLength - $delta['prefix']) {
                throw new \InvalidArgumentException('Changed domain delta out of bounds');
            }
            $result = substr($old, 0, $delta['prefix']) . $delta['insert'] .
                substr($old, $delta['prefix'] + $delta['delete']);
            if (strlen($result) > self::MAX_LIST_BYTES) {
                throw new \InvalidArgumentException('Changed domain list exceeds safe size');
            }
            $fields['hostlist'][$name] = $result;
        }
        return $fields;
    }

    public static function encode(string $page, array $fields, array $sync): string
    {
        if (!in_array($page, ['voice', 'strategies'], true)) {
            throw new \InvalidArgumentException('Invalid shared Apply page');
        }
        $required = $page === 'voice' ? 'snapshot' : 'telegramips_baseline';
        if (array_keys($sync) !== [$required] || !is_string($sync[$required])) {
            throw new \InvalidArgumentException('Missing shared Apply form baseline');
        }
        $raw = json_encode(
            ['page' => $page, 'fields' => $fields, 'sync' => $sync],
            JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES
        );
        $encoded = rtrim(strtr(base64_encode($raw), '+/', '-_'), '=');
        if ($encoded === '' || strlen($encoded) > self::LIMIT) {
            throw new \InvalidArgumentException(
                'Shared Apply request is too large; shorten the destination lists'
            );
        }
        return $encoded;
    }
}
