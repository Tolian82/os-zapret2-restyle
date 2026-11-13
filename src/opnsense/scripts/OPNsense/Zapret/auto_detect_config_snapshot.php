<?php

/**
 * #1052 P2k8a — native, deliberately read-only Config + shared HOSTLIST
 * snapshot. No standalone parser for config.xml and no Config writer.
 *
 * The one original Config lock remains held while the existing P2k5 native
 * reader obtains its own checked HOSTLIST lock. A later file transaction MAY
 * NOT use this returned snapshot as authorization: the file lock has been
 * released and a durable owned-source ledger does not yet exist.
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
    private const MAX_NATIVE_REPLY = 50000;
    private const NATIVE_PYTHON = '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh';
    private const FINAL_READER = '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_gui_hostlist.py';

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
     * P2k5 final-file reader. Both operations are inside Config::lock.
     * Failure releases Config; there is never an auto-owned empty-dict guess.
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
            return [
                'schema_version' => 1,
                'status' => 'read_only_unqualified',
                'manual_hostlists' => $manual['lists'],
                'shared_auto' => $content,
                'shared_auto_status' => $status,
                'shared_auto_revision' => $final['revision'],
                'global_exclude' => $manual['global_exclude'],
                'config_snapshot_sha256' => VoiceSettingsSnapshot::digest($nodes),
                // Never confuse "not yet implemented" with "known empty".
                'auto_owned_components' => null,
                'auto_owned_complete' => false,
                'commit_authorized' => false,
            ];
        } finally {
            $config->unlock();
        }
    }

    /** Direct root-native invocation. No call through shared Apply/configd. */
    public static function nativeFinalRead(): array
    {
        $pipes = [];
        $process = @proc_open(
            [self::NATIVE_PYTHON, self::FINAL_READER, 'read'],
            [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
            $pipes, null, ['LC_ALL' => 'C']
        );
        if (!is_resource($process)) {
            throw new \RuntimeException('Native root final Hostlist reader unavailable');
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
                throw new \RuntimeException('Native root Hostlist read failed');
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

    public static function main(array $argv): int
    {
        if (count($argv) !== 2 || $argv[1] !== 'read' ||
            PHP_OS_FAMILY !== 'BSD' || !function_exists('posix_geteuid') ||
            posix_geteuid() !== 0) {
            fwrite(STDERR, "ERROR: native root read-only Config snapshot required\n");
            return 64;
        }
        try {
            require_once('script/load_phalcon.php');
            $config = \OPNsense\Core\Config::getInstance();
            $result = self::capture(
                $config, static fn() => new \OPNsense\Zapret\Zapret(),
                static fn() => self::nativeFinalRead()
            );
            echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
            return 0;
        } catch (\Throwable $error) {
            // No user domains, raw Config or Python stderr in failure output.
            fwrite(STDERR, "ERROR: read-only native Config/Hostlist snapshot unavailable\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(AutoDetectConfigSnapshot::main($argv));
}