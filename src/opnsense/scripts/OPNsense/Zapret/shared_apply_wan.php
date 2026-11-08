<?php
/**
 * LC-06: a WAN-only, *configuration-only* branch of the EXISTING Strategies
 * Apply. Entered exclusively by zapret_service.sh while it owns original
 * FD9 and has independently verified there is NO active common/legacy owner.
 *
 * This is NOT another Config writer: reuse SharedConfigCommit::persist()
 * with the original whitelist, model, snapshot, native Config lock, save
 * uncertainty and readback. The root service handles the runtime/FD9/IPFW
 * ownership check before calling "commit"; PHP cannot approve it itself.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/shared_apply_request.php';
require_once __DIR__ . '/apply_settings.php';
require_once __DIR__ . '/shared_apply_lock.php';

use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

final class WanOnlyConfig
{
    public static function prepare(string $encoded, array $current, string $activeXml): array
    {
        $request = SharedApplyRequest::decode($encoded);
        // The caller does not choose a whitelist or a second page. The
        // existing SharedApplyEnvelope can be reused only for ONE WAN leaf.
        if ($request['page'] !== 'strategies' ||
            array_keys($request['fields']) !== ['general'] ||
            !is_array($request['fields']['general']) ||
            array_keys($request['fields']['general']) !== ['waninterface'] ||
            !is_string($request['fields']['general']['waninterface'])) {
            throw new \InvalidArgumentException('WAN-only Apply requires exactly the native WAN field');
        }
        $targetWan = $request['fields']['general']['waninterface'];
        if (strlen($targetWan) > 64 ||
            ($targetWan !== '' && !preg_match('/^[a-z][a-z0-9_]{0,31}$/D', $targetWan))) {
            throw new \InvalidArgumentException('Invalid logical WAN interface');
        }
        $plan = SettingsApply::prepareStrategies(
            $current, $request['fields'], $request['sync']['telegramips_baseline']
        );
        $changed = $plan['changed_fields'];
        if ($changed !== [] && $changed !== ['general.waninterface']) {
            throw new \InvalidArgumentException('WAN-only Apply modifies foreign settings');
        }
        // Reuse the same old/current snapshot and exact changed-field XML
        // generator as the full shared Strategies transaction.
        SettingsApply::renderCandidateXml($activeXml, $current, $plan, 'strategies');
        return $plan;
    }

    public static function execute(
        string $action,
        string $encoded,
        object $config,
        callable $modelFactory
    ): array {
        if (!in_array($action, ['probe', 'commit'], true)) {
            throw new \InvalidArgumentException('Unknown WAN-only operation');
        }
        $config->lock();
        try {
            $current = $modelFactory()->getNodes();
            $plan = self::prepare($encoded, $current, (string)$config);
        } finally {
            $config->unlock();
        }
        if ($action === 'probe') {
            return ['result' => 'eligible', 'changed' => $plan['changed_fields']];
        }
        // The original FD9 shell has ALREADY proven the complete absence of
        // owned runtime/process/IPFW and an unfinished operation. A fresh
        // Config lock + full snapshot guard inside persist() prevents races
        // with another OPNsense GUI page after this probe.
        return SharedConfigCommit::persist($plan, 'strategies', $config, $modelFactory);
    }

    public static function main(array $argv): int
    {
        if (count($argv) !== 3 || !in_array($argv[1], ['probe','commit'], true)) {
            fwrite(STDERR, "usage: shared_apply_wan.php probe|commit ENCODED\n");
            return 64;
        }
        $attempted = $argv[1] === 'commit';
        try {
            if (PHP_OS_FAMILY !== 'BSD' ||
                SharedApplyLifecycleLock::effectiveUid() !== 0) {
                throw new \RuntimeException('Root native OPNsense required');
            }
            SharedApplyLifecycleLock::assertHeld();
            require_once('script/load_phalcon.php');
            $result = self::execute(
                $argv[1], $argv[2],
                \OPNsense\Core\Config::getInstance(),
                static fn() => new \OPNsense\Zapret\Zapret()
            );
            // The caller treats missing/partial output after a *commit* as
            // uncertain. Only an unambiguous native hash proves completion.
            $response = $argv[1] === 'probe'
                ? 'wan-eligible=1' . "\n"
                : 'wan-saved=' . $result['snapshot'] . "\n";
            if (fwrite(STDOUT, $response) !== strlen($response)) {
                throw new SharedConfigSaveUncertain('WAN-only Config response unavailable');
            }
            return 0;
        } catch (SharedConfigSaveUncertain $error) {
            fwrite(STDERR, "ERROR: WAN-only native Config save outcome requires review\n");
            return 70;
        } catch (\Throwable $error) {
            // Once an actual commit was entered, its outcome is known safe
            // ONLY if the error happened before Config::save; the reused
            // SharedConfigCommit differentiates uncertain saves explicitly.
            fwrite(STDERR, "ERROR: WAN-only native Config " .
                ($attempted ? 'commit' : 'probe') . " refused: " .
                get_class($error) . "\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' && isset($argv) &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(WanOnlyConfig::main($argv));
}
