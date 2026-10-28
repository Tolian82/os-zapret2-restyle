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
require_once __DIR__ . '/shared_apply_lock.php';

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
        $owner = $owner ?? SharedApplyLifecycleLock::effectiveUid();
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
        try {
            $plan = json_decode($json, true, 32, JSON_THROW_ON_ERROR);
        } catch (\JsonException $error) {
            throw new \RuntimeException('Corrupt stored native shared plan', 0, $error);
        }
        if (!is_array($plan) || ($plan['result'] ?? null) !== 'prepared' ||
            !isset($plan['candidate'], $plan['changed_fields'], $plan['dependencies']) ||
            !is_array($plan['candidate']) || !is_array($plan['changed_fields']) ||
            !in_array($plan['page'] ?? null, ['voice','strategies'], true)) {
            throw new \RuntimeException('Malformed stored native shared candidate');
        }
        // The Config and full release must have been staged together; a
        // symlinked/missing XML is not authority to persist its plan.
        self::secureFile($dir . '/candidate.xml', false, $owner);
        return $plan;
    }

    public static function preflight(
        array $plan, array $current, string $page, ?object $model = null
    ): array {
        $target = SettingsApply::mergeForCommit($current, $plan, $page);
        if ($model !== null && count($plan['changed_fields']) > 0) {
            // Full getNodes() contains selection-option arrays not suitable
            // for native setNodes(). Validate only form-owned scalar leaves,
            // using exactly the same write method as Config persist.
            SharedConfigCommit::validateOwnedModelFields(
                $model, $target, $plan['changed_fields']
            );
        }
        $mode = (string)($target['general']['enabled'] ?? '0');
        if (!in_array($mode, ['0', '1'], true)) {
            throw new \InvalidArgumentException('Invalid shared candidate runtime mode');
        }
        return [
            'result' => 'prepared',
            'snapshot' => VoiceSettingsSnapshot::digest($target),
            'enabled' => $mode,
            'changes' => count($plan['changed_fields']),
            'base' => $plan['dependencies'],
            'candidate' => VoiceSettingsSnapshot::digest($plan['candidate']),
            'fields' => $plan['changed_fields'],
        ];
    }

    /**
     * Boot may only replay the *saved* common candidate; unlike preflight,
     * its previous generation is necessarily obsolete after Config::save.
     * Compare the entire live Voice/Strategies dependency snapshot under the
     * actual native Config lock, not a stale GUI baseline or an XML file.
     */
    public static function saved(array $plan, array $current): array
    {
        $expected = VoiceSettingsSnapshot::digest($plan['candidate']);
        $actual = VoiceSettingsSnapshot::digest($current);
        if (!hash_equals($expected, $actual)) {
            throw new \RuntimeException('Saved native Config differs from shared owner');
        }
        $enabled = (string)($current['general']['enabled'] ?? '0');
        if (!in_array($enabled, ['0','1'], true)) {
            throw new \RuntimeException('Invalid saved native runtime mode');
        }
        return ['result'=>'committed','snapshot'=>$actual,'enabled'=>$enabled];
    }

    /** The saved Config cannot be labelled pre-save if output encoding fails. */
    public static function postSaveReceipt(array $result): string
    {
        try {
            return json_encode(
                $result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES
            ) . "\n";
        } catch (\Throwable $error) {
            throw new SharedConfigSaveUncertain(
                'Native saved Config receipt encoding requires review', 0, $error
            );
        }
    }

    public static function main(array $argv): int
    {
        if (count($argv) !== 4 || !in_array($argv[1], ['preflight','save','saved'], true) ||
            !in_array($argv[3], ['voice','strategies'], true)) {
            fwrite(STDERR, "usage: shared_apply_config.php preflight|save ID voice|strategies\n");
            return 64;
        }
        try {
            if (PHP_OS_FAMILY !== 'BSD' || SharedApplyLifecycleLock::effectiveUid() !== 0) {
                throw new \RuntimeException('Root OPNsense native Config required');
            }
            SharedApplyLifecycleLock::assertHeld();
            require_once('script/load_phalcon.php');
            $plan = self::readPlan($argv[2], self::ROOT, 0);
            if ($plan['page'] !== $argv[3]) {
                throw new \InvalidArgumentException('Stored native Apply page differs from request');
            }
            $config = \OPNsense\Core\Config::getInstance();
            $factory = static fn() => new \OPNsense\Zapret\Zapret();
            if ($argv[1] === 'preflight' || $argv[1] === 'saved') {
                $config->lock();
                try {
                    $model = $factory();
                    $fresh = $model->getNodes();
                    $result = $argv[1] === 'preflight'
                        ? self::preflight($plan, $fresh, $argv[3], $model)
                        : self::saved($plan, $fresh);
                } finally {
                    $config->unlock();
                }
                echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
                return 0;
            }
            $result = SharedConfigCommit::persist($plan, $argv[3], $config, $factory);
            $receipt = self::postSaveReceipt($result);
            // Even a short response write is uncertain to the caller:
            // Config is already persisted and runtime must not be rolled back.
            if (fwrite(STDOUT, $receipt) !== strlen($receipt)) {
                throw new SharedConfigSaveUncertain(
                    'Native saved Config receipt could not be delivered'
                );
            }
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
