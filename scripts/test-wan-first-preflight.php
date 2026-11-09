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
$phase=null;
try {
    SharedApplyRequest::prepare(['page'=>'strategies','fields'=>[],
        'sync'=>['telegramips_baseline'=>'']],$active,'<broken-strategy',$phase);
    wanAssert(false,'invalid candidate masked missing WAN');
} catch (\InvalidArgumentException $e) {
    wanAssert($phase==='wan-required','WAN not first candidate preflight');
}
echo "PASS: WAN-first inactive Save, candidate, Voice, TUN\n";
