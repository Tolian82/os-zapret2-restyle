<?php

/**
 * Internal root FD9 request staging for the ONE Strategies/Voice Apply.
 *
 * No Config save, template reload, IPFW mutation, or runtime switch.
 * The service owns FD9. Only a complete, freshly read OPNsense Config model
 * can produce a detached XML candidate in the fixed, private work root.
 * A later step renders it with the native template engine and builds the
 * complete shared release before committing any live resource.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';
require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php';
require_once __DIR__ . '/shared_apply_lock.php';

use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\SharedApplyEnvelope;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

final class SharedApplyRequest
{
    private const ROOT = '/var/db/zapret2/shared-work';
    private const MAX_REQUEST = 65536;
    private const MAX_XML = 16777216;

    public static function decode(string $encoded): array
    {
        if ($encoded === '' || strlen($encoded) > self::MAX_REQUEST ||
            !preg_match('/^[A-Za-z0-9_-]+$/D', $encoded)) {
            throw new \InvalidArgumentException('Invalid shared Apply request envelope');
        }
        $bytes = base64_decode(strtr($encoded, '-_', '+/'), true);
        if (!is_string($bytes) || strlen($bytes) > self::MAX_REQUEST ||
            rtrim(strtr(base64_encode($bytes), '+/', '-_'), '=') !== $encoded) {
            throw new \InvalidArgumentException('Invalid shared Apply request encoding');
        }
        $data = json_decode($bytes, true, 20, JSON_THROW_ON_ERROR);
        if (!is_array($data) || array_keys($data) !== ['page', 'fields', 'sync'] ||
            !in_array($data['page'], ['voice', 'strategies'], true) ||
            !is_array($data['fields']) || !is_array($data['sync'])) {
            throw new \InvalidArgumentException('Invalid shared Apply request content');
        }
        if ($data['page'] === 'voice') {
            if (array_keys($data['sync']) !== ['snapshot']) {
                throw new \InvalidArgumentException('Voice snapshot required');
            }
        } elseif (array_keys($data['sync']) !== ['telegramips_baseline']) {
            throw new \InvalidArgumentException('Strategies Telegram baseline required');
        }
        return $data;
    }

    public static function prepare(
        array $request, array $current, string $activeXml
    ): array {
        $plan = $request['page'] === 'voice'
            ? SettingsApply::prepareVoice(
                $current, $request['fields'], $request['sync']['snapshot']
            )
            : SettingsApply::prepareStrategies(
                $current, $request['fields'], $request['sync']['telegramips_baseline']
            );
        if (($plan['result'] ?? null) !== 'prepared') {
            throw new \InvalidArgumentException('Shared native Apply candidate rejected');
        }
        $xml = SettingsApply::renderCandidateXml(
            $activeXml, $current, $plan, $request['page']
        );
        if (strlen($xml) > self::MAX_XML) {
            throw new \InvalidArgumentException('Detached Config exceeds native limit');
        }
        // Bind the form's page to the native plan itself. A configd caller
        // cannot replay a Voice candidate as a Strategies transaction.
        $plan['page'] = $request['page'];
        return ['plan' => $plan, 'xml' => $xml];
    }

    private static function secureDir(string $path, bool $create): void
    {
        if ($create && !file_exists($path) && !is_link($path) && !mkdir($path, 0700)) {
            throw new \RuntimeException('Cannot initialize shared candidate directory');
        }
        $stat = @lstat($path);
        if (!is_array($stat) || !is_dir($path) || is_link($path) ||
            $stat['uid'] !== 0 || ($stat['mode'] & 0077) !== 0) {
            throw new \RuntimeException('Unsafe shared candidate directory');
        }
    }

    private static function writeExclusive(string $path, string $content): void
    {
        $handle = @fopen($path, 'xb');
        if ($handle === false) {
            throw new \RuntimeException('Shared candidate file already exists');
        }
        try {
            if (!chmod($path, 0600)) {
                throw new \RuntimeException('Shared candidate permissions failed');
            }
            $length = strlen($content);
            $written = 0;
            while ($written < $length) {
                $chunk = fwrite($handle, substr($content, $written));
                if ($chunk === false || $chunk === 0) {
                    throw new \RuntimeException('Shared candidate write failed');
                }
                $written += $chunk;
            }
            if (!fflush($handle) || !fsync($handle)) {
                throw new \RuntimeException('Shared candidate fsync failed');
            }
        } finally {
            fclose($handle);
        }
    }

    /**
     * Only the privileged original-FD9 service invokes materialize().
     * The request is already decoded, modeled and rendered. No active file
     * is replaced; incomplete work remains inert and cannot be reused.
     */
    public static function materialize(array $result, string $base = self::ROOT): string
    {
        if (!isset($result['plan'], $result['xml']) ||
            !is_array($result['plan']) || !is_string($result['xml'])) {
            throw new \InvalidArgumentException('Malformed native shared preparation');
        }
        $originalUmask = umask(0077);
        try {
            if ($base === self::ROOT) {
                self::secureDir('/var/db/zapret2', true);
            }
            self::secureDir($base, true);
            $id = bin2hex(random_bytes(16));
            $work = rtrim($base, '/') . '/' . $id;
            self::secureDir($work, true);
            $planJson = json_encode($result['plan'], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
            self::writeExclusive($work . '/candidate.xml', $result['xml']);
            self::writeExclusive($work . '/plan.json', $planJson . "\n");
            return $id;
        } finally {
            umask($originalUmask);
        }
    }


    /**
     * Compatibility configctl names are adapters to the SAME shared Apply.
     * Only Telegram's ON/OFF preference changes, and native saved STUN args,
     * all other profiles and shared IPSET fields are preserved verbatim.
     * No marker, parallel engine, Config save or runtime modification.
     */
    public static function telegramEnvelope(array $current, string $action): string
    {
        if (!in_array($action, ['enable', 'disable'], true)) {
            throw new \InvalidArgumentException('Invalid Telegram Voice compatibility action');
        }
        if (!isset($current['voice'], $current['hostlist']) ||
            !is_array($current['voice']) || !is_array($current['hostlist']) ||
            !isset($current['general']['waninterface'])) {
            throw new \InvalidArgumentException('Incomplete native Voice model');
        }
        // The compatibility action also inherits the Strategies WAN; never
        // send the saved legacy Voice override as a writable form field.
        $voice = [];
        $ips = [];
        foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
            $entry = $current['voice'][$service] ?? null;
            $ip = $current['hostlist'][$service . 'ips'] ?? null;
            if (!is_array($entry) || !isset($entry['enabled'], $entry['args']) ||
                !is_string($entry['enabled']) || !is_string($entry['args']) ||
                !is_string($ip)) {
                throw new \InvalidArgumentException('Incomplete native Voice service');
            }
            $voice[$service] = $entry;
            $ips[$service . 'ips'] = $ip;
        }
        $voice['telegram']['enabled'] = $action === 'enable' ? '1' : '0';
        $snapshot = VoiceSettingsSnapshot::digest($current);
        $encoded = SharedApplyEnvelope::encode(
            'voice', ['voice' => $voice, 'hostlist' => $ips],
            ['snapshot' => $snapshot]
        );
        // The root stage and Config save both repeat this exact model check.
        $candidate = SettingsApply::prepareVoice(
            $current, self::decode($encoded)['fields'], $snapshot
        );
        if (($candidate['result'] ?? null) !== 'prepared') {
            throw new \InvalidArgumentException(
                'Configure valid Telegram STUN parameters and IPSET in Voice before enabling'
            );
        }
        // An adapter for Telegram must never normalize, enable or rewrite
        // another Voice service, even as a side effect of full-model Apply.
        foreach ($candidate['changed_fields'] as $field) {
            if (!in_array($field, ['voice.telegram.enabled', 'hostlist.telegramips'], true)) {
                throw new \InvalidArgumentException(
                    'Another Voice service requires its own explicit Apply'
                );
            }
        }
        return $encoded;
    }

    /** Read-only durable intent, never the obsolete /var/run PoC marker. */
    public static function telegramSaved(array $current): array
    {
        $enabled = $current['voice']['telegram']['enabled'] ?? null;
        if (!in_array($enabled, ['0', '1'], true)) {
            throw new \InvalidArgumentException('Invalid saved Telegram Voice preference');
        }
        return ['requested' => $enabled === '1' ? 'on' : 'off',
                'snapshot' => VoiceSettingsSnapshot::digest($current)];
    }

    public static function main(array $argv): int
    {
        if (!in_array($argv[1] ?? '', ['stage', 'telegram-envelope', 'telegram-saved'], true) ||
            (($argv[1] ?? '') === 'telegram-saved' ? count($argv) !== 2 : count($argv) !== 3)) {
            fwrite(STDERR, "usage: shared_apply_request.php stage ENCODED_REQUEST | telegram-envelope enable|disable | telegram-saved\n");
            return 64;
        }
        $phase = 'root-gate';
        try {
            if (PHP_OS_FAMILY !== 'BSD' || SharedApplyLifecycleLock::effectiveUid() !== 0) {
                throw new \RuntimeException('Native root staging required');
            }
            SharedApplyLifecycleLock::assertHeld();
            $phase = 'bootstrap';
            // Same installed OPNsense bootstrapping as built-in PHP scripts.
            require_once('script/load_phalcon.php');
            $config = \OPNsense\Core\Config::getInstance();
            $config->lock();
            $phase = 'model';
            try {
                $current = (new \OPNsense\Zapret\Zapret())->getNodes();
                if ($argv[1] === 'telegram-envelope') {
                    $response = self::telegramEnvelope($current, $argv[2]);
                } elseif ($argv[1] === 'telegram-saved') {
                    $response = json_encode(self::telegramSaved($current), JSON_THROW_ON_ERROR);
                } else {
                    $phase = 'decode';
                    $request = self::decode($argv[2]);
                    $activeXml = file_get_contents('/conf/config.xml');
                    if (!is_string($activeXml)) {
                        throw new \RuntimeException('Could not read locked native Config');
                    }
                    $phase = 'candidate';
                    $prepared = self::prepare($request, $current, $activeXml);
                    $phase = 'workspace';
                    $id = self::materialize($prepared);
                    $response = "prepared-id=$id";
                }
            } finally {
                $config->unlock();
            }
            echo $response . "\n";
            return 0;
        } catch (\Throwable $error) {
            if ($argv[1] === 'stage') {
                // Stage prepares only an inert detached candidate. No Config save,
                // IPFW or process switch is possible here. Return a bounded
                // negative receipt rather than an indistinguishable configd 69.
                // Never echo the submitted envelope or exception text.
                error_log(sprintf('Zapret shared Apply stage refused phase=%s type=%s',
                    $phase, get_class($error)));
                echo 'preflight-rejected=' . $phase . "\n";
                return 0;
            }
            fwrite(STDERR, "ERROR: shared native request preparation refused: " .
                $error->getMessage() . "\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' && isset($argv) &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(SharedApplyRequest::main($argv));
}
