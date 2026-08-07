<?php

/**
 * Copyright (C) 2026 Umur Gorur
 * All rights reserved.
 */

namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;

class CircularController extends ApiControllerBase
{
    private const JOB_PATTERN = '/^job\.[A-Za-z0-9]+$/D';
    private const BACKEND_TIMEOUT_SECONDS = 190;

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
            return ['status' => 'error', 'message' => 'Circular validation returned no output.'];
        }

        $decoded = json_decode($response, true);
        if (!is_array($decoded)) {
            return ['status' => 'error', 'message' => 'Circular validation returned invalid output.'];
        }

        return $decoded;
    }

    public function startAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $jobId = trim((string)$this->request->getPost('job_id', 'striptags', ''));
        if (!preg_match(self::JOB_PATTERN, $jobId)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab job id.'];
        }

        return $this->backendResponse('strategy_lab_circular_start', [$jobId]);
    }

    public function statusAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        return $this->backendResponse('strategy_lab_circular_status');
    }

    public function stopAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        return $this->backendResponse('strategy_lab_circular_stop');
    }
}
