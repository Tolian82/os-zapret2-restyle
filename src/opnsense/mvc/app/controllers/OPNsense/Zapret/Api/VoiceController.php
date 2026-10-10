<?php

/**
 * Native Voice validation, diagnostics, and persistent inactive draft saves.
 * An ON profile still requires the unfinished whole-runtime Apply transaction.
 */
namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;
use OPNsense\Core\Config;

require_once __DIR__ . '/VoiceCandidateValidator.php';
require_once __DIR__ . '/VoiceSettingsSnapshot.php';
require_once __DIR__ . '/VoiceSettingsPayload.php';
require_once __DIR__ . '/VoiceApplyCandidate.php';

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
            unset($fields['sync']);
            // Build a normalized *in-memory* preview under the same Config
            // lock. The actual Save/Apply transaction must re-run this
            // entire preparation and the Python release compiler.
            $plan = VoiceApplyCandidate::prepare($current, $fields, $sync['snapshot']);
            if ($plan['result'] !== 'prepared') {
                return $plan;
            }
            return [
                'result' => 'validated',
                'scope' => 'syntax-only',
                'change_count' => count($plan['changed_fields']),
            ];
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

    /**
     * Persist editable Voice drafts while ALL native Voice services remain
     * OFF. This is the first real write path for the Voice GUI, but is NOT
     * Apply: it never invokes configd, dvtws2, IPFW or a service restart.
     *
     * Saving ON would make the existing staged-only runtime guard reject a
     * later reboot, so it MUST remain impossible until native cutover ships.
     */
    public function saveDraftAction(): array
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

        // ApiControllerBase protects privileged configuration writes. This
        // check MUST precede any model mutation or Config persistence.
        $this->throwReadOnly();
        $config = Config::getInstance();
        $config->lock();
        try {
            $model = new \OPNsense\Zapret\Zapret();
            $current = $model->getNodes();
            $sync = $fields['sync'] ?? null;
            if (!is_array($sync) || array_keys($sync) !== ['snapshot']) {
                throw new \InvalidArgumentException(
                    'Voice configuration baseline is missing. Reload the Voice page.'
                );
            }
            unset($fields['sync']);
            $plan = VoiceApplyCandidate::prepare($current, $fields, $sync['snapshot']);
            if ($plan['result'] !== 'prepared') {
                return $plan;
            }

            // Native Voice ON cannot be saved safely ahead of its runtime:
            // even the normal boot path would hit the staged-only guard.
            foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
                if (($plan['candidate']['voice'][$service]['enabled'] ?? '0') !== '0' ||
                    ($current['voice'][$service]['enabled'] ?? '0') !== '0'
                ) {
                    return ['result' => 'failed', 'validations' => [
                        'zapret.voice.' . $service . '.enabled' =>
                            'Voice activation is not available yet; save only disabled service drafts'
                    ]];
                }
            }

            if ($plan['changed_fields'] !== []) {
                $model->setNodes($plan['candidate']);
                $messages = $model->performValidation(false);
                if (count($messages) > 0) {
                    $validations = [];
                    foreach ($messages as $message) {
                        $validations['zapret.' . $message->getField()] = $message->getMessage();
                    }
                    return ['result' => 'failed', 'validations' => $validations];
                }
                // The same native OPNsense model persistence path as
                // SettingsController, without a second Voice state store.
                if (!$model->serializeToConfig(false, true)) {
                    throw new \RuntimeException('Unable to serialize Voice draft');
                }
                $config->save(['description' => gettext('Saved inactive Zapret Voice draft')]);
            }
            return [
                'result' => 'saved',
                'applied' => false,
                'change_count' => count($plan['changed_fields']),
                'snapshot' => VoiceSettingsSnapshot::digest($model->getNodes()),
            ];
        } catch (\InvalidArgumentException $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => $error->getMessage()
            ]];
        } catch (\Throwable $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'Voice draft could not be saved'
            ]];
        } finally {
            $config->unlock();
        }
    }

    /**
     * Apply an OFF-only Voice configuration using the actual existing Zapret
     * reconfigure action. Enabled Voice is still rejected until the one-engine
     * IPFW transaction exists. This updates the shared managed IPSETs used
     * by ordinary Strategies, without enabling a native Voice profile.
     */
    public function applyAction(): array
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
        $this->throwReadOnly();
        $backend = new Backend();
        // Refuse when Strategy Lab owns the runtime or the guard is unknown.
        $guard = json_decode(trim((string)$backend->configdRun('zapret strategy_lab_guard')), true);
        if (!is_array($guard) || ($guard['busy'] ?? true) !== false) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'Zapret lifecycle is busy; retry after diagnostics finish'
            ]];
        }
        $config = Config::getInstance();
        $config->lock();
        $model = new \OPNsense\Zapret\Zapret();
        try {
            $previous = $model->getNodes();
            $sync = $fields['sync'] ?? null;
            if (!is_array($sync) || array_keys($sync) !== ['snapshot']) {
                throw new \InvalidArgumentException(
                    'Voice configuration baseline is missing. Reload the Voice page.'
                );
            }
            unset($fields['sync']);
            $plan = VoiceApplyCandidate::prepare($previous, $fields, $sync['snapshot']);
            if ($plan['result'] !== 'prepared') {
                return $plan;
            }
            foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
                if (($plan['candidate']['voice'][$service]['enabled'] ?? '0') !== '0' ||
                    ($previous['voice'][$service]['enabled'] ?? '0') !== '0'
                ) {
                    return ['result' => 'failed', 'validations' => [
                        'zapret.voice.' . $service . '.enabled' =>
                            'Native Voice ON still needs the shared IPFW cutover; apply only OFF profiles'
                    ]];
                }
            }
            // Reject stale / changed runtime ownership before any Config write.
            $guard = json_decode(trim((string)$backend->configdRun('zapret strategy_lab_guard')), true);
            if (!is_array($guard) || ($guard['busy'] ?? true) !== false) {
                return ['result' => 'failed', 'validations' => [
                    'zapret.voice.waninterface' => 'Zapret lifecycle became busy before applying'
                ]];
            }
            // Reconfigure even for an unchanged draft: the earlier Save
            // Draft endpoint deliberately made NO runtime changes.
            if ($plan['changed_fields'] !== []) {
                $model->setNodes($plan['candidate']);
                $messages = $model->performValidation(false);
                if (count($messages) > 0) {
                    $validations = [];
                    foreach ($messages as $message) {
                        $validations['zapret.' . $message->getField()] = $message->getMessage();
                    }
                    return ['result' => 'failed', 'validations' => $validations];
                }
                if (!$model->serializeToConfig(false, true)) {
                    throw new \RuntimeException('Voice configuration serialization failed');
                }
                $config->save(['description' => gettext('Applied inactive Zapret Voice settings')]);
            }
        } catch (\InvalidArgumentException $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => $error->getMessage()
            ]];
        } catch (\Throwable $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'Voice settings could not be saved'
            ]];
        } finally {
            $config->unlock();
        }
        // Config.save() releases its flock internally. Never hold the
        // lifecycle FD9 while invoking configd: reconfigure acquires FD9.
        // Future ON Apply must replace this OFF-only path with one complete
        // transaction owner, not merely widen its checkbox condition.
        $response = trim((string)$backend->configdRun('zapret reconfigure', false, 180));
        if ($response !== 'OK') {
            // Do not falsely claim that the previous runtime is restored:
            // a failed reconfigure may already have partially changed it.
            // Preserve the saved state for explicit operator inspection.
            return [
                'result' => 'failed',
                'saved' => true,
                'applied' => false,
                'requires_review' => true,
                'snapshot' => VoiceSettingsSnapshot::digest($plan['candidate']),
                'validations' => [
                    'zapret.voice.waninterface' =>
                        'Settings saved, but Zapret reconfigure failed; inspect current runtime before retrying'
                ],
            ];
        }
        return [
            'result' => 'saved',
            'applied' => true,
            'change_count' => count($plan['changed_fields']),
            'snapshot' => VoiceSettingsSnapshot::digest($plan['candidate']),
        ];
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
