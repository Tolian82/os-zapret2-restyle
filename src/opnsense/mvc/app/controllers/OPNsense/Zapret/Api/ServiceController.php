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

    /**
     * Read-only status of manually installed Lua/BIN resources. No service
     * restarts or downloads are made by the status endpoint.
     */
    private function getExtraResourceState(Backend $backend): array
    {
        $response = trim((string)$backend->configdRun('zapret extra_resources_status', false, 20));
        $state = [
            'busy' => false,
            'phase' => 'unknown',
            'installed' => null,
            'operation' => '',
            'revision' => '',
            'lua' => 0,
            'bin' => 0,
            'detail' => '',
        ];
        foreach (preg_split('/\R/u', $response) as $line) {
            if (!preg_match('/^([a-z]+)=(.*)$/D', trim($line), $matches)) {
                continue;
            }
            $value = $matches[2];
            switch ($matches[1]) {
                case 'installed':
                    if ($value === '1' || $value === '0') {
                        $state['installed'] = $value === '1';
                    }
                    break;
                case 'busy':
                    $state['busy'] = $value === '1';
                    break;
                case 'operation':
                    if ($value === '' || preg_match('/^[a-f0-9]{32}$/D', $value)) {
                        $state['operation'] = $value;
                    }
                    break;
                case 'phase':
                    if (in_array($value, [
                        'unknown', 'downloading', 'verifying', 'installing',
                        'ready', 'failed', 'restore_failed', 'recovery_required',
                        'recovering', 'restored', 'no_recovery_needed',
                        'removing', 'not_installed'
                    ], true)) {
                        $state['phase'] = $value;
                    }
                    break;
                case 'revision':
                    if ($value === '' || preg_match('/^[a-f0-9]{40}$/D', $value)) {
                        $state['revision'] = $value;
                    }
                    break;
                case 'lua':
                case 'bin':
                    if (preg_match('/^[0-9]{1,5}$/D', $value) && (int)$value <= 10000) {
                        $state[$matches[1]] = (int)$value;
                    }
                    break;
                case 'detail':
                    $state['detail'] = substr($value, 0, 300);
                    break;
            }
        }
        return $state;
    }

    public function resourcesStatusAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }
        try {
            return array_merge(['status' => 'ok'], $this->getExtraResourceState(new Backend()));
        } catch (\Throwable $exception) {
            return ['status' => 'unavailable', 'busy' => true, 'phase' => 'unknown'];
        }
    }

    /**
     * Cached Lua/BIN names only. The configd action performs no Git or
     * directory scan; enumeration happens when resource sets change.
     */
    public function resourcesInventoryAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }
        try {
            $raw = (string)(new Backend())->configdRun(
                'zapret extra_resources_inventory', false, 10
            );
            if (strlen($raw) > 1048576) {
                throw new \RuntimeException('inventory cache response too large');
            }
            $data = json_decode(trim($raw), true);
            if (!is_array($data) || ($data['status'] ?? '') !== 'ok' ||
                !is_bool($data['installed'] ?? null)) {
                throw new \RuntimeException('inventory cache unavailable');
            }
            foreach (['lua', 'bin'] as $kind) {
                if (!isset($data[$kind]) || !is_array($data[$kind]) ||
                    count($data[$kind]) > 4096) {
                    throw new \RuntimeException('invalid inventory list');
                }
                $suffix = $kind === 'lua' ? 'lua' : 'bin';
                foreach ($data[$kind] as $entry) {
                    if (!is_array($entry) ||
                        !in_array($entry['origin'] ?? '', ['upstream', 'other'], true) ||
                        !is_string($entry['name'] ?? null) ||
                        !preg_match('/^[A-Za-z0-9_.+\\-]+\\.' . $suffix . '$/D', $entry['name'])) {
                        throw new \RuntimeException('invalid cached resource');
                    }
                }
            }
            return $data;
        } catch (\Throwable $exception) {
            return ['status' => 'unavailable'];
        }
    }

    /**
     * Read-only, owner-locked exact upstream HEAD Remove plan. Never an
     * authorization to mutate: the native common GUI Apply trial is not yet
     * connected, and the server explicitly returns ready=false.
     */
    public function resourcesRemovePlanAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }
        $backend = new Backend();
        $runtime = $this->getRuntimeState($backend);
        $extras = $this->getExtraResourceState($backend);
        if (!$runtime['installed'] || $runtime['service'] !== 'started' ||
            $runtime['busy'] || $extras['busy'] ||
            in_array($extras['phase'], ['restore_failed', 'recovery_required'], true)) {
            throw new UserException(
                gettext('Start Zapret2 and finish any pending runtime operation or recovery first.'),
                gettext('Additional Resources unavailable')
            );
        }
        $raw = trim((string)$backend->configdRun(
            'zapret extra_resources_remove_plan', false, 120
        ));
        $prefix = 'extra-resources-remove-plan=';
        if (strlen($raw) > 4096 || !str_starts_with($raw, $prefix)) {
            return ['status' => 'unavailable', 'ready' => false];
        }
        $plan = json_decode(substr($raw, strlen($prefix)), true);
        if (!is_array($plan) || ($plan['status'] ?? '') !== 'dry_run_only' ||
            ($plan['ready'] ?? null) !== false ||
            !is_string($plan['inventory_sha256'] ?? null) ||
            !preg_match('/^[a-f0-9]{64}$/D', $plan['inventory_sha256'])) {
            return ['status' => 'unavailable', 'ready' => false];
        }
        foreach (['lua', 'bin', 'total'] as $key) {
            if (!isset($plan[$key]) || !is_int($plan[$key]) ||
                $plan[$key] < 0 || $plan[$key] > 10000) {
                return ['status' => 'unavailable', 'ready' => false];
            }
        }
        if ($plan['lua'] + $plan['bin'] !== $plan['total']) {
            return ['status' => 'unavailable', 'ready' => false];
        }
        return [
            'status' => 'ok',
            'ready' => false,
            'lua' => $plan['lua'],
            'bin' => $plan['bin'],
            'total' => $plan['total'],
            'inventory_sha256' => $plan['inventory_sha256'],
        ];
    }


    /**
     * Authenticated POST only. The 64-hex plan digest binds the exact HEAD,
     * Lua/BIN inodes and full persisted Config generation. The confirmation
     * additionally names the positive number of files being deleted.
     * This is NOT the GUI handler; Stage 7 must add its own modal and polling.
     */
    public function resourcesRemoveAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }

        // A declined destructive request is not an internal server failure.
        // Return a predictable JSON receipt rather than throwing UserException
        // (the OPNsense API exception renderer gives those HTTP 500).
        $witness = $this->request->getPost('inventory_sha256');
        $confirmation = $this->request->getPost('confirmation');
        if (!is_string($witness) || !preg_match('/^[a-f0-9]{64}$/D', $witness) ||
            !is_string($confirmation) || strlen($confirmation) > 40) {
            return ['status' => 'rejected', 'started' => false,
                    'reason' => 'invalid_confirmation'];
        }

        $backend = new Backend();
        try {
            $runtime = $this->getRuntimeState($backend);
            $extras = $this->getExtraResourceState($backend);
            if (!$runtime['installed'] || $runtime['service'] !== 'started' ||
                $runtime['busy'] || $extras['busy'] ||
                in_array($extras['phase'], ['restore_failed', 'recovery_required'], true)) {
                return ['status' => 'rejected', 'started' => false,
                        'reason' => 'not_ready'];
            }

            // This must remain the existing native Git HEAD/Config/inode plan.
            // The worker repeats the same exact digest under setup.lock -> FD9.
            $plan = $this->resourcesRemovePlanAction();
        } catch (\Throwable $e) {
            // No configd mutation has been requested: fail closed.
            return ['status' => 'unavailable', 'started' => false,
                    'reason' => 'preflight_unavailable'];
        }

        if (($plan['status'] ?? '') !== 'ok') {
            return ['status' => 'unavailable', 'started' => false,
                    'reason' => 'preflight_unavailable'];
        }
        if (($plan['total'] ?? 0) < 1) {
            return ['status' => 'rejected', 'started' => false,
                    'reason' => 'nothing_to_remove'];
        }
        if (($plan['inventory_sha256'] ?? '') !== $witness ||
            $confirmation !== 'REMOVE ' . (string)$plan['total']) {
            return ['status' => 'rejected', 'started' => false,
                    'reason' => 'plan_changed'];
        }

        $operation = bin2hex(random_bytes(16));
        try {
            $response = trim((string)$backend->configdpRun(
                'zapret extra_resources_remove',
                [$operation, $witness, 'REMOVE_ADDITIONAL_RESOURCES'], false, 30
            ));
        } catch (\Throwable $e) {
            return ['status' => 'uncertain', 'started' => false,
                    'operation' => $operation];
        }
        if ($response !== 'OK') {
            // A timeout or lost acknowledgement does not prove a job did not
            // start. Never retry this destructive request without reconciling
            // the correlated operation status.
            return ['status' => 'uncertain', 'started' => false,
                    'operation' => $operation];
        }
        return ['status' => 'ok', 'started' => true, 'operation' => $operation];
    }

    public function resourcesInstallAction(): array
    {
        if (!$this->request->isPost()) {
            return ['status' => 'failed'];
        }

        $backend = new Backend();
        $runtime = $this->getRuntimeState($backend);
        $extras = $this->getExtraResourceState($backend);
        if (!$runtime['installed'] || $runtime['service'] !== 'started' ||
            $runtime['busy'] || $extras['busy'] ||
            in_array($extras['phase'], ['restore_failed', 'recovery_required'], true)) {
            throw new UserException(
                gettext('Start Zapret2 and finish any pending runtime operation or recovery first.'),
                gettext('Additional Resources unavailable')
            );
        }

        // A token is tied to this request, not a transient daemon PID.
        $operation = bin2hex(random_bytes(16));
        $response = trim((string)$backend->configdpRun(
            'zapret extra_resources_install', [$operation], false, 30
        ));
        if ($response !== 'OK') {
            throw new UserException(
                gettext('The Additional Resources installation could not be started.'),
                gettext('Additional Resources error')
            );
        }

        return ['status' => 'ok', 'started' => true, 'operation' => $operation];
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
                $message,
                gettext('Zapret configuration error')
            );
        }

        return ['status' => 'ok', 'response' => $response];
    }
}
