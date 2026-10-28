<?php

/**
 * Copyright (C) 2026 Umur Gorur
 * All rights reserved.
 */

namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiMutableModelControllerBase;
use OPNsense\Base\UserException;
use OPNsense\Core\Backend;
use OPNsense\Core\Config;

require_once __DIR__ . '/SettingsApply.php';
require_once __DIR__ . '/SharedApplyEnvelope.php';
require_once __DIR__ . '/IPSetPolicyBridge.php';

class SettingsController extends ApiMutableModelControllerBase
{
    protected static $internalModelName = 'zapret';
    protected static $internalModelClass = '\OPNsense\Zapret\Zapret';

    private const TARGET_FIELDS = [
        'youtubedomains' => 'YouTube Domains',
        'telegramips' => 'Telegram IPs',
        'userdomains' => 'User Domains',
        'excludedomains' => 'Exclude Domains',
        'excludeipset' => 'Exclude IPSet',
    ];

    private function validationFailure(string $field, string $message): array
    {
        return [
            'result' => 'failed',
            'validations' => ["zapret.hostlist.{$field}" => $message],
        ];
    }

    private function lifecycleGuard(): array
    {
        $backend = new Backend();
        $response = trim((string)$backend->configdRun('zapret strategy_lab_guard'));
        if ($response === '') {
            return [
                'status' => 'busy',
                'busy' => true,
                'owner' => 'unknown',
                'state' => 'unavailable',
                'reason' => 'guard_unavailable',
            ];
        }

        $decoded = json_decode($response, true);
        if (!is_array($decoded) || !array_key_exists('busy', $decoded)) {
            return [
                'status' => 'busy',
                'busy' => true,
                'owner' => 'unknown',
                'state' => 'invalid',
                'reason' => 'guard_invalid',
            ];
        }

        return $decoded;
    }

    private function assertLifecycleAvailable(): void
    {
        $guard = $this->lifecycleGuard();
        if (($guard['busy'] ?? true) !== true) {
            return;
        }

        $owner = (string)($guard['owner'] ?? 'unknown');
        $state = (string)($guard['state'] ?? 'unknown');
        throw new UserException(
            sprintf(
                gettext('Settings cannot be applied while Strategy Lab controls Zapret2 (owner: %s, state: %s). Stop the active diagnostics operation and wait for verified restoration.'),
                $owner,
                $state
            ),
            gettext('Zapret lifecycle is busy')
        );
    }

