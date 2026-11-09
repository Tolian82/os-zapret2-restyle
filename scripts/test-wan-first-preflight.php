<?php
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/WanRequirement.php';
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php';
use OPNsense\Zapret\Api\WanRequirement;
use OPNsense\Zapret\Native\SharedApplyRequest;
function wanAssert(bool $condition, string $message): void {
    if (!$condition) { fwrite(STDERR, "FAIL WAN-FIRST: $message\n"); exit(1); }
}
$empty=['general'=>['enabled'=>'0','waninterface'=>''],
    'voice'=>['telegram'=>['enabled'=>'0']]];
wanAssert(!WanRequirement::missingBeforeActivation($empty),'disabled settings Save blocked');
$active=$empty; $active['general']['enabled']='1';
wanAssert(WanRequirement::missingBeforeActivation($active),'missing WAN bypassed');
wanAssert(!WanRequirement::missingBeforeActivation($active,
    ['general'=>['waninterface'=>'wan']]),'same-Apply WAN blocked');
wanAssert(WanRequirement::missingBeforeActivation($empty,
    ['voice'=>['telegram'=>['enabled'=>'1']]]),'Voice-only bypassed');
wanAssert(WanRequirement::effectiveWan($empty,
    ['general'=>['waninterface'=>'opt0']])==='opt0','TUN selection lost');
$native = $active;
$native['general']['waninterface'] = [
    'wan'=>['selected'=>'0'], 'lo0'=>['selected'=>'1'],
    'opt0'=>['selected'=>'0'],
];
wanAssert(WanRequirement::effectiveWan($native)==='lo0',
    'native OPNsense selected-option InterfaceField was misread');
wanAssert(!WanRequirement::missingBeforeActivation($native),
    'native selected WAN incorrectly reported missing');
$native['general']['waninterface'] = [
    'wan'=>['selected'=>'0'], 'lo0'=>['selected'=>'0'],
];
wanAssert(WanRequirement::missingBeforeActivation($native),
    'no native selected WAN incorrectly accepted');
$phase=null;
try {
    SharedApplyRequest::prepare(['page'=>'strategies','fields'=>[],
        'sync'=>['telegramips_baseline'=>'']],$active,'<broken-strategy',$phase);
    wanAssert(false,'invalid candidate masked missing WAN');
} catch (\InvalidArgumentException $e) {
    wanAssert($phase==='wan-required','WAN not first candidate preflight');
}
// Internal inherited-FD9 Lab start must not skip the same prerequisite.
$serviceSource = file_get_contents(__DIR__ .
    '/../src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh');
$labStart = strpos($serviceSource, "        strategy-lab-start)\n");
wanAssert($labStart !== false, 'internal Laboratory start entry is missing');
$labTail = substr($serviceSource, $labStart, 420);
$labGate = strpos($labTail, 'wan_first_service require');
$labOwner = strpos($labTail, 'if shared_apply_has_record_service; then');
wanAssert($labGate !== false && $labOwner !== false && $labGate < $labOwner,
    'inherited-FD9 Laboratory start can bypass WAN-first before runtime');
echo "PASS: WAN-first inactive Save, candidate, Voice, TUN, internal Lab\n";
