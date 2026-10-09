<?php

/**
 * Side-effect-free Voice form validation; produces native GUI field errors.
 *
 * This validation is a GUI precheck, not installed-dvtws2 capability proof.
 * The authoritative Python release compiler, managed targets and atomic
 * lifecycle MUST all succeed again before any live Apply can be enabled.
 */
namespace OPNsense\Zapret\Api;

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

    private static function normalizeTargets(string $raw, string $name, array &$errors): array
    {
        $field = 'zapret.hostlist.' . $name . 'ips';
        if (strlen($raw) > 1048576) {
            self::error($errors, $field, 'IPv4/CIDR list is too large');
            return [];
        }
        $items = [];
        $nets = [];
        foreach (preg_split('/\r\n|\n|\r/', $raw) as $index => $line) {
            $input = trim(trim($line), ',;:');
            if ($input === '') {
                continue;
            }
            $parts = explode('/', $input, 2);
            if (filter_var($parts[0], FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) === false ||
                (count($parts) === 2 && !preg_match('/^(?:[0-9]|[12][0-9]|3[0-2])$/D', $parts[1]))
            ) {
                self::error($errors, $field, sprintf('Invalid IPv4/CIDR at line %d', $index + 1));
                return [];
            }
            $prefix = count($parts) === 2 ? (int)$parts[1] : 32;
            $unsigned = (int)sprintf('%u', ip2long($parts[0]));
            $mask = $prefix === 0 ? 0 : ((0xffffffff << (32 - $prefix)) & 0xffffffff);
            if (($unsigned & $mask) !== $unsigned) {
                self::error($errors, $field, sprintf('CIDR contains host bits at line %d', $index + 1));
                return [];
            }
            $canonical = count($parts) === 2 ? long2ip($unsigned) . '/' . $prefix : long2ip($unsigned);
            if (!isset($items[$canonical])) {
                $items[$canonical] = true;
                $nets[] = [$unsigned, $prefix];
            }
            if (count($items) > self::MAX_TARGETS) {
                self::error($errors, $field, 'Too many destination addresses');
                return [];
            }
        }
        return $nets;
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
            if ($errors) {
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

    private static function targetsOverlap(array $a, array $b): bool
    {
        foreach ($a as [$ipA, $prefixA]) {
            foreach ($b as [$ipB, $prefixB]) {
                $prefix = min($prefixA, $prefixB);
                $mask = $prefix === 0 ? 0 : ((0xffffffff << (32 - $prefix)) & 0xffffffff);
                if (($ipA & $mask) === ($ipB & $mask)) {
                    return true;
                }
            }
        }
        return false;
    }

    public static function check(array $request): array
    {
        $errors = [];
        if (array_diff(array_keys($request), ['voice', 'hostlist'])) {
            return ['zapret.voice.waninterface' => 'Unexpected Voice form fields'];
        }
        $voice = $request['voice'] ?? null;
        $hostlist = $request['hostlist'] ?? null;
        if (!is_array($voice) || !is_array($hostlist)) {
            return ['zapret.voice.waninterface' => 'Voice settings and IPSET fields are required'];
        }
        $names = self::SERVICES;
        $enabled = [];
        $wan = $voice['waninterface'] ?? '';
        if (!is_string($wan) || strlen($wan) > 64 ||
            ($wan !== '' && !preg_match('/^[A-Za-z][A-Za-z0-9_.:-]{0,63}$/D', $wan))) {
            self::error($errors, 'zapret.voice.waninterface', 'Invalid Voice WAN selection');
        }
        if (array_diff(array_keys($voice), array_merge(['waninterface'], $names)) ||
            array_diff(array_keys($hostlist), array_map(static fn($n) => $n . 'ips', $names))
        ) {
            self::error($errors, 'zapret.voice.waninterface', 'Unexpected Voice form fields');
        }
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
                continue;
            }
            if (!is_string($raw)) {
                self::error($errors, 'zapret.hostlist.' . $name . 'ips', 'IPSET must be a text list');
                continue;
            }
            if ($record['enabled'] !== '1') {
                // Disabled services preserve their raw drafts, including
                // incomplete arguments; their IPSETs are still editable.
                continue;
            }
            $nets = self::normalizeTargets($raw, $name, $errors);
            $ports = self::parseArgs($record['args'], $name, $errors);
            if (!$nets) {
                self::error($errors, 'zapret.hostlist.' . $name . 'ips', 'Enabled Voice service requires destination IPs');
            }
            foreach ($enabled as $other => $candidate) {
                if (self::intersects($ports, $candidate['ports']) &&
                    self::targetsOverlap($nets, $candidate['nets'])) {
                    self::error($errors, $prefix . '.enabled',
                        sprintf('UDP ports and destinations overlap with %s', $other));
                }
            }
            $enabled[$name] = ['nets' => $nets, 'ports' => $ports];
        }
        return $errors;
    }
}
