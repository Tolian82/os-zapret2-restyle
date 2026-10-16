<?php
// Pure native-form ownership regression, with no running OPNsense backend.
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategySettingsPayload.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceSettingsPayload.php';

use OPNsense\Zapret\Api\VoiceSettingsPayload;
use OPNsense\Zapret\Api\StrategySettingsPayload;

function assertEq($expected, $actual, string $name): void
{
    if ($expected !== $actual) {
        fwrite(STDERR, "FAIL: {$name}\n");
        exit(1);
    }
}

function failPayload($state, $input, string $name): void
{
    try {
        VoiceSettingsPayload::overlay($state, $input);
    } catch (\InvalidArgumentException $exception) {
        return;
    }
    fwrite(STDERR, "FAIL: illegal Voice field accepted: {$name}\n");
    exit(1);
}

$current = [
    'general' => ['enabled' => '1', 'waninterface' => 'WAN', 'divertport' => '989'],
    'strategy' => ['trafficargs' => '--filter-udp=596-599', 'extraargs' => ''],
    'strategylab' => ['enablequic' => '1'],
    'hostlist' => [
        'mode' => 'auto',
        'telegramips' => '91.108.0.0/16',
        'discordips' => '',
        'xips' => '',
        'sipips' => '',
        'customips' => '',
        'userdomains' => 'foo.example',
    ],
    'voice' => [
        'waninterface' => '',
        'telegram' => ['enabled' => '0', 'args' => ''],
        'discord' => ['enabled' => '0', 'args' => ''],
        'x' => ['enabled' => '0', 'args' => ''],
        'sip' => ['enabled' => '0', 'args' => ''],
        'custom' => ['enabled' => '0', 'args' => ''],
    ],
];
VoiceSettingsPayload::requireFreshTelegram($current, '91.108.0.0/16');
try {
    VoiceSettingsPayload::requireFreshTelegram($current, '91.108.13.10');
    fwrite(STDERR, "FAIL: stale Telegram IPSET accepted by Voice\n");
    exit(1);
} catch (\InvalidArgumentException $exception) {
    // Correct.
}

$post = [
    'voice' => [
        'waninterface' => 'WAN',
        'telegram' => ['enabled' => '1', 'args' => '--filter-udp=*'],
        'discord' => ['enabled' => '0', 'args' => 'not-yet-approved'],
    ],
    'hostlist' => [
        'telegramips' => '91.108.13.10',
        'discordips' => '203.0.113.0/24',
    ],
];
$expected = $current;
$expected['voice']['waninterface'] = 'WAN';
$expected['voice']['telegram'] = ['enabled' => '1', 'args' => '--filter-udp=*'];
$expected['voice']['discord']['args'] = 'not-yet-approved';
$expected['hostlist']['telegramips'] = '91.108.13.10';
$expected['hostlist']['discordips'] = '203.0.113.0/24';
assertEq($expected, VoiceSettingsPayload::overlay($current, $post),
    'Voice fields must not overwrite general, Strategies, Laboratory or unrelated domains');
assertEq($current, VoiceSettingsPayload::overlay($current, []), 'empty patch must preserve prior config');
assertEq('0', $current['voice']['telegram']['enabled'], 'saved source changed during overlay');

failPayload($current, ['general' => ['enabled' => '0']], 'global service');
failPayload($current, ['strategy' => ['trafficargs' => 'evil']], 'ordinary Strategy');
failPayload($current, ['hostlist' => ['mode' => 'all']], 'Target Mode');
failPayload($current, ['hostlist' => ['userdomains' => 'evil']], 'unrelated domains');
failPayload($current, ['voice' => ['custom' => ['secret' => 'evil']]], 'new service field');
failPayload($current, ['voice' => ['discord' => ['enabled' => 'yes']]], 'invalid switch');
failPayload($current, ['voice' => ['telegram' => ['args' => ['--new']]]], 'non-scalar args');
failPayload($current, ['voice' => ['waninterface' => []]], 'non-scalar WAN');
failPayload($current, ['voice' => ['foo' => ['enabled' => '1']]], 'unknown service');
failPayload($current, ['hostlist' => ['xips' => ['8.8.8.8']]], 'non-scalar IPSET');

// Reversal: existing Strategies form must also reject Voice values.
try {
    StrategySettingsPayload::overlay($current, ['voice' => ['telegram' => ['enabled' => '0']]]);
    fwrite(STDERR, "FAIL: Strategies accepted Voice injection\n");
    exit(1);
} catch (\InvalidArgumentException $exception) {
}

echo "PASS: Voice and Strategies own separate settings; shared Telegram baseline is checked\n";
