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

use OPNsense\Base\ApiMutableModelControllerBase;
use OPNsense\Base\UserException;
use OPNsense\Core\Backend;
use OPNsense\Core\Config;

class SettingsController extends ApiMutableModelControllerBase
{
    protected static $internalModelName = 'zapret';
    protected static $internalModelClass = '\OPNsense\Zapret\Zapret';

    private const TARGET_FIELDS = [
        'youtubedomains' => 'YouTube Domains',
        'telegramips' => 'Telegram IPs',
        'userdomains' => 'User Domains',
        'excludedomains' => 'Exclude Domains',
    ];

    private function validationFailure(string $field, string $message): array
    {
        return [
            'result' => 'failed',
            'validations' => ["zapret.hostlist.{$field}" => $message],
        ];
    }

    private function normalizeDomainList(string $text, string $label): array
    {
        $normalized = [];
        $seen = [];
        $changed = 0;
        $duplicates = 0;

        foreach (preg_split('/\R/u', $text) as $index => $raw) {
            $lineNo = $index + 1;
            $value = trim($raw);
            if ($value === '') {
                continue;
            }
            $original = $value;
            $value = preg_replace('#^https?://#i', '', $value);
            $value = preg_replace('/[\/?#].*$/', '', $value);
            $value = preg_replace('/^\*\./', '', trim($value));
            $value = preg_replace('/^[,;:]+|[,;:]+$/', '', $value);
            $value = trim($value, ". \t\n\r\0\x0B");
            $value = strtolower($value);

            if ($value === '' || strlen($value) > 253 || strpos($value, '..') !== false) {
                throw new \InvalidArgumentException(
                    sprintf("%s, line %d: invalid domain entry '%s'", $label, $lineNo, $raw)
                );
            }
            // IP addresses and network-like values are not domains.
            if (preg_match('/^[0-9.]+$/', $value) || strpos($value, '/') !== false) {
                throw new \InvalidArgumentException(
                    sprintf("%s, line %d: IP addresses and networks are not allowed in a domain list ('%s')", $label, $lineNo, $raw)
                );
            }
            foreach (explode('.', $value) as $part) {
                if (
                    $part === '' || strlen($part) > 63 ||
                    !preg_match('/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/', $part)
                ) {
                    throw new \InvalidArgumentException(
                        sprintf("%s, line %d: invalid domain entry '%s' after normalization to '%s'", $label, $lineNo, $raw, $value)
                    );
                }
            }

            if ($value !== $original) {
                $changed++;
            }
            if (isset($seen[$value])) {
                $duplicates++;
                continue;
            }
            $seen[$value] = true;
            $normalized[] = $value;
        }

        return [implode("\n", $normalized), $changed, $duplicates];
    }

    private function normalizeIpList(string $text, string $label): array
    {
        $normalized = [];
        $seen = [];
        $changed = 0;
        $duplicates = 0;

        foreach (preg_split('/\R/u', $text) as $index => $raw) {
            $lineNo = $index + 1;
            $value = trim(trim($raw), ',;:');
            if ($value === '') {
                continue;
            }
            $canonical = $value;

            if (strpos($value, '/') !== false) {
                [$address, $prefixText] = array_pad(explode('/', $value, 2), 2, null);
                if (
                    filter_var($address, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) === false ||
                    $prefixText === null || !preg_match('/^(?:[0-9]|[12][0-9]|3[0-2])$/', $prefixText)
                ) {
                    throw new \InvalidArgumentException(
                        sprintf("%s, line %d: invalid IPv4 address or CIDR '%s'", $label, $lineNo, $raw)
                    );
                }
                $prefix = (int)$prefixText;
                $ip = (int)sprintf('%u', ip2long($address));
                $mask = $prefix === 0 ? 0 : ((0xFFFFFFFF << (32 - $prefix)) & 0xFFFFFFFF);
                if (($ip & $mask) !== $ip) {
                    throw new \InvalidArgumentException(
                        sprintf("%s, line %d: CIDR contains host bits ('%s')", $label, $lineNo, $raw)
                    );
                }
                $canonical = long2ip($ip) . '/' . $prefix;
            } elseif (filter_var($value, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) === false) {
                throw new \InvalidArgumentException(
                    sprintf("%s, line %d: invalid IPv4 address or CIDR '%s'", $label, $lineNo, $raw)
                );
            }

            if ($canonical !== trim($raw)) {
                $changed++;
            }
            if (isset($seen[$canonical])) {
                $duplicates++;
                continue;
            }
            $seen[$canonical] = true;
            $normalized[] = $canonical;
        }

        return [implode("\n", $normalized), $changed, $duplicates];
    }

