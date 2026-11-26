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
require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/DomainSetPolicyBridge.php';
require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/IPSetPolicyBridge.php';

use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\DomainSetPolicyBridge;
use OPNsense\Zapret\Api\IPSetPolicyBridge;
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
    /**
     * Native MVC getNodes() returns option dictionaries for InterfaceField
     * and OptionField. The inverse setNodes() REJECTS such dictionaries:
     * leaf updates require one scalar. Never feed a full read-only snapshot
     * back to OPNsense (particularly the unchanged Strategies WAN).
     *
     * mergeForCommit() has already verified the exact changed-field whitelist
     * and complete candidate. Mutate ONLY those approved leaf nodes on the
     * fresh in-memory model, for both preflight and real Config save.
     */
    public static function validateOwnedModelFields(
        object $model,
        array $target,
        array $changedFields
    ): void {
        // The native Model owns types/fields/Config serialization, NOT domain
        // or IPSET syntax. Enforce the canonical Python grammars again under
        // original FD9 in root preflight AND immediately before Config::save.
        // Only changed owned leaves are checked, preserving legacy user lists.
        $domainFields = [];
        $ipsetFields = [];
        foreach ($changedFields as $reference) {
            if (in_array($reference, [
                'hostlist.youtubedomains', 'hostlist.userdomains',
                'hostlist.excludedomains'
            ], true)) {
                $domainFields[] = substr($reference, strlen('hostlist.'));
            } elseif (in_array($reference, [
                'hostlist.telegramips', 'hostlist.discordips',
                'hostlist.xips', 'hostlist.sipips', 'hostlist.customips',
                'hostlist.excludeipset'
            ], true)) {
                $ipsetFields[] = substr($reference, strlen('hostlist.'));
            }
        }
        if ($domainFields || $ipsetFields) {
            $hostlist = $target['hostlist'] ?? null;
            if (!is_array($hostlist)) {
                throw new \InvalidArgumentException('Missing native hostlist candidate');
            }
            foreach ($domainFields as $field) {
                $value = $hostlist[$field] ?? null;
                if (!is_string($value) ||
                    DomainSetPolicyBridge::inspect($value, $field)['normalized'] !== $value) {
                    throw new \InvalidArgumentException(
                        'Native domain candidate requires canonical Python normalization: ' . $field
                    );
                }
            }
            if ($ipsetFields) {
                $policy = IPSetPolicyBridge::inspect(
                    IPSetPolicyBridge::allFromHostlist($hostlist)
                );
                foreach ($ipsetFields as $field) {
                    $name = $field === 'excludeipset' ? 'exclude' : substr($field, 0, -3);
                    $value = $hostlist[$field] ?? null;
                    if (!is_string($value) ||
                        $policy['lists'][$name]['normalized'] !== $value) {
                        throw new \InvalidArgumentException(
                            'Native IPSET candidate requires canonical Python normalization: ' . $field
                        );
                    }
                }
            }
        }
        foreach ($changedFields as $reference) {
            if (!is_string($reference) ||
                !preg_match('/^[a-z]+(?:\.[a-z]+){1,2}$/D', $reference)) {
                throw new \InvalidArgumentException('Invalid native changed-field reference');
            }
            $value = $target;
            foreach (explode('.', $reference) as $part) {
                if (!is_array($value) || !array_key_exists($part, $value)) {
                    throw new \InvalidArgumentException('Missing native changed-field leaf');
                }
                $value = $value[$part];
            }
            if (!is_string($value) ||
                $model->setNodeByReference($reference, $value) !== true) {
                throw new \InvalidArgumentException('Native changed-field leaf refused');
            }
        }
        $errors = $model->performValidation(false);
        if (count($errors) > 0) {
            throw new \InvalidArgumentException(
                'Native OPNsense model rejected the shared Apply candidate'
            );
        }
    }

    public static function persist(
        array $plan,
        string $page,
        object $config,
        callable $modelFactory
    ): array {
        // The original found-file CAS and cold-crash protocol are not yet
        // authorized. Never persist only XML (including a found-only click)
        // from a sealed three-source intent: that would split one Apply.
        if (array_key_exists('found_intent', $plan)) {
            throw new \InvalidArgumentException(
                'Original Config and three HOSTLIST files require joint protected Apply'
            );
        }
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
            self::validateOwnedModelFields($model, $target, $plan['changed_fields']);
            if (!$model->serializeToConfig(false, true)) {
                throw new \RuntimeException(
                    'Native OPNsense model serialization failed'
                );
            }
            $saveAttempted = true;
            // Use native Config revision, audit and backup notifications.
            self::saveNativeModel($config, $page);
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
        try {
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
        } catch (SharedConfigSaveUncertain $error) {
            throw $error;
        } catch (\Throwable $error) {
            // Once Config::save() returned, ANY failure in relock,
            // model construction, readback or unlock is post-save uncertainty.
            // The shell distinguishes 69 (no save) from 70 (review required).
            throw new SharedConfigSaveUncertain(
                'Native Config readback failed after save; runtime requires review',
                0, $error
            );
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
     * Original single-Config-writer INTERNAL cutover for an already durable
     * three-file found WAL. NO native worker/configd/GUI route calls this yet.
     *
     * $withOriginalP2 receives its callback and the fresh locked Model
     * digest (base before serialization, saved candidate on readback).
     * It must execute its callback exactly once, releasing P2 before return.
     * $attestOriginal must prove FD9, original locked Config FD4, exact
     * sealed release/plan, found-files-written journal and three physical
     * after-images while P2 is held. $recordFoundPhase must fsync the SAME
     * FD9 operation.json from the original Config/P2 owner.
     *
     * CRITICAL: Config::save() releases the Config flock on OPNsense 26.7.
     * The P2 scope remains held through save() but MUST EXIT before a fresh
     * Config::lock(); reacquire Config THEN P2 for readback and saved-phase
     * journal fsync. Unknown outcomes are never safe to mark restored.
     */
    public static function persistFoundUnderOriginalOwner(
        array $plan,
        string $page,
        object $config,
        callable $modelFactory,
        callable $withOriginalP2,
        callable $attestOriginal,
        callable $recordFoundPhase
    ): array {
        $intent = $plan['found_intent'] ?? null;
        if ($page !== 'strategies' ||
            !is_array($intent) ||
            ($intent['commit_authorized'] ?? null) !== false ||
            !isset($plan['found_batch']) || !is_array($plan['found_batch']) ||
            array_keys($plan['found_batch']) !== ['youtube', 'user', 'auto'] ||
            !isset($plan['changed_fields']) || !is_array($plan['changed_fields'])) {
            throw new \InvalidArgumentException(
                'Original sealed three-source Config owner required'
            );
        }
        $attemptRecorded = false;
        $saveAttempted = false;
        $changeCount = count($plan['changed_fields']);
        $targetDigest = null;
        $config->lock();
        try {
            $model = $modelFactory();
            $live = $model->getNodes();
            $baseDigest = VoiceSettingsSnapshot::digest($live);
            $target = SettingsApply::mergeForCommit($live, $plan, $page);
            $targetDigest = VoiceSettingsSnapshot::digest($target);
            if ($changeCount > 0) {
                self::validateOwnedModelFields($model, $target, $plan['changed_fields']);
                if (!$model->serializeToConfig(false, true)) {
                    throw new \RuntimeException('Native found Config model serialization refused');
                }
            }
            $p2Invocations = 0;
            $status = $withOriginalP2(static function () use (
                &$p2Invocations, &$attemptRecorded, &$saveAttempted,
                $attestOriginal, $recordFoundPhase, $targetDigest,
                $config, $changeCount
            ): string {
                if (++$p2Invocations !== 1 ||
                    $attestOriginal('before-config-save', $targetDigest) !== true) {
                    throw new \RuntimeException('Original Config/P2 witness refused before save');
                }
                // A native Config::save exception may mean it wrote part of
                // the XML. WAL must be durable BEFORE the first save call.
                if ($recordFoundPhase('found-config-saving') !== true) {
                    throw new \RuntimeException('Original Config-save intent not durable');
                }
                $attemptRecorded = true;
                if ($changeCount > 0) {
                    $saveAttempted = true;
                    self::saveNativeModel($config, 'strategies');
                }
                return 'original-config-save-scope-exited';
            }, $baseDigest);
            if ($p2Invocations !== 1 || $status !== 'original-config-save-scope-exited') {
                throw new \RuntimeException('Original Config/P2 owner did not release scope');
            }
        } catch (\Throwable $error) {
            if ($saveAttempted || $attemptRecorded) {
                throw new SharedConfigSaveUncertain(
                    'Original Config save/intent outcome requires review', 0, $error
                );
            }
            throw $error;
        } finally {
            $config->unlock();
        }

        // FIRST P2 scope has ended. Acquire original Config, THEN new P2:
        // never invert the order with the minute queue's Config->P2 path.
        try {
            $config->lock();
            try {
                $saved = $modelFactory()->getNodes();
                $savedDigest = VoiceSettingsSnapshot::digest($saved);
                if (!hash_equals($targetDigest, $savedDigest)) {
                    throw new SharedConfigSaveUncertain(
                        'Original native Config changed during save/readback'
                    );
                }
                $postInvocations = 0;
                $status = $withOriginalP2(static function () use (
                    &$postInvocations, $attestOriginal, $recordFoundPhase,
                    $targetDigest
                ): string {
                    if (++$postInvocations !== 1 ||
                        $attestOriginal('after-config-save', $targetDigest) !== true) {
                        throw new \RuntimeException('Original saved Config/P2 proof refused');
                    }
                    if ($recordFoundPhase('found-config-saved') !== true) {
                        throw new \RuntimeException('Original saved Config WAL not durable');
                    }
                    return 'original-config-readback-attested';
                }, $savedDigest);
                if ($postInvocations !== 1 ||
                    $status !== 'original-config-readback-attested') {
                    throw new \RuntimeException('Original saved Config/P2 handoff refused');
                }
            } finally {
                $config->unlock();
            }
        } catch (SharedConfigSaveUncertain $error) {
            throw $error;
        } catch (\Throwable $error) {
            throw new SharedConfigSaveUncertain(
                'Original found Config readback or WAL uncertain', 0, $error
            );
        }
        return [
            'result' => 'found-config-saved-nonterminal',
            'saved' => $saveAttempted,
            'applied' => false,
            'snapshot' => $targetDigest,
            'change_count' => $changeCount,
            'requires_review' => false,
            // There is still NO public final runtime/IPFW/epoch commit.
            'commit_authorized' => false,
        ];
    }

    /** The existing native singleton performs every Config::save call. */
    private static function saveNativeModel(object $config, string $page): void
    {
        $config->save([
            'description' => $page === 'voice'
                ? 'Applied shared Zapret Voice settings'
                : 'Applied shared Zapret Strategies settings',
        ]);
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
        // This legacy callable coordinator must reject found intent BEFORE
        // making a journal record or activating a runtime, not only when its
        // later Config persistence would be refused.
        if (array_key_exists('found_intent', $plan)) {
            throw new \InvalidArgumentException(
                'Found sources require original FD9 joint destination transaction'
            );
        }
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
