<?php
/**
 * Detached native Strategies/Voice candidate from the single Config snapshot.
 * Pure tests deliberately do not load OPNsense bootstrap or write active Config.
 */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php';

use OPNsense\Zapret\Native\SharedApplyRequest as Request;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot as Snapshot;

function must(bool $pass, string $reason): void {
    if (!$pass) { fwrite(STDERR, "FAIL: $reason\n"); exit(1); }
}
function rejects(callable $run, string $reason): void {
    try { $run(); }
    catch (\InvalidArgumentException $expected) { return; }
    throw new \RuntimeException("FAIL: $reason");
}
$all = [
    'general'=>['enabled'=>'1','waninterface'=>'WAN','divertport'=>'989'],
    'strategy'=>['trafficargs'=>'--filter-tcp=443','extraargs'=>''],
    'hostlist'=>['mode'=>'list','telegramips'=>'91.108.0.0/16',
        'youtubedomains'=>'','userdomains'=>'example.org','excludedomains'=>'',
        'discordips'=>'','xips'=>'','sipips'=>'','customips'=>''],
    'voice'=>['waninterface'=>'WAN'],
    'strategylab'=>['enablequic'=>'1'],
];
foreach (['telegram','discord','x','sip','custom'] as $svc) {
    $all['voice'][$svc]=['enabled'=>'0','args'=>'--filter-udp=*'];
}
$active = '<?xml version="1.0"?><opnsense><system><hostname>keep</hostname></system>' .
    '<OPNsense><Unboundplus><enabled>1</enabled></Unboundplus><Zapret>' .
    '<general><enabled>1</enabled><waninterface>WAN</waninterface>' .
    '<divertport>989</divertport></general><strategy>' .
    '<trafficargs>--filter-tcp=443</trafficargs><extraargs/></strategy>' .
    '<voice><waninterface>WAN</waninterface>';
foreach (['telegram','discord','x','sip','custom'] as $svc) {
    $active .= "<$svc><enabled>0</enabled><args>--filter-udp=*</args></$svc>";
}
$active .= '</voice><hostlist><telegramips>91.108.0.0/16</telegramips></hostlist>' .
    '<strategylab><enablequic>1</enablequic></strategylab></Zapret>' .
    '</OPNsense></opnsense>';
$raw = json_encode([
    'page'=>'strategies',
    'fields'=>['strategy'=>['trafficargs'=>'--filter-tcp=80']],
    'sync'=>['telegramips_baseline'=>'91.108.0.0/16'],
],JSON_THROW_ON_ERROR);
$input=rtrim(strtr(base64_encode($raw),'+/','-_'),'=');
$parsed=Request::decode($input);
must($parsed['page']==='strategies','request parse');
$out=Request::prepare($parsed,$all,$active);
must(str_contains($out['xml'],'<trafficargs>--filter-tcp=80</trafficargs>'),
    'Strategies candidate did not generate detached runtime XML');
must(str_contains($out['xml'],'<hostname>keep</hostname>') &&
    str_contains($out['xml'],'<Unboundplus><enabled>1</enabled></Unboundplus>'),
    'detached Config erased unrelated OPNsense services');
must($out['plan']['page']==='strategies', 'saved plan lost Strategies page ownership');
must($out['plan']['dependencies']===Snapshot::digest($all),
    'detached candidate generation not pinned to native model');
must(str_contains($active,'<trafficargs>--filter-tcp=443</trafficargs>'),
    'original native XML was changed');
$completeVoice = $all['voice'];
$completeHostlists = [];
foreach (['telegram','discord','x','sip','custom'] as $svc) {
    $completeHostlists[$svc . 'ips'] = $all['hostlist'][$svc . 'ips'];
}
$completeVoice['telegram']['enabled'] = '1';
$completeVoice['telegram']['args'] =
    "--filter-udp=*\n--filter-l7=stun\n--payload=stun\n" .
    "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2";
$completeHostlists['telegramips'] = '91.108.13.10';
$voiceInput=['page'=>'voice',
    'fields'=>['voice'=>$completeVoice, 'hostlist'=>$completeHostlists],
    'sync'=>['snapshot'=>Snapshot::digest($all)]];