    public function lifecycleAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'busy' => true, 'reason' => 'post_required'];
        }
        return $this->lifecycleGuard();
    }

    private function normalizeDomainList(string $text, string $label): array
    {
        $normalized = [];
        $seen = [];
        $changed = 0;
        $duplicates = 0;

        foreach (preg_split('/\R/u', $text) as $index => $raw) {
            $lineNo = $index + 1;
            $value = trim($raw);
            if ($value === '') {
                continue;
            }
            $original = $value;
            $value = preg_replace('#^https?://#i', '', $value);
            $value = preg_replace('/[\/?#].*$/', '', $value);
            $value = preg_replace('/^\*\./', '', trim($value));
            $value = preg_replace('/^[,;:]+|[,;:]+$/', '', $value);
            $value = trim($value, ". \t\n\r\0\x0B");
            $value = strtolower($value);

            if ($value === '' || strlen($value) > 253 || strpos($value, '..') !== false) {
                throw new \InvalidArgumentException(
                    sprintf("%s, line %d: invalid domain entry '%s'", $label, $lineNo, $raw)
                );
            }
            if (preg_match('/^[0-9.]+$/', $value) || strpos($value, '/') !== false) {
                throw new \InvalidArgumentException(
                    sprintf("%s, line %d: IP addresses and networks are not allowed in a domain list ('%s')", $label, $lineNo, $raw)
                );
            }
            foreach (explode('.', $value) as $part) {
                if (
                    $part === '' || strlen($part) > 63 ||
                    !preg_match('/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/', $part)
                ) {
                    throw new \InvalidArgumentException(
                        sprintf("%s, line %d: invalid domain entry '%s' after normalization to '%s'", $label, $lineNo, $raw, $value)
                    );
                }
            }

            if ($value !== $original) {
                $changed++;
            }
            if (isset($seen[$value])) {
                $duplicates++;
                continue;
            }
            $seen[$value] = true;
            $normalized[] = $value;
        }

        return [implode("\n", $normalized), $changed, $duplicates];
    }

    private function backendFailureMessage(string $fallback): string
    {
        $stageFile = '/var/run/zapret2-execution.status';
        if (is_readable($stageFile)) {
            $parts = explode('|', trim((string)file_get_contents($stageFile)), 6);
            if (count($parts) === 6 && $parts[3] === 'failed' && trim($parts[5]) !== '') {
                return trim($parts[5]);
            }
        }
        return $fallback;
    }

    /**
     * The same one-FD9 Apply as Voice, retaining the established Strategies
     * normalization and response contract. No GUI-side Config::save precedes
     * runtime activation; the root Config worker revalidates the full model.
     */
    public function applyAction()
    {
        if (!$this->request->isPost()) {
            return ['result' => 'failed'];
        }
        $this->throwReadOnly();
        $post = $this->request->getPost(static::$internalModelName);
        if (!is_array($post) || !isset($post['sync']) ||
            !is_array($post['sync']) ||
            array_keys($post['sync']) !== ['telegramips_baseline']
        ) {
            return ['result' => 'failed',
                'message' => gettext('Missing or invalid Strategies baseline; reload this page')];
        }
        $sync = $post['sync'];
        unset($post['sync']);
        $summary = [];
        // From original-FD9 dispatch onward, an exception is not proof of
        // a pre-write rejection, regardless of its PHP class. This is the
        // same commit-result contract as VoiceController::applyAction.
        $nativeApplyDispatched = false;
        $preflightStage = 'lifecycle-guard';
        try {
            $this->assertLifecycleAvailable();
            $preflightStage = 'model';
            $config = Config::getInstance();
            $config->lock();
            try {
                $current = (new \OPNsense\Zapret\Zapret())->getNodes();
                $plan = SettingsApply::prepareStrategies(
                    $current, $post, $sync['telegramips_baseline']
                );
                $preflightStage = 'normalization';
                // Native Python is the only IP/CIDR grammar. This read-only
                // preflight inspects all six user lists once and does not
                // write any Config, target file, engine or firewall state.
                try {
                    $ipset = IPSetPolicyBridge::inspect(
                        IPSetPolicyBridge::allFromHostlist($plan['candidate']['hostlist'] ?? [])
                    );
                } catch (\InvalidArgumentException $error) {
                    foreach (['Telegram IPs' => 'telegramips', 'DISCORD IPs' => 'discordips',
                        'X IPs' => 'xips', 'SIP IPs' => 'sipips', 'CUSTOM IPs' => 'customips',
                        'Exclude IPSet' => 'excludeipset'] as $label => $field) {
                        if (str_contains($error->getMessage(), $label)) {
                            return $this->validationFailure($field, $error->getMessage());
                        }
                    }
                    return $this->validationFailure('excludeipset', $error->getMessage());
                }
                // Domain lists stay domain-only and never enter Python IPSETs.
                foreach (self::TARGET_FIELDS as $field => $label) {
                    $raw = (string)($plan['candidate']['hostlist'][$field] ?? '');
                    if ($field === 'telegramips' || $field === 'excludeipset') {
                        $name = $field === 'excludeipset' ? 'exclude' : 'telegram';
                        $value = $ipset['lists'][$name]['normalized'];
                        $changed = ($value !== rtrim(str_replace(["\r\n", "\r"], "\n", $raw), "\n")) ? 1 : 0;
                        $duplicates = 0;
                    } else {
                        [$value, $changed, $duplicates] = $this->normalizeDomainList($raw, $label);
                    }
                    if ($changed > 0 || $duplicates > 0) {
                        $summary[] = sprintf(
                            '%s: normalized %d, removed duplicates %d',
                            $label, $changed, $duplicates
                        );
                    }
                    if ($raw !== $value) {
                        if (!isset($post['hostlist'])) {
                            $post['hostlist'] = [];
                        }
                        $post['hostlist'][$field] = $value;
                    }
                }
                $plan = SettingsApply::prepareStrategies(
                    $current, $post, $sync['telegramips_baseline']
                );
                $preflightStage = 'candidate-validation';
                // Validate against a detached model, never serialize it to
                // the live OPNsense Config before the privileged transaction.
                $model = new \OPNsense\Zapret\Zapret();
                // Native getNodes() includes non-scalar selected-option
                // dictionaries. OPNsense setNodes() cannot accept them.
                // Match SharedConfigCommit: validate only the explicitly
                // changed scalar leaves on a fresh detached model.
                foreach ($plan['changed_fields'] as $reference) {
                    $value = $plan['candidate'];
                    foreach (explode('.', $reference) as $part) {
                        if (!is_array($value) || !array_key_exists($part, $value)) {
                            throw new \InvalidArgumentException(
                                'Incomplete Strategies candidate field'
                            );
                        }
                        $value = $value[$part];
                    }
                    if (!is_string($value) ||
                        $model->setNodeByReference($reference, $value) !== true) {
                        throw new \InvalidArgumentException(
                            'Strategies candidate field validation refused'
                        );
                    }
                }
                $errors = $model->performValidation(false);
                if (count($errors) > 0) {
                    $validations = [];
                    foreach ($errors as $error) {
                        $validations['zapret.' . $error->getField()] = $error->getMessage();
                    }
                    return ['result' => 'failed', 'validations' => $validations];
                }
                $preflightStage = 'candidate-xml';
                SettingsApply::renderCandidateXml(
                    (string)$config, $current, $plan, 'strategies'
                );
                $preflightStage = 'envelope';
                // Original POST may include megabytes of unchanged domains.
                // Native configd argv is intentionally limited to 65536 bytes.
                // Root FD9 rereads the current Config and overlays only edits.
                $transport = [];
                foreach ($plan['changed_fields'] as $reference) {
                    if (!preg_match('/^(general|strategy|hostlist)\.[a-z]+$/D', $reference)) {
                        throw new \InvalidArgumentException('Invalid Strategies changed field');
                    }
                    [$group, $field] = explode('.', $reference, 2);
                    $value = $plan['candidate'][$group][$field] ?? null;
                    if (!is_string($value)) {
                        throw new \InvalidArgumentException('Invalid Strategies changed value');
                    }
                    $transport[$group][$field] = $value;
                }
                // Do not relax envelope size checks for actually edited lists.
                $encoded = SharedApplyEnvelope::encode('strategies', $transport, $sync);
            } finally {
                $config->unlock();
            }
            // No Config lock while configd owns original FD9.
            $preflightStage = 'dispatch-guard';
            $this->assertLifecycleAvailable();
            $backend = new Backend();
            $nativeApplyDispatched = true;
            $response = trim((string)$backend->configdpRun(
                'zapret shared_apply', ['strategies', $encoded], false, 600
            ));
            // Root preflight receipts are definitive: shared_apply_run returns
            // them only before journal PREPARED / Config / runtime / IPFW changes.
            // A generic requires_review here would freeze the GUI for a
            // safely rejected candidate and conceal the actual stage.
            if (preg_match('/^preflight-rejected=(root-gate|bootstrap|model|decode|candidate|candidate-plan|candidate-validation|candidate-xml|candidate-size|workspace|render|runtime-build|seal|bundle-verify|config-preflight|runtime-preflight)$/D', $response, $match)) {
                return [
                    'result' => 'failed', 'applied' => false,
                    'requires_review' => false,
                    'message' => sprintf(
                        gettext('Native Strategies preflight rejected before Apply (%s)'),
                        $match[1]
                    ),
                ];
            }
            if (!preg_match('/(?:^|\n)applied-id=([a-f0-9]{32})$/D', $response)) {
                return [
                    'result' => 'failed', 'applied' => false,
                    'requires_review' => true,
                    'message' => gettext(
                        'Native Apply did not confirm Config and runtime commit; inspect recovery status'
                    ),
                ];
            }
            return [
                'result' => 'saved',
                'status' => 'ok',
                'normalized' => !empty($summary),
                'normalization' => $summary,
                static::$internalModelName => $plan['candidate'],
            ];
        } catch (\InvalidArgumentException $error) {
            if ($nativeApplyDispatched) {
                return [
                    'result' => 'failed', 'applied' => false,
                    'requires_review' => true,
                    'message' => gettext(
                        'Native Strategies Apply result is uncertain; inspect runtime before retrying'
                    ),
                ];
            }
            return ['result' => 'failed', 'message' => $error->getMessage()];
        } catch (\Throwable $error) {
            if (!$nativeApplyDispatched) {
                // All failures before configdpRun are known non-mutating.
                // Log only bounded labels, never a Config or request envelope.
                error_log(sprintf('Zapret Strategies pre-Apply refused stage=%s type=%s',
                    $preflightStage, get_class($error)));
                return [
                    'result' => 'failed', 'applied' => false,
                    'requires_review' => false,
                    'message' => sprintf(
                        gettext('Strategies preflight failed before native Apply (%s)'),
                        $preflightStage
                    ),
                ];
            }
            return [
                'result' => 'failed', 'applied' => false,
                'requires_review' => true,
                'message' => gettext(
                    'Native Strategies Apply failed or was interrupted; inspect runtime before retrying'
                ),
            ];
        }
    }

}
