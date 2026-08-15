<?php

/**
 * Copyright (C) 2026 Umur Gorur
 * All rights reserved.
 */

namespace OPNsense\Zapret\Api;

use OPNsense\Base\ApiMutableModelControllerBase;
use OPNsense\Core\Config;

class StrategyLabSettingsController extends ApiMutableModelControllerBase
{
    protected static $internalModelName = 'zapret';
    protected static $internalModelClass = '\\OPNsense\\Zapret\\Zapret';

    public function quicAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required.'];
        }

        $model = $this->getModel();
        $raw = trim((string)$this->request->getPost('enabled', 'striptags', ''));
        if ($raw === '') {
            return [
                'status' => 'ok',
                'enabled' => (string)$model->strategylab->enablequic === '1'
            ];
        }
        if (!in_array($raw, ['0', '1'], true)) {
            return ['status' => 'error', 'message' => 'Invalid Strategy Lab QUIC setting.'];
        }

        $config = Config::getInstance();
        $config->lock();
        try {
            $model->strategylab->enablequic = $raw;
            $this->setSaveAuditMessage(gettext('Updated Strategy Lab QUIC preference'));
            $this->save(false, true);
        } finally {
            $config->unlock();
        }

        return ['status' => 'ok', 'enabled' => $raw === '1'];
    }
}
