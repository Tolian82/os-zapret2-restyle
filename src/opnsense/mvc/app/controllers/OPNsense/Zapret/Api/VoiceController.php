<?php

/**
 * Read-only Voice status endpoint. No Apply/Save method is present until
 * the shared transactional runtime has been qualified.
 */
namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

require_once __DIR__ . '/VoiceCandidateValidator.php';

class VoiceController extends ApiControllerBase
{
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
        try {
            $errors = VoiceCandidateValidator::check($fields);
            if ($errors) {
                return ['result' => 'failed', 'validations' => $errors];
            }
            return ['result' => 'validated', 'scope' => 'syntax-only'];
        } catch (\\Throwable $error) {
            // Never reveal PHP stack, unrelated configuration or raw input.
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'Voice validation failed'
            ]];
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
