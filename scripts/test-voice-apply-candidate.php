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
        'voice' => array_diff_key($record['voice'], ['waninterface' => true]),
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
$form['hostlist']['telegramips'] = "91.108.0.0/16\r\n91.108.13.10/32\r\n91.108.13.10\r\n91.108.13.10/32\r\n";

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
       'retired Voice WAN form submission must be rejected');
$legacy = $before;
$legacy['voice']['waninterface'] = 'WAN2';
$legacyPlan = VoiceApplyCandidate::prepare(
    $legacy, $form, VoiceSettingsSnapshot::digest($legacy)
);
verify($legacyPlan['result'] === 'prepared' &&
       $legacyPlan['candidate']['voice']['waninterface'] === 'WAN2' &&
       !in_array('voice.waninterface', $legacyPlan['changed_fields'], true),
       'saved historical Voice override must not block inherited Strategies WAN');
$wanMissing = $before;
$wanMissing['general']['waninterface'] = '';
$missing = VoiceApplyCandidate::prepare(
    $wanMissing, $form, VoiceSettingsSnapshot::digest($wanMissing)
);
verify($missing['result'] === 'failed' &&
       isset($missing['validations']['zapret.voice.waninterface']),
       'missing Strategies WAN must fail before Apply');

// Inactive-only drafts are editable before the Strategies WAN is selected.
// Historical saved Voice WAN overrides are inert and retained unchanged.
$offline = $before;
$offline['general']['waninterface'] = '';
$offline['voice']['waninterface'] = 'WAN2';
$offlineForm = formFrom($offline);
$offlineForm['voice']['discord']['args'] = "unfinished STUN parameters";
$offlineForm['hostlist']['discordips'] = "203.0.113.0/24";
$offlinePlan = VoiceApplyCandidate::prepare(
    $offline, $offlineForm, VoiceSettingsSnapshot::digest($offline)
);
verify($offlinePlan['result'] === 'prepared' &&
       $offlinePlan['enabled_services'] === [] &&
       $offlinePlan['candidate']['general']['waninterface'] === '' &&
       $offlinePlan['candidate']['voice']['waninterface'] === 'WAN2' &&
       $offlinePlan['candidate']['voice']['discord']['args'] === "unfinished STUN parameters" &&
       $offlinePlan['candidate']['hostlist']['discordips'] === "203.0.113.0/24",
       'inactive Voice drafts must remain editable without a configured Strategies WAN');
$offlineForm['voice']['telegram']['enabled'] = '1';
$offlineForm['voice']['telegram']['args'] = $telegram;
$offlineRejected = VoiceApplyCandidate::prepare(
    $offline, $offlineForm, VoiceSettingsSnapshot::digest($offline)
);
verify($offlineRejected['result'] === 'failed' &&
       isset($offlineRejected['validations']['zapret.voice.waninterface']),
       'enabling Voice must still reject an unconfigured Strategies WAN');

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

// A native Config writer must preserve unrelated concurrent edits while
// refusing to accept old shared Strategies/Voice/runtime inputs.
$foreignNow = $before;
$foreignNow['strategylab']['enablequic'] = '0';
$strategyMerged = SettingsApply::mergeForCommit($foreignNow, $strategyPlan, 'strategies');
verify($strategyMerged['strategylab']['enablequic'] === '0' &&
       $strategyMerged['voice'] === $before['voice'] &&
       $strategyMerged['strategy']['trafficargs'] ===
           $strategyPlan['candidate']['strategy']['trafficargs'],
       'native Strategies merge lost unrelated state');
$voiceForm = formFrom($before);
$voiceForm['voice']['telegram'] = ['enabled'=>'1', 'args'=>$telegram];
$voiceForm['hostlist']['telegramips'] = '91.108.13.10';
$voiceMergePlan = SettingsApply::prepareVoice($before, $voiceForm, $token);
verify($voiceMergePlan['result'] === 'prepared', 'Voice commit plan failed');
$voiceMerged = SettingsApply::mergeForCommit($foreignNow, $voiceMergePlan, 'voice');
verify($voiceMerged['strategylab']['enablequic'] === '0' &&
       $voiceMerged['voice']['telegram']['enabled'] === '1' &&
       $voiceMerged['strategy'] === $before['strategy'],
       'native Voice merge lost unrelated state');
$corrupt = $strategyPlan;
$corrupt['candidate']['voice']['telegram']['enabled'] = '1';
try {
    SettingsApply::mergeForCommit($foreignNow, $corrupt, 'strategies');
    verify(false, 'foreign Voice injection accepted');
} catch (\InvalidArgumentException $ex) {}
$staleModel = $foreignNow;
$staleModel['general']['divertport'] = '990';
try {
    SettingsApply::mergeForCommit($staleModel, $strategyPlan, 'strategies');
    verify(false, 'stale shared divertport accepted');
} catch (\InvalidArgumentException $ex) {}
$missing = $strategyPlan;
$missing['changed_fields'] = [];
try {
    SettingsApply::mergeForCommit($foreignNow, $missing, 'strategies');
    verify(false, 'missing changed field accepted');
} catch (\InvalidArgumentException $ex) {}

echo "PASS: shared Strategies/Voice candidate and dependency generation; Voice normalization/conflict/stale\n";
