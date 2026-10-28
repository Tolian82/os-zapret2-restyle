<?php

/**
 * Side-effect-free Voice form validation; produces native GUI field errors.
 *
 * This validation is a GUI precheck, not installed-dvtws2 capability proof.
 * The authoritative Python release compiler, managed targets and atomic
 * lifecycle MUST all succeed again before any live Apply can be enabled.
 */
namespace OPNsense\Zapret\Api;

require_once __DIR__ . '/IPSetPolicyBridge.php';

final class VoiceCandidateValidator
{
    private const SERVICES = ['telegram', 'discord', 'x', 'sip', 'custom'];
    private const MAX_ARGS_BYTES = 16384;
    private const MAX_TARGETS = 4096;

    private static function error(array &$errors, string $key, string $message): void
    {
        if (!isset($errors[$key])) {
            $errors[$key] = $message;
        }
    }

    private static function parsePorts(string $value, string $field, array &$errors): array
    {
        if ($value === '*') {
            return [[1, 65535]];
        }
        $parts = explode(',', $value);
        if (count($parts) === 0 || count($parts) > 128) {
            self::error($errors, $field, 'UDP ports must be numeric intervals or *');
            return [];
        }
        $result = [];
        foreach ($parts as $part) {
            if (!preg_match('/^[0-9]{1,5}(?:-[0-9]{1,5})?$/D', $part)) {
                self::error($errors, $field, 'Invalid UDP port selector');
                return [];
            }
            $values = array_map('intval', explode('-', $part));
            $lo = $values[0];
            $hi = end($values);
            if ($lo < 1 || $hi > 65535 || $lo > $hi) {
                self::error($errors, $field, 'UDP port is outside 1–65535');
                return [];
            }
            $result[] = [$lo, $hi];
        }
        return $result;
    }

    private static function validateFake(string $item, string $field, array &$errors): void
    {
        $parts = explode(':', $item);
        if (array_shift($parts) !== '--lua-desync=fake') {
            self::error($errors, $field, 'Only the native fake Lua action is currently supported');
            return;
        }
        $seen = [];
        $size = null;
        $fragPos = null;
        foreach ($parts as $part) {
            $key = explode('=', $part, 2)[0];
            if (isset($seen[$key])) {
                self::error($errors, $field, 'Duplicate fake option: ' . $key);
                return;
            }
            $seen[$key] = true;
            switch ($key) {
                case 'blob':
                    if (!preg_match('/^blob=0x([0-9a-fA-F]{2,8192})$/D', $part, $matches) ||
                        strlen($matches[1] ?? '') % 2 !== 0) {
                        self::error($errors, $field, 'Fake blob must be whole bytes of 0xHEX');
                        return;
                    }
                    $size = strlen($matches[1]) / 2;
                    break;
                case 'repeats':
                    if (!preg_match('/^repeats=([0-9]{1,2})$/D', $part, $matches) ||
                        (int)$matches[1] < 1 || (int)$matches[1] > 10) {
                        self::error($errors, $field, 'Fake repeats must be 1–10');
                        return;
                    }
                    break;
                case 'ip_ttl':
                    if (!preg_match('/^ip_ttl=([0-9]{1,3})$/D', $part, $matches) ||
                        (int)$matches[1] < 1 || (int)$matches[1] > 255) {
                        self::error($errors, $field, 'Fake TTL must be 1–255');
                        return;
                    }
                    break;
                case 'ipfrag_pos_udp':
                    if (!preg_match('/^ipfrag_pos_udp=([0-9]{1,4})$/D', $part, $matches) ||
                        (int)$matches[1] < 8 || (int)$matches[1] > 4096 ||
                        (int)$matches[1] % 8 !== 0) {
                        self::error($errors, $field, 'UDP fake fragment offset must be a multiple of 8');
                        return;
                    }
                    $fragPos = (int)$matches[1];
                    break;
                case 'badsum':
                case 'ipfrag':
                case 'ipfrag_disorder':
                    if ($part !== $key) {
                        self::error($errors, $field, 'Invalid fake option flag');
                        return;
                    }
                    break;
                default:
                    self::error($errors, $field, 'Unverified native fake option');
                    return;
            }
        }
        if ($size === null ||
            ((isset($seen['ipfrag_pos_udp']) || isset($seen['ipfrag_disorder'])) &&
             !isset($seen['ipfrag'])) ||
            ($fragPos !== null && $fragPos >= 8 + $size) ||
            (isset($seen['ipfrag']) && isset($seen['badsum']))
        ) {
            self::error($errors, $field, 'Missing fake blob or invalid fragmentation combination');
        }
    }

