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
check(Snapshot::nativeRootAllowed()===false,
      'off-FreeBSD even root PHP CLI must refuse native authority');++$count;
check(Snapshot::main(['script','read'])===64,'Linux CLI must refuse native authority');++$count;

// P2k8e: queue owner is established by the upstream worker BEFORE this
// method. The native Config owner then spans the *whole* synchronous
// policy->physical commit callback, not a detached read-only snapshot.
$queueHeld=true;
$c=new TestConfig;
$syncCalls=0;
$originalDigest=null;
$done=Snapshot::withLockedOriginalModel(
    $c,
    function() use($c,$queueHeld):TestModel {
        check($queueHeld&&$c->held,'original Config lock must follow queue ownership');
        return new TestModel(nativeModel());
    },
    function(array $source) use($c,&$syncCalls,&$originalDigest):array {
        check($c->held,'destination operation escaped original Config lock');
        check(array_keys($source)===['manual_hostlists','global_exclude','config_snapshot_sha256'],
              'must pass only original Model fields; no Config object or XML writer');
        check($source['manual_hostlists']['youtube']==="youtube.com\n!^test.invalid\n",
              'real original YouTube Model input required');
        check($source['global_exclude']==="bad.example\n",'original Exclude input required');
        $originalDigest=$source['config_snapshot_sha256'];
        ++$syncCalls;
        return ['kind'=>'destination-and-cursor-committed','ack_authorized'=>false];
    }
);
check($syncCalls===1 && $c->locks===1 && $c->unlocks===1 &&
      !$c->held && $c->writes===0 && $done['ack_authorized']===false &&
      strlen($originalDigest)===64,
      'original Config lock not held for complete synchronous operation');
++$count;

$c=new TestConfig;
expectFailure(
    fn()=>Snapshot::withLockedOriginalModel(
        $c,
        fn()=>new TestModel(nativeModel()),
        function(array $source) use($c):array {
            check($c->held,'callback exception escaped Config lock');
            throw new RuntimeException('destination write interrupted');
        }),
    'P2k2b failure must release original Config and retain pending'
);
check(!$c->held && $c->unlocks===1 && $c->writes===0,'failure lock discipline');
++$count;

$c=new TestConfig;
expectFailure(fn()=>Snapshot::withLockedOriginalModel(
    $c,fn()=>new TestModel(nativeModel()),
    fn($source)=>['kind'=>'destination-and-cursor-committed','ack_authorized'=>true]
),'no synchronous callback may authorize acknowledgment');
check(!$c->held && $c->unlocks===1 && $c->writes===0,'unsafe checkpoint refusal');
++$count;

// If the original source fields drift while the callback runs, the original
// Config generation must no longer be reported as successfully committed.
$c=new TestConfig;
$modified=false;
expectFailure(fn()=>Snapshot::withLockedOriginalModel(
    $c,
    function() use(&$modified):TestModel {
        $nodes=nativeModel();
        if($modified){$nodes['hostlist']['excludedomains']="new-block.example\n";}
        return new TestModel($nodes);
    },
    function(array $source) use(&$modified):array {
        $modified=true;
        return ['kind'=>'destination-and-cursor-committed','ack_authorized'=>false];
    }
),'original Model generation changed while callback was active');
check(!$c->held && $c->unlocks===1 && $c->writes===0,'changed generation lock discipline');
++$count;

echo "P2k8a/P2k8e original native Config lock/read/transaction contracts PASS ($count scenarios)\n";