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
use OPNsense\Base\UserException;
use OPNsense\Core\Backend;

class ServiceController extends ApiMutableServiceControllerBase
{
    protected static $internalServiceClass = '\OPNsense\Zapret\Zapret';
    protected static $internalServiceTemplate = 'OPNsense/Zapret';
    protected static $internalServiceEnabled = 'general.enabled';
    protected static $internalServiceName = 'zapret';

    private const RELEASE_PATTERN = '/^v[0-9]+(?:\\.[0-9]+)+$/D';

    private function getReleaseList(Backend $backend): array
    {
        $response = trim((string)$backend->configdRun('zapret setup_releases', false, 90));
        $releases = [];

        foreach (preg_split('/\\R/u', $response) as $release) {
            $release = trim($release);
            if ($release !== '' && preg_match(self::RELEASE_PATTERN, $release)) {
                $releases[] = $release;
            }
        }

        $releases = array_values(array_unique($releases));
        if (empty($releases)) {
            throw new \RuntimeException('no stable bol-van/zapret2 releases were returned');
        }

        return array_slice($releases, 0, 4);
    }

    private function getRuntimeState(Backend $backend): array
    {
        $response = trim((string)$backend->configdRun('zapret setup_status', false, 30));
        $state = [
            'installed' => false,
            'service' => 'error',
            'version' => '',
            'setup' => 'unknown',
            'busy' => false,
        ];

        foreach (preg_split('/\\R/u', $response) as $line) {
            if (!preg_match('/^([a-z]+)=(.*)$/D', trim($line), $matches)) {
                continue;
            }

            switch ($matches[1]) {
                case 'installed':
                    $state['installed'] = $matches[2] === '1';
                    break;
                case 'service':
                    if (in_array($matches[2], ['started', 'stopped', 'error'], true)) {
                        $state['service'] = $matches[2];
                    }
                    break;
                case 'version':
                    if ($matches[2] === '' || preg_match(self::RELEASE_PATTERN, $matches[2])) {
                        $state['version'] = $matches[2];
                    }
                    break;
                case 'setup':
                    if (in_array($matches[2], ['ready', 'installing', 'failed', 'unknown'], true)) {
                        $state['setup'] = $matches[2];
                    }
                    break;
                case 'busy':
                    $state['busy'] = $matches[2] === '1';
                    break;
            }
        }

        if (!$state['installed']) {
            $state['service'] = 'error';
            $state['version'] = '';
        }

        return $state;
    }

    public function releasesAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }

        try {
            return [
                'status' => 'ok',
                'releases' => $this->getReleaseList(new Backend()),
            ];
        } catch (\Throwable $exception) {
            return [
                'status' => 'unavailable',
                'releases' => [],
            ];
        }
    }

    public function runtimeAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }

        return array_merge(['status' => 'ok'], $this->getRuntimeState(new Backend()));
    }

    public function installAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }

        $version = trim((string)$this->request->getPost('version'));
        if (!preg_match(self::RELEASE_PATTERN, $version)) {
            throw new UserException(
                gettext('Select a valid published bol-van/zapret2 release.'),
                gettext('Zapret2 release error')
            );
        }

        $backend = new Backend();
        try {
            $releases = $this->getReleaseList($backend);
        } catch (\Throwable $exception) {
            throw new UserException(
                gettext('No stable bol-van/zapret2 releases could be obtained.'),
                gettext('Zapret2 release error')
            );
        }

        if (!in_array($version, $releases, true)) {
            throw new UserException(
                gettext('The selected bol-van/zapret2 release is no longer available.'),
                gettext('Zapret2 release error')
            );
        }

        if ($this->getRuntimeState($backend)['busy']) {
            throw new UserException(
                gettext('A zapret2 runtime operation is already in progress.'),
                gettext('Zapret2 runtime busy')
            );
        }

        $response = trim((string)$backend->configdpRun(
            'zapret setup_install',
            [$version],
            false,
            30
        ));
        if ($response !== 'OK') {
            throw new UserException(
                gettext('The zapret2 runtime operation could not be started.'),
                gettext('Zapret2 setup error')
            );
        }

        return [
            'status' => 'ok',
            'version' => $version,
        ];
    }

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
            throw new UserException(
                $messae,
                gettext('Zapret configuration error')
            );
        }

        return ['status' => 'ok', 'response' => $response];
    }
}
