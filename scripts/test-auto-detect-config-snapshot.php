<?php
/** P2k8a: actual native read-only model bridge, no Config write or active worker. */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/auto_detect_config_snapshot.php';
use OPNsense\Zapret\Native\AutoDetectConfigSnapshot as Snapshot;

final class TestConfig
{
    public bool $held = false;
    public int $locks = 0;
    public int $unlocks = 0;
    public int $writes = 0;
    public function lock(): void { if ($this->held) throw new RuntimeException('double lock'); $this->held = true; ++$this->locks; }
    public function unlock(): void { if (!$this->held) throw new RuntimeException('not locked'); $this->held = false; ++$this->unlocks; }
    public function save(): void { ++$this->writes; throw new RuntimeException('must not save'); }
}
final class TestModel
{
    public function __construct(public array $nodes) {}
    public function getNodes(): array { return $this->nodes; }
    public function serializeToConfig(): void { throw new RuntimeException('must not serialize'); }
}
function check(bool $ok, string $why):void { if (!$ok) throw new RuntimeException($why); }
function correctFile(?string $text):array
{
    return ['result'=>'ok', 'status'=>$text===null?'missing':($text===''?'empty':'populated'),
      'revision'=>hash('sha256',$text===null?"missing\0":"present\0".$text),
      'content'=>$text ?? '',
      'auto_owned_components'=>null,'auto_owned_complete'=>false];
}
function nativeModel():array {return ['hostlist'=>[
    'youtubedomains'=>"youtube.com\n!^test.invalid\n",
    'userdomains'=>"example.org\n^t.me\n", 'excludedomains'=>"bad.example\n",
    'domains'=>'historical-config-field', 'telegramips'=>'10.0.0.1/32'
]];}
function expectFailure(callable $f,string $description):void
{
    try {$f();} catch (RuntimeException $e) {return;}
    throw new RuntimeException("expected refusal: $description");
}
$count=0;
$source = file_get_contents(__DIR__.'/../src/opnsense/scripts/OPNsense/Zapret/backend/registry.sh');
check(is_string($source),'registry unavailable');
preg_match_all("/printf 'HOSTLIST\\\\t([a-z]+)\\\\t/",$source,$matches);
check($matches[1] === ['youtube','user','auto'],'registered HOSTLIST names changed: adapt native snapshot before proceeding');
++$count;

$c=new TestConfig;
$factory=function() use ($c): TestModel {check($c->held,'model read must hold native config lock');return new TestModel(nativeModel());};
$fileReader=function() use ($c):array {check($c->held,'native final reader must run under native config lock');return correctFile("!^negative.test\nnew.example\n");};
$r=Snapshot::capture($c,$factory,$fileReader);
check($c->locks===1&&$c->unlocks===1&&!$c->held&&$c->writes===0,'lock release and no save');
check($r['manual_hostlists'] === ['youtube'=>"youtube.com\n!^test.invalid\n",'user'=>"example.org\n^t.me\n"], 'original manual HOSTLIST bytes must stay unchanged');
check($r['shared_auto']==="!^negative.test\nnew.example\n"&&$r['global_exclude']==="bad.example\n",'complete current registered domain sources');
check($r['auto_owned_components']===null&&$r['auto_owned_complete']===false&&$r['commit_authorized']===false,'ledger absence must refuse authorization');
check(strlen($r['config_snapshot_sha256'])===64,'full native model digest');
$r2=correctFile('new.example\n');
$r2['auto_owned_components']=['youtube'=>'', 'user'=>'known.example\n'];
$r2['auto_owned_complete']=true;
$c2=new TestConfig;
$known=Snapshot::capture($c2,fn()=>new TestModel(nativeModel()),fn()=>$r2);
check($known['auto_owned_complete']===true && $known['auto_owned_components']===$r2['auto_owned_components'] && !$known['commit_authorized'],'proven owned components remain read-only');
check(!$c2->held&&$c2->writes===0,'proven read never writes');
++$count;
++$count;

foreach ([null,'',"manual.example\n"] as $content) {
    $c=new TestConfig;
    $r=Snapshot::capture($c, fn()=>new TestModel(nativeModel()),fn()=>correctFile($content));
    check($r['shared_auto_status']===($content===null?'missing':($content===''?'empty':'populated')),'status discrepancy');
    check($c->locks===1&&$c->unlocks===1&&!$c->held,'lock not balanced');
    ++$count;
}

foreach (['youtubedomains','userdomains','excludedomains'] as $field) {
    $nodes=nativeModel();unset($nodes['hostlist'][$field]);
    $c=new TestConfig;
    expectFailure(fn()=>Snapshot::capture($c,fn()=>new TestModel($nodes),fn()=>correctFile('')),"missing $field");
    check(!$c->held&&$c->unlocks===1,'missing field must release Config');
    ++$count;
}
$nodes=nativeModel();$nodes['hostlist']['userdomains']=['selected'=>'example.com'];
$c=new TestConfig;expectFailure(fn()=>Snapshot::capture($c,fn()=>new TestModel($nodes),fn()=>correctFile('')),'dropdown cannot masquerade as text');
check(!$c->held,'invalid model lock release');++$count;
$nodes=nativeModel();$nodes['hostlist']['youtubedomains']=str_repeat('A',1048577);
$c=new TestConfig;expectFailure(fn()=>Snapshot::capture($c,fn()=>new TestModel($nodes),fn()=>correctFile('')),'oversized model');
check(!$c->held,'oversized model lock release');++$count;

foreach ([['status'=>'populated','content'=>'','revision'=>correctFile('')['revision'],'result'=>'ok'],
          ['status'=>'populated','content'=>'tampered.example','revision'=>str_repeat('0',64),'result'=>'ok'],
          ['status'=>'missing','content'=>'unexpected','revision'=>correctFile(null)['revision'],'result'=>'ok'],
          ['result'=>'error','reason'=>'gui_writer_busy'],
          array_merge(correctFile(''), ['auto_owned_components'=>[], 'auto_owned_complete'=>true]),
          array_merge(correctFile(''), ['auto_owned_components'=>['youtube'=>'!bad.example\n','user'=>''], 'auto_owned_complete'=>true]),
          array_merge(correctFile(''), ['auto_owned_components'=>['youtube'=>''], 'auto_owned_complete'=>false]) ] as $bad) {
    $c=new TestConfig;expectFailure(fn()=>Snapshot::capture($c,fn()=>new TestModel(nativeModel()),fn()=>$bad),'untrusted native reader reply');
    check(!$c->held&&$c->unlocks===1,'reader refusal must release native lock');
    ++$count;
}
$c=new TestConfig;
expectFailure(fn()=>Snapshot::capture($c,fn()=>new TestModel(nativeModel()),function(){throw new RuntimeException('reader failed');}),'failure propagation');
check(!$c->held&&$c->unlocks===1,'exception releases lock');++$count;
check(Snapshot::main(['script','read'])===64,'Linux CLI must refuse native authority');++$count;
echo "P2k8a native Config+final-HOSTLIST lock/read-only contract PASS ($count scenarios)\n";