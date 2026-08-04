<?php

/**
 *    Copyright (C) 2026 Umur Gorur
 *    All rights reserved.
 *
 *    Redistribution and use in source and binary forms, with or without
 *    modification, are permitted provided that the following conditions are met:
 *
 *    1. Redistributions of source code must retain the above copyright notice,
 *       this list of conditions and the following disclaimer.
 *
 *    2. Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *
 *    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 *    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 *    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 *    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 *    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 *    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 *    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 *    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *    POSSIBILITY OF SUCH DAMAGE.
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
            return [
                'status' => 'error',
                'message' => 'Strategy Lab returned no output.'
            ];
        }

        $decoded = json_decode($response, true);
        if (!is_array($decoded)) {
            return [
                'status' => 'error',
                'message' => 'Strategy Lab returned invalid output.'
            ];
        }

        return $decoded;
    }

    private function jobId(): string
    {
        $jobId = trim((string)$this->request->getPost('job_id', 'striptags', ''));
        return preg_match(self::JOB_PATTERN, $jobId) ? $jobId : '';
    }

    /**
     * Start the dormant asynchronous Strategy Lab framework. The existing Blockcheck
     * button remains on the legacy Diagnostics path until the final migration patch.
     */
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

        return $this->backendResponse(
            'strategy_lab_start',
            [$target, $mode, $language]
        );
    }

    public function statusAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $jobId = $this->jobId();
        return $this->backendResponse(
            'strategy_lab_status',
            [$jobId !== '' ? $jobId : '-']
        );
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
