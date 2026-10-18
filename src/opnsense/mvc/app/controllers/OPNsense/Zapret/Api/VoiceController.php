<?php

/**
 * Native Voice validation, inactive drafts and one shared ON/OFF Apply.
 * The existing original-FD9 Strategies/Voice worker owns the runtime/IPFW transaction.
 */
namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;
use OPNsense\Core\Config;

require_once __DIR__ . '/VoiceCandidateValidator.php';
require_once __DIR__ . '/VoiceSettingsSnapshot.php';
require_once __DIR__ . '/VoiceSettingsPayload.php';
require_once __DIR__ . '/SettingsApply.php';
require_once __DIR__ . '/SharedApplyEnvelope.php';
require_once __DIR__ . '/VoiceCandidateXml.php';
require_once __DIR__ . '/VoiceDraftSelection.php';

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
        $validationStage = 'model';
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
            $validationStage = 'model';
            $plan = SettingsApply::prepareVoice($current, $fields, $sync['snapshot']);
            if ($plan['result'] !== 'prepared') {
                return $plan;
            }
            // Render a real detached OPNsense XML candidate in memory while
            // Config::lock() protects the source generation. Never call
            // setNodes(), serializeToConfig() or Config::save() here: Voice
            // ON must not enter the live XML ahead of original FD9 cutover.
            $validationStage = 'candidate-xml';
            $candidateXml = VoiceCandidateXml::render(
                (string)$config, $current, $plan['candidate'], $plan['changed_fields']
            );
            return [
                'result' => 'validated',
                'scope' => 'detached-xml-preview-only',
                'change_count' => count($plan['changed_fields']),
                'candidate_xml_sha256' => hash('sha256', $candidateXml),
                // This hash is a planning witness, not an Apply authority.
                'applied' => false,
            ];
        } catch (\InvalidArgumentException $error) {
            $safe = [
                'Voice configuration baseline is missing. Reload the Voice page.',
                'Voice or shared Strategies settings changed in another tab. Reload the Voice page.',
            ];
            if (in_array($error->getMessage(), $safe, true)) {
                return ['result' => 'failed', 'validations' => [
                    'zapret.voice.waninterface' => $error->getMessage()
                ]];
            }
            error_log(sprintf('Zapret Voice validation rejection stage=%s type=%s',
                $validationStage, get_class($error)));
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' =>
                    'Voice validation preflight rejected (' . $validationStage . ')'
            ]];
        } catch (\Throwable $error) {
            // No raw PHP exception/Config/user fields in the public API.
            error_log(sprintf('Zapret Voice validation error stage=%s type=%s',
                $validationStage, get_class($error)));
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' =>
                    'Voice validation preflight rejected (' . $validationStage . ')'
            ]];
        } finally {
            $config->unlock();
        }
    }

    /**
     * Read-only full native saved-draft preflight, under ONE original FD9
     * and ONE original Config inode flock in the installed backend.
     *
     * No XML/secret or arbitrary path travels through configd. PHP releases
     * its own Config::lock before acquiring FD9 in configd (no lock inversion).
     * This method CANNOT prepare PREPARED or mutate runtime/IPFW/Config.
     */
    protected function originalConfigDigest(): string
    {
        return VoiceDraftSelection::digestOriginalConfig();
    }

    public function previewDraftAction(): array
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
            $saved = $model->getNodes();
            $sync = $fields['sync'] ?? null;
            if (!is_array($sync) || array_keys($sync) !== ['snapshot']) {
                throw new \InvalidArgumentException(
                    'Voice configuration baseline is missing. Reload the Voice page.'
                );
            }
            unset($fields['sync']);
            $selection = VoiceDraftSelection::plan($saved, $fields, $sync['snapshot']);
            if (($selection['result'] ?? null) !== 'eligible') {
                return $selection;
            }
            // This is the exact BYTES hash read again by the root-only
            // backend while holding FD9 and the original on-disk inode.
            $digest = $this->originalConfigDigest();
            $mask = $selection['mask'];
            $count = $selection['selected_count'];
        } catch (\InvalidArgumentException $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => $error->getMessage()
            ]];
        } catch (\Throwable $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => 'Saved native Voice preview unavailable'
            ]];
        } finally {
            $config->unlock();
        }
        // Never hold PHP Config::lock across configd: backend obtains FD9
        // first, then its own lock of the ORIGINAL Config inode. The digest
        // pins the exact previous generation across that lock handoff.
        try {
            $backend = new Backend();
            $raw = trim((string)$backend->configdpRun(
                'zapret voice_preview_draft', [$mask, $digest], false, 40
            ));
            $report = json_decode($raw, true);
            if (!is_array($report) ||
                ($report['state'] ?? null) !== 'native-voice-saved-draft-preview' ||
                ($report['selected_profiles'] ?? null) !== $count ||
                ($report['safe_to_enable_voice'] ?? null) !== false ||
                ($report['public_voice_apply'] ?? null) !== false ||
                !isset($report['saved_xml_sha256']) ||
                !is_string($report['saved_xml_sha256']) ||
                !preg_match('/^[0-9a-f]{64}$/D', $report['saved_xml_sha256'])
            ) {
                throw new \RuntimeException('invalid native Voice preflight result');
            }
            return [
                'result' => 'previewed',
                'selected_profiles' => $count,
                'candidate_xml_sha256' => $report['saved_xml_sha256'],
                'saved' => false,
                'prepared' => false,
                'applied' => false,
            ];
        } catch (\Throwable $error) {
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' =>
                    'Saved Voice drafts or Config generation changed; reload and retry'
            ]];
        }
    }

    /**
     * Persist editable Voice drafts while ALL native Voice services remain
     * OFF. This is the first real write path for the Voice GUI, but is NOT
     * Apply: it never invokes configd, dvtws2, IPFW or a service restart.
     *
     * Saving ON through this draft-only path would bypass shared Apply;
     * enabled profiles use applyAction with native runtime commit.
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
        // From serialization onward even InvalidArgumentException is an
        // uncertain write, not a safe pre-write form validation failure.
        $draftWriteStarted = false;
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
            $plan = SettingsApply::prepareVoice($current, $fields, $sync['snapshot']);
            if ($plan['result'] !== 'prepared') {
                return $plan;
            }

            // Draft-only persistence must not change any native ON selection:
            // the shared Apply worker must commit Config, runtime and IPFW together.
            foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
                if (($plan['candidate']['voice'][$service]['enabled'] ?? '0') !== '0' ||
                    ($current['voice'][$service]['enabled'] ?? '0') !== '0'
                ) {
                    return ['result' => 'failed', 'validations' => [
                        'zapret.voice.' . $service . '.enabled' =>
                            'Save inactive draft requires all Voice services OFF; use Apply to change active profiles'
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
                // Keep this marker through Config::save and the post-save
                // digest; either may throw after a durable write.
                $draftWriteStarted = true;
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
            if ($draftWriteStarted) {
                // The exception class does not prove a pre-write rejection:
                // Config::save or the post-save digest may already have run.
                return ['result' => 'failed', 'requires_review' => true, 'validations' => [
                    'zapret.voice.waninterface' => 'Voice draft could not be saved'
                ]];
            }
            return ['result' => 'failed', 'validations' => [
                'zapret.voice.waninterface' => $error->getMessage()
            ]];
        } catch (\Throwable $error) {
            // Serialization or Config::save may have changed persistent
            // settings before a subsequent error. An indeterminate write
            // requires a fresh Config load, never an automatic retry.
            return ['result' => 'failed', 'requires_review' => true, 'validations' => [
                'zapret.voice.waninterface' => 'Voice draft could not be saved'
            ]];
        } finally {
            $config->unlock();
        }
    }

    /**
     * The unchanged Voice Apply action now uses the same native
     * Strategies/Voice Config/runtime/IPFW transaction under original FD9.
     * Never save Voice ON ahead of runtime. GUI Config lock is released
     * before configd takes FD9; root worker reloads and validates again.
     */
    public function applyAction(): array
    {
        $failed = static function (string $message, bool $review = false): array {
            return [
                'result' => 'failed',
                'applied' => false,
                'requires_review' => $review,
                'validations' => ['zapret.voice.waninterface' => $message],
            ];
        };
        if (!$this->request->isPost()) {
            return $failed('POST request required');
        }
        $post = $this->request->getPost('zapret');
        if (!is_array($post)) {
            return $failed('Missing Voice form');
        }
        $this->throwReadOnly();
        // After dispatch to the privileged worker, even an exception that
        // looks like invalid user input cannot prove that Config/runtime/IPFW
        // were untouched. Pre-dispatch validation keeps its normal errors.
        $nativeApplyDispatched = false;
        // Stable, non-sensitive stage labels for errors BEFORE FD9. Do not
        // print Config, submitted arguments or PHP exception text to the GUI.
        $preflightStage = 'guard';
        try {
            $backend = new Backend();
            $guard = json_decode(trim((string)$backend->configdRun('zapret strategy_lab_guard')), true);
            if (!is_array($guard) || ($guard['busy'] ?? true) !== false) {
                return $failed('Zapret lifecycle is busy; retry after diagnostics finish');
            }
            $sync = $post['sync'] ?? null;
            if (!is_array($sync) || array_keys($sync) !== ['snapshot']) {
                return $failed('Voice configuration baseline is missing; reload this page');
            }
            $fields = $post;
            unset($fields['sync']);
            $preflightStage = 'model';
            $config = Config::getInstance();
            $config->lock();
            try {
                $current = (new \OPNsense\Zapret\Zapret())->getNodes();
                $plan = SettingsApply::prepareVoice($current, $fields, $sync['snapshot']);
                if (($plan['result'] ?? null) !== 'prepared') {
                    return $plan;
                }
                // Keep the original native model XML validation before FD9.
                // Root repeats it from a freshly loaded Config snapshot.
                $preflightStage = 'candidate-xml';
                SettingsApply::renderCandidateXml(
                    (string)$config, $current, $plan, 'voice'
                );
                $preflightStage = 'envelope';
                $encoded = SharedApplyEnvelope::encode('voice', $fields, $sync);
            } finally {
                $config->unlock();
            }
            $nativeApplyDispatched = true;
            $output = trim((string)$backend->configdpRun(
                'zapret shared_apply', ['voice', $encoded], false, 600
            ));
            if (preg_match('/^preflight-rejected=(root-gate|bootstrap|model|decode|candidate|candidate-plan|candidate-validation|candidate-xml|candidate-size|workspace|render|runtime-build|seal)$/D', $output, $match)) {
                // The one FD9 worker explicitly attests failure before the
                // shared transaction. Do not classify this as an unknown
                // post-activation result or freeze editable Voice settings.
                return $failed('Native Voice preflight rejected before runtime (' . $match[1] . ')');
            }
            if (!preg_match('/(?:^|\n)applied-id=([a-f0-9]{32})$/D', $output)) {
                return $failed(
                    'Native Voice Apply was not confirmed; inspect Zapret runtime and recovery status',
                    true
                );
            }
            // Persisted snapshot was rechecked in native Config after save.
            return [
                'result' => 'saved',
                'applied' => true,
                'change_count' => count($plan['changed_fields']),
                'snapshot' => VoiceSettingsSnapshot::digest($plan['candidate']),
            ];
        } catch (\InvalidArgumentException $error) {
            if ($nativeApplyDispatched) {
                return $failed(
                    'Native Voice Apply result is uncertain; inspect the shared service state before retrying',
                    true
                );
            }
            // Known user form errors remain specific. Candidate XML
            // boundary errors are internal, not an instruction to re-Apply.
            $safeMessages = [
                'Voice configuration baseline is missing; reload this page',
                'Voice or shared Strategies settings changed in another tab. Reload the Voice page.',
                'Strategies WAN must be configured before Voice',
                'Independent Voice WAN cannot be isolated by the shared engine yet; select the Strategies WAN',
            ];
            if (in_array($error->getMessage(), $safeMessages, true)) {
                return $failed($error->getMessage());
            }
            error_log(sprintf('Zapret Voice pre-Apply rejection stage=%s type=%s',
                $preflightStage, get_class($error)));
            return $failed('Voice preflight rejected before native Apply (' . $preflightStage . ')');
        } catch (\Throwable $error) {
            if (!$nativeApplyDispatched) {
                // A PHP/Config/model failure before configdpRun cannot have
                // executed the shared native transaction. Never mislabel it
                // "result unknown" or freeze editable form state.
                error_log(sprintf('Zapret Voice pre-Apply error stage=%s type=%s',
                    $preflightStage, get_class($error)));
                return $failed('Voice preflight rejected before native Apply (' . $preflightStage . ')');
            }
            return $failed(
                'Native Voice Apply failed or was interrupted; inspect the shared service state before retrying',
                true
            );
        }
    }

    public function inspectAction(): array
    {
        if (!$this->request->isPost()) {
            return ['state' => 'inspection-error', 'can_activate' => false,
                    'remedy' => 'post-required'];
        }
        try {
            // A failed read-only configd status query must not throw a GUI
            // 500 or imply that the native Voice runtime is usable.
            $backend = new Backend();
            $output = trim((string)$backend->configdRun('zapret voice_inspect', false, 20));
            $payload = json_decode($output, true);
        } catch (\Throwable $error) {
            return ['state' => 'inspection-error', 'can_activate' => false,
                    'remedy' => 'status-unavailable'];
        }
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
            'ready', 'stopped', 'uninitialized', 'interrupted', 'mismatched-range',
            'foreign-or-modified-rules', 'foreign-or-modified-table',
            'orphan-stage-table', 'inspection-error',
        ];
        if (!in_array($payload['state'], $allowed, true)) {
            return ['state' => 'inspection-error', 'can_activate' => false,
                    'remedy' => 'invalid-status'];
        }
        $result = [
            'state' => $payload['state'],
            'can_activate' => $payload['can_activate'] === true,
            'condition' => (string)($payload['condition'] ?? ''),
            'service' => (string)($payload['service'] ?? ''),
            'rule_count' => (int)($payload['rule_count'] ?? 0),
            'table_count' => (int)($payload['table_count'] ?? 0),
        ];
        // Ready/stopped is only a verified status when the shared owner
        // really is native-common. Do not return an unqualified "ready"
        // (even without profiles) to other API callers when a foreign
        // inspector or incomplete report claims a successful runtime.
        if (in_array($payload['state'], ['ready', 'stopped'], true) &&
            ($payload['source'] ?? null) !== 'native-common') {
            return ['state' => 'interrupted', 'can_activate' => false,
                    'condition' => 'common-profile-unverified'];
        }
        // Only a committed native-common owner may associate five runtime
        // profiles with saved Voice checkboxes. The read-only inspector
        // witnessed exact release bytes, processes and kernel IPFW; confirm
        // its SEALED candidate digest against freshly locked native Config.
        // A stale browser form, standalone legacy ledger, or incomplete
        // native operation can never fabricate an active service.
        if (in_array($payload['state'], ['ready', 'stopped'], true) &&
            ($payload['source'] ?? null) === 'native-common') {
            try {
                $config = Config::getInstance();
                $config->lock();
                try {
                    $current = (new \OPNsense\Zapret\Zapret())->getNodes();
                    $savedDigest = VoiceSettingsSnapshot::digest($current);
                } finally {
                    $config->unlock();
                }
                $committedDigest = $payload['config_digest'] ?? null;
                if (!is_string($committedDigest) ||
                    !preg_match('/^[a-f0-9]{64}$/D', $committedDigest) ||
                    !hash_equals($committedDigest, $savedDigest)) {
                    return [
                        'state' => 'interrupted', 'can_activate' => false,
                        'condition' => 'common-config-mismatch',
                    ];
                }
                $runtime = $payload['runtime'] ?? null;
                $services = is_array($runtime) ? ($runtime['services'] ?? null) : null;
                $expectedState = $payload['state'] === 'ready' ? 'running' : 'stopped';
                if (!is_array($runtime) || !is_array($services) ||
                    ($runtime['state'] ?? null) !== $expectedState ||
                    ($runtime['source_verified'] ?? null) !== true ||
                    ($runtime['engine_verified'] ?? null) !== ($expectedState === 'running') ||
                    ($runtime['supervisor_verified'] ?? null) !== ($expectedState === 'running')) {
                    return [
                        'state' => 'interrupted', 'can_activate' => false,
                        'condition' => 'common-profile-unverified',
                    ];
                }
                $result['profiles'] = [];
                $seenRules = [];
                foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $name) {
                    $enabled = ($current['voice'][$name]['enabled'] ?? '0') === '1';
                    $report = $services[$name] ?? null;
                    if (!is_array($report) ||
                        !is_bool($report['configured'] ?? null) ||
                        !is_bool($report['capture_verified'] ?? null) ||
                        !is_string($report['runtime_state'] ?? null)) {
                        return [
                            'state' => 'interrupted', 'can_activate' => false,
                            'condition' => 'common-profile-unverified',
                        ];
                    }
                    $configured = $report['configured'];
                    $expectedProfileState = $enabled
                        ? ($expectedState === 'running' ? 'engine-present' : 'engine-not-confirmed')
                        : 'disabled';
                    if ($configured !== $enabled ||
                        $report['capture_verified'] !== $enabled ||
                        $report['runtime_state'] !== $expectedProfileState) {
                        return [
                            'state' => 'interrupted', 'can_activate' => false,
                            'condition' => 'common-profile-unverified',
                        ];
                    }
                    $status = [
                        'saved_enabled' => $enabled,
                        'runtime' => !$enabled ? 'disabled' :
                            ($expectedState === 'running' ? 'active' : 'stopped'),
                        // Readiness of engine/IPFW is never evidence of a
                        // STUN response, media passage, or a working call.
                        'media_verified' => false,
                        'call_verified' => false,
                    ];
                    if ($enabled) {
                        $id = $report['profile_id'] ?? null;
                        $revision = $report['profile_revision'] ?? null;
                        $wan = $report['wan'] ?? null;
                        $ports = $report['udp_ports'] ?? null;
                        $count = $report['ipset_entries'] ?? null;
                        if ($id !== 'voice-' . $name ||
                            !is_string($revision) ||
                            !preg_match('/^[a-f0-9]{12}$/D', $revision) ||
                            !is_string($wan) ||
                            !preg_match('/^[A-Za-z][A-Za-z0-9_.:-]{0,63}$/D', $wan) ||
                            !is_string($ports) || strlen($ports) > 1024 ||
                            !preg_match('/^[0-9,-]{1,1024}$/D', $ports) ||
                            !is_int($count) || $count < 1 || $count > 4096) {
                            return [
                                'state' => 'interrupted', 'can_activate' => false,
                                'condition' => 'common-profile-unverified',
                            ];
                        }
                        $status['profile_id'] = $id;
                        $status['profile_revision'] = $revision;
                        $status['wan'] = $wan;
                        $status['udp_ports'] = $ports;
                        $status['ipset_entries'] = $count;
                        // The shared inspector has already verified the
                        // sealed manifest and exact kernel IPFW rules. Only
                        // expose one uniquely owned live rule while RUNNING;
                        // stopped profiles retain their saved identity but
                        // have no installed IPFW rule or live counters.
                        if ($expectedState === 'running') {
                            $rule = $report['rule'] ?? null;
                            if (!is_int($rule) || $rule < 1 || $rule > 65534 ||
                                isset($seenRules[$rule])) {
                                return [
                                    'state' => 'interrupted', 'can_activate' => false,
                                    'condition' => 'common-profile-unverified',
                                ];
                            }
                            $seenRules[$rule] = true;
                            $status['rule'] = $rule;
                            // JS numbers above 2^53-1 may be rounded; omit
                            // unrepresentable counters rather than invent
                            // or truncate packets/bytes.
                            foreach (['rule_packets', 'rule_bytes'] as $counterName) {
                                $value = $report[$counterName] ?? null;
                                if (is_int($value) && $value >= 0 &&
                                    $value <= 9007199254740991) {
                                    $status[$counterName] = $value;
                                }
                            }
                        }
                    }
                    $result['profiles'][$name] = $status;
                }
            } catch (\Throwable $error) {
                return ['state' => 'inspection-error', 'can_activate' => false,
                        'remedy' => 'status-unavailable'];
            }
        }
        return $result;
    }
}
