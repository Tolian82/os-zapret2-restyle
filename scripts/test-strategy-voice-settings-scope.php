<?php

/**
 * Native Strategies POST scoping regression; intentionally independent of
 * OPNsense services, XML config and the actual router.
 */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategySettingsPayload.php';

use OPNsense\Zapret\Api\StrategySettingsPayload;

function assertSameDeep($expected, $actual, $label)
{
    if ($expected !== $actual) {
        fwrite(STDERR, "FAIL: " . $label . "\n" . var_export($actual, true) . "\n");
        exit(1);
    }
}

function reject($current, $payload, $label)
{
    try {
        StrategySettingsPayload::overlay($current, $payload);
    } catch (\InvalidArgumentException $e) {
        return;
    }
    fwrite(STDERR, "FAIL: accepted " . $label . "\n");
    exit(1);
}

$current = [
    'general' => ['enabled' => '1', 'waninterface' => 'WAN', 'divertport' => '989', 'ports' => '80,443'],
    'strategy' => [
        'httpargs' => 'legacy', 'trafficargs' => '--filter-tcp=443',
        'extraargs' => '',
    ],
    'voice' => [
        'waninterface' => 'WAN',
        'telegram' => ['enabled' => '1', 'args' => '--filter-udp=*'],
        'discord' => ['enabled' => '0', 'args' => 'draft'],
    ],
    'strategylab' => ['enablequic' => '1'],
    'hostlist' => [
        'mode' => 'auto', 'telegramips' => '91.108.0.0/16',
        'discordips' => '203.0.113.0/24', 'xips' => '192.0.2.0/24',
        'sipips' => '', 'customips' => '198.51.100.0/24',
        'excludedomains' => 'nalog.ru',
    ],
];

$post = [
    'general' => ['enabled' => '0', 'waninterface' => 'WAN'],
    'strategy' => ['trafficargs' => '--filter-udp=596-599'],
    'hostlist' => ['mode' => 'list', 'telegramips' => '91.108.13.10'],
];
$expected = $current;
$expected['general']['enabled'] = '0';
$expected['strategy']['trafficargs'] = '--filter-udp=596-599';
$expected['hostlist']['mode'] = 'list';
$expected['hostlist']['telegramips'] = '91.108.13.10';

assertSameDeep($expected, StrategySettingsPayload::overlay($current, $post),
    'Strategies overlay must update submitted values and retain Voice/legacy/unrelated lists');
assertSameDeep($current, StrategySettingsPayload::overlay($current, []),
    'empty Strategies form must preserve entire model');
assertSameDeep('1', $current['voice']['telegram']['enabled'], 'source snapshot was modified');

reject($current, ['voice' => ['telegram' => ['enabled' => '0']]], 'Voice tampering');
reject($current, ['hostlist' => ['discordips' => '1.1.1.1']], 'Discord IPSET tampering');
reject($current, ['strategylab' => ['enablequic' => '0']], 'Strategy Lab tampering');
reject($current, ['strategy' => ['httpargs' => 'legacy change']], 'legacy profile field tampering');
reject($current, ['general' => ['enabled' => ['1']]], 'non-scalar enabled');
reject($current, ['general' => null], 'non-map group');
reject($current, ['other' => []], 'unrecognized section');

echo "PASS: Strategies Apply is scoped; Voice, other IPSETs and Strategy Lab remain unchanged\n";
