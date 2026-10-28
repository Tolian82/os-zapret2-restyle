<?php
/**
 * Pure RU/EN Voice GUI validation contract — no config.xml or IPFW access.
 */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateValidator.php';

use OPNsense\Zapret\Api\VoiceCandidateValidator;

function check(bool $condition, string $reason): void
{
    if (!$condition) {
        fwrite(STDERR, "FAIL: {$reason}\n");
        exit(1);
    }
}

function data(): array
{
    $voice = [];
    $ips = [];
    foreach (['telegram','discord','x','sip','custom'] as $name) {
        $voice[$name] = ['enabled' => '0', 'args' => ''];
        $ips[$name . 'ips'] = '';
    }
    return ['voice' => $voice, 'hostlist' => $ips];
}

function active(array $data, string $name, string $ips, ?string $args = null): array
{
    $data['voice'][$name] = [
        'enabled' => '1',
        'args' => $args ?? "--filter-udp=*\n--filter-l7=stun\n--payload=stun\n"
    ];
    $data['hostlist'][$name.'ips'] = $ips;
    return $data;
}

function invalid(array $data, string $field, string $reason): void
{
    $problems = VoiceCandidateValidator::check($data);
    check(isset($problems[$field]), $reason . ': missing ' . $field . '; errors: ' .
        json_encode($problems));
}

$empty = data();
check(VoiceCandidateValidator::check($empty) === [], 'All OFF with empty parameters must validate');
$empty['voice']['discord']['args'] = "incomplete\n--new";
check(VoiceCandidateValidator::check($empty) === [], 'Disabled draft remains editable/untested');

check(VoiceCandidateValidator::check(active(data(), 'telegram', "2001:db8::1\n::")) === [],
    'IPv6 destinations are accepted in read-only GUI preflight');
$telegram = active(data(), 'telegram', "91.108.0.0/16\n91.108.13.10\n91.108.13.10");
check(VoiceCandidateValidator::check($telegram) === [], 'Telegram fake-free native STUN candidate');

$two = active($telegram,'discord',"203.0.113.0/24",
    "--filter-udp=5000-5002\n--filter-l7=stun\n--payload=stun\n");
check(VoiceCandidateValidator::check($two) === [], 'Two disjoint services');

$conflict = active($telegram,'discord',"91.108.13.10");
invalid($conflict,'zapret.voice.discord.enabled','IPSET+UDP overlap must be refused');
$conflict['voice']['telegram']['args'] =
    "--filter-udp=596-599\n--filter-l7=stun\n--payload=stun";
$conflict['voice']['discord']['args'] =
    "--filter-udp=40000\n--filter-l7=stun\n--payload=stun";
check(VoiceCandidateValidator::check($conflict) === [], 'Disjoint UDP ports allow overlapping IPs');

foreach (["91.108.13.10/24","2001:db8::1/64","1.2.3.4/33","127.0.0.1;echo foo","::/0","0.0.0.0/1\n128.0.0.0/1"] as $ip) {
    invalid(active(data(),'telegram',$ip),'zapret.hostlist.telegramips','reject invalid IPv4/IPv6/CIDR');
}
invalid(active(data(),'telegram',''),'zapret.hostlist.telegramips','empty IPSET forbidden for enabled service');

 // A populated but INVALID list must report the parser's actual failure,
 // not invent a second "destination IPs required" error after parsing fails.
 $badAddress = active(data(), 'telegram', '91.108.13.10');
 $badAddress['hostlist']['discordips'] = 'not-an-ip';
 $errors = VoiceCandidateValidator::check($badAddress);
 check(!in_array('Enabled Voice service requires destination IPs', $errors, true),
     'failed six-list parser invented missing Telegram destinations');
 check(count($errors) > 0, 'bad second list was silently accepted');


 // Separate invalid fields must be reported together: the earlier IPSET
 // error must not stop parsing later STUN arguments of that same profile.
$both = active(data(), 'telegram', 'not-an-ip',
    "--filter-udp=3478\n--filter-l7=stun\n--payload=bogus");
$problems = VoiceCandidateValidator::check($both);
check(isset($problems['zapret.hostlist.telegramips']) &&
      isset($problems['zapret.voice.telegram.args']),
      'Malformed IPSET must not hide the later invalid STUN payload: ' .
      json_encode($problems));
// An error in Telegram must not suppress Discord argument validation either.
$both = active($both, 'discord', '203.0.113.0/24',
    "--filter-udp=5000\n--filter-l7=stun\n--payload=invalid");
$problems = VoiceCandidateValidator::check($both);
check(isset($problems['zapret.voice.telegram.args']) &&
      isset($problems['zapret.voice.discord.args']),
      'Each enabled Voice service must report its own STUN error: ' .
      json_encode($problems));

$base = "--filter-udp=596-599\n--filter-l7=stun\n--payload=stun\n";
$allowed = [
    '--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2:ip_ttl=4',
    '--lua-desync=fake:blob=0x00000000000000000000000000000000:ipfrag:ipfrag_pos_udp=8',
    '--lua-desync=fake:blob=0x00000000000000000000000000000000:badsum',
];
foreach ($allowed as $fake) {
    check(VoiceCandidateValidator::check(active(data(),'telegram','91.108.0.0/16',
        $base."--out-range=n1-n10\n".$fake)) === [], 'Valid bounded fake Lua option failed: ' . $fake);
}
foreach ([
    '--filter-tcp=443','--new','$(touch /tmp/pwn)',
    '--lua-desync=send:ipfrag','--out-range=n1;rm',
    '--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=0',
    '--lua-desync=fake:blob=0x00000000000000000000000000000000:ip_ttl=500',
    '--lua-desync=fake:blob=0x00000000000000000000000000000000:ipfrag_pos_udp=8',
] as $bad) {
    invalid(active(data(),'telegram','91.108.0.0/16',$base.$bad),
        'zapret.voice.telegram.args', 'native option should be rejected: '.$bad);
}

$bad = data();
$bad['voice']['telegram']['enabled'] = 'yes';
invalid($bad,'zapret.voice.telegram.enabled','invalid checkbox');
$bad = data();
$bad['general']=['enabled'=>'1'];
invalid($bad,'zapret.voice.waninterface','unexpected form fields');
$bad = data();
$bad['hostlist']['userdomains']='foo';
invalid($bad,'zapret.voice.waninterface','Voice cannot submit unrelated domain lists');
$bad = data();
$bad['voice']['waninterface']='WAN; rm';
invalid($bad,'zapret.voice.waninterface','WAN injection');
$bad = data();
$bad['voice']['telegram']['args']=['--new'];
invalid($bad,'zapret.voice.telegram.enabled','array injection');

echo "PASS: pure Voice GUI validate-only endpoint contract, native STUN/IPv4, scope and injection guards\n";
