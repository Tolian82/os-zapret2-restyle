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

use OPNsense\Base\ApiMutableServiceControllerBase;
use OPNsense\Core\Backend;

class ServiceController extends ApiMutableServiceControllerBase
{
    protected static $internalServiceClass = '\OPNsense\Zapret\Zapret';
    protected static $internalServiceTemplate = 'OPNsense/Zapret';
    protected static $internalServiceEnabled = 'general.enabled';
    protected static $internalServiceName = 'zapret';
    /**
     * Build and validate a candidate release before replacing the live runtime.
     * Backend failures are translated to a user-visible OPNsense exception.
     */
    public function reconfigureAction()
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }

        $backend = new Backend();
        try {
            $response = trim((string)$backend->configdRun('zapret reconfigure', false, 180));
            if ($response !== 'OK') {
                throw new \RuntimeException(
                    'backend returned: ' . ($response !== '' ? $response : 'empty response')
                );
            }
        } catch (\Throwable $exception) {
            $message = gettext('The new configuration could not be applied. The previous runtime was kept or restored.');
            $stageFile = '/var/run/zapret2-execution.status';
            if (is_readable($stageFile)) {
                $record = trim((string)file_get_contents($stageFile));
                $parts = explode('|', $record, 6);
                if (count($parts) === 6 && $parts[3] === 'failed' && trim($parts[5]) !== '') {
                    $message = trim($parts[5]);
                }
            }
            throw new \OPNsense\Base\UserException(
                $message,
                gettext('Zapret configuration error')
            );
        }

        return ['status' => 'ok', 'response' => $response];
    }

}
