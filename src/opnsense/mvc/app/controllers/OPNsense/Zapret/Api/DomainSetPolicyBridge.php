<?php

/**
 * Read-only PHP bridge to the ONE Python domain_policy.py normalizer.
 * Mirrors the established IPSetPolicyBridge pattern without a second grammar.
 * No Config, IPFW, FD9, engine or target-file writes.
 */
namespace OPNsense\Zapret\Api;

final class DomainSetPolicyBridge
{
    private const FIELDS = [
        'youtubedomains' => 'youtube',
        'userdomains' => 'user',
        'excludedomains' => 'exclude',
    ];
    private const MAX_INPUT_BYTES = 4 * 1048576;
    private const MAX_RESULT_BYTES = 8 * 1048576;
    private const ERROR_CODES = [
        'missing_domain' => 'Missing domain',
        'repeated_modifier' => 'Repeated ! or ^ modifier',
        'modifiers_not_allowed' => 'Modifiers are not permitted in Exclude Domains',
        'modifier_with_wildcard' => 'Modifiers cannot be combined with wildcard domains',
        'ip_in_domain_list' => 'IP addresses and networks are not allowed in domain lists',
        'invalid_domain' => 'Invalid domain',
        'conflicting_modifiers' => 'Conflicting rules for the same domain',
    ];

    /** @return array{normalized:string,changed:int,duplicates:int,entry_count:int} */
    public static function inspect(string $input, string $field, ?string $python = null, ?string $module = null): array
    {
        if (!isset(self::FIELDS[$field]) || strlen($input) > self::MAX_INPUT_BYTES) {
            throw new \InvalidArgumentException('Invalid bounded domain field');
        }
        $binary = $python ?? (PHP_OS_FAMILY === 'BSD'
            ? '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh' : '/usr/bin/python3');
        $installed = '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/domain_policy.py';
        $source = dirname(__DIR__, 6) . '/scripts/OPNsense/Zapret/backend/domain_policy.py';
        $script = $module ?? (is_file($installed) ? $installed : $source);
        if (!is_file($binary) || !is_executable($binary) || !is_file($script)) {
            throw new \RuntimeException('Native Python domain preflight unavailable');
        }
        $encoded = json_encode([
            'kind' => self::FIELDS[$field],
            'text' => $input,
        ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        $pipes = [];
        $process = @proc_open(
            [$binary, $script, 'inspect'],
            [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
            $pipes,
            null,
            ['LC_ALL' => 'C']
        );
        if (!is_resource($process)) {
            throw new \RuntimeException('Native Python domain preflight unavailable');
        }
        try {
            $sent = 0;
            $length = strlen($encoded);
            while ($sent < $length) {
                $written = fwrite($pipes[0], substr($encoded, $sent, 16384));
                if ($written === false || $written === 0) {
                    throw new \RuntimeException('Unable to submit bounded domain preflight');
                }
                $sent += $written;
            }
            fclose($pipes[0]);
            $response = stream_get_contents($pipes[1], self::MAX_RESULT_BYTES + 1);
            fclose($pipes[1]);
            // Never surface raw Python diagnostics or user-provided values.
            stream_get_contents($pipes[2], 1024);
            fclose($pipes[2]);
            $status = proc_close($process);
            $process = null;
            if (!is_string($response) || strlen($response) > self::MAX_RESULT_BYTES) {
                throw new \RuntimeException('Native Python domain preflight exceeded result bounds');
            }
            $decoded = json_decode($response, true, 512, JSON_THROW_ON_ERROR);
            if (!is_array($decoded) || ($decoded['schema_version'] ?? null) !== 1) {
                throw new \RuntimeException('Native Python domain preflight returned invalid evidence');
            }
            if ($status !== 0) {
                $error = $decoded['error'] ?? null;
                if (!is_array($error) || ($error['field'] ?? null) !== $field ||
                    !is_int($error['line'] ?? null) || ($error['line'] ?? 0) < 1 ||
                    !is_string($error['code'] ?? null) ||
                    !isset(self::ERROR_CODES[$error['code']])) {
                    throw new \RuntimeException('Native Python domain preflight refused input');
                }
                throw new \InvalidArgumentException(
                    self::ERROR_CODES[$error['code']] . ' (line ' . $error['line'] . ')'
                );
            }
            if (($decoded['field'] ?? null) !== $field ||
                !is_string($decoded['normalized'] ?? null) ||
                !is_int($decoded['changed'] ?? null) ||
                !is_int($decoded['duplicates'] ?? null) ||
                !is_int($decoded['entry_count'] ?? null) ||
                min($decoded['changed'], $decoded['duplicates'], $decoded['entry_count']) < 0) {
                throw new \RuntimeException('Native Python domain preflight returned incomplete result');
            }
            return [
                'normalized' => $decoded['normalized'],
                'changed' => $decoded['changed'],
                'duplicates' => $decoded['duplicates'],
                'entry_count' => $decoded['entry_count'],
            ];
        } finally {
            foreach ($pipes as $pipe) {
                if (is_resource($pipe)) {
                    fclose($pipe);
                }
            }
            if (is_resource($process)) {
                proc_terminate($process);
                proc_close($process);
            }
        }
    }
}
