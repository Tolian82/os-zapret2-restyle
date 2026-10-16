<?php

/**
 * Authoritative read-only GUI -> fixed five-bit native saved-OFF-draft request.
 *
 * This is deliberately narrower than full Voice Apply. Saved Voice/IPSET
 * inputs must remain identical; only the five service enabled switches may
 * be selected in the request. The native FD9 route will re-read the original
 * Config inode and verify its SHA-256 before accepting anything.
 */
namespace OPNsense\Zapret\Api;

require_once __DIR__ . '/VoiceApplyCandidate.php';

final class VoiceDraftSelection
{
    private const SERVICES = ['telegram', 'discord', 'x', 'sip', 'custom'];
    public const MAX_CONFIG_BYTES = 4194304;

    public static function plan(array $saved, array $form, $snapshot): array
    {
        $result = VoiceApplyCandidate::prepare($saved, $form, $snapshot);
        if (($result['result'] ?? null) !== 'prepared') {
            return $result;
        }
        if (($saved['general']['enabled'] ?? null) !== '1') {
            throw new \InvalidArgumentException('Enable Zapret2 before preparing saved Voice drafts');
        }
        $mask = '';
        foreach (self::SERVICES as $service) {
            if (($saved['voice'][$service]['enabled'] ?? null) !== '0') {
                throw new \InvalidArgumentException(
                    'Existing native Voice ON cannot be prepared from inactive drafts'
                );
            }
            $requested = $result['candidate']['voice'][$service]['enabled'] ?? null;
            if (!in_array($requested, ['0', '1'], true)) {
                throw new \InvalidArgumentException('Invalid saved Voice selection');
            }
            $mask .= $requested;
        }
        if ($mask === '00000') {
            throw new \InvalidArgumentException('Select at least one Voice service to preview');
        }
        $expected = [];
        foreach (self::SERVICES as $index => $service) {
            if ($mask[$index] === '1') {
                $expected[] = 'voice.' . $service . '.enabled';
            }
        }
        $changed = $result['changed_fields'];
        sort($changed, SORT_STRING);
        sort($expected, SORT_STRING);
        if ($changed !== $expected) {
            throw new \InvalidArgumentException(
                'Save inactive Voice parameters and IPSET changes before native preview'
            );
        }
        return [
            'result' => 'eligible',
            'mask' => $mask,
            'selected_count' => count($expected),
        ];
    }

    /**
     * Only the exact original saved Config bytes are accepted by the native
     * original-FD9 route. Never put contents or arbitrary paths on configd
     * arguments or return them to the GUI.
     */
    public static function digestOriginalConfig(string $path = '/conf/config.xml'): string
    {
        if ($path === '' || !is_file($path) || is_link($path)) {
            throw new \RuntimeException('Saved OPNsense Config unavailable');
        }
        $size = filesize($path);
        if (!is_int($size) || $size < 1 || $size > self::MAX_CONFIG_BYTES) {
            throw new \RuntimeException('Saved OPNsense Config size outside native bounds');
        }
        $content = file_get_contents($path);
        if (!is_string($content) || strlen($content) !== $size) {
            throw new \RuntimeException('Cannot read complete saved OPNsense Config');
        }
        return hash('sha256', $content);
    }
}
