<?php
/** P2k8a: actual native read-only model bridge, no Config write or active worker. */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/auto_detect_config_snapshot.php';
use OPNsense\Zapret\Native\AutoDetectConfigSnapshot as Snapshot;
use OPNsense\Zapret\Api\StrategiesHostlistCatalog as Catalog;

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
// The real native child emits a prefixed status line; the existing shared
// Apply consumes ONLY {result: created|existing}. This must not become a 69
// before the first journal merely because the PHP adapter passes the prefix.
foreach (['created','existing'] as $state) {
    $wire = json_encode(['result'=>Snapshot::parseNativeBootstrapReceipt(
        "auto-owned-bootstrap=$state\n")], JSON_THROW_ON_ERROR);
    check(json_decode($wire, true, 4, JSON_THROW_ON_ERROR)['result'] === $state,
          'original native known baseline not decoded for shared Apply');
    ++$count;
}
foreach (['', 'auto-owned-bootstrap=created',
          "auto-owned-bootstrap=created\ntrailer",
          "auto-owned-bootstrap=unexpected\n",
          "auto-owned-bootstrap=existing\r\n"] as $invalid) {
    expectFailure(fn()=>Snapshot::parseNativeBootstrapReceipt($invalid),
                  'unqualified original known baseline should refuse');
    ++$count;
}
$executeSource = file_get_contents(__DIR__.'/../src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh');
check(is_string($executeSource) && str_contains($executeSource,
      '.result | select(.=="created" or .=="existing")'),
      'original Apply bootstrap result contract drifted');
++$count;
$source = file_get_contents(__DIR__.'/../src/opnsense/scripts/OPNsense/Zapret/backend/registry.sh');
check(is_string($source),'registry unavailable');
preg_match_all("/printf 'HOSTLIST\\\\t([a-z]+)\\\\t/",$source,$matches);
check($matches[1] === ['youtube','user','auto'],'registered HOSTLIST names changed: adapt native snapshot before proceeding');
check(Catalog::editorIds() === [
    'youtube_manual','youtube_found','user_manual','user_found','shared_found'
] && Catalog::manualModelFields() === [
    'youtubedomains'=>'youtube', 'userdomains'=>'user'
] && Catalog::manualTargets() === ['youtube','user'] &&
    Catalog::ownedTargets() === ['youtube','user'], 'Strategies catalogue mapping drift');
check(Catalog::editorOwners() === [
    'youtube_manual'=>'config', 'youtube_found'=>'auto-owned',
    'user_manual'=>'config', 'user_found'=>'auto-owned', 'shared_found'=>'shared-auto'
], 'Strategies catalogue owners drift');
foreach (Catalog::sources() as $id => $row) {
    check($row['kind']==='hostlist' &&
        in_array($row['target'], $matches[1], true) &&
        in_array($row['storage_kind'], ['config','file'], true) &&
        (($row['owner']==='config') === ($row['model_field']!==null)),
        'Strategies source must match existing target registry: '.$id);
}
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

// S0/TZ6v3: owner's real 1,774,109-byte source is rejected by the
// current 1 MiB product guard even with a verified empty shared source.
// This negative witness becomes a positive assertion in the read-API change.
$ownerText = str_repeat("a.com\n", 295684) . "x.io\n";
check(strlen($ownerText) === 1774109, 'owner fixture exact byte count');
$ownerNodes = nativeModel();
$ownerNodes['hostlist']['userdomains'] = $ownerText;
$ownerLock = new TestConfig;
$ownedReads = 0;
expectFailure(fn()=>Snapshot::capture($ownerLock,
    fn()=>new TestModel($ownerNodes),
    function() use (&$ownedReads): array { ++$ownedReads; return correctFile(''); }),
    'owner 1,774,109 bytes still over original read guard');
check(!$ownerLock->held && $ownerLock->locks === 1 &&
    $ownerLock->unlocks === 1 && $ownerLock->writes === 0 &&
    $ownedReads === 0, 'oversize refusal must release lock without mutation');
++$count;