    private function backendFailureMessage(string $fallback): string
    {
        $stageFile = '/var/run/zapret2-execution.status';
        if (is_readable($stageFile)) {
            $parts = explode('|', trim((string)file_get_contents($stageFile)), 6);
            if (count($parts) === 6 && $parts[3] === 'failed' && trim($parts[5]) !== '') {
                return trim($parts[5]);
            }
        }
        return $fallback;
    }

    /**
     * Validate, normalize, save and safely reconfigure as one user operation.
     * On any backend failure the previous model is restored and the safe
     * reconfigure backend keeps or restores the previous live runtime.
     */
    public function applyAction()
    {
        if (!$this->request->isPost()) {
            return ['result' => 'failed'];
        }

        $config = Config::getInstance();
        $config->lock();
        $model = $this->getModel();
        $oldNodes = $model->getNodes();
        $post = $this->request->getPost(static::$internalModelName);
        $model->setNodes($post);

        $result = $this->validate(null, null, true);
        if (!empty($result['result'])) {
            $config->unlock();
            return $result;
        }

        $summary = [];
        try {
            foreach (self::TARGET_FIELDS as $field => $label) {
                $raw = (string)$model->hostlist->{$field};
                if ($field === 'telegramips') {
                    [$value, $changed, $duplicates] = $this->normalizeIpList($raw, $label);
                } else {
                    [$value, $changed, $duplicates] = $this->normalizeDomainList($raw, $label);
                }
                $model->hostlist->{$field} = $value;
                if ($changed > 0 || $duplicates > 0) {
                    $summary[] = sprintf(
                        '%s: normalized %d, removed duplicates %d',
                        $label,
                        $changed,
                        $duplicates
                    );
                }
            }
        } catch (\InvalidArgumentException $exception) {
            $config->unlock();
            foreach (self::TARGET_FIELDS as $field => $label) {
                if (strpos($exception->getMessage(), $label . ',') === 0) {
                    return $this->validationFailure($field, $exception->getMessage());
                }
            }
            throw $exception;
        }

        $result = $this->validate(null, null, true);
        if (!empty($result['result'])) {
            $config->unlock();
            return $result;
        }

        $this->setSaveAuditMessage(gettext('Applied Zapret settings'));
        $this->save(false, true);
        $config->unlock();

        $backend = new Backend();
        $templateResponse = trim((string)$backend->configdRun('template reload OPNsense/Zapret'));
        $reconfigureResponse = $templateResponse !== ''
            ? trim((string)$backend->configdRun('zapret reconfigure', false, 180))
            : '';

        if ($templateResponse === '' || $reconfigureResponse === '') {
            $config->lock();
            $model->setNodes($oldNodes);
            $this->setSaveAuditMessage(gettext('Restored previous Zapret settings after failed apply'));
            $this->save(false, true);
            $config->unlock();
            $backend->configdRun('template reload OPNsense/Zapret');

            throw new UserException(
                $this->backendFailureMessage(
                    gettext('The new configuration could not be applied. Previous settings and runtime were restored.')
                ),
                gettext('Zapret configuration error')
            );
        }

        return [
            'result' => 'saved',
            'status' => 'ok',
            'normalized' => !empty($summary),
            'normalization' => $summary,
            static::$internalModelName => $model->getNodes(),
        ];
    }
}
