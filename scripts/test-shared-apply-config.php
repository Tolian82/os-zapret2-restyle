<?php
/** Validate native shared Config preflight and fixed owned plan paths. */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';

use OPNsense\Zapret\Native\SharedApplyConfigWorker as Worker;
use OPNsense\Zapret\Api\SettingsApply;

function must(bool $ok, string $why): void {
    if (!$ok) { fwrite(STDERR, "FAIL: $why\n"); exit(1); }
}
function denies(callable $cb): void {
    try { $cb(); }
    catch (\InvalidArgumentException | \RuntimeException $expected) { return; }
    throw new \RuntimeException('Unexpected accepted native Config plan');
}
$root=sys_get_temp_dir().'/native-shared-'.bin2hex(random_bytes(8));
mkdir($root,0700);
chmod($root,0700);
$id=str_repeat('a',32);
$work=$root.'/'.$id;
mkdir($work,0700);
chmod($work,0700);
$state=[
    'general'=>['enabled'=>'1','waninterface'=>'WAN','divertport'=>'989'],
    'strategy'=>['trafficargs'=>'--filter-tcp=443','extraargs'=>''],
    'hostlist'=>['mode'=>'list','telegramips'=>'91.108.0.0/16',
                 'youtubedomains'=>'','userdomains'=>'','excludedomains'=>''],
    'voice'=>['waninterface'=>'WAN'],
    'strategylab'=>['enablequic'=>'1'],
];
foreach (['telegram','discord','x','sip','custom'] as $name) {
    $state['voice'][$name]=['enabled'=>'0','args'=>''];
    if ($name!=='telegram') $state['hostlist'][$name.'ips']='';
}
$plan=SettingsApply::prepareStrategies(
    $state,['strategy'=>['trafficargs'=>'--filter-tcp=80']],'91.108.0.0/16'
);
$plan['page']='strategies';
file_put_contents($work.'/plan.json',json_encode($plan,JSON_THROW_ON_ERROR));
file_put_contents($work.'/candidate.xml','<opnsense/>');
chmod($work.'/plan.json',0600);
chmod($work.'/candidate.xml',0600);
$stored=Worker::readPlan($id,$root,posix_geteuid());
$savedCandidate=$plan['candidate'];
$savedRow=Worker::saved($plan,$savedCandidate);
must($savedRow['result']==='committed' && $savedRow['enabled']==='1',
     'native committed reboot witness rejected saved model');
$drifted=$savedCandidate;
$drifted['hostlist']['telegramips']='91.108.13.10';
denies(fn()=>Worker::saved($plan,$drifted));

must($stored['dependencies']===$plan['dependencies'],'stored plan lost dependency');
$unrelated=$state;
$unrelated['strategylab']['enablequic']='0';
$prepared=Worker::preflight($stored,$unrelated,'strategies');
must($prepared['result']==='prepared' && $prepared['enabled']==='1' &&
     $prepared['changes']===1,'fresh native Config preflight refused owned field');
$stale=$unrelated;
$stale['hostlist']['telegramips']='91.108.13.10';
denies(fn()=>Worker::preflight($stored,$stale,'strategies'));
denies(fn()=>Worker::readPlan('../evil',$root,posix_geteuid()));
file_put_contents($work.'/plan.json','{broken');
denies(fn()=>Worker::readPlan($id,$root,posix_geteuid()));
file_put_contents($work.'/plan.json',json_encode($plan,JSON_THROW_ON_ERROR));
$foreign=$root.'/foreign';
file_put_contents($foreign,'bad');
unlink($work.'/plan.json');
symlink($foreign,$work.'/plan.json');
denies(fn()=>Worker::readPlan($id,$root,posix_geteuid()));
unlink($work.'/plan.json');
unlink($work.'/candidate.xml');
unlink($foreign);
rmdir($work);
rmdir($root);
echo "PASS: native shared Config plan inode ownership and locked-model preflight\n";
