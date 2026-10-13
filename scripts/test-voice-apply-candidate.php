<?php
/**
 * Side-effect-free future Voice Apply planning tests; no router connection.
 */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceApplyCandidate.php';
use OPNsense\Zapret\Api\VoiceApplyCandidate;
use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

function verify(bool $pass, string $message): void {
    if (!$pass) {
        fwrite(STDERR, "FAIL: {$message}\n");
        exit(1);
    }
}

function records(): array {
    $voice = ['waninterface' => 'WAN'];
    $ips = [];
    foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $name) {
        $voice[$name] = ['enabled' => '0', 'args' => ''];
        $ips[$name . 'ips'] = '';
    }
    return [
        'general' => ['enabled' => '1', 'waninterface' => 'WAN', 'divertport' => '989'],
        'strategy' => ['trafficargs' => "--filter-tcp=443\n--payload=tls_client_hello"],
        'hostlist' => [
            'telegramips' => "91.108.0.0/16\n",
            'youtubedomains' => "youtube.com\n",
            'userdomains' => 'example.org',
            'excludedomains' => '',
            'mode' => 'list',
        ] + $ips,
        'voice' => $voice,
        'strategylab' => ['enablequic' => '1'],
    ];
}

function formFrom(array $record): array {
    return [
        'voice' => $record['voice'],
        'hostlist' => [
            'telegramips' => $record['hostlist']['telegramips'],
            'discordips' => $record['hostlist']['discordips'],
            'xips' => $record['hostlist']['xips'],
            'sipips' => $record['hostlist']['sipips'],
            'customips' => $record['hostlist']['customips'],
        ],
    ];
}

$before = records();
$token = VoiceSettingsSnapshot::digest($before);
$form = formFrom($before);
$telegram = "--filter-udp=596-599\n--filter-l7=stun\n--payload=stun\n";
$form['voice']['telegram'] = ['enabled' => '1', 'args' => $telegram];
$form['hostlist']['telegramips'] = "91.108.0.0/16\r\n91.108.13.10\r\n91.108.13.10\r\n";

$plan = VoiceApplyCandidate::prepare($before, $form, $token);
verify($plan['result'] === 'prepared', 'valid Voice candidate failed');
verify($plan['enabled_services'] === ['telegram'], 'unexpected enabled services');
verify($plan['target_counts']['telegram'] === 2, 'duplicate IPSET should normalize to 2');
verify($plan['candidate']['hostlist']['telegramips'] === "91.108.0.0/16\n91.108.13.10",
       'enabled IPSET normalization is incorrect');
verify($plan['candidate']['voice']['telegram']['args'] === $telegram, 'STUN option data modified');
verify(in_array('voice.telegram.enabled', $plan['changed_fields'], true),
       'change map omitted enabled flag');
verify(in_array('hostlist.telegramips', $plan['changed_fields'], true),
       'change map omitted normalized IPSET');
verify($plan['candidate']['hostlist']['youtubedomains'] === "youtube.com\n" &&
       $plan['candidate']['general'] === $before['general'] &&
       $plan['candidate']['strategy'] === $before['strategy'] &&
       $plan['candidate']['strategylab'] === $before['strategylab'],
       'candidate changed unrelated saved settings');
verify($before === records(), 'pure prepare mutated current configuration');

$form['voice']['discord']['args'] = "--new\n--filter-l7=not-stun";
$form['hostlist']['discordips'] = "203.0.113.7";
$draft = VoiceApplyCandidate::prepare($before, $form, $token);
verify($draft['result'] === 'prepared', 'disabled invalid STUN draft was incorrectly rejected');
verify($draft['candidate']['voice']['discord']['args'] === $form['voice']['discord']['args'] &&
       $draft['candidate']['hostlist']['discordips'] === '203.0.113.7',
       'disabled drafts must survive without syntax validation');

$wanMismatch = $form;
$wanMismatch['voice']['waninterface'] = 'WAN2';
$wan = VoiceApplyCandidate::prepare($before, $wanMismatch, $token);
verify($wan['result'] === 'failed' &&
       isset($wan['validations']['zapret.voice.waninterface']),
       'independent Voice WAN must fail before a candidate is accepted');