    private static function parseArgs(string $source, string $service, array &$errors): array
    {
        $field = 'zapret.voice.' . $service . '.args';
        if (strlen($source) > self::MAX_ARGS_BYTES) {
            self::error($errors, $field, 'STUN parameters are too long');
            return [];
        }
        $seen = [];
        $ports = [];
        foreach (preg_split('/\r\n|\n|\r/', $source) as $index => $line) {
            $item = trim($line);
            if ($item === '') {
                continue;
            }
            if (strlen($item) > 9000 || !preg_match('/^[\x21-\x7e]+$/D', $item)) {
                self::error($errors, $field, 'Only single-token native ASCII arguments are permitted');
                return [];
            }
            $parts = explode('=', $item, 2);
            $option = $parts[0];
            if (isset($seen[$option])) {
                self::error($errors, $field, sprintf('Repeated %s at line %d', $option, $index + 1));
                return [];
            }
            $seen[$option] = true;
            if ($option === '--filter-udp') {
                $ports = self::parsePorts($parts[1] ?? '', $field, $errors);
            } elseif ($option === '--filter-l7' || $option === '--payload') {
                if ($item !== $option . '=stun') {
                    self::error($errors, $field, 'Only native STUN filtering is allowed');
                }
            } elseif ($option === '--lua-desync') {
                self::validateFake($item, $field, $errors);
            } elseif ($option === '--out-range') {
                if (!preg_match('/^--out-range=(?:[ndb][0-9]{1,6}(?:[-<][ndb][0-9]{1,6})?|a|x)$/D', $item)) {
                    self::error($errors, $field, 'Unsupported UDP out-range selector');
                }
            } else {
                self::error($errors, $field, 'Forbidden or unverified dvtws2 parameter at line ' . ($index + 1));
            }
            // A different service's IPSET/argument error must not suppress
            // validation of THIS service's later STUN options. Only an error
            // reported for this exact args field stops its parser.
            if (isset($errors[$field])) {
                return [];
            }
        }
        foreach (['--filter-udp', '--filter-l7', '--payload'] as $required) {
            if (!isset($seen[$required])) {
                self::error($errors, $field, 'Required native STUN option missing: ' . $required);
            }
        }
        return $ports;
    }

