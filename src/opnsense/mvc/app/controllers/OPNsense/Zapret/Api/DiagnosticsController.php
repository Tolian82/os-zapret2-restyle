<?php

/**
 * Copyright (C) 2026 Umur Gorur
 * All rights reserved.
 */

namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiControllerBase;

class DiagnosticsController extends ApiControllerBase
{
    public function testdomainAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $domain = trim((string)$this->request->getPost('domain', 'striptags', ''));
        if ($domain === '' || !preg_match('/^[a-zA-Z0-9.\-]+$/D', $domain)) {
            return ['status' => 'error', 'message' => 'Invalid domain name.'];
        }

        $backend = new \OPNsense\Core\Backend();
        $response = (string)$backend->configdpRun('zapret testdomain', [$domain]);
        if (trim($response) === '') {
            return [
                'status' => 'error',
                'message' => 'Domain connectivity test returned no output.'
            ];
        }

        return ['status' => 'ok', 'result' => $response];
    }
}
