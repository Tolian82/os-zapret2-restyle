<?php

/**
 * Copyright (C) 2026 Umur Gorur
 * All rights reserved.
 */

namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;

class StrategyLabController extends ApiControllerBase
{
    private const JOB_PATTERN = '/^job\.[A-Za-z0-9]+$/D';
    private const UDP_PAYLOAD_MAX_BYTES = 4096;
    private const UDP_PAYLOAD_MAX_BASE64_LENGTH = 5464;

    private function backendResponse(string $action, array $params = [], int $timeout = 10): array
    {
        $backend = new \OPNsense\Core\Backend();
        $response = trim((string)$backend->configdpRun(
            'zapret ' . $action,
            $params,
            false,
            $timeout
        ));

        if ($response === '') {
            return ['status' => 'error', 'message' => 'Strategy Lab returned no output.'];
        }

        $decoded = json_decode($response, true);
        if (!is_array($decoded)) {
            return ['status' => 'error', 'message' => 'Strategy Lab returned invalid output.'];
        }

        return $decoded;
    }

    private function jobId(): string
    {
        $jobId = trim((string)$this->request->getPost('job_id', 'striptags', ''));
        return preg_match(self::JOB_PATTERN, $jobId) ? $jobId : '';
    }

    private function domainTarget(): string
    {
        $target = strtolower(trim((string)$this->request->getPost('target', 'striptags', '')));
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

        $target = $this->domainTarget();
        $mode = trim((string)$this->request->getPost('mode', 'striptags', 'standard'));
        $language = trim((string)$this->request->getPost('language', 'striptags', 'en'));

        if ($target === '') {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab domain.'];
        }
        if (!in_array($mode, ['standard', 'extended'], true)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab mode.'];
        }
        if (!in_array($language, ['en', 'ru'], true)) {
            $language = 'en';
        }

        $udpInput = $this->udpInput($mode);
        if ($udpInput['status'] !== 'ok') {
            return $udpInput;
        }

        return $this->backendResponse('strategy_lab_start', [
            $target,
            $mode,
            $language,
            $udpInput['port'],
            $udpInput['payload']
        ]);
    }

    public function statusAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $jobId = $this->jobId();
        return $this->backendResponse('strategy_lab_status', [$jobId !== '' ? $jobId : '-']);
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
