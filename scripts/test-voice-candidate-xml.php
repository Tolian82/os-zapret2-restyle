<?php
/**
 * The real OPNsense Voice candidate XML must be in-memory, field-scoped and
 * isolated from the previous Config until native FD9 owns all five resources.
 */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceCandidateXml.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceApplyCandidate.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';

use OPNsense\Zapret\Api\VoiceApplyCandidate;
use OPNsense\Zapret\Api\VoiceCandidateXml;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;
use OPNsense\Zapret\Api\SettingsApply;

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
        'hostlist' => [
            'mode' => 'list', 'telegramips' => '91.108.0.0/16',
            'youtubedomains' => '', 'userdomains' => 'untouched.example',
            'excludedomains' => '',
        ] + $ips,
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

// Both public forms must produce one full detached candidate without
// introducing a second Config writer or silently replacing the Voice subtree.
$strategyForm = [
    'general' => ['waninterface' => 'WAN'],
    'strategy' => ['trafficargs' => "--filter-tcp=80\n--payload=http_req"],
    'hostlist' => ['telegramips' => "91.108.13.10"],
];
$strategy = SettingsApply::prepareStrategies(
    $previous, $strategyForm, $previous['hostlist']['telegramips']
);
$fullStrategyXml = SettingsApply::renderCandidateXml(
    $liveXml, $previous, $strategy, 'strategies'
);
$strategyDoc = new \DOMDocument();
must($strategyDoc->loadXML($fullStrategyXml), 'Strategies XML is malformed');
$sxp = new \DOMXPath($strategyDoc);
must($sxp->evaluate('string(/opnsense/OPNsense/Zapret/strategy/trafficargs)') ===
     $strategyForm['strategy']['trafficargs'], 'Strategies candidate missed own trafficargs');
must($sxp->evaluate('string(/opnsense/OPNsense/Zapret/hostlist/telegramips)') ===
     '91.108.13.10', 'shared Telegram IPSET not propagated to full candidate');
foreach (['/opnsense/system','/opnsense/openvpn','/opnsense/OPNsense/Unboundplus',
          '/opnsense/OPNsense/Zapret/voice','/opnsense/OPNsense/Zapret/strategylab'] as $path) {
    must($docOld->query($path)->item(0)->C14N() === $sxp->query($path)->item(0)->C14N(),
         'Strategies candidate modified foreign XML at ' . $path);
}
must(str_contains($fullStrategyXml, '<secret>KEEP_ME</secret>'),
     'Strategies candidate erased unrelated system content');
must(SettingsApply::renderCandidateXml(
    $liveXml, $previous, SettingsApply::prepareStrategies(
        $previous, [], $previous['hostlist']['telegramips']
    ), 'strategies'
) === $liveXml, 'no-op Strategies candidate modified full XML');
must(SettingsApply::renderCandidateXml(
    $liveXml, $previous, SettingsApply::prepareVoice(
        $previous, $form, VoiceSettingsSnapshot::digest($previous)
    ), 'voice'
) === $candidate, 'shared Voice candidate differs from existing native Voice XML');
refuses(fn() => SettingsApply::renderCandidateXml(
    $liveXml, $previous, $strategy, 'voice'
), 'Strategies fields injected into Voice XML scope');
refuses(fn() => SettingsApply::renderCandidateXml(
    $liveXml, $previous, $strategy, 'unknown'
), 'unknown full candidate scope accepted');
$tainted = $strategy;
$tainted['candidate']['voice']['telegram']['enabled'] = '1';
refuses(fn() => SettingsApply::renderCandidateXml(
    $liveXml, $previous, $tainted, 'strategies'
), 'Strategies candidate secretly enabled Voice');
$missing = $strategy;
$missing['changed_fields'] = [];
refuses(fn() => SettingsApply::renderCandidateXml(
    $liveXml, $previous, $missing, 'strategies'
), 'Strategies candidate omitted changed fields');
refuses(fn() => SettingsApply::renderCandidateXml(
    $doctype, $previous, $strategy, 'strategies'
), 'DOCTYPE injected into Strategies candidate');


/*
 * Use the real BaseListField::getNodeData() shape: option objects are
 * shown to the form, but the detached Config writer needs selected keys.
 */
$options = records();
$optionRows = [
    '' => ['value' => 'None', 'selected' => 0],
    'WAN' => ['value' => 'WAN', 'selected' => 1],
    'WAN2' => ['value' => 'WAN2', 'selected' => 0],
];
$options['general']['waninterface'] = $optionRows;
$options['voice']['waninterface'] = $optionRows;
$options['hostlist']['mode'] = [
    'all' => ['value' => 'All', 'selected' => 0],
    'list' => ['value' => 'Listed', 'selected' => 1],
];
$dropdownForm = $form;
$dropdownForm['voice']['telegram']['enabled'] = '0';
$dropdownForm['voice']['telegram']['args'] = '';
$dropdownForm['voice']['waninterface'] = 'WAN';
$dropdown = VoiceApplyCandidate::prepare(
    $options, $dropdownForm, VoiceSettingsSnapshot::digest($options)
);
must(($dropdown['result'] ?? '') === 'prepared', 'real InterfaceField options rejected');
must(!in_array('voice.waninterface', $dropdown['changed_fields'], true),
     'same WAN choice falsely differs from saved value');
must(VoiceCandidateXml::render(
    $liveXml, $options, $dropdown['candidate'], $dropdown['changed_fields']
) === $liveXml, 'unchanged native dropdown rewrote Config');
// Real dropdown + an ON checkbox: the combination exercised on the
// installed owner's Voice form must prepare a detached XML without a
// false foreign-field or unchanged-field exception.
$dropdownForm['voice']['telegram']['enabled'] = '1';
$dropdownForm['voice']['telegram']['args'] =
    "--filter-udp=*\n--filter-l7=stun\n--payload=stun";
$onDropdown = VoiceApplyCandidate::prepare(
    $options, $dropdownForm, VoiceSettingsSnapshot::digest($options)
);
must(($onDropdown['result'] ?? null) === 'prepared', 'ON and native WAN options rejected');
$onDropdownXml = VoiceCandidateXml::render(
    $liveXml, $options, $onDropdown['candidate'], $onDropdown['changed_fields']
);
must(str_contains($onDropdownXml, '<enabled>1</enabled>'),
     'ON profile disappeared from native option-selected candidate');
$dropdownForm['voice']['telegram']['enabled'] = '0';
$dropdownForm['voice']['telegram']['args'] = '';
$dropdownForm['voice']['waninterface'] = 'WAN2';
$changedDropdown = VoiceApplyCandidate::prepare(
    $options, $dropdownForm, VoiceSettingsSnapshot::digest($options)
);
must(($changedDropdown['result'] ?? '') === 'prepared' &&
     in_array('voice.waninterface', $changedDropdown['changed_fields'], true),
     'new WAN not recognized as selected raw value');
$dropdownXml = VoiceCandidateXml::render(
    $liveXml, $options, $changedDropdown['candidate'], $changedDropdown['changed_fields']
);
must(str_contains($dropdownXml, '<waninterface>WAN2</waninterface>'),
     'WAN selection did not become correct XML leaf');
$invalidOptions = $options;
$invalidOptions['voice']['waninterface']['WAN2']['selected'] = 1;
refuses(fn() => VoiceCandidateXml::render(
    $liveXml, $invalidOptions, $invalidOptions, []
), 'ambiguous native InterfaceField selection accepted');

echo "PASS: shared detached native XML for Strategies/Voice, ownership, no-op and foreign-node preservation\n";