$wanMissing = $before;
$wanMissing['general']['waninterface'] = '';
$missing = VoiceApplyCandidate::prepare(
    $wanMissing, $form, VoiceSettingsSnapshot::digest($wanMissing)
);
verify($missing['result'] === 'failed' &&
       isset($missing['validations']['zapret.voice.waninterface']),
       'missing Strategies WAN must fail before Apply');

$changed = $before;
$changed['strategy']['trafficargs'] .= "\n--new";
try {
    VoiceApplyCandidate::prepare($changed, $form, $token);
    verify(false, 'stale model token incorrectly accepted');
} catch (\InvalidArgumentException $ex) {
    verify(str_contains($ex->getMessage(), 'changed'), 'stale token wrong error');
}

$form['voice']['discord']['enabled'] = '1';
$form['voice']['discord']['args'] = $telegram;
$form['hostlist']['discordips'] = "91.108.13.10";
$bad = VoiceApplyCandidate::prepare($before, $form, $token);
verify($bad['result'] === 'failed' &&
       isset($bad['validations']['zapret.voice.discord.enabled']),
       'overlapping destinations+port must fail closed');

$form = formFrom($before);
$form['hostlist']['telegramips'] = '';
$form['voice']['telegram']['enabled'] = '0';
$form['voice']['telegram']['args'] = '--new';
$allOff = VoiceApplyCandidate::prepare($before, $form, $token);
verify($allOff['result'] === 'prepared' &&
       $allOff['candidate']['voice']['telegram']['args'] === '--new' &&
       $allOff['candidate']['hostlist']['telegramips'] === '',
       'OFF should preserve even an incomplete draft and blank IPSET');

$foreign = VoiceApplyCandidate::prepare(
    $before, $form + ['general'=>['enabled'=>'0']], $token
);
verify($foreign['result'] === 'failed' &&
       isset($foreign['validations']['zapret.voice.waninterface']),
       'foreign model group unexpectedly accepted');

// Stage 3: both public pages prepare a full model through the same boundary.
$strategyForm = [
    'general' => ['waninterface' => 'WAN'],
    'strategy' => ['trafficargs' => "--filter-tcp=80\n--payload=http_req"],
    'hostlist' => ['telegramips' => "91.108.0.0/16\n"],
];
$strategyPlan = SettingsApply::prepareStrategies(
    $before, $strategyForm, $before['hostlist']['telegramips']
);
verify($strategyPlan['result'] === 'prepared', 'Strategies shared candidate failed');
verify($strategyPlan['candidate']['voice'] === $before['voice'] &&
       $strategyPlan['candidate']['hostlist']['discordips'] === $before['hostlist']['discordips'] &&
       $strategyPlan['candidate']['strategylab'] === $before['strategylab'],
       'Strategies candidate overwrote a foreign field');
verify($strategyPlan['changed_fields'] === ['strategy.trafficargs'],
       'Strategies change map must list only changed owned fields');
SettingsApply::requireUnchanged($strategyPlan, $before);
$unrelated = $before;
$unrelated['strategylab']['enablequic'] = '0';
SettingsApply::requireUnchanged($strategyPlan, $unrelated);
$stale = $before;
$stale['voice']['telegram']['enabled'] = '1';
try {
    SettingsApply::requireUnchanged($strategyPlan, $stale);
    verify(false, 'shared candidate accepted changed Voice dependencies');
} catch (\InvalidArgumentException $ex) {
    verify(str_contains($ex->getMessage(), 'changed'), 'wrong shared stale failure');
}
$voicePlan = SettingsApply::prepareVoice($before, formFrom($before), $token);
verify($voicePlan['result'] === 'prepared', 'Voice shared candidate failed');
SettingsApply::requireUnchanged($voicePlan, $before);
try {
    SettingsApply::prepareStrategies($before, ['voice' => ['telegram' => '1']],
        $before['hostlist']['telegramips']);
    verify(false, 'foreign Strategies fields accepted by shared boundary');
} catch (\InvalidArgumentException $ex) {
    verify(str_contains($ex->getMessage(), 'Unexpected'), 'wrong Strategies whitelist failure');
}
try {
    SettingsApply::prepareStrategies($before, $strategyForm, '91.108.99.0/24');
    verify(false, 'stale shared Telegram IPSET baseline accepted');
} catch (\InvalidArgumentException $ex) {
    verify(str_contains($ex->getMessage(), 'changed'), 'wrong Telegram stale failure');
}
echo "PASS: shared Strategies/Voice candidate and dependency generation; Voice normalization/conflict/stale\n";
