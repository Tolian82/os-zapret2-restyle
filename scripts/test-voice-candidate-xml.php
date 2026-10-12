<?php
/**
 * The real OPNsense Voice candidate XML must be in-memory, field-scoped and
 * isolated from the previous Config until native FD9 owns all five resources.
 */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateXml.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceApplyCandidate.php';

use OPNsense\Zapret\Api\VoiceApplyCandidate;
use OPNsense\Zapret\Api\VoiceCandidateXml;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

function must(bool $ok, string $why): void
{
    if (!$ok) {
        fwrite(STDERR, "FAIL: " . $why . "\n");
        exit(1);
    }
}
function refuses(callable $action, string $why): void
{
    try {
        $action();
    } catch (\InvalidArgumentException $ex) {
        return;
    }
    must(false, $why);
}
function records(): array
{
    $voice = ['waninterface' => 'WAN'];
    $ips = [];
    foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
        $voice[$service] = ['enabled' => '0', 'args' => ''];
        $ips[$service . 'ips'] = '';
    }
    return [
        'general' => ['enabled' => '1', 'waninterface' => 'WAN', 'divertport' => '989'],
        'strategy' => ['trafficargs' => "--filter-tcp=443\n--filter-l7=tls", 'extraargs' => ''],
        'voice' => $voice,
        'hostlist' => ['mode' => 'list', 'telegramips' => '91.108.0.0/16'] + $ips,
        'strategylab' => ['enablequic' => '1'],
    ];
}

$liveXml = <<<'XML'
<?xml version="1.0" encoding="utf-8"?>
<opnsense>
  <system><hostname>router</hostname><secret>KEEP_ME</secret></system>
  <openvpn><instance><name>old</name></instance><instance><name>second</name></instance></openvpn>
  <OPNsense>
    <Unboundplus><general><enabled>1</enabled></general></Unboundplus>
    <Zapret>
      <general><enabled>1</enabled><waninterface>WAN</waninterface><divertport>989</divertport></general>
      <strategy><trafficargs>--filter-tcp=443</trafficargs></strategy>
      <strategylab><enablequic>1</enablequic></strategylab>
      <voice><waninterface>WAN</waninterface><telegram><enabled>0</enabled><args/></telegram></voice>
      <hostlist><mode>list</mode><telegramips>91.108.0.0/16</telegramips><userdomains>untouched.example</userdomains></hostlist>
    </Zapret>
  </OPNsense>
</opnsense>
XML;

$previous = records();
$form = [
    'voice' => $previous['voice'],
    'hostlist' => [
        'telegramips' => '91.108.0.0/16',
        'discordips' => '',
        'xips' => '',
        'sipips' => '',
        'customips' => '',
    ],
];
$form['voice']['telegram'] = [
    'enabled' => '1',
    'args' => "--filter-udp=*\n--filter-l7=stun\n--payload=stun\n",
];
$plan = VoiceApplyCandidate::prepare($previous, $form, VoiceSettingsSnapshot::digest($previous));
must($plan['result'] === 'prepared', 'actual planning rejected good Voice input');
$before = $liveXml;
$candidate = VoiceCandidateXml::render(
    $liveXml, $previous, $plan['candidate'], $plan['changed_fields']
);
must($liveXml === $before, 'source Config bytes changed');
must(str_contains($candidate, '<secret>KEEP_ME</secret>'), 'foreign secret lost');
must(str_contains($candidate, '<userdomains>untouched.example</userdomains>'), 'hostlist domain changed');
$old = new \DOMDocument();
$new = new \DOMDocument();
must($old->loadXML($liveXml) && $new->loadXML($candidate), 'rendered XML invalid');
$xpath = new \DOMXPath($new);
must($xpath->evaluate('string(/opnsense/OPNsense/Zapret/voice/telegram/enabled)') === '1',
     'native Telegram ON was not put in isolated candidate');
must($xpath->evaluate('string(/opnsense/OPNsense/Zapret/voice/telegram/args)') ===
     $form['voice']['telegram']['args'], 'native multiline arguments not preserved');
must($xpath->evaluate('count(/opnsense/openvpn/instance)') === 2.0,
     'unrelated repeated OpenVPN instances altered');
$docOld = new \DOMXPath($old);
foreach (['/opnsense/system','/opnsense/openvpn','/opnsense/OPNsense/Unboundplus',
          '/opnsense/OPNsense/Zapret/general','/opnsense/OPNsense/Zapret/strategy',
          '/opnsense/OPNsense/Zapret/strategylab'] as $path) {
    must($docOld->query($path)->item(0)->C14N() === $xpath->query($path)->item(0)->C14N(),
         'changed unrelated document at ' . $path);
}
must($xpath->evaluate('string(/opnsense/OPNsense/Zapret/hostlist/userdomains)') ===
     'untouched.example', 'shared non-Voice hostlist field altered');

// OFF / no-change path preserves exact source bytes.
must(VoiceCandidateXml::render($liveXml, $previous, $previous, []) === $liveXml,
     'no-change path rewrote Config');

// Candidate cannot sneak an unrelated Strategy or System field into memory.
$wrong = $plan['candidate'];
$wrong['strategy']['trafficargs'] = '--filter-tcp=80';
refuses(fn() => VoiceCandidateXml::render(
    $liveXml, $previous, $wrong, $plan['changed_fields']
), 'unowned Strategies edit accepted');
refuses(fn() => VoiceCandidateXml::render(
    $liveXml, $previous, $plan['candidate'], []
), 'missing changed-field proof accepted');
refuses(fn() => VoiceCandidateXml::render(
    $liveXml, $previous, $plan['candidate'],
    array_merge($plan['changed_fields'], ['general.enabled'])
), 'foreign changed field accepted');
refuses(fn() => VoiceCandidateXml::render(
    $liveXml, $previous, $plan['candidate'],
    array_merge($plan['changed_fields'], [$plan['changed_fields'][0]])
), 'duplicate changed field accepted');

// Never choose which of duplicate XML anchors should receive a new Voice flag.
$duplicated = str_replace(
    '</Zapret>', '</Zapret><Zapret><voice/></Zapret>', $liveXml
);
refuses(fn() => VoiceCandidateXml::render(
    $duplicated, $previous, $plan['candidate'], $plan['changed_fields']
), 'duplicate Zapret mount accepted');
$nested = str_replace('<enabled>0</enabled><args/>',
    '<enabled><child>1</child></enabled><args/>', $liveXml);
refuses(fn() => VoiceCandidateXml::render(
    $nested, $previous, $plan['candidate'], $plan['changed_fields']
), 'nested editable leaf accepted');
$doctype = '<!DOCTYPE opnsense [<!ENTITY e SYSTEM "file:///etc/passwd">]>' . $liveXml;
refuses(fn() => VoiceCandidateXml::render(
    $doctype, $previous, $plan['candidate'], $plan['changed_fields']
), 'DTD accepted');

// Missing voice group is okay; only missing approved nodes may be created.
$oldVoice = preg_replace('/<voice>.*?<\/voice>/s', '', $liveXml);
$created = VoiceCandidateXml::render(
    $oldVoice, $previous, $plan['candidate'], $plan['changed_fields']
);
must(str_contains($created, '<telegram>'), 'missing Voice section not created');

echo "PASS: in-memory OPNsense candidate XML preserves foreign configuration, checks changed fields, no active write\n";
