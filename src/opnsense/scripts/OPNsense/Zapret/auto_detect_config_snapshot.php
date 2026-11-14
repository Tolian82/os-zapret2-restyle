<?php

/**
 * #1052 P2k8a — native, deliberately read-only Config + shared HOSTLIST
 * snapshot. No standalone parser for config.xml and no Config writer.
 *
 * The one original Config lock remains held while the existing P2k5 native
 * reader obtains its own checked HOSTLIST lock for both the final file and
 * root-owned known-list components. A later file transaction MAY
 * NOT use this returned snapshot as authorization: the file lock has been
 * released and no trusted owner is installed to authorize an auto-owned update.
 *
 * There is no configd action for this CLI, no timer, no FD9 ownership claim,
 * no pending acknowledgement and no runtime or IPFW change.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/VoiceSettingsSnapshot.php';

use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

final class AutoDetectConfigSnapshot
{
    private const MAX_MODEL_TEXT = 1048576;
    private const MAX_NATIVE_REPLY = 150000;
    private const NATIVE_PYTHON = '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh';
    private const FINAL_READER = '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_owned_sources.py';
    private const FD_COMMIT = '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_original_lock_handoff.py';

    /**
     * Extract exactly the MANUAL HOSTLIST owners currently registered by the
     * original native registry.sh: youtube and user. IPSETs are not HOSTLISTs.
     * The historical hostlist.domains field is not a registered destination.
     * Any new registered HOSTLIST requires an explicit update plus drift test.
     */
    public static function manualFromModel(array $model): array
    {
        $fields = $model['hostlist'] ?? null;
        if (!is_array($fields)) {
            throw new \RuntimeException('Native Hostlist model unavailable');
        }
        $textFields = ['youtubedomains' => 'youtube', 'userdomains' => 'user'];
        $lists = [];
        $total = 0;
        foreach ($textFields as $field => $name) {
            if (!array_key_exists($field, $fields) || !is_string($fields[$field]) ||
                strlen($fields[$field]) > self::MAX_MODEL_TEXT) {
                throw new \RuntimeException('Required native manual Hostlist missing or oversized');
            }
            $lists[$name] = $fields[$field];
            $total += strlen($fields[$field]);
        }
        if (!array_key_exists('excludedomains', $fields) ||
            !is_string($fields['excludedomains']) ||
            strlen($fields['excludedomains']) > self::MAX_MODEL_TEXT ||
            $total + strlen($fields['excludedomains']) > self::MAX_MODEL_TEXT * 3) {
            throw new \RuntimeException('Native global domain exclusion unavailable');
        }
        return ['lists' => $lists, 'global_exclude' => $fields['excludedomains']];
    }

    /**
     * The caller supplies a *real fresh native Model factory* and a read-only
     * P2k8b single-locked final/known-owned file reader. Both are under
     * Config::lock. Missing unbootstrapped ownership never becomes {}.
     */
    public static function capture(object $config, callable $modelFactory,
                                   callable $finalReader): array
    {
        $config->lock();
        try {
            $model = $modelFactory();
            if (!is_object($model) || !method_exists($model, 'getNodes')) {
                throw new \RuntimeException('Native Config model factory unavailable');
            }
            $nodes = $model->getNodes();
            if (!is_array($nodes)) {
                throw new \RuntimeException('Native Config model invalid');
            }
            $manual = self::manualFromModel($nodes);
            $final = $finalReader();
            if (!is_array($final) || ($final['result'] ?? null) !== 'ok' ||
                !in_array($final['status'] ?? null, ['missing', 'empty', 'populated'], true) ||
                !is_string($final['revision'] ?? null) ||
                preg_match('/^[0-9a-f]{64}$/D', $final['revision']) !== 1 ||
                !is_string($final['content'] ?? null) ||
                strlen($final['content']) > 40960) {
                throw new \RuntimeException('Untrusted native final Auto Hostlist snapshot');
            }
            $content = $final['content'];
            $status = $final['status'];
            $expectedRevision = hash('sha256', $status === 'missing'
                ? "missing\0" : "present\0" . $content);
            if (!hash_equals($expectedRevision, $final['revision']) ||
                ($status === 'missing' && $content !== '') ||
                ($status === 'empty' && $content !== '') ||
                ($status === 'populated' && $content === '')) {
                throw new \RuntimeException('Native final Hostlist revision mismatch');
            }
            $complete = $final['auto_owned_complete'] ?? false;
            $owned = $final['auto_owned_components'] ?? null;
            if (!is_bool($complete) ||
                ($complete && (!is_array($owned) || array_keys($owned) !== ['youtube', 'user'])) ||
                (!$complete && $owned !== null)) {
                throw new \RuntimeException('Untrusted automatic owned-source snapshot');
            }
            if ($complete) {
                foreach ($owned as $value) {
                    if (!is_string($value) || strlen($value) > 40960 ||
                        preg_match('/(?:^|\n)[!^]/', $value) === 1 ||
                        str_contains($value, "\r")) {
                        throw new \RuntimeException('Unsafe owned-source component');
                    }
                }
            }
            return [
                'schema_version' => 1,
                'status' => 'read_only_unqualified',
                'manual_hostlists' => $manual['lists'],
                'shared_auto' => $content,
                'shared_auto_status' => $status,
                'shared_auto_revision' => $final['revision'],
                'global_exclude' => $manual['global_exclude'],
                'config_snapshot_sha256' => VoiceSettingsSnapshot::digest($nodes),
                // Strictly distinguish a proven sealed empty baseline from
                // uninitialized/missing ownership; neither authorizes writes.
                'auto_owned_components' => $owned,
                'auto_owned_complete' => $complete,
                'commit_authorized' => false,
            ];
        } finally {
            $config->unlock();
        }
    }

    /**
     * P2k8e: the original OPNsense Config owner remains locked across the
     * complete synchronous P1 -> P2k2b operation. The native queue lock must
     * already belong to the caller (queue -> Config -> HOSTLIST order).
     *
     * There is deliberately NO public 'commit' CLI: the only current native
     * command remains 'read'. A future qualified worker must call this from
     * its original queue/FD9 owner, not from a detached stale read snapshot.
     * The operation receives original Model values, NOT a second XML parser
     * or permission to call Config::save().
     */
    public static function withLockedOriginalModel(
        object $config, callable $modelFactory, callable $operation
    ): array {
        $config->lock();
        try {
            $model = $modelFactory();
            if (!is_object($model) || !method_exists($model, 'getNodes')) {
                throw new \RuntimeException('Original Config model unavailable');
            }
            $nodes = $model->getNodes();
            if (!is_array($nodes)) {
                throw new \RuntimeException('Original Config model invalid');
            }
            $manual = self::manualFromModel($nodes);
            $digest = VoiceSettingsSnapshot::digest($nodes);
            // The synchronous child must acquire the shared destination lock
            // *after* native Config; no preliminary final-file lock here.
            $result = $operation([
                'manual_hostlists' => $manual['lists'],
                'global_exclude' => $manual['global_exclude'],
                'config_snapshot_sha256' => $digest,
            ]);
            if (!is_array($result) ||
                ($result['kind'] ?? null) !== 'destination-and-cursor-committed' ||
                ($result['ack_authorized'] ?? null) !== false) {
                throw new \RuntimeException('Unqualified destination checkpoint');
            }
            // No Config::save() in this method. A child that changes the
            // original Model generation cannot claim a valid final decision.
            $after = $modelFactory();
            if (!is_object($after) || !method_exists($after, 'getNodes')) {
                throw new \RuntimeException('Original Config model changed');
            }
            $afterNodes = $after->getNodes();
            if (!is_array($afterNodes) ||
                !hash_equals($digest, VoiceSettingsSnapshot::digest($afterNodes))) {
                throw new \RuntimeException('Original Config changed during transaction');
            }
            return $result;  // always unacknowledged; no source deletion here
        } finally {
            $config->unlock();
        }
    }

    /**
     * #1052 P2k8f: real queue-lock descriptor -> native PHP Config lock
     * -> Python same-open-description destination transaction.
     *
     * No second queue lock, Config parser, daemon or Config writer. The
     * original worker already holds queue/worker.lock before invoking PHP.
     * Only the fixed native CLI uses this; injected file/argv parameters are
     * for portable source tests, NOT a registered configd action.
     */
    public static function commitWithInheritedOriginalLocks(
        object $config, callable $modelFactory, int $queueFd,
        string $queuePath, string $configPath, array $pythonCommand
    ): array {
        if ($queueFd < 3 || $queueFd > 1024 || $queuePath === '' ||
            $configPath === '' || !str_starts_with($queuePath, '/') ||
            !str_starts_with($configPath, '/') ||
            !$pythonCommand || !array_is_list($pythonCommand) ||
            array_filter($pythonCommand, static fn($arg) => !is_string($arg) || $arg === '')) {
            throw new \RuntimeException('Unqualified original queue/Config bridge');
        }
        return self::withLockedOriginalModel(
            $config, $modelFactory,
            static function (array $source) use ($config, $queueFd, $queuePath, $configPath, $pythonCommand): array {
                // Both descriptors come from their ORIGINAL owners. The
                // child receives duped open-file descriptions, not newly
                // opened paths or guessed flock ownership.
                $original = new \ReflectionObject($config);
                if (!$original->hasProperty('config_file_handle') ||
                    !$original->hasProperty('config_file')) {
                    throw new \RuntimeException('Original Config handle unavailable');
                }
                $handle = $original->getProperty('config_file_handle')->getValue($config);
                $path = $original->getProperty('config_file')->getValue($config);
                if (!is_resource($handle) || $path !== $configPath ||
                    !is_array($cfgSt = @fstat($handle)) ||
                    !is_array($namedSt = @lstat($configPath)) ||
                    $cfgSt['dev'] !== $namedSt['dev'] ||
                    $cfgSt['ino'] !== $namedSt['ino']) {
                    throw new \RuntimeException('Original Config descriptor replaced');
                }
                $queueStream = @fopen('php://fd/' . $queueFd, 'r+');
                if (!is_resource($queueStream)) {
                    throw new \RuntimeException('Inherited original queue descriptor unavailable');
                }
                try {
                    $queueSt = @fstat($queueStream);
                    $namedQueue = @lstat($queuePath);
                    if (!is_array($queueSt) || !is_array($namedQueue) ||
                        $queueSt['dev'] !== $namedQueue['dev'] ||
                        $queueSt['ino'] !== $namedQueue['ino']) {
                        throw new \RuntimeException('Foreign original queue descriptor');
                    }
                    $pipes = [];
                    $process = @proc_open(
                        $pythonCommand,
                        [0 => ['pipe', 'r'], 1 => ['pipe', 'w'],
                         2 => ['file', '/dev/null', 'a'],
                         3 => $queueStream, 4 => $handle],
                        $pipes, null, ['LC_ALL' => 'C']
                    );
                    if (!is_resource($process)) {
                        throw new \RuntimeException('Original locked Python child unavailable');
                    }
                    try {
                        $input = json_encode($source, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
                        if (strlen($input) > 3 * 1048576) {
                            throw new \RuntimeException('Original Model transport oversized');
                        }
                        $view = $input;
                        while ($view !== '') {
                            $n = fwrite($pipes[0], $view);
                            if ($n === false || $n === 0) {
                                throw new \RuntimeException('Original Model transport interrupted');
                            }
                            $view = substr($view, $n);
                        }
                        fclose($pipes[0]);
                        unset($pipes[0]);

                        // A bounded native child: no abandoned PHP Config
                        // lock or unbounded 60-second worker overlap.
                        stream_set_blocking($pipes[1], false);
                        $reply = '';
                        $deadline = microtime(true) + 120;
                        while (!feof($pipes[1])) {
                            if (microtime(true) >= $deadline || strlen($reply) > 16384) {
                                throw new \RuntimeException('Original locked child timed out');
                            }
                            $read = [$pipes[1]];
                            $write = [];
                            $except = [];
                            $ready = @stream_select($read, $write, $except, 1);
                            if ($ready === false) {
                                throw new \RuntimeException('Original locked child I/O failure');
                            }
                            if ($ready > 0) {
                                $part = fread($pipes[1], 16385 - strlen($reply));
                                if ($part === false) {
                                    throw new \RuntimeException('Original locked child read failure');
                                }
                                $reply .= $part;
                            }
                        }
                        fclose($pipes[1]);
                        unset($pipes[1]);
                        $exit = proc_close($process);
                        $process = null;
                        if ($exit !== 0 || $reply === '' || strlen($reply) > 16384) {
                            throw new \RuntimeException('Original locked child refused');
                        }
                        $value = json_decode($reply, true, 8, JSON_THROW_ON_ERROR);
                        if (!is_array($value)) {
                            throw new \RuntimeException('Unqualified original child result');
                        }
                        return $value;  // validated by withLockedOriginalModel()
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
                } finally {
                    fclose($queueStream);
                }
            }
        );
    }

    /** Original Config remains held during one shared final/owned file lock. */
    public static function nativeFinalRead(): array
    {
        $pipes = [];
        $process = @proc_open(
            [self::NATIVE_PYTHON, self::FINAL_READER, 'read'],
            [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
            $pipes, null, ['LC_ALL' => 'C']
        );
        if (!is_resource($process)) {
            throw new \RuntimeException('Native root Hostlist/ownership reader unavailable');
        }
        try {
            fclose($pipes[0]);
            $text = stream_get_contents($pipes[1], self::MAX_NATIVE_REPLY + 1);
            fclose($pipes[1]);
            // Never surface child diagnostics or domains in an error message.
            stream_get_contents($pipes[2], 1024);
            fclose($pipes[2]);
            $exit = proc_close($process);
            $process = null;
            if ($exit !== 0 || !is_string($text) || strlen($text) > self::MAX_NATIVE_REPLY) {
                throw new \RuntimeException('Native root Hostlist/ownership read failed');
            }
            $result = json_decode($text, true, 8, JSON_THROW_ON_ERROR);
            if (!is_array($result)) {
                throw new \RuntimeException('Native Hostlist response invalid');
            }
            return $result;
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

    /**
     * Original OPNsense PHP CLI can omit the optional POSIX extension.
     * A non-root CLI must never read Config or inherit FD authorization.
     * Query the kernel's effective UID through native /usr/bin/id -u only
     * when posix_geteuid() is not available. No shell, PATH or environment
     * identity tokens; reject errors, extra output and unsafe executable.
     */
    public static function nativeRootAllowed(): bool
    {
        if (PHP_OS_FAMILY !== 'BSD' || PHP_SAPI !== 'cli') {
            return false;
        }
        if (function_exists('posix_geteuid')) {
            return posix_geteuid() === 0;
        }
        $idPath = '/usr/bin/id';
        $info = @lstat($idPath);
        if (!is_array($info) || $info['uid'] !== 0 ||
            ($info['mode'] & 0o022) !== 0 || !is_executable($idPath)) {
            return false;
        }
        $pipes = [];
        $process = @proc_open(
            [$idPath, '-u'],
            [0 => ['file', '/dev/null', 'r'],
             1 => ['pipe', 'w'],
             2 => ['file', '/dev/null', 'w']],
            $pipes, null, ['LC_ALL' => 'C']
        );
        if (!is_resource($process)) {
            return false;
        }
        try {
            $response = stream_get_contents($pipes[1], 8);
            fclose($pipes[1]);
            unset($pipes[1]);
            $exit = proc_close($process);
            $process = null;
            return $exit === 0 && $response === "0\n";
        } catch (\Throwable $error) {
            return false;
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

    public static function main(array $argv): int
    {
        if (!self::nativeRootAllowed() ||
            (count($argv) !== 2 && count($argv) !== 4)) {
            fwrite(STDERR, "ERROR: root native original Config required\n");
            return 64;
        }
        try {
            require_once('script/load_phalcon.php');
            $config = \OPNsense\Core\Config::getInstance();
            if (count($argv) === 2 && $argv[1] === 'read') {
                $result = self::capture(
                    $config, static fn() => new \OPNsense\Zapret\Zapret(),
                    static fn() => self::nativeFinalRead()
                );
            } elseif (count($argv) === 4 && $argv[1] === 'commit-with-fds' &&
                      preg_match('/^[0-9]{1,4}$/D', $argv[2]) === 1 &&
                      preg_match('/^[0-9a-f]{32}-[0-9a-f]{32}\.txt$/D', $argv[3]) === 1) {
                // No direct worker, no independent Config/XML writer. A
                // native parent must already hold the P2a worker.lock.
                $result = self::commitWithInheritedOriginalLocks(
                    $config, static fn() => new \OPNsense\Zapret\Zapret(),
                    (int)$argv[2], '/var/db/zapret2-auto-detect/worker.lock',
                    '/conf/config.xml',
                    [self::NATIVE_PYTHON, self::FD_COMMIT, 'commit-fds', $argv[3]]
                );
            } else {
                return 64;
            }
            echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
            return 0;
        } catch (\Throwable $error) {
            // No domains, FD details, original Config or Python stderr.
            fwrite(STDERR, "ERROR: original native Config/Hostlist operation unavailable\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(AutoDetectConfigSnapshot::main($argv));
}