<?php

/**
 * Copyright (C) 2026 Umur Gorur
 * All rights reserved.
 */

namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;
require_once __DIR__ . '/WanRequirement.php';

class StrategyLabController extends ApiControllerBase
{
    private const JOB_PATTERN = '/^job\.[A-Za-z0-9]+$/D';
    private const UDP_PAYLOAD_MAX_BYTES = 4096;
    private const UDP_PAYLOAD_MAX_BASE64_LENGTH = 5464;
    private const BACKEND_TIMEOUT_SECONDS = 190;

    /**
     * HTTP presentation of large Lab jobs. The complete authoritative job
     * remains in its original state/evidence files and configd/CLI output.
     * Never truncate disk evidence or omit stages, restoration or shortlist.
     */
    private static function compactLargeEvidence(array $value): array
    {
        $topLevel = [
            'status', 'schema', 'revision', 'job_id', 'state', 'outcome',
            'target', 'target_type', 'endpoints', 'network', 'baseline',
            'mode', 'language', 'ipv6_enabled', 'initial_service_state',
            'cancel_requested', 'cancel_requested_at', 'current_stage',
            'message', 'progress', 'stages', 'restoration', 'shortlist',
            'circular_eligible', 'circular_eligibility_reason',
            'circular_candidate_count', 'started_at', 'standard_deadline_at',
            'deadline_at', 'standard_budget_seconds', 'extended_budget_seconds',
            'search_budget_seconds', 'stage80_budget_seconds'
        ];
        $compact = array_intersect_key($value, array_fill_keys($topLevel, true));
        $summaries = [
            'candidate_smoke' => ['search_epoch_id', 'total', 'completed',
                                  'accepted', 'rejected', 'all_pass',
                                  'infrastructure_error', 'stopped_reason'],
            'parameter_expansion' => ['search_epoch_id', 'total_available',
                                      'completed', 'working', 'failed',
                                      'stopped_reason', 'partial', 'execution_model'],
            'stability' => ['search_epoch_id', 'completed', 'stable', 'unstable',
                            'stopped_reason', 'partial'],
            'family_screening' => ['total', 'completed', 'accepted', 'rejected'],
        ];
        foreach ($summaries as $name => $fields) {
            if (isset($value[$name]) && is_array($value[$name])) {
                $compact[$name] = array_intersect_key(
                    $value[$name], array_fill_keys($fields, true)
                );
            }
        }
        $compact['api_evidence_compacted'] = true;
        return $compact;
    }

    private function backendResponse(string $action, array $params = []): array
    {
        $backend = new \OPNsense\Core\Backend();
        $response = trim((string)$backend->configdpRun(
            'zapret ' . $action,
            $params,
            false,
            self::BACKEND_TIMEOUT_SECONDS
        ));

        if ($response === '') {
            return [
                'status' => 'error',
                'transient' => true,
                'message' => 'Strategy Lab returned no output.'
            ];
        }

        $decoded = json_decode($response, true);
        if (!is_array($decoded)) {
            return [
                'status' => 'error',
                'transient' => true,
                'message' => 'Strategy Lab returned invalid output.'
            ];
        }

        // A full Model C expansion can exceed the guest's reliable HTTP
        // chunked-response envelope. Preserve the exact CLI/disk evidence,
        // but render bounded job summaries through the existing GUI API.
        if (in_array($action, [
            'strategy_lab_status', 'strategy_lab_result', 'strategy_lab_cancel'
        ], true) && strlen($response) > 65536) {
            return self::compactLargeEvidence($decoded);
        }

        return $decoded;
    }

    private function jobId(): string
    {
        $jobId = trim((string)$this->request->getPost('job_id', 'striptags', ''));
        return preg_match(self::JOB_PATTERN, $jobId) ? $jobId : '';
    }

    private function domainValue(string $value): string
    {
        $target = strtolower(trim($value));
        if (substr($target, -1) === '.') {
            $target = substr($target, 0, -1);
        }
        if ($target === '' || strlen($target) > 253 || filter_var($target, FILTER_VALIDATE_IP) !== false) {
            return '';
        }

        $labels = explode('.', $target);
        if (count($labels) < 2) {
            return '';
        }
        foreach ($labels as $label) {
            if (
                strlen($label) < 1 || strlen($label) > 63 ||
                !preg_match('/^[a-z0-9-]+$/D', $label) ||
                $label[0] === '-' || substr($label, -1) === '-'
            ) {
                return '';
            }
        }
        if (!preg_match('/[a-z]/D', $labels[count($labels) - 1])) {
            return '';
        }

        return $target;
    }

    private function targetContract(): array
    {
        $raw = strtolower(trim((string)$this->request->getPost('target', 'striptags', '')));
        if ($raw === '') {
            return ['target' => '', 'type' => ''];
        }
        if (filter_var($raw, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) !== false) {
            return ['target' => $raw, 'type' => 'ip'];
        }
        if (filter_var($raw, FILTER_VALIDATE_IP, FILTER_FLAG_IPV6) !== false) {
            $canonical = inet_ntop(inet_pton($raw));
            return ['target' => $canonical, 'type' => 'ip'];
        }
        $domain = $this->domainValue($raw);
        return $domain !== '' ? ['target' => $domain, 'type' => 'domain'] : ['target' => '', 'type' => ''];
    }

    private function serviceHost(string $targetType): array
    {
        $raw = trim((string)$this->request->getPost('service_host', 'striptags', ''));
        if ($raw === '') {
            return ['status' => 'ok', 'value' => ''];
        }
        if ($targetType !== 'ip') {
            return ['status' => 'error', 'message' => 'Host / SNI is valid only for an IP Strategy Lab target.'];
        }
        $value = $this->domainValue($raw);
        if ($value === '') {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab Host / SNI.'];
        }
        return ['status' => 'ok', 'value' => $value];
    }

    private function udpInput(string $mode): array
    {
        $port = trim((string)$this->request->getPost('udp_port', 'striptags', ''));
        $payload = trim((string)$this->request->getPost('udp_payload_base64', 'striptags', ''));

        if ($port === '' && $payload === '') {
            return ['status' => 'ok', 'port' => '-', 'payload' => '-'];
        }
        if ($mode !== 'extended') {
            return [
                'status' => 'error',
                'message' => 'Generic UDP input is available only in extended mode.'
            ];
        }
        if ($port === '' || $payload === '') {
            return [
                'status' => 'error',
                'message' => 'Generic UDP requires both a port and a payload file.'
            ];
        }
        if (!preg_match('/^[0-9]+$/D', $port)) {
            return ['status' => 'error', 'message' => 'Invalid generic UDP port.'];
        }

        $portNumber = (int)$port;
        if ($portNumber < 1 || $portNumber > 65535) {
            return ['status' => 'error', 'message' => 'Invalid generic UDP port.'];
        }
        if (
            strlen($payload) > self::UDP_PAYLOAD_MAX_BASE64_LENGTH ||
            !preg_match('/^[A-Za-z0-9+\/]+={0,2}$/D', $payload) ||
            strlen($payload) % 4 !== 0
        ) {
            return ['status' => 'error', 'message' => 'Invalid generic UDP payload encoding.'];
        }

        $decoded = base64_decode($payload, true);
        if (
            $decoded === false ||
            $decoded === '' ||
            strlen($decoded) > self::UDP_PAYLOAD_MAX_BYTES ||
            base64_encode($decoded) !== $payload
        ) {
            return ['status' => 'error', 'message' => 'Invalid generic UDP payload file.'];
        }

        return ['status' => 'ok', 'port' => (string)$portNumber, 'payload' => $payload];
    }

    public function startAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        // Check the saved WAN first, before target, engine or Job validation.
        $wanLanguage = trim((string)$this->request->getPost('language', 'striptags', 'en'));
        $config = \OPNsense\Core\Config::getInstance();
        $config->lock();
        try {
            $wan = WanRequirement::effectiveWan((new \OPNsense\Zapret\Zapret())->getNodes());
        } finally {
            $config->unlock();
        }
        if ($wan === '') {
            return ['status' => 'error', 'reason' => 'wan-required',
                'message' => $wanLanguage === 'ru'
                    ? 'Укажите WAN интерфейс' : 'Select a WAN interface'];
        }
        // The existing native read-only preflight resolves the *saved* WAN.
        // No second mapping algorithm, and do not validate a Lab target or
        // create a Job before the selected interface and engine are ready.
        $wanProbe = trim((string)(new \OPNsense\Core\Backend())->configdRun(
            'zapret wan_preflight', false, 20
        ));
        if ($wanProbe === 'wan-required') {
            return ['status' => 'error', 'reason' => 'wan-required',
                'message' => $wanLanguage === 'ru'
                    ? 'Укажите WAN интерфейс' : 'Select a WAN interface'];
        }
        if ($wanProbe === 'wan-invalid') {
            return ['status' => 'error', 'reason' => 'wan-invalid',
                'message' => $wanLanguage === 'ru'
                    ? 'Выбранный WAN интерфейс недоступен'
                    : 'Selected WAN interface is not assigned or unavailable'];
        }
        if ($wanProbe !== 'wan-ready') {
            return ['status' => 'error', 'reason' => 'wan-unavailable',
                'message' => $wanLanguage === 'ru'
                    ? 'Проверка сохранённого WAN недоступна'
                    : 'Saved WAN preflight is unavailable'];
        }
        if (!is_executable('/usr/local/etc/zapret2/binaries/my/dvtws2')) {
            return ['status' => 'error', 'reason' => 'engine-not-installed',
                'message' => $wanLanguage === 'ru'
                    ? 'Служба zapret2 не установлена'
                    : 'The zapret2 service is not installed'];
        }
        $targetContract = $this->targetContract();
        $target = $targetContract['target'];
        $targetType = $targetContract['type'];
        $mode = trim((string)$this->request->getPost('mode', 'striptags', 'standard'));
        $language = trim((string)$this->request->getPost('language', 'striptags', 'en'));
        $enableQuic = trim((string)$this->request->getPost('enable_quic', 'striptags', '0'));
        $ipv6Enabled = trim((string)$this->request->getPost('ipv6_enabled', 'striptags', '0'));

        if ($target === '') {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab domain or IP address.'];
        }
        $serviceHost = $this->serviceHost($targetType);
        if ($serviceHost['status'] !== 'ok') {
            return $serviceHost;
        }
        if (!in_array($mode, ['standard', 'extended'], true)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab mode.'];
        }
        if (!in_array($language, ['en', 'ru'], true)) {
            $language = 'en';
        }
        if (!in_array($enableQuic, ['0', '1'], true)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab QUIC setting.'];
        }
        if (!in_array($ipv6Enabled, ['0', '1'], true)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab IPv6 setting.'];
        }

        if ($targetType === 'ip' && strpos($target, ':') !== false && $ipv6Enabled !== '1') {
            return ['status' => 'error', 'message' => $language === 'ru'
                ? 'Для проверки IPv6-адреса включите галочку IPv6.'
                : 'Enable IPv6 to test an IPv6 address.'];
        }

        $udpInput = $this->udpInput($mode);
        if ($udpInput['status'] !== 'ok') {
            return $udpInput;
        }

        return $this->backendResponse('strategy_lab_start', [
            $target,
            $mode,
            $language,
            $enableQuic,
            $udpInput['port'],
            $udpInput['payload'],
            $serviceHost['value'] !== '' ? $serviceHost['value'] : '-',
            $ipv6Enabled
        ]);
    }

    public function statusAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $jobId = $this->jobId();
        return $this->backendResponse('strategy_lab_status', [$jobId !== '' ? $jobId : '@active']);
    }

    public function cancelAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $jobId = $this->jobId();
        if ($jobId === '') {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab job id.'];
        }

        return $this->backendResponse('strategy_lab_cancel', [$jobId]);
    }

    public function resultAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $jobId = $this->jobId();
        if ($jobId === '') {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab job id.'];
        }

        return $this->backendResponse('strategy_lab_result', [$jobId]);
    }
}
