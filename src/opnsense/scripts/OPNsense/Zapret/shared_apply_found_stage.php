<?php
/**
 * TZ6v2: READ-ONLY five-list preparation under the already-held Config+FD9.
 *
 * This helper is invoked only by the original SharedApplyRequest staging PHP
 * while its stock OPNsense Config::lock is held. It gives the Python P1/P2
 * bridge the exact original Config open file description (fd4) and FD9.
 * No Config::save(), file write, independent Apply or service action exists.
 */
namespace OPNsense\Zapret\Native;

use OPNsense\Zapret\Api\VoiceModelValues;

final class SharedApplyFoundStage
{
    private const PYTHON = '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh';
    private const SCRIPT = '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/shared_apply_found_stage.py';
    private const CONFIG = '/conf/config.xml';
    private const MAX_INPUT = 4 * 1024 * 1024;
    private const MAX_OUTPUT = 512 * 1024;

    public static function prepare(object $config, array $plan): array
    {
        SharedApplyLifecycleLock::assertHeld();
        if (($plan['page'] ?? null) !== 'strategies' ||
            !is_array($plan['candidate']['hostlist'] ?? null) ||
            !is_array($plan['found_intent'] ?? null) ||
            !is_string($plan['dependencies'] ?? null) ||
            !preg_match('/^[a-f0-9]{64}$/D', $plan['dependencies']) ||
            !hash_equals($plan['dependencies'],
                (string)($plan['found_intent']['config_revision'] ?? ''))) {
            throw new \InvalidArgumentException('Unqualified found Config candidate');
        }
        $host = $plan['candidate']['hostlist'];
        $payload = [
            'schema_version' => 1,
            'kind' => 'tz6v2-found-root-stage',
            'config_revision' => $plan['dependencies'],
            'found_intent' => $plan['found_intent'],
            'manual' => [
                'youtube' => VoiceModelValues::text($host['youtubedomains'] ?? ''),
                'user' => VoiceModelValues::text($host['userdomains'] ?? ''),
            ],
            'global_exclude' => VoiceModelValues::text($host['excludedomains'] ?? ''),
        ];
        $body = json_encode($payload, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        if (strlen($body) > self::MAX_INPUT) {
            throw new \InvalidArgumentException('Oversized original found candidate');
        }
        // Native Config::lock owns this original handle. No additional
        // Config object/lock, synthetic fd or pathname-derived authority.
        $reflect = new \ReflectionObject($config);
        if (!$reflect->hasProperty('config_file_handle') ||
            !$reflect->hasProperty('config_file')) {
            throw new \RuntimeException('Original native Config descriptor unavailable');
        }
        $handle = $reflect->getProperty('config_file_handle')->getValue($config);
        $path = $reflect->getProperty('config_file')->getValue($config);
        $named = @lstat(self::CONFIG);
        $opened = is_resource($handle) ? @fstat($handle) : false;
        if ($path !== self::CONFIG ||
            !is_array($named) || !is_array($opened) ||
            $opened['dev'] !== $named['dev'] ||
            $opened['ino'] !== $named['ino']) {
            throw new \RuntimeException('Foreign original Config handle');
        }
        $lifecycle = @fopen('php://fd/9', 'r+b');
        if (!is_resource($lifecycle)) {
            throw new \RuntimeException('Original FD9 descriptor unavailable');
        }
        try {
            $pipes = [];
            $proc = @proc_open(
                [self::PYTHON, self::SCRIPT, 'prepare-locked'],
                [0 => ['pipe', 'r'], 1 => ['pipe', 'w'],
                 2 => ['file', '/dev/null', 'a'],
                 4 => $handle, 9 => $lifecycle],
                $pipes, null,
                ['LC_ALL' => 'C', 'PATH' => '/usr/bin:/bin:/usr/local/bin']
            );
            if (!is_resource($proc)) {
                throw new \RuntimeException('Original found read-only child unavailable');
            }
            try {
                $remaining = $body;
                while ($remaining !== '') {
                    $n = @fwrite($pipes[0], $remaining);
                    if (!is_int($n) || $n < 1) {
                        throw new \RuntimeException('Original found candidate transport interrupted');
                    }
                    $remaining = substr($remaining, $n);
                }
                fclose($pipes[0]);
                unset($pipes[0]);
                stream_set_blocking($pipes[1], false);
                $reply = '';
                $deadline = microtime(true) + 90;
                while (!feof($pipes[1])) {
                    if (microtime(true) >= $deadline ||
                        strlen($reply) > self::MAX_OUTPUT) {
                        throw new \RuntimeException('Original found candidate child timeout');
                    }
                    $read = [$pipes[1]];
                    $write = [];
                    $except = [];
                    $ready = @stream_select($read, $write, $except, 1);
                    if ($ready === false) {
                        throw new \RuntimeException('Original found candidate child I/O failed');
                    }
                    if ($ready > 0) {
                        $part = fread($pipes[1], self::MAX_OUTPUT + 1 - strlen($reply));
                        if ($part === false) {
                            throw new \RuntimeException('Original found candidate child read failed');
                        }
                        $reply .= $part;
                    }
                }
                fclose($pipes[1]);
                unset($pipes[1]);
                $status = proc_close($proc);
                $proc = null;
                if ($status === 69 && $reply !== '' && strlen($reply) < 128) {
                    $issue = json_decode($reply, true);
                    if (is_array($issue) && in_array($issue['field'] ?? null,
                            ['youtube', 'user', 'auto'], true) &&
                        is_int($issue['line'] ?? null) &&
                        $issue['line'] >= 1 && $issue['line'] <= 999999) {
                        throw new \InvalidArgumentException(
                            'found-' . $issue['field'] . '-line-' . $issue['line']
                        );
                    }
                }
                if ($status !== 0 || $reply === '' ||
                    strlen($reply) > self::MAX_OUTPUT) {
                    throw new \RuntimeException('Original found candidate refused');
                }
                // Native Python st_dev/st_ino are unsigned 64-bit on FreeBSD.
                // Without JSON_BIGINT_AS_STRING PHP silently turns values
                // above PHP_INT_MAX into floats, invalidating exact P2 pins.
                // Keep their decimal digits lossless for native validation.
                $result = json_decode(
                    $reply, true, 12, JSON_THROW_ON_ERROR | JSON_BIGINT_AS_STRING
                );
                if (!is_array($result) ||
                    array_keys($result) !== [
                        'schema_version', 'kind', 'found_batch',
                        'cross_source_validated', 'commit_authorized',
                        'config_committed'
                    ] ||
                    $result['schema_version'] !== 1 ||
                    $result['kind'] !== 'tz6v2-found-readonly-candidate' ||
                    $result['cross_source_validated'] !== true ||
                    $result['commit_authorized'] !== false ||
                    $result['config_committed'] !== false ||
                    !is_array($result['found_batch']) ||
                    array_keys($result['found_batch']) !==
                        ['youtube', 'user', 'auto']) {
                    throw new \RuntimeException('Unqualified original found preview');
                }
                SharedApplyLifecycleLock::assertHeld();
                return $result['found_batch'];
            } finally {
                foreach ($pipes as $pipe) {
                    if (is_resource($pipe)) {
                        fclose($pipe);
                    }
                }
                if (is_resource($proc)) {
                    @proc_terminate($proc);
                    @proc_close($proc);
                }
            }
        } finally {
            fclose($lifecycle);
        }
    }
}
