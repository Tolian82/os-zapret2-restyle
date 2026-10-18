<?php
/** Read-only saved OFF Voice selection + exact OPNsense Config baseline. */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceDraftSelection.php';

use OPNsense\Zapret\Api\VoiceDraftSelection;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

function assertDraft(bool $yes, string $why): void
{
    if (!$yes) { fwrite(STDERR, "FAIL: {$why}\n"); exit(1); }
}
function rejectDraft(callable $code, string $why): void
{
    try { $code(); } catch (\InvalidArgumentException $error) { return; }
    assertDraft(false, $why);
}
function model(): array
{
    $voice = ['waninterface' => 'WAN'];
    $ips = [];
    foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $name) {
        $voice[$name] = [
            'enabled' => '0',
            'args' => "--filter-udp=*\n--filter-l7=stun\n--payload=stun",
        ];
        $ips[$name . 'ips'] = $name === 'telegram'
            ? '91.108.0.0/16' : '203.0.113.0/24';
    }
    return [
        'general' => ['enabled' => '1', 'waninterface' => 'WAN', 'divertport' => '989'],
        'strategy' => ['trafficargs' => '--filter-tcp=443', 'extraargs' => ''],
        'voice' => $voice,
        'hostlist' => [
            'mode' => 'all', 'youtubedomains' => 'youtube.com',
        ] + $ips,
        'strategylab' => ['enablequic' => '1'],
    ];
}
function form(array $saved): array
{
    $ips=[];
    foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $name) {
        $ips[$name.'ips'] = $saved['hostlist'][$name.'ips'];
    }
    return ['voice' => array_diff_key($saved['voice'], ['waninterface' => true]), 'hostlist' => $ips];
}
$saved = model();
$input = form($saved);
$input['voice']['telegram']['enabled'] = '1';
$token = VoiceSettingsSnapshot::digest($saved);
$plan = VoiceDraftSelection::plan($saved, $input, $token);
assertDraft($plan['result'] === 'eligible' && $plan['mask'] === '10000' &&
    $plan['selected_count'] === 1, 'saved Telegram selection was not selected: ' . json_encode($plan));
assertDraft($saved['voice']['telegram']['enabled'] === '0',
    'pure selection changed saved Voice ON flags');
$input['voice']['custom']['enabled'] = '1';
$custom = VoiceDraftSelection::plan($saved, $input, $token);
assertDraft($custom['mask'] === '10001' && $custom['selected_count'] === 2,
    'two services mask must follow canonical order');

// The selected ON flags are the ONLY allowed unsaved GUI edits.
$changedArgs = $input;
$changedArgs['voice']['telegram']['args'] .= "\n--out-range=n1-n3";
rejectDraft(fn() => VoiceDraftSelection::plan($saved, $changedArgs, $token),
    'unsaved native STUN change accepted');
$changedIps = $input;
$changedIps['hostlist']['customips'] = '198.51.100.0/24';
rejectDraft(fn() => VoiceDraftSelection::plan($saved, $changedIps, $token),
    'unsaved shared IPSET change accepted');
$changedWan = $input;
$changedWan['voice']['waninterface'] = '';
rejectDraft(fn() => VoiceDraftSelection::plan($saved, $changedWan, $token),
    'unsaved Voice WAN change accepted');
$noSelect=form($saved);
rejectDraft(fn() => VoiceDraftSelection::plan($saved, $noSelect, $token),
    'empty active selection accepted');
$onSaved=$saved;
$onSaved['voice']['telegram']['enabled']='1';
rejectDraft(fn() => VoiceDraftSelection::plan(
    $onSaved, $input, VoiceSettingsSnapshot::digest($onSaved)
), 'existing active Voice accepted as a saved OFF draft');
$off=$saved;
$off['general']['enabled']='0';
rejectDraft(fn() => VoiceDraftSelection::plan(
    $off, $input, VoiceSettingsSnapshot::digest($off)
), 'globally disabled service accepted');
rejectDraft(fn() => VoiceDraftSelection::plan($saved, $input, str_repeat('0',64)),
    'stale snapshot accepted');
$stale=$saved;
$stale['strategy']['trafficargs'] .= "\n--new";
rejectDraft(fn() => VoiceDraftSelection::plan(
    $stale, $input, $token
), 'changed ordinary Strategies accepted');

// Exact root-private consumer uses original BYTES, not reserialized model.
$path=tempnam(sys_get_temp_dir(), 'voice-config-');
assertDraft(is_string($path), 'temporary Config fixture unavailable');
try {
    $raw="<opnsense><system><password>top-secret</password></system></opnsense>\n";
    file_put_contents($path,$raw);
    assertDraft(VoiceDraftSelection::digestOriginalConfig($path) ===
        hash('sha256',$raw), 'Config baseline must hash the exact bytes');
    assertDraft(file_get_contents($path) === $raw, 'digest mutated Config fixture');
} finally { unlink($path); }
echo "PASS: saved OFF Voice GUI selection is mask-only; original Config baseline exact; no mutations\n";
