<?php
/** G11 LC-06D: a verified no-runtime, unchanged inert form gets one exact
 * diagnostic. WAN-first and actual WAN-only Save retain their ownership.
 * No network, Config, pkg, process or IPFW mutation.
 */
require_once dirname(__DIR__) . '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';
use OPNsense\Zapret\Api\SettingsApply;

function chk(bool $ok, string $why): void {
    if (!$ok) {
        fwrite(STDERR, "G11_EMPTY_RUNTIME_FAIL:$why\n");
        exit(1);
    }
}
$zero = [
    'general' => ['enabled' => '0', 'waninterface' => '',
                  'ports' => '80,443', 'divertport' => '989'],
    'strategy' => ['trafficargs' => '', 'httpargs' => '',
                   'httpsargs' => '', 'extraargs' => ''],
    'hostlist' => ['mode' => 'all', 'domains' => '', 'youtubedomains' => '',
                   'telegramips' => '', 'discordips' => '', 'xips' => '',
                   'sipips' => '', 'customips' => '', 'userdomains' => '',
                   'excludedomains' => '', 'excludeipset' => ''],
    'voice' => [
        'telegram' => ['enabled' => '0', 'args' => '--filter-udp=*'],
        'discord' => ['enabled' => '0', 'args' => ''],
        'x' => ['enabled' => '0', 'args' => ''],
        'sip' => ['enabled' => '0', 'args' => ''],
        'custom' => ['enabled' => '0', 'args' => ''],
    ],
];
$plan = ['result' => 'prepared', 'candidate' => $zero, 'changed_fields' => []];
$clean = "installed=0\nservice=error\nversion=\nsetup=unknown\nbusy=0";
chk(SettingsApply::isPassiveStrategiesPlan($plan),
    'an unchanged empty passive candidate was rejected');
foreach (['unknown', 'failed', 'ready'] as $setup) {
    $receipt = str_replace('setup=unknown', 'setup=' . $setup, $clean);
    chk(SettingsApply::isVerifiedMissingUpstream($receipt),
        'real installed=0 with an old setup receipt was rejected');
}
foreach ([
    '', "installed=0\nservice=error\nversion=\nsetup=unknown",
    "installed=0\nservice=error\nversion=\nsetup=installing\nbusy=1",
    "installed=0\nservice=error\nversion=\nsetup=installing\nbusy=0",
    "installed=1\nservice=started\nversion=v1.0.7\nsetup=ready\nbusy=0",
    $clean . "\nextra=1",
    $clean . "\ninstalled=0",
    str_replace('busy=0', 'busy=1', $clean),
] as $bad) {
    chk(!SettingsApply::isVerifiedMissingUpstream($bad),
        'malformed, busy, active or uncertain status treated as absent');
}
$wan = $plan;
$wan['changed_fields'] = ['general.waninterface'];
$wan['candidate']['general']['waninterface'] = 'wan';
chk(!SettingsApply::isPassiveStrategiesPlan($wan),
    'WAN-only Save incorrectly blocked by runtime installation');
$wanMixed = $wan;
$wanMixed['changed_fields'] = ['general.waninterface', 'strategy.trafficargs'];
chk(!SettingsApply::isPassiveStrategiesPlan($wanMixed),
    'WAN edit mixed with Strategies must not skip WAN validation');

$active = $plan;
$active['candidate']['general']['enabled'] = '1';
chk(!SettingsApply::isPassiveStrategiesPlan($active),
    'active candidate must follow WAN-first/normal activation');
$voice = $plan;
$voice['candidate']['voice']['telegram']['enabled'] = '1';
chk(!SettingsApply::isPassiveStrategiesPlan($voice),
    'active Voice-only candidate bypassed WAN-first');
$seeded = $plan;
$seeded['candidate']['strategy']['trafficargs'] =
    "--filter-tcp=80,443\n--filter-l7=http,tls\n--new\n--filter-udp=443";
$seeded['candidate']['hostlist']['youtubedomains'] =
    "youtube.com\ngooglevideo.com\nyoutu.be";
chk(SettingsApply::isPassiveStrategiesPlan($seeded),
    'real first-install preseeded passive Strategies incorrectly rejected');
$clearing = $seeded;
$clearing['candidate']['strategy']['trafficargs'] = '';
$clearing['candidate']['hostlist']['youtubedomains'] = '';
$clearing['changed_fields'] = [
    'strategy.trafficargs', 'hostlist.youtubedomains',
];
chk(SettingsApply::isPassiveStrategiesPlan($clearing),
    'user clear form is still incorrectly treated as not an inert Apply');
$edit = $seeded;
$edit['changed_fields'] = ['strategy.trafficargs'];
$edit['candidate']['strategy']['trafficargs'] = "--filter-tcp=443";
chk(SettingsApply::isPassiveStrategiesPlan($edit),
    'non-mutating service warning did not cover passive user strategy edit');
$broken = $plan;
unset($broken['candidate']['voice']['custom']);
chk(!SettingsApply::isPassiveStrategiesPlan($broken),
    'missing Voice section accepted as a complete model');
$broken = $plan;
unset($broken['candidate']['general']);
chk(!SettingsApply::isPassiveStrategiesPlan($broken),
    'missing General model accepted');
$invalid = $plan;
$invalid['candidate']['general']['enabled'] = [
    'on' => ['selected' => 1], 'off' => ['selected' => 1],
];
chk(!SettingsApply::isPassiveStrategiesPlan($invalid),
    'ambiguous OPNsense option map accepted');

$source = file_get_contents(dirname(__DIR__) .
    '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php');
$view = file_get_contents(dirname(__DIR__) .
    '/src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt');
$wanFirst = strpos($source, "WanRequirement::missingBeforeActivation(\$plan['candidate'])");
$proof = strpos($source, 'SettingsApply::isPassiveStrategiesPlan($plan)');
$liveReceipt = strpos($source, "'zapret setup_status'");
$wanOnly = strpos($source, "\$wanOnlyCandidate = \$plan['changed_fields'] === ['general.waninterface']");
$dispatch = strpos($source, '$nativeApplyDispatched = true;');
chk($wanFirst !== false && $wanOnly !== false && $proof !== false &&
    $liveReceipt !== false && $dispatch !== false &&
    $wanFirst < $wanOnly && $wanOnly < $proof &&
    $proof < $liveReceipt && $liveReceipt < $dispatch,
    'LC-06D did not preserve WAN-first and native no-write preflight order');
chk(strpos($source, "gettext('The zapret2 service must be installed')") !== false &&
    strpos($view, "'The zapret2 service must be installed': 'Требуется установка службы zapret2'") !== false,
    'exact required English/Russian GUI error is not wired');
echo "PASS_G11_EMPTY_RUNTIME_APPLY_WAN_FIRST=1\n";
