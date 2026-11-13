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
require_once __DIR__ . '/WanRequirement.php';

require_once __DIR__ . '/SettingsApply.php';
require_once __DIR__ . '/SharedApplyEnvelope.php';
require_once __DIR__ . '/IPSetPolicyBridge.php';
require_once __DIR__ . '/DomainSetPolicyBridge.php';

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
                // WAN must be the first semantic preflight, before the
                // strategy candidate, hostlists/IPSET and runtime checks.
                if (WanRequirement::missingBeforeActivation($current, $post)) {
                    return [
                        'result' => 'failed',
                        'applied' => false, 'requires_review' => false,
                        'message' => gettext('Select a WAN interface'),
                        'validations' => [
                            'zapret.general.waninterface' =>
                                gettext('Select a WAN interface'),
                        ],
                    ];
                }
                // Native missing-upstream diagnosis must precede seeded
                // candidate overlay/normalization; WAN-first already ran.
                if (SettingsApply::isPassiveStrategiesRequest($current, $post)) {
                    $preflightStage = 'runtime-status';
                    $runtimeReceipt = (string)(new Backend())->configdRun(
                        'zapret setup_status', false, 30
                    );
                    if (SettingsApply::isVerifiedMissingUpstream($runtimeReceipt)) {
                        return [
                            'result' => 'failed', 'applied' => false,
                            'requires_review' => false,
                            'reason' => 'runtime-not-installed',
                            'message' => gettext('The zapret2 service must be installed'),
                        ];
                    }
                }
                $preflightStage = 'model';
                $plan = SettingsApply::prepareStrategies(
                    $current, $post, $sync['telegramips_baseline']
                );
                // WAN-first on every active candidate; no other profile
                // validation may mask a missing selected WAN.
                if (WanRequirement::missingBeforeActivation($plan['candidate'])) {
                    return [
                        'result' => 'failed',
                        'applied' => false, 'requires_review' => false,
                        'message' => gettext('Select a WAN interface'),
                        'validations' => ['zapret.general.waninterface' =>
                            gettext('Select a WAN interface')],
                    ];
                }
                // LC-06: the actual changed-field scope, not the full POST,
                // identifies an independent WAN edit. Stored lists/IPSETs
                // are irrelevant to that field when runtime is stopped.
                $wanOnlyCandidate = $plan['changed_fields'] === ['general.waninterface'];
                if (!$wanOnlyCandidate) {
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
                    // Normalize only genuine user edits. An unchanged, large
                    // saved list may have a trailing newline or formatting
                    // that normalization would otherwise turn into a NEW
                    // megabyte-scale transport field. Preserve its bytes and
                    // keep the bounded configd envelope for the actual edit.
                    if (!in_array('hostlist.' . $field, $plan['changed_fields'], true)) {
                        continue;
                    }
                    $raw = (string)($plan['candidate']['hostlist'][$field] ?? '');
                    if ($field === 'telegramips' || $field === 'excludeipset') {
                        $name = $field === 'excludeipset' ? 'exclude' : 'telegram';
                        $value = $ipset['lists'][$name]['normalized'];
                        $changed = ($value !== rtrim(str_replace(["\r\n", "\r"], "\n", $raw), "\n")) ? 1 : 0;
                        $duplicates = 0;
                    } else {
                        try {
                            $domain = DomainSetPolicyBridge::inspect($raw, $field);
                        } catch (\InvalidArgumentException $error) {
                            return $this->validationFailure($field, $error->getMessage());
                        }
                        $value = $domain['normalized'];
                        $changed = $domain['changed'];
                        $duplicates = $domain['duplicates'];
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
                } // WAN-only does not run unrelated IPSET/domain normalization.
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
                $encoded = SharedApplyEnvelope::encode('strategies',
                    SharedApplyEnvelope::compactStrategies($transport, $current), $sync);
            } finally {
                $config->unlock();
            }
            // No Config lock while configd owns original FD9.
            $preflightStage = 'dispatch-guard';
            $this->assertLifecycleAvailable();
            $backend = new Backend();
            $nativeApplyDispatched = true;
            // One original FD9 owner: safe stopped WAN persists Config only;
            // a running/common owner still takes full runtime Apply/rollback.
            $response = trim((string)$backend->configdpRun(
                $wanOnlyCandidate ? 'zapret shared_apply_wan' : 'zapret shared_apply',
                $wanOnlyCandidate ? [$encoded] : ['strategies', $encoded],
                false, 600
            ));
            // Root preflight receipts are definitive: shared_apply_run returns
            // them only before journal PREPARED / Config / runtime / IPFW changes.
            // A generic requires_review here would freeze the GUI for a
            // safely rejected candidate and conceal the actual stage.
            if (preg_match('/^preflight-rejected=(root-gate|bootstrap|model|decode|candidate|wan-required|candidate-plan|candidate-validation|candidate-xml|candidate-size|workspace|render|runtime-build|seal|bundle-verify|config-preflight|runtime-preflight|wan-candidate|wan-lifecycle|wan-runtime-owner|wan-kernel|wan-model)$/D', $response, $match)) {
                return [
                    'result' => 'failed', 'applied' => false,
                    'requires_review' => false,
                    // Only the exact root receipt allowlist can supply this stage.
                    'reason' => 'native-preflight-' . $match[1],
                    'message' => sprintf(
                        gettext('Native Strategies preflight rejected before Apply (%s)'),
                        $match[1]
                    ),
                ];
            }
            $wanSaved = $wanOnlyCandidate &&
                preg_match('/^wan-saved=[a-f0-9]{64}$/D', $response) === 1;
            if (!$wanSaved &&
                !preg_match('/(?:^|\n)applied-id=([a-f0-9]{32})$/D', $response)) {
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
                'applied' => !$wanSaved,
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
                    'reason' => 'strategies-preflight-' . $preflightStage,
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

    /**
     * P2k5: the Auto Hostlist belongs to a root-owned final file, never
     * the mutable Config model or the full shared Apply. The root configd
     * action holds the same checked flock as P2k4 destination commits.
     */
    public function autoHostlistReadAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'error', 'reason' => 'post_required'];
        }
        try {
            $output = (string)(new Backend())->configdRun(
                'zapret auto_hostlist_read', false, 30
            );
            if (strlen($output) > 50000) {
                throw new \RuntimeException('Auto Hostlist reply too large');
            }
            $data = json_decode(trim($output), true);
            if (!is_array($data) || !in_array($data['result'] ?? null, ['ok', 'error'], true)) {
                throw new \RuntimeException('Invalid Auto Hostlist response');
            }
            if ($data['result'] === 'ok' &&
                (!in_array($data['status'] ?? null, ['missing', 'empty', 'populated'], true) ||
                 !is_string($data['content'] ?? null) ||
                 !is_string($data['revision'] ?? null) ||
                 preg_match('/^[a-f0-9]{64}$/D', $data['revision']) !== 1)
            ) {
                throw new \RuntimeException('Invalid Auto Hostlist snapshot');
            }
            return $data;
        } catch (\Throwable $error) {
            error_log('Zapret Auto Hostlist read unavailable: ' . get_class($error));
            return ['result' => 'error', 'reason' => 'unavailable'];
        }
    }

    public function autoHostlistSaveAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'error', 'reason' => 'post_required'];
        }
        $this->throwReadOnly();
        $post = $this->request->getPost('auto_hostlist');
        if (!is_array($post) || count($post) !== 2 ||
            !isset($post['revision'], $post['content']) ||
            !is_string($post['revision']) || !is_string($post['content']) ||
            preg_match('/^[a-f0-9]{64}$/D', $post['revision']) !== 1 ||
            strlen($post['content']) > 40960) {
            return ['result' => 'error', 'reason' => 'invalid_request'];
        }
        try {
            $json = json_encode(
                ['revision' => $post['revision'], 'content' => $post['content']],
                JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES
            );
            $token = rtrim(strtr(base64_encode($json), '+/', '-_'), '=');
            if (strlen($token) > 57000) {
                return ['result' => 'error', 'reason' => 'input_too_large'];
            }
            $output = (string)(new Backend())->configdpRun(
                'zapret auto_hostlist_save', [$token], false, 30
            );
            if (strlen($output) > 50000) {
                throw new \RuntimeException('Auto Hostlist save reply too large');
            }
            $data = json_decode(trim($output), true);
            if (!is_array($data) || !in_array($data['result'] ?? null,
                    ['saved', 'conflict', 'error'], true)) {
                throw new \RuntimeException('Invalid Auto Hostlist save response');
            }
            if ($data['result'] === 'saved' &&
                (!is_string($data['revision'] ?? null) ||
                 preg_match('/^[a-f0-9]{64}$/D', $data['revision']) !== 1 ||
                 !is_string($data['content'] ?? null) ||
                 !in_array($data['status'] ?? null, ['empty', 'populated'], true))) {
                throw new \RuntimeException('Invalid Auto Hostlist save receipt');
            }
            return $data;
        } catch (\Throwable $error) {
            error_log('Zapret Auto Hostlist save unavailable: ' . get_class($error));
            return ['result' => 'error', 'reason' => 'unavailable'];
        }
    }

    /**
     * P2k6 explicit, one-shot two-populated-file legacy union. The root
     * configd action (not this PHP process) holds the P2k5 destination flock
     * across revision checks, durable migration intent and atomic replacement.
     * No Config/Apply/FD9 operation can be reached.
     */
    public function autoHostlistMigrateAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'error', 'reason' => 'post_required'];
        }
        $this->throwReadOnly();
        $posted = $this->request->getPost('migration');
        if (!is_array($posted) || count($posted) !== 2 ||
            !isset($posted['revision'], $posted['legacy_digest']) ||
            !is_string($posted['revision']) ||
            !is_string($posted['legacy_digest']) ||
            preg_match('/^[a-f0-9]{64}$/D', $posted['revision']) !== 1 ||
            preg_match('/^[a-f0-9]{64}$/D', $posted['legacy_digest']) !== 1) {
            return ['result' => 'error', 'reason' => 'invalid_request'];
        }
        try {
            $raw = (string)(new Backend())->configdpRun(
                'zapret auto_hostlist_migrate',
                [$posted['revision'], $posted['legacy_digest']], false, 30
            );
            if (strlen($raw) > 4096) {
                throw new \RuntimeException('Unexpected legacy merge reply');
            }
            $receipt = json_decode(trim($raw), true);
            if (!is_array($receipt) ||
                !in_array($receipt['result'] ?? null, ['migrated', 'conflict', 'error'], true)) {
                throw new \RuntimeException('Missing native legacy merge receipt');
            }
            if (($receipt['result'] ?? null) === 'migrated' &&
                (!is_string($receipt['revision'] ?? null) ||
                 preg_match('/^[a-f0-9]{64}$/D', $receipt['revision']) !== 1 ||
                 !is_int($receipt['added'] ?? null) ||
                 $receipt['added'] < 0 || $receipt['added'] > 4096)) {
                throw new \RuntimeException('Invalid native legacy merge receipt');
            }
            return $receipt;
        } catch (\Throwable $error) {
            error_log('Zapret Auto Hostlist migration unavailable: ' . get_class($error));
            return ['result' => 'error', 'reason' => 'unavailable'];
        }
    }

    /**
     * P5c unsaved Strategies preview. No persistent Apply, Config::save,
     * candidate storage, or native runtime switch is reachable from here.
     * Native configd owns the same original FD9 used by ordinary Apply.
     */
    public function previewAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'failed', 'status' => 'POST_REQUIRED'];
        }
        $posted = $this->request->getPost(static::$internalModelName);
        if (!is_array($posted) || !isset($posted['sync']) ||
            !is_array($posted['sync']) ||
            array_keys($posted['sync']) !== ['telegramips_baseline'] ||
            !is_string($posted['sync']['telegramips_baseline'])
        ) {
            return ['result' => 'failed', 'status' => 'PREVIEW_BASELINE_INVALID'];
        }
        $sync = $posted['sync'];
        unset($posted['sync']);
        try {
            $config = Config::getInstance();
            $config->lock();
            try {
                $current = (new \OPNsense\Zapret\Zapret())->getNodes();
                $plan = SettingsApply::prepareStrategies(
                    $current, $posted, $sync['telegramips_baseline']
                );
                // Preserve the ONE Python domain/IPSET normalization authority
                // for edited lists. Preview never replaces text in the form.
                $ipset = null;
                $edits = $plan['changed_fields'];
                if (in_array('hostlist.telegramips', $edits, true) ||
                    in_array('hostlist.excludeipset', $edits, true)) {
                    try {
                        $ipset = IPSetPolicyBridge::inspect(
                            IPSetPolicyBridge::allFromHostlist($plan['candidate']['hostlist'] ?? [])
                        );
                    } catch (\InvalidArgumentException $error) {
                        $field = str_contains($error->getMessage(), 'Exclude IPSet')
                            ? 'excludeipset' : 'telegramips';
                        return $this->validationFailure($field, $error->getMessage());
                    }
                }
                foreach (self::TARGET_FIELDS as $field => $label) {
                    if (!in_array('hostlist.' . $field, $edits, true)) {
                        continue;
                    }
                    $raw = (string)($plan['candidate']['hostlist'][$field] ?? '');
                    if ($field === 'telegramips' || $field === 'excludeipset') {
                        $normalized = $ipset['lists'][$field === 'excludeipset' ? 'exclude' : 'telegram']['normalized'];
                    } else {
                        try {
                            $normalized = DomainSetPolicyBridge::inspect($raw, $field)['normalized'];
                        } catch (\InvalidArgumentException $error) {
                            return $this->validationFailure($field, $error->getMessage());
                        }
                    }
                    if ($normalized !== $raw) {
                        $posted['hostlist'][$field] = $normalized;
                    }
                }
                // The root worker re-reads Config, stale-tab token and model
                // after obtaining FD9; this is not an optimistic Apply token.
                $plan = SettingsApply::prepareStrategies(
                    $current, $posted, $sync['telegramips_baseline']
                );
                $transport = [];
                foreach ($plan['changed_fields'] as $reference) {
                    if (!preg_match('/^(general|strategy|hostlist)\.[a-z]+$/D', $reference)) {
                        throw new \InvalidArgumentException('Invalid preview changed field');
                    }
                    [$group, $field] = explode('.', $reference, 2);
                    $value = $plan['candidate'][$group][$field] ?? null;
                    if (!is_string($value)) {
                        throw new \InvalidArgumentException('Invalid preview value');
                    }
                    $transport[$group][$field] = $value;
                }
                $encoded = SharedApplyEnvelope::encode('strategies',
                    SharedApplyEnvelope::compactStrategies($transport, $current), $sync);
            } finally {
                $config->unlock();
            }
            $raw = trim((string)(new Backend())->configdpRun(
                'zapret strategy_preview', [$encoded], false, 160
            ));
            if (strlen($raw) > 65536) {
                throw new \RuntimeException('Preview reply exceeds limit');
            }
            $report = json_decode($raw, true);
            if (!is_array($report) || ($report['result'] ?? null) !== 'preview' ||
                ($report['saved'] ?? null) !== false ||
                ($report['applied'] ?? null) !== false ||
                !is_array($report['structure'] ?? null) ||
                !is_array($report['native_validation'] ?? null) ||
                !is_string($report['status'] ?? null)
            ) {
                throw new \RuntimeException('Preview receipt unavailable');
            }
            return $report;
        } catch (\Throwable $error) {
            // Fixed code only. No form content, candidate XML or engine output.
            error_log('Zapret Strategies preview refused type=' . get_class($error));
            return [
                'result' => 'failed', 'status' => 'PREVIEW_UNAVAILABLE',
                'message' => gettext('Unable to validate the draft without applying it'),
            ];
        }
    }

}
