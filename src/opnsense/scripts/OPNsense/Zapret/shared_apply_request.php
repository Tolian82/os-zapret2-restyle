<?php

/**
 * Internal root FD9 request staging for the ONE Strategies/Voice Apply.
 *
 * No Config save, template reload, IPFW mutation, or runtime switch.
 * The service owns FD9. Only a complete, freshly read OPNsense Config model
 * can produce a detached XML candidate in the fixed, private work root.
 * A later step renders it with the native template engine and builds the
 * complete shared release before committing any live resource.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';

use OPNsense\Zapret\Api\SettingsApply;

final class SharedApplyRequest
{
    private const ROOT = '/var/db/zapret2/shared-work';
    private const MAX_REQUEST = 65536;
    private const MAX_XML = 16777216;

    public static function decode(string $encoded): array
    {
        if ($encoded === '' || strlen($encoded) > self::MAX_REQUEST ||
            !preg_match('/^[A-Za-z0-9_-]+$/D', $encoded)) {
            throw new \InvalidArgumentException('Invalid shared Apply request envelope');
        }
        $bytes = base64_decode(strtr($encoded, '-_', '+/'), true);
        if (!is_string($bytes) || strlen($bytes) > self::MAX_REQUEST ||
            rtrim(strtr(base64_encode($bytes), '+/', '-_'), '=') !== $encoded) {
            throw new \InvalidArgumentException('Invalid shared Apply request encoding');
        }
        $data = json_decode($bytes, true, 20, JSON_THROW_ON_ERROR);
        if (!is_array($data) || array_keys($data) !== ['page', 'fields', 'sync'] ||
            !in_array($data['page'], ['voice', 'strategies'], true) ||
            !is_array($data['fields']) || !is_array($data['sync'])) {
            throw new \InvalidArgumentException('Invalid shared Apply request content');
        }
        if ($data['page'] === 'voice') {
            if (array_keys($data['sync']) !== ['snapshot']) {
                throw new \InvalidArgumentException('Voice snapshot required');
            }
        } elseif (array_keys($data['sync']) !== ['telegramips_baseline']) {
            throw new \InvalidArgumentException('Strategies Telegram baseline required');
        }
        return $data;
    }

    public static function prepare(
        array $request, array $current, string $activeXml
    ): array {
        $plan = $request['page'] === 'voice'
            ? SettingsApply::prepareVoice(
                $current, $request['fields'], $request['sync']['snapshot']
            )
            : SettingsApply::prepareStrategies(
                $current, $request['fields'], $request['sync']['telegramips_baseline']
            );
        if (($plan['result'] ?? null) !== 'prepared') {
            throw new \InvalidArgumentException('Shared native Apply candidate rejected');
        }
        $xml = SettingsApply::renderCandidateXml(
            $activeXml, $current, $plan, $request['page']
        );
        if (strlen($xml) > self::MAX_XML) {
            throw new \InvalidArgumentException('Detached Config exceeds native limit');
        }
        return ['plan' => $plan, 'xml' => $xml];
    }

    private static function secureDir(string $path, bool $create): void
    {
        if ($create && !file_exists($path) && !is_link($path) && !mkdir($path, 0700)) {
            throw new \RuntimeException('Cannot initialize shared candidate directory');
        }
        $stat = @lstat($path);
        if (!is_array($stat) || !is_dir($path) || is_link($path) ||
            $stat['uid'] !== 0 || ($stat['mode'] & 0077) !== 0) {
            throw new \RuntimeException('Unsafe shared candidate directory');
        }
    }

    private static function writeExclusive(string $path, string $content): void
    {
        $handle = @fopen($path, 'xb');
        if ($handle === false) {
            throw new \RuntimeException('Shared candidate file already exists');
        }
        try {
            if (!chmod($path, 0600)) {
                throw new \RuntimeException('Shared candidate permissions failed');
            }
            $length = strlen($content);
            $written = 0;
            while ($written < $length) {
                $chunk = fwrite($handle, substr($content, $written));
                if ($chunk === false || $chunk === 0) {
                    throw new \RuntimeException('Shared candidate write failed');
                }
                $written += $chunk;
            }
            if (!fflush($handle) || !fsync($handle)) {
                throw new \RuntimeException('Shared candidate fsync failed');
            }
        } finally {
            fclose($handle);
        }
    }

    /**
     * Only the privileged original-FD9 service invokes materialize().
     * The request is already decoded, modeled and rendered. No active file
     * is replaced; incomplete work remains inert and cannot be reused.
     */
    public static function materialize(array $result, string $base = self::ROOT): string
    {
        if (!isset($result['plan'], $result['xml']) ||
            !is_array($result['plan']) || !is_string($result['xml'])) {
            throw new \InvalidArgumentException('Malformed native shared preparation');
        }
        $originalUmask = umask(0077);
        try {
            if ($base === self::ROOT) {
                self::secureDir('/var/db/zapret2', true);
            }
            self::secureDir($base, true);
            $id = bin2hex(random_bytes(16));
            $work = rtrim($base, '/') . '/' . $id;
            self::secureDir($work, true);
            $planJson = json_encode($result['plan'], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
            self::writeExclusive($work . '/candidate.xml', $result['xml']);
            self::writeExclusive($work . '/plan.json', $planJson . "\n");
            return $id;
        } finally {
            umask($originalUmask);
        }
    }

    public static function main(array $argv): int
    {
        if (count($argv) !== 3 || $argv[1] !== 'stage') {
            fwrite(STDERR, "usage: shared_apply_request.php stage ENCODED_REQUEST\n");
            return 64;
        }
        try {
            if (PHP_OS_FAMILY !== 'BSD' || posix_geteuid() !== 0) {
                throw new \RuntimeException('Native root staging required');
            }
            // Same installed OPNsense bootstrapping as built-in PHP scripts.
            require_once('script/load_phalcon.php');
            $request = self::decode($argv[2]);
            $config = \OPNsense\Core\Config::getInstance();
            $config->lock();
            try {
                $current = (new \OPNsense\Zapret\Zapret())->getNodes();
                $activeXml = file_get_contents('/conf/config.xml');
                if (!is_string($activeXml)) {
                    throw new \RuntimeException('Could not read locked native Config');
                }
                $prepared = self::prepare($request, $current, $activeXml);
                $id = self::materialize($prepared);
            } finally {
                $config->unlock();
            }
            echo "prepared-id=$id\n";
            return 0;
        } catch (\Throwable $error) {
            fwrite(STDERR, "ERROR: shared native request preparation refused: " .
                $error->getMessage() . "\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' && isset($argv) &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(SharedApplyRequest::main($argv));
}
