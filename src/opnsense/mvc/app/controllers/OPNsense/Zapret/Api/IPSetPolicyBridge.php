<?php

/**
 * Read-only PHP entrypoint to the ONE native Python IPSET semantic parser.
 *
 * The unprivileged form preflight does not save Config, write target files,
 * change IPFW or create a second PHP address grammar. The privileged FD9
 * candidate will independently enforce the exact same Python policy.
 */
namespace OPNsense\Zapret\Api;

final class IPSetPolicyBridge
{
    private const NAMES = ['telegram', 'discord', 'x', 'sip', 'custom', 'exclude'];
    private const MAX_LIST_BYTES = 262144;
    private const MAX_RESULT_BYTES = 4 * 1048576;

    /** Explicit binary/module overrides are for isolated unit tests only. */
    public static function inspect(array $lists, ?string $python = null, ?string $module = null): array
    {
        if (array_keys($lists) !== self::NAMES) {
            // Stable, ordered input eliminates ambiguity and implicit sources.
            throw new \InvalidArgumentException('IPSET inspection requires six ordered lists');
        }
        foreach ($lists as $name => $text) {
            if (!is_string($text) || strlen($text) > self::MAX_LIST_BYTES) {
                throw new \InvalidArgumentException('IPSET input must be a bounded text list: ' . $name);
            }
        }
        $encoded = json_encode($lists, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        $runtimeLauncher = '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh';
        // Test overrides retain the direct interpreter route; installed
        // preflight uses the same checked runtime as configd and FD9.
        $binary = $python ?? '/bin/sh';
        $installed = '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/ipset_policy.py';
        $source = dirname(__DIR__, 6) . '/scripts/OPNsense/Zapret/backend/ipset_policy.py';
        $script = $module ?? (is_file($installed) ? $installed : $source);
        // Isolated source-tree PHP tests use the *same* packaged resolver.
        // An installed appliance with a missing installed launcher still fails.
        if ($python === null && !is_file($installed)) {
            $runtimeLauncher = dirname(__DIR__, 6) . '/scripts/OPNsense/Zapret/python_runtime.sh';
        }
        if (!is_file($script) || !is_file($binary) || !is_executable($binary) ||
            ($python === null && !is_readable($runtimeLauncher))) {
            throw new \RuntimeException('Native Python IPSET preflight unavailable');
        }
        // PHP's explicit child environment does not inherit the source-tree
        // test override. Pass it only for an uninstalled source checkout,
        // never for the installed production path.
        $childEnvironment = ['LC_ALL' => 'C'];
        if ($python === null && !is_file($installed)) {
            $sourceOverride = getenv('ZAPRET_PYTHON_BIN');
            if (is_string($sourceOverride) && $sourceOverride !== '') {
                $childEnvironment['ZAPRET_PYTHON_BIN'] = $sourceOverride;
            }
        }
        $pipes = [];
        $process = @proc_open(
            $python === null
                ? [$binary, $runtimeLauncher, '--exec', $script, 'inspect']
                : [$binary, $script, 'inspect'],
            [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
            $pipes,
            null,
            $childEnvironment
        );
        if (!is_resource($process)) {
            throw new \RuntimeException('Native Python IPSET preflight unavailable');
        }
        try {
            $length = strlen($encoded);
            $written = 0;
            while ($written < $length) {
                $bytes = fwrite($pipes[0], substr($encoded, $written, 16384));
                if ($bytes === false || $bytes === 0) {
                    throw new \RuntimeException('Unable to submit bounded IPSET preflight');
                }
                $written += $bytes;
            }
            fclose($pipes[0]);
            $response = stream_get_contents($pipes[1], self::MAX_RESULT_BYTES + 1);
            fclose($pipes[1]);
            $error = stream_get_contents($pipes[2], 1024);
            fclose($pipes[2]);
            $status = proc_close($process);
            $process = null;
            if ($status !== 0) {
                // Never return raw list data from an error to an HTML view.
                if (preg_match('/^ERROR: ([A-Za-z ()]+)(?:, line (\d+))?:/D', trim($error), $match)) {
                    $line = isset($match[2]) ? ' at line ' . $match[2] : '';
                    throw new \InvalidArgumentException('Invalid IPSET ' . $match[1] . $line);
                }
                throw new \InvalidArgumentException('Native IPSET preflight refused invalid addresses or networks');
            }
            if (!is_string($response) || strlen($response) > self::MAX_RESULT_BYTES) {
                throw new \RuntimeException('Native IPSET preflight output exceeded bounds');
            }
            $decoded = json_decode($response, true, 512, JSON_THROW_ON_ERROR);
            if (!is_array($decoded) || ($decoded['schema_version'] ?? null) !== 1 ||
                !isset($decoded['lists'], $decoded['overlaps']) ||
                !is_array($decoded['lists']) || !is_array($decoded['overlaps']) ||
                array_keys($decoded['lists']) !== self::NAMES
            ) {
                throw new \RuntimeException('Native IPSET preflight returned invalid evidence');
            }
            foreach (self::NAMES as $name) {
                if (!isset($decoded['lists'][$name]['normalized']) ||
                    !is_string($decoded['lists'][$name]['normalized']) ||
                    !isset($decoded['lists'][$name]['entry_count']) ||
                    !is_int($decoded['lists'][$name]['entry_count'])) {
                    throw new \RuntimeException('Native IPSET preflight returned incomplete list evidence');
                }
            }
            return $decoded;
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

    public static function allFromHostlist(array $hostlist): array
    {
        $result = [];
        foreach (self::NAMES as $name) {
            $field = $name === 'exclude' ? 'excludeipset' : $name . 'ips';
            $value = $hostlist[$field] ?? '';
            if (!is_string($value)) {
                throw new \InvalidArgumentException('IPSET input must be text: ' . $field);
            }
            $result[$name] = $value;
        }
        return $result;
    }
}
