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

/**
 * Persistence after Config::save was attempted cannot be classified as an
 * ordinary pre-save failure. Native save may have written only part of the
 * new XML and releases its flock. Runtime must remain reviewable.
 */
final class SharedConfigSaveUncertain extends \RuntimeException {}

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
                throw new SharedConfigSaveUncertain(
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
                throw new SharedConfigSaveUncertain(
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
    /**
     * The one cross-resource FD9 transaction boundary.
     *
     * The service-owned worker supplies ONLY its existing runtime adapter
     * and the ONE durable common-operation record, not a second Voice
     * lifecycle. Every record callback must return true only after durable
     * persistence; refusing an intent MUST stop before runtime mutation.
     * This method has no public route until the FD9/receipt worker is wired.
     *
     * The runtime adapter's activation failure is treated as ambiguous:
     * apply_runtime_activate already attempts its own rollback and returns
     * a distinct RESTORE_FAILED if that fails. We must not double-rollback
     * after an unknown partial transition.
     */
    public static function transact(
        array $plan,
        string $page,
        object $config,
        callable $modelFactory,
        callable $assertFd9,
        callable $record,
        callable $activate,
        callable $rollback,
        callable $commit
    ): array {
        if ($assertFd9() !== true) {
            throw new \RuntimeException('Shared Apply requires existing FD9 ownership');
        }
        if (!in_array($page, ['voice', 'strategies'], true)) {
            throw new \InvalidArgumentException('Unknown native Apply page');
        }
        // No side effects before fresh model check. The running service may
        // change after preflight, therefore persist() repeats it under lock.
        $config->lock();
        try {
            $current = $modelFactory()->getNodes();
            self::validatePlanBeforeRuntime($current, $plan, $page);
        } finally {
            $config->unlock();
        }

        $detail = [
            'id' => bin2hex(random_bytes(16)),
            'page' => $page,
            'base' => $plan['dependencies'],
            'candidate' => VoiceSettingsSnapshot::digest($plan['candidate']),
            'changed_fields' => $plan['changed_fields'],
        ];
        $recordPhase = static function (string $phase) use ($record, $detail): void {
            if ($record($phase, $detail) !== true) {
                throw new \RuntimeException('Shared Apply durable operation record failed');
            }
        };
        $recordPhase('prepared');
        $recordPhase('activating');
        $activationCompleted = false;
        $saveCompleted = false;
        try {
            if ($activate() !== true) {
                throw new \RuntimeException('Shared runtime activation not verified');
            }
            $activationCompleted = true;
            $recordPhase('activated');
            $save = self::persist($plan, $page, $config, $modelFactory);
            $saveCompleted = true;
            $recordPhase('config-saved');
            if ($commit() !== true) {
                throw new \RuntimeException('Shared runtime/IPFW commit not verified');
            }
            $recordPhase('committed');
            return [
                'result' => 'applied',
                'applied' => true,
                'saved' => $save['saved'],
                'snapshot' => $save['snapshot'],
                'change_count' => $save['change_count'],
                'requires_review' => false,
            ];
        } catch (\Throwable $error) {
            // Native save uncertainty or a post-save failure cannot be
            // reverted by just putting back the previous runtime. Preserve
            // common operation intent and old IPFW stages for boot recovery.
            if (!$activationCompleted || $saveCompleted ||
                $error instanceof SharedConfigSaveUncertain) {
                try {
                    $recordPhase('requires-review');
                } catch (\Throwable $recordError) {
                    // The root reason remains uncertain; never claim success.
                }
                return [
                    'result' => 'failed',
                    'applied' => false,
                    'saved' => $saveCompleted ? true : null,
                    'requires_review' => true,
                    'restored' => false,
                    'message' => $error->getMessage(),
                ];
            }

            // All failures before native save are recoverable if and ONLY
            // if the existing runtime/IPFW rollback confirms every resource.
            try {
                if ($rollback() !== true) {
                    throw new \RuntimeException('Shared runtime rollback not verified');
                }
                $recordPhase('restored');
                return [
                    'result' => 'failed',
                    'applied' => false,
                    'saved' => false,
                    'requires_review' => false,
                    'restored' => true,
                    'message' => $error->getMessage(),
                ];
            } catch (\Throwable $rollbackError) {
                try {
                    $recordPhase('restore-failed');
                } catch (\Throwable $recordError) {
                    // Keep uncertainty explicit; do not hide primary failure.
                }
                return [
                    'result' => 'failed',
                    'applied' => false,
                    'saved' => false,
                    'requires_review' => true,
                    'restored' => false,
                    'message' => 'RESTORE_FAILED: shared runtime requires review',
                ];
            }
        }
    }

    private static function validatePlanBeforeRuntime(array $live, array $plan, string $page): void
    {
        $candidate = SettingsApply::mergeForCommit($live, $plan, $page);
        if (!isset($plan['changed_fields']) || !is_array($plan['changed_fields']) ||
            $candidate === [] || !isset($plan['dependencies'])) {
            throw new \InvalidArgumentException('Incomplete native shared Apply candidate');
        }
    }

}
