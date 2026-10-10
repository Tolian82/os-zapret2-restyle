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


// A second GUI tab may change the shared Telegram IPSET while Strategies is
// still open; the original Strategies data must no longer overwrite it.
StrategySettingsPayload::requireFreshTelegram($current, "91.108.0.0/16");
StrategySettingsPayload::requireFreshTelegram($current, "91.108.0.0/16\r\n");
foreach (["203.0.113.0/24", null, "", 12] as $stale) {
    try {
        StrategySettingsPayload::requireFreshTelegram($current, $stale);
        fwrite(STDERR, "FAIL: stale/missing Telegram baseline accepted\n");
        exit(1);
    } catch (\InvalidArgumentException $exception) {
        // Correct: fail before model setNodes() and save().
    }
}
$controller = file_get_contents(__DIR__ .
    '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php');
$view = file_get_contents(__DIR__ .
    '/../src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt');
if (strpos($controller, "requireFreshTelegram(\$oldNodes, \$baseline)") === false ||
    strpos($controller, "unset(\$post['sync'])") === false ||
    strpos($view, 'zapret.sync.telegramips_baseline') === false ||
    strpos($view, 'telegramBaseline.val(currentField ? currentField.value') === false
) {
    fwrite(STDERR, "FAIL: Strategies Apply optimistic lock not wired through GUI+API\n");
    exit(1);
}

echo "PASS: Strategies Apply is scoped; Voice/other IPSETs remain unchanged and shared Telegram updates require a fresh baseline\n";
