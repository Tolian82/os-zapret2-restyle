<?php

/**
 * Read-only Voice status endpoint. No Apply/Save method is present until
 * the shared transactional runtime has been qualified.
 */
namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;
use OPNsense\Core\Config;

require_once __DIR__ . '/VoiceCandidateValidator.php';
require_once __DIR__ . '/VoiceSettingsSnapshot.php';
require_once __DIR__ . '/VoiceSettingsPayload.php';

class VoiceController extends ApiControllerBase
{
    /**
     * One native model response contains both the visible form and its exact
     * optimistic concurrency baseline. A second request for the token would
     * introduce a race with updates from Strategies or another Voice tab.
     */
    public function loadAction(): array
    {
        if (!$this->request->isGet()) {
            return ['result' => 'failed'];
        }
        $config = Config::getInstance();
        $config->lock();
        try {
            $model = new \OPNsense\Zapret\Zapret();
            $nodes = $model->getNodes();
            return [
                'zapret' => $nodes,
                'snapshot' => VoiceSettingsSnapshot::digest($nodes),
            ];
        } finally {
            $config->unlock();
        }
    }

    public function validateAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'POST request required'
            ]];
        }
        $fields = $this->request->getPost('zapret');
        if (!is_array($fields)) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'Missing Voice form'
            ]];
        }
        $config = Config::getInstance();
        $config->lock();
        try {
            $model = new \OPNsense\Zapret\Zapret();
            $current = $model->getNodes();
            $sync = $fields['sync'] ?? null;
            if (!is_array($sync) || array_keys($sync) !== ['snapshot']) {
                throw new \InvalidArgumentException('Voice configuration baseline is missing. Reload the Voice page.');
            }
            VoiceSettingsSnapshot::requireFresh($current, $sync['snapshot']);
            unset($fields['sync']);
            // Strict form ownership applies to validation as well as future
            // Apply; no unrelated model fields can be submitted.
            VoiceSettingsPayload::overlay($current, $fields);
            $errors = VoiceCandidateValidator::check($fields);
            if ($errors) {
                return ['result' => 'failed', 'validations' => $errors];
            }
            // This is an observation, not a promise that a future Apply will
            // succeed. The authoritative candidate and runtime are untouched.
            return ['result' => 'validated', 'scope' => 'syntax-only'];
        } catch (\InvalidArgumentException $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => $error->getMessage()
            ]];
        } catch (\Throwable $error) {
            // Never reveal PHP stack, unrelated configuration or raw input.
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'Voice validation failed'
            ]];
        } finally {
            $config->unlock();
        }
    }

    public function inspectAction(): array
    {
        if (!$this->request->isPost()) {
            return ['state' => 'inspection-error', 'can_activate' => false,
                    'remedy' => 'post-required'];
        }
        $backend = new Backend();
        $output = trim((string)$backend->configdRun('zapret voice_inspect', false, 20));
        $payload = json_decode($output, true);
        if (!is_array($payload) ||
            !isset($payload['state']) ||
            !is_string($payload['state']) ||
            !array_key_exists('can_activate', $payload) ||
            !is_bool($payload['can_activate'])
        ) {
            return ['state' => 'inspection-error', 'can_activate' => false,
                    'remedy' => 'status-unavailable'];
        }
        // The backend only emits known sanitized status fields. Never expose
        // raw configd output or an arbitrary kernel failure message to GUI.
        $allowed = [
            'ready', 'uninitialized', 'interrupted', 'mismatched-range',
            'foreign-or-modified-rules', 'foreign-or-modified-table',
            'orphan-stage-table', 'inspection-error',
        ];
        if (!in_array($payload['state'], $allowed, true)) {
            return ['state' => 'inspection-error', 'can_activate' => false,
                    'remedy' => 'invalid-status'];
        }
        return [
            'state' => $payload['state'],
            'can_activate' => $payload['can_activate'] === true,
            'condition' => (string)($payload['condition'] ?? ''),
            'service' => (string)($payload['service'] ?? ''),
            'rule_count' => (int)($payload['rule_count'] ?? 0),
            'table_count' => (int)($payload['table_count'] ?? 0),
        ];
    }
}
