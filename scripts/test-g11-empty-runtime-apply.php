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
chk(SettingsApply::isInertEmptyStrategiesPlan($plan),
    'a genuinely empty/no-change inert candidate was rejected');
chk(SettingsApply::isVerifiedMissingUpstream($clean),
    'genuine native no-runtime receipt was rejected');
foreach ([
    '', "installed=0\nservice=error\nversion=\nsetup=unknown",
    "installed=0\nservice=error\nversion=\nsetup=failed\nbusy=0",
    "installed=0\nservice=error\nversion=\nsetup=installing\nbusy=1",
    "installed=1\nservice=started\nversion=v1.0.7\nsetup=ready\nbusy=0",
    $clean . "\nextra=1",
] as $bad) {
    chk(!SettingsApply::isVerifiedMissingUpstream($bad),
        'malformed, busy, active or unknown runtime treated as missing');
}
$wan = $plan;
$wan['changed_fields'] = ['general.waninterface'];
$wan['candidate']['general']['waninterface'] = 'wan';
chk(!SettingsApply::isInertEmptyStrategiesPlan($wan),
    'WAN-only Save mistaken for inert no-op');
$active = $plan;
$active['candidate']['general']['enabled'] = '1';
chk(!SettingsApply::isInertEmptyStrategiesPlan($active),
    'active enabled candidate received no-runtime shortcut before WAN-first');
$voice = $plan;
$voice['candidate']['voice']['telegram']['enabled'] = '1';
chk(!SettingsApply::isInertEmptyStrategiesPlan($voice),
    'active Voice-only candidate bypassed WAN-first');
foreach ([
    ['strategy', 'trafficargs', '--filter-tcp=443'],
    ['hostlist', 'youtubedomains', 'youtube.com'],
    ['hostlist', 'excludeipset', '192.0.2.0/24'],
    ['hostlist', 'discordips', '192.0.2.1/32'],
] as [$group, $field, $value]) {
    $configured = $plan;
    $configured['candidate'][$group][$field] = $value;
    chk(!SettingsApply::isInertEmptyStrategiesPlan($configured),
        'nonempty persisted data mistaken for fully empty');
}
$broken = $plan;
unset($broken['candidate']['voice']['custom']);
chk(!SettingsApply::isInertEmptyStrategiesPlan($broken),
    'missing Voice section accepted as an inert complete model');
$broken = $plan;
unset($broken['candidate']['general']);
chk(!SettingsApply::isInertEmptyStrategiesPlan($broken),
    'missing general section accepted as a valid empty model');
$untrusted = $plan;
$untrusted['candidate']['general']['enabled'] = ['on' => ['selected' => 1],
                                               'off' => ['selected' => 1]];
chk(!SettingsApply::isInertEmptyStrategiesPlan($untrusted),
    'ambiguous native model accepted');
$source = file_get_contents(dirname(__DIR__) .
    '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php');
$view = file_get_contents(dirname(__DIR__) .
    '/src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt');
$wanFirst = strpos($source, "WanRequirement::missingBeforeActivation(\$plan['candidate'])");
$proof = strpos($source, 'SettingsApply::isInertEmptyStrategiesPlan($plan)');
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
