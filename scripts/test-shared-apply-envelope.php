<?php
/** Common GUI envelope and both unchanged Apply backend endpoints. */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php';
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';
use OPNsense\Zapret\Api\SharedApplyEnvelope as Envelope;
use OPNsense\Zapret\Native\SharedApplyRequest as RootRequest;
use OPNsense\Zapret\Api\SettingsApply;

function must(bool $pass, string $message): void {
    if (!$pass) { fwrite(STDERR, "FAIL: $message\n"); exit(1); }
}
function invalid(callable $callback): void {
    try { $callback(); }
    catch (\InvalidArgumentException $error) { return; }
    throw new \RuntimeException('Invalid shared Apply form accepted');
}
foreach (['voice','strategies'] as $page) {
    $sync = $page === 'voice'
        ? ['snapshot'=>str_repeat('a',64)]
        : ['telegramips_baseline'=>'91.108.0.0/16'];
    $fields = $page === 'voice'
        ? ['voice'=>['telegram'=>['enabled'=>'1','args'=>'--filter-udp=*']],
           'hostlist'=>['telegramips'=>'91.108.13.10']]
        : ['strategy'=>['trafficargs'=>'--filter-tcp=443'],
           'hostlist'=>['telegramips'=>'91.108.0.0/16']];
    $token = Envelope::encode($page,$fields,$sync);
    must(strlen($token) <= 65536 && preg_match('/^[A-Za-z0-9_-]+$/D',$token) === 1,
         'Native configd parameter is not bounded base64url');
    $decoded = RootRequest::decode($token);
    must($decoded === ['page'=>$page,'fields'=>$fields,'sync'=>$sync],
         'Native root did not decode precisely the GUI page fields');
}
invalid(fn()=>Envelope::encode('unknown',[],['snapshot'=>'x']));
invalid(fn()=>Envelope::encode('voice',[],['telegramips_baseline'=>'old']));
invalid(fn()=>Envelope::encode('strategies',[],['snapshot'=>'bad']));
invalid(fn()=>Envelope::encode('voice',['hostlist'=>['customips'=>str_repeat('x',100000)]],
                             ['snapshot'=>str_repeat('a',64)]));
// A single new Exclude IPSet entry must never implicitly normalize a huge
// unchanged domain list (e.g. the user's saved file ends with a newline).
// Previously, eager normalization expanded the changed map past 64 KiB.
$largeUnchangedDomains = implode("\n", array_map(
    static fn(int $index): string => sprintf('node%05d.example.org', $index),
    range(1, 4400)
)) . "\n";
$previous = [
    'general' => ['enabled'=>'1','waninterface'=>'WAN','divertport'=>'989'],
    'strategy' => ['trafficargs'=>'--filter-tcp=443','extraargs'=>''],
    'hostlist' => [
        'mode'=>'all', 'telegramips'=>'91.108.0.0/16',
        'youtubedomains'=>$largeUnchangedDomains, 'excludeipset'=>'',
    ],
    'voice' => ['waninterface'=>'WAN'],
];
$posted = ['hostlist'=>[
    'youtubedomains'=>$largeUnchangedDomains,
    'excludeipset'=>'192.0.2.0/24',
]];
$plan = SettingsApply::prepareStrategies($previous, $posted, '91.108.0.0/16');
must($plan['changed_fields'] === ['hostlist.excludeipset'],
     'Exclude-only POST unexpectedly changes unchanged saved domain data');
$smallFields = ['hostlist'=>['excludeipset'=>$plan['candidate']['hostlist']['excludeipset']]];
$small = Envelope::encode('strategies', $smallFields,
                          ['telegramips_baseline'=>'91.108.0.0/16']);
must(RootRequest::decode($small)['fields'] === $smallFields,
     'Excluded-only native envelope did not preserve the real edited field');
$eagerNormalized = rtrim($largeUnchangedDomains, "\n");
must($eagerNormalized !== $largeUnchangedDomains && strlen($eagerNormalized) > 65536,
     'Oversized unchanged fixture is not an eager-normalization regression');
invalid(fn()=>Envelope::encode('strategies', [
    'hostlist'=>['excludeipset'=>'192.0.2.0/24',
                 'youtubedomains'=>$eagerNormalized],
], ['telegramips_baseline'=>'91.108.0.0/16']));
$root=dirname(__DIR__).'/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/';
$voice=file_get_contents($root.'VoiceController.php');
$settings=file_get_contents($root.'SettingsController.php');
must(str_contains($settings,
     "if (!in_array('hostlist.' . \$field, \$plan['changed_fields'], true)) {"),
     'Strategies controller can normalize untouched large lists into configd argv');
foreach (['voice'=>$voice,'strategies'=>$settings] as $page=>$source) {
    $start=strpos($source,'public function applyAction()');
    must($start!==false,'Existing '.$page.' GUI Apply action was renamed');
    $end=strpos($source,'public function ', $start+20);
    $apply=$end===false?substr($source,$start):substr($source,$start,$end-$start);
    must(str_contains($apply,"configdpRun(") &&
         str_contains($apply,"'zapret shared_apply'") &&
         str_contains($apply,"SharedApplyEnvelope::encode('$page'"),
         'GUI Apply not wired to the same native FD9 action');
    must(!str_contains($apply,"configdRun('zapret reconfigure'") &&
         !str_contains($apply,'$config->save(') &&
         !str_contains($apply,'serializeToConfig('),
         'GUI save-then-reconfigure remained in '.$page.' Apply');
    must(str_contains($apply,'throwReadOnly()'), 'Read-only RBAC check absent');
    must(str_contains($apply,'$config->unlock();'), 'GUI Config lock may leak into FD9');
}
$action=file_get_contents(dirname(__DIR__).'/src/opnsense/service/conf/actions.d/actions_zapret.conf');
must(str_contains($action,"[shared_apply]\n") &&
     str_contains($action,'zapret_service.sh shared-apply-run') &&
     str_contains($action,'parameters:%s %s'),
     'Shared configd action contract missing');
echo "PASS: both unchanged GUI Apply endpoints use same bounded native FD9 envelope\n";