$voice= Request::prepare($voiceInput,$all,$active);
must($voice['plan']['page']==='voice', 'saved plan lost Voice page ownership');
must(str_contains($voice['xml'],'<telegram><enabled>1</enabled>') &&
    str_contains($voice['xml'],'<telegramips>91.108.13.10</telegramips>'),
    'Voice ON did not create isolated native XML');
must(str_contains($voice['xml'],'<trafficargs>--filter-tcp=443</trafficargs>'),
    'Voice candidate changed ordinary Strategies');
$stale=$voiceInput;
$stale['sync']['snapshot']=str_repeat('0',64);
rejects(fn()=>Request::prepare($stale,$all,$active),
        'stale Voice baseline accepted');
rejects(fn()=>Request::decode('a/b'), 'non-base64url syntax accepted');
rejects(fn()=>Request::decode($input.'='), 'noncanonical encoding accepted');
$foreign=['page'=>'strategies','fields'=>['voice'=>['telegram'=>['enabled'=>'1']]],
         'sync'=>['telegramips_baseline'=>'91.108.0.0/16']];
rejects(fn()=>Request::prepare($foreign,$all,$active),'foreign Voice write via Strategies');
// Legacy configctl compatibility must use the SAME Voice envelope, not the
// Phase-B marker/strategy. Preserve every other profile and IPSET unchanged.
$native = $all;
$native['voice']['telegram']['args'] =
    "--filter-udp=3478\n--filter-l7=stun\n--payload=stun";
$native['hostlist']['telegramips'] = "91.108.13.10";
$compat = Request::decode(Request::telegramEnvelope($native, 'enable'));
must($compat['page'] === 'voice' && $compat['sync']['snapshot'] === Snapshot::digest($native),
     'Telegram adapter bypassed shared Voice snapshot/whitelist');
must($compat['fields']['voice']['telegram']['enabled'] === '1' &&
     $compat['fields']['voice']['telegram']['args'] === $native['voice']['telegram']['args'],
     'Telegram adapter did not reuse saved native STUN parameters');
foreach (['discord','x','sip','custom'] as $service) {
    must($compat['fields']['voice'][$service] === $native['voice'][$service] &&
         $compat['fields']['hostlist'][$service.'ips'] === $native['hostlist'][$service.'ips'],
         'Telegram compatibility overwrote a foreign Voice service');
}
must(Request::prepare($compat, $native, $active)['plan']['changed_fields'] ===
     ['voice.telegram.enabled'], 'Telegram ON touched unrelated Config');
$disabled = $native;
$disabled['voice']['telegram']['enabled'] = '1';
$off = Request::decode(Request::telegramEnvelope($disabled, 'disable'));
must($off['fields']['voice']['telegram']['enabled'] === '0' &&
     $off['fields']['voice']['discord'] === $disabled['voice']['discord'],
     'Telegram OFF changed another service');
must(Request::telegramSaved($disabled) ===
     ['requested'=>'on','snapshot'=>Snapshot::digest($disabled)] &&
     Request::telegramSaved($native)['requested'] === 'off',
     'Telegram status inferred intent from an old PoC marker');
rejects(fn()=>Request::telegramEnvelope($native, 'toggle'),
        'foreign compatibility action accepted');
$noProfile = $native;
$noProfile['voice']['telegram']['args'] = '';
rejects(fn()=>Request::telegramEnvelope($noProfile, 'enable'),
        'adapter invented a hardcoded PoC profile without saved STUN');
$otherChanged = $native;
$otherChanged['voice']['discord']['enabled'] = '1';
$otherChanged['voice']['discord']['args'] =
    "--filter-udp=3478\n--filter-l7=stun\n--payload=stun";
$otherChanged['hostlist']['discordips'] = "203.0.113.3/32\n";
rejects(fn()=>Request::telegramEnvelope($otherChanged, 'enable'),
        'Telegram adapter normalized or modified an independently enabled service');

echo "PASS: one scoped detached native Config candidate, fresh snapshot and strict base64 request\n";
