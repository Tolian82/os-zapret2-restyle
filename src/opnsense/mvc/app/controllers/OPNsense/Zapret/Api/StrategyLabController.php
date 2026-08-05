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
    private const TARGET_PATTERN = '/^[A-Za-z0-9][A-Za-z0-9.:-]{0,252}$/D';

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

    public function startAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $target = trim((string)$this->request->getPost('target', 'striptags', ''));
        $mode = trim((string)$this->request->getPost('mode', 'striptags', 'standard'));
        $language = trim((string)$this->request->getPost('language', 'striptags', 'en'));

        if (!preg_match(self::TARGET_PATTERN, $target)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab target.'];
        }
        if (!in_array($mode, ['standard', 'extended'], true)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab mode.'];
        }
        if (!in_array($language, ['en', 'ru'], true)) {
            $language = 'en';
        }

        return $this->backendResponse('strategy_lab_start', [$target, $mode, $language]);
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