// TZ6v3 editor-only read accepts the same owner-sized saved Model without
// weakening the original background P2 worker's 1 MiB limit or writing files.
$editorLock = new TestConfig;
$editorReaderCalls = 0;
$ownerSnap = Snapshot::capture($editorLock,
    fn()=>new TestModel($ownerNodes),
    function() use (&$editorReaderCalls): array {
        ++$editorReaderCalls;
        return correctFile('');
    }, true);
$ownerEditor = Snapshot::fiveEditorsFromCapture($ownerSnap);
check($editorReaderCalls === 1 && $editorLock->locks === 1 &&
    $editorLock->unlocks === 1 && $editorLock->writes === 0 &&
    !$editorLock->held, 'editor-only root read must keep original lock and no writes');
check($ownerEditor['schema_version'] === 3 &&
    $ownerEditor['kind'] === 'tz6v3-five-hostlist-snapshot' &&
    $ownerEditor['editors']['user_manual']['length_bytes'] === 1774109 &&
    !array_key_exists('content', $ownerEditor['editors']['user_manual']) &&
    $ownerEditor['editors']['user_manual']['revision'] ===
        hash('sha256', "present\0" . $ownerText) &&
    $ownerEditor['editors']['shared_found']['status'] === 'empty' &&
    $ownerEditor['editors']['shared_found']['content'] === '' &&
    $ownerEditor['editors']['shared_found']['revision'] === hash('sha256', "present\0") &&
    !$ownerEditor['commit_authorized'],
    'owner-sized native manual metadata plus physically safe empty shared');
++$count;

$tooLargeEditorNodes = nativeModel();
$tooLargeEditorNodes['hostlist']['userdomains'] = str_repeat('x', 4 * 1048576 + 1);
$noReader = 0; $unsafeLock = new TestConfig;
expectFailure(fn()=>Snapshot::capture($unsafeLock,
    fn()=>new TestModel($tooLargeEditorNodes),
    function() use (&$noReader): array { ++$noReader; return correctFile(''); },
    true), 'editor root read must retain finite 4 MiB aggregate bound');
check($noReader === 0 && $unsafeLock->locks === $unsafeLock->unlocks &&
    $unsafeLock->writes === 0, 'oversized editor refusal before P2 read');
++$count;

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

// TZ6v2 STEP 4: the real capture() owns one Config+destination snapshot.
// The pure projection MUST NOT take a second lock, read a new file, save or
// invent a baseline for an unsealed known-source root.
$captured = correctFile("shared.example\n");
$captured['auto_owned_components'] = [
    'youtube' => "youtube-found.example\n",
    'user' => "user-found.example\n",
];
$captured['auto_owned_complete'] = true;
$cFive = new TestConfig;
$callReader = 0;
$fOne = Snapshot::capture(
    $cFive,
    function () use ($cFive): TestModel {
        check($cFive->held, 'five editors: Config must be locked before model');
        return new TestModel(nativeModel());
    },
    function () use ($cFive, $captured, &$callReader): array {
        check($cFive->held, 'five editors: protected source read under Config');
        ++$callReader;
        return $captured;
    }
);
$five = Snapshot::fiveEditorsFromCapture($fOne);
check($cFive->locks === 1 && $cFive->unlocks === 1 && $cFive->writes === 0 &&
    $callReader === 1 && !$cFive->held, 'five-editor read must not write or reread');
check($five['schema_version'] === 3 &&
    $five['kind'] === 'tz6v3-five-hostlist-snapshot' &&
    $five['result'] === 'ok' && $five['commit_authorized'] === false &&
    $five['auto_owned_complete'] === true, 'five-source contract');
