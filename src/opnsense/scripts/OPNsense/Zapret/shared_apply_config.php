<?php

/**
 * The single shared Strategies/Voice native Config commit command.
 *
 * A service shell process must already own the original FD9. The staged
 * plan and detached XML are produced by shared_apply_request.php and
 * the complete release by shared-apply-build before this point.
 *
 * preflight => freshly locked native model, no save (before runtime switch)
 * save      => the existing SharedConfigCommit::persist, NOT a second writer
 *
 * This command does not control IPFW, start engines or edit the journal.
 * A failed save after an attempted Config::save is categorically UNCERTAIN.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/apply_settings.php';

use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

final class SharedApplyConfigWorker
{
    public const ROOT = '/var/db/zapret2/shared-work';
    private const MAX_PLAN = 4 * 1024 * 1024;

    private static function secureFile(string $path, bool $directory, int $owner): void
    {
        $s = @lstat($path);
        if ($s === false ||
            (($s['mode'] & 0170000) !== ($directory ? 0040000 : 0100000)) ||
            $s['uid'] !== $owner || ($s['mode'] & 0077) !== 0 ||
            (!$directory && ($s['nlink'] !== 1 || $s['size'] > self::MAX_PLAN))) {
            throw new \RuntimeException('Unsafe native common Apply evidence');
        }
    }

    public static function readPlan(string $id, string $root = self::ROOT, ?int $owner = null): array
    {
        if (!preg_match('/^[a-f0-9]{32}$/D', $id)) {
            throw new \InvalidArgumentException('Invalid common Apply ID');
        }
        $owner = $owner ?? posix_geteuid();
        self::secureFile($root, true, $owner);
        $dir = rtrim($root, '/') . '/' . $id;
        self::secureFile($dir, true, $owner);
        $file = $dir . '/plan.json';
        self::secureFile($file, false, $owner);
        $fp = @fopen($file, 'rb');
        if ($fp === false) {
            throw new \RuntimeException('Unable to open shared Apply plan');
        }
        try {
            $handle = fstat($fp);
            $named = @lstat($file);
            if ($named === false || $handle['ino'] !== $named['ino'] ||
                $handle['dev'] !== $named['dev']) {
                throw new \RuntimeException('Shared Apply plan changed inode');
            }
            $json = stream_get_contents($fp, self::MAX_PLAN + 1);
            if (!is_string($json) || strlen($json) > self::MAX_PLAN) {
                throw new \RuntimeException('Unsafe shared Apply plan size');
            }
        } finally {
            fclose($fp);
        }
        $plan = json_decode($json, true, 32, JSON_THROW_ON_ERROR);
        if (!is_array($plan) || ($plan['result'] ?? null) !== 'prepared' ||
            !isset($plan['candidate'], $plan['changed_fields'], $plan['dependencies']) ||
            !is_array($plan['candidate']) || !is_array($plan['changed_fields'])) {
            throw new \RuntimeException('Malformed stored native shared candidate');
        }
        // The Config and full release must have been staged together; a
        // symlinked/missing XML is not authority to persist its plan.
        self::secureFile($dir . '/candidate.xml', false, $owner);
        return $plan;
    }

    public static function preflight(
        array $plan, array $current, string $page
    ): array {
        $target = SettingsApply::mergeForCommit($current, $plan, $page);
        $mode = (string)($target['general']['enabled'] ?? '0');
        if (!in_array($mode, ['0', '1'], true)) {
            throw new \InvalidArgumentException('Invalid shared candidate runtime mode');
        }
        return [
            'result' => 'prepared',
            'snapshot' => VoiceSettingsSnapshot::digest($target),
            'enabled' => $mode,
            'changes' => count($plan['changed_fields']),
        ];
    }

    public static function main(array $argv): int
    {
        if (count($argv) !== 4 || !in_array($argv[1], ['preflight','save'], true) ||
            !in_array($argv[3], ['voice','strategies'], true)) {
            fwrite(STDERR, "usage: shared_apply_config.php preflight|save ID voice|strategies\n");
            return 64;
        }
        try {
            if (PHP_OS_FAMILY !== 'BSD' || posix_geteuid() !== 0) {
                throw new \RuntimeException('Root OPNsense native Config required');
            }
            require_once('script/load_phalcon.php');
            $plan = self::readPlan($argv[2], self::ROOT, 0);
            $config = \OPNsense\Core\Config::getInstance();
            $factory = static fn() => new \OPNsense\Zapret\Zapret();
            if ($argv[1] === 'preflight') {
                $config->lock();
                try {
                    $result = self::preflight($plan, $factory()->getNodes(), $argv[3]);
                } finally {
                    $config->unlock();
                }
                echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
                return 0;
            }
            $result = SharedConfigCommit::persist($plan, $argv[3], $config, $factory);
            echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
            return 0;
        } catch (SharedConfigSaveUncertain $error) {
            fwrite(STDERR, "ERROR: native shared Config save uncertain; retain recovery evidence\n");
            return 70;
        } catch (\Throwable $error) {
            fwrite(STDERR, "ERROR: native shared Config refused before save: " .
                $error->getMessage() . "\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' && isset($argv) &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(SharedApplyConfigWorker::main($argv));
}