    private static function intersects(array $a, array $b): bool
    {
        foreach ($a as $left) {
            foreach ($b as $right) {
                if (max($left[0], $right[0]) <= min($left[1], $right[1])) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Preview all six user IP lists through the one native Python parser.
     * Keep STUN option checks in PHP; address meaning and overlap are owned
     * solely by ipset_policy.py. No mutation is authorized by this preview.
     */
    public static function checkWithTargets(array $request): array
    {
        $errors = [];
        $empty = ['errors' => [], 'normalized' => []];
        if (array_diff(array_keys($request), ['voice', 'hostlist'])) {
            return ['errors' => ['zapret.voice.waninterface' => 'Unexpected Voice form fields'],
                    'normalized' => []];
        }
        $voice = $request['voice'] ?? null;
        $hostlist = $request['hostlist'] ?? null;
        if (!is_array($voice) || !is_array($hostlist)) {
            return ['errors' => ['zapret.voice.waninterface' => 'Voice settings and IPSET fields are required'],
                    'normalized' => []];
        }
        $names = self::SERVICES;
        if (array_diff(array_keys($voice), $names) ||
            array_diff(array_keys($hostlist), array_map(static fn($n) => $n . 'ips', $names))
        ) {
            self::error($errors, 'zapret.voice.waninterface', 'Unexpected Voice form fields');
        }
        $fields = [];
        $enabled = [];
        $ports = [];
        foreach ($names as $name) {
            $record = $voice[$name] ?? null;
            $raw = $hostlist[$name . 'ips'] ?? null;
            $prefix = 'zapret.voice.' . $name;
            if (!is_array($record) ||
                array_diff(array_keys($record), ['enabled', 'args']) ||
                !isset($record['enabled']) || !is_string($record['enabled']) ||
                !in_array($record['enabled'], ['0', '1'], true) ||
                !isset($record['args']) || !is_string($record['args'])) {
                self::error($errors, $prefix . '.enabled', 'Service checkbox and parameters are required');
                $fields[$name] = is_string($raw) ? $raw : '';
                continue;
            }
            if (!is_string($raw)) {
                self::error($errors, 'zapret.hostlist.' . $name . 'ips', 'IPSET must be a text list');
                $fields[$name] = '';
                continue;
            }
            // All supplied IPSETs are checked for universal /0, even for
            // disabled services. Disabled STUN argument drafts stay editable.
            $fields[$name] = $raw;
            if ($record['enabled'] === '1') {
                $enabled[$name] = true;
                $ports[$name] = self::parseArgs($record['args'], $name, $errors);
            }
        }
        $fields['exclude'] = '';
        $normalized = [];
        $overlaps = [];
        $targetsParsed = false;
        try {
            $preview = IPSetPolicyBridge::inspect($fields);
            $targetsParsed = true;
            foreach ($names as $name) {
                $normalized[$name] = $preview['lists'][$name]['normalized'];
            }
            $overlaps = $preview['overlaps'];
        } catch (\InvalidArgumentException $error) {
            $labels = ['Telegram IPs' => 'telegramips',
                       'DISCORD IPs' => 'discordips',
                       'X IPs' => 'xips',
                       'SIP IPs' => 'sipips',
                       'CUSTOM IPs' => 'customips'];
            $found = false;
            foreach ($labels as $label => $field) {
                if (str_contains($error->getMessage(), $label)) {
                    self::error($errors, 'zapret.hostlist.' . $field, $error->getMessage());
                    $found = true;
                    break;
                }
            }
            if (!$found) {
                self::error($errors, 'zapret.voice.waninterface', $error->getMessage());
            }
        } catch (\Throwable $error) {
            // Native interpreter or preflight failure must be fail-closed.
            self::error($errors, 'zapret.voice.waninterface', 'Native IPSET preflight unavailable');
        }

        foreach (array_keys($enabled) as $name) {
            // If the ONE native parser refused input (or was unavailable),
            // report that actual error; never invent "no destination IPs"
            // while the operator's non-empty list remains visible.
            if ($targetsParsed && ($normalized[$name] ?? '') === '') {
                self::error($errors, 'zapret.hostlist.' . $name . 'ips',
                    'Enabled Voice service requires destination IPs');
            }
        }
        foreach ($overlaps as $pair) {
            if (!is_array($pair) || count($pair) !== 2) {
                self::error($errors, 'zapret.voice.waninterface', 'Invalid native overlap evidence');
                continue;
            }
            [$left, $right] = $pair;
            if (isset($enabled[$left], $enabled[$right]) &&
                self::intersects($ports[$left], $ports[$right])) {
                self::error($errors, 'zapret.voice.' . $right . '.enabled',
                    sprintf('UDP ports and destinations overlap with %s', $left));
            }
        }
        return ['errors' => $errors, 'normalized' => $normalized];
    }

    public static function check(array $request): array
    {
        return self::checkWithTargets($request)['errors'];
    }
}