check(array_keys($five['editors']) === [
    'youtube_manual', 'youtube_found', 'user_manual',
    'user_found', 'shared_found'
], 'exact ordered five sources');
foreach ([
    'youtube_manual' => "youtube.com\n!^test.invalid\n",
    'user_manual' => "example.org\n^t.me\n"
] as $name => $original) {
    $row = $five['editors'][$name];
    check($row['length_bytes'] === strlen($original) &&
        $row['revision'] === hash('sha256', "present\0" . $original) &&
        !array_key_exists('content', $row),
        'manual native Model bytes must not cross configd: '.$name);
}
check($five['editors']['youtube_found']['content'] === "youtube-found.example\n" &&
    $five['editors']['user_found']['content'] === "user-found.example\n" &&
    $five['editors']['shared_found']['content'] === "shared.example\n",
    'all three physical automatically discovered sources must remain distinct');
check($five['editors']['youtube_manual']['owner'] === 'config' &&
    $five['editors']['youtube_found']['owner'] === 'auto-owned' &&
    $five['editors']['shared_found']['owner'] === 'shared-auto',
    'no automatic sources reclassified as manual');
foreach ($five['editors'] as $name => $entry) {
    $original = $entry['owner'] === 'config'
        ? ($name === 'youtube_manual' ? "youtube.com\n!^test.invalid\n" : "example.org\n^t.me\n")
        : $entry['content'];
    check($entry['status'] === 'populated' &&
        $entry['revision'] === hash('sha256', "present\0" . $original),
        "five source content/revision mismatch: $name");
}
check($five['config_revision'] === $fOne['config_snapshot_sha256'],
    'full original native model revision retained');
++$count;

$cMissing = new TestConfig;
$missing = Snapshot::fiveEditorsFromCapture(Snapshot::capture(
    $cMissing, fn() => new TestModel(nativeModel()),
    fn() => correctFile(null)
));
check($missing['editors']['youtube_found']['status'] === 'uninitialized' &&
    $missing['editors']['user_found']['status'] === 'uninitialized' &&
    $missing['editors']['youtube_found']['content'] === '' &&
    $missing['editors']['youtube_found']['revision'] === null &&
    $missing['editors']['user_found']['revision'] === null &&
    !$missing['auto_owned_complete'] &&
    $missing['editors']['shared_found']['status'] === 'missing' &&
    $missing['editors']['shared_found']['revision'] === hash('sha256', "missing\0") &&
    !$missing['commit_authorized'] && $cMissing->writes === 0,
    'never silently treat unsealed owned roots as verified empty or initialize files');
++$count;

$emptyKnown = correctFile('');
$emptyKnown['auto_owned_complete'] = true;
$emptyKnown['auto_owned_components'] = ['youtube' => '', 'user' => ''];
$cEmpty = new TestConfig;
$empty = Snapshot::fiveEditorsFromCapture(Snapshot::capture(
    $cEmpty, fn() => new TestModel(nativeModel()), fn() => $emptyKnown
));
check($empty['editors']['youtube_found']['status'] === 'empty' &&
    $empty['editors']['youtube_found']['revision'] === hash('sha256', "present\0") &&
    $empty['editors']['shared_found']['status'] === 'empty' &&
    $empty['editors']['shared_found']['revision'] === hash('sha256', "present\0"),
    'verified empty exists must differ from absent/uninitialized');
++$count;

foreach ([
    ['auto_owned_complete' => true, 'auto_owned_components' => null],
    ['auto_owned_complete' => false, 'auto_owned_components' => ['youtube' => '', 'user' => '']],
    ['shared_auto_revision' => str_repeat('f', 64)],
    ['commit_authorized' => true],
] as $tamper) {
    expectFailure(fn() => Snapshot::fiveEditorsFromCapture(array_replace(
        $fOne, $tamper)), 'forged read-only five-source payload');
    ++$count;
}

$actions = file_get_contents(__DIR__ . '/../src/opnsense/service/conf/actions.d/actions_zapret.conf');
$controller = file_get_contents(__DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php');
check(is_string($actions) && str_contains($actions, '[hostlist_editors_read]') &&
    str_contains($actions, 'auto_detect_config_snapshot.php read-editors') &&
    is_string($controller) &&
    str_contains($controller, 'function hostlistEditorsReadAction(): array') &&
    str_contains($controller, "'zapret hostlist_editors_read'"),
    'five-source GUI API must call original root Config-locked CLI');
++$count;

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