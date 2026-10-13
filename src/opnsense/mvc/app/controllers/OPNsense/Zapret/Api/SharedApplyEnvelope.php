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
