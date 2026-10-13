<?php

/**
 * Native OPNsense Config commit seam for the ONE shared Strategies/Voice Apply.
 *
 * This is an internal PHP library, NOT a second executable entrypoint or
 * independent writer. The future privileged service worker must own FD9 and
 * an interruption record before calling persist(), with the whole shared
 * runtime already activated but not yet committed. The caller coordinates
 * runtime/IPFW rollback on an error. No GUI/configd action invokes it yet.
 *
 * Config::save() unlocks its own flock on OPNsense 26.7: a fresh lock and
 * model read AFTER save are mandatory. Never restore an old full Config XML
 * over later concurrent edits; ambiguities require explicit review.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';

use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

final class SharedConfigCommit
{
    /**
     * $config is the native OPNsense\Core\Config singleton.
     * $modelFactory must construct a fresh OPNsense\Zapret\Zapret under lock.
     * Injected dependencies keep the OPNsense lock/save contract testable
     * without a live router or independent persistence implementation.
     */
    public static function persist(
        array $plan,
        string $page,
        object $config,
        callable $modelFactory
    ): array {
        $saveAttempted = false;
        $targetSnapshot = null;
        $changeCount = null;
        $config->lock();
        try {
            $model = $modelFactory();
            $current = $model->getNodes();
            $target = SettingsApply::mergeForCommit($current, $plan, $page);
            $targetSnapshot = VoiceSettingsSnapshot::digest($target);
            $changeCount = count($plan['changed_fields']);
            // Repeated Apply must not manufacture a second Config revision.
            if ($changeCount === 0) {
                return [
                    'result' => 'unchanged',
                    'saved' => false,
                    'snapshot' => $targetSnapshot,
                    'change_count' => 0,
                ];
            }
            $model->setNodes($target);
            $errors = $model->performValidation(false);
            if (count($errors) > 0) {
                throw new \InvalidArgumentException(
                    'Native OPNsense model rejected the shared Apply candidate'
                );
            }
            if (!$model->serializeToConfig(false, true)) {
                throw new \RuntimeException(
                    'Native OPNsense model serialization failed'
                );
            }
            $saveAttempted = true;
            // Use native Config revision, audit and backup notifications.
            $config->save([
                'description' => $page === 'voice'
                    ? 'Applied shared Zapret Voice settings'
                    : 'Applied shared Zapret Strategies settings',
            ]);
        } catch (\Throwable $error) {
            if ($saveAttempted) {
                // Config::save may have partly written the target, and
                // releases its original flock before returning. Do not
                // claim the old preferences or runtime are restored.
                throw new \RuntimeException(
                    'Native Config save outcome requires explicit review',
                    0,
                    $error
                );
            }
            throw $error;
        } finally {
            $config->unlock();
        }

        // The same Config object may have been modified by another OPNsense
        // page immediately after save(). Reacquire and LOAD a fresh model.
        $config->lock();
        try {
            $saved = $modelFactory()->getNodes();
            if (!hash_equals($targetSnapshot, VoiceSettingsSnapshot::digest($saved))) {
                throw new \RuntimeException(
                    'Native Config changed after save; runtime reconciliation required'
                );
            }
        } finally {
            $config->unlock();
        }
        return [
            'result' => 'saved',
            'saved' => true,
            // This is persistence only. A public Apply success requires
            // runtime/IPFW commit and subsequent attestation by FD9 owner.
            'applied' => false,
            'snapshot' => $targetSnapshot,
            'change_count' => $changeCount,
        ];
    }
}
