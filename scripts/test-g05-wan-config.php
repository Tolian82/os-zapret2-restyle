<?php
/** LC-06: WAN-only native Config write via the existing SharedConfigCommit. */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_wan.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php';

use OPNsense\Zapret\Native\WanOnlyConfig;
use OPNsense\Zapret\Native\SharedConfigSaveUncertain;
use OPNsense\Zapret\Api\SharedApplyEnvelope as Envelope;

function g05must(bool $ok, string $why): void {
    if (!$ok) { fwrite(STDERR,"FAIL G05: $why\n"); exit(1); }
}
function g05refuse(callable $fn, string $label): void {
    try { $fn(); }
    catch (\InvalidArgumentException | \RuntimeException $expected) { return; }
    g05must(false, $label . ' was accepted');
}
function g05state(): array {
    return [
        'general'=>['enabled'=>'0','waninterface'=>'','divertport'=>'989'],
        'strategy'=>['trafficargs'=>'','extraargs'=>''],
        'hostlist'=>[
            'mode'=>'list','youtubedomains'=>'','telegramips'=>'192.0.2.1',
            'userdomains'=>'','excludedomains'=>'','excludeipset'=>'',
        ],
        'voice'=>['waninterface'=>''],
        'strategylab'=>['enablequic'=>'1'],
    ];
}
function g05form(string $wan,string $baseline='192.0.2.1',
    array $extra=[]): string {
    $fields=['general'=>['waninterface'=>$wan]];
    foreach($extra as $key=>$value) { $fields[$key]=$value; }
    return Envelope::encode('strategies',$fields,
        ['telegramips_baseline'=>$baseline]);
}
class G05Config {
    public array $stored;
    public bool $locked=false;
    public bool $uncertain=false;
    public int $saveCount=0;
    public function __construct(?array $values=null) {
        $this->stored=$values??g05state();
    }
    public function lock(): void {
        g05must(!$this->locked,'double Config lock');
        $this->locked=true;
    }
    public function unlock(): void { $this->locked=false; }
    public function save(array $meta): void {
        g05must($this->locked && isset($meta['description']),
            'native Config save not locked or unaudited');
        ++$this->saveCount;
        $this->locked=false; // OPNsense save releases its own flock
        if ($this->uncertain) {
            throw new \RuntimeException('simulated interrupted native save');
        }
    }
    public function __toString(): string {
        $d=new \DOMDocument('1.0','UTF-8');
        $root=$d->createElement('opnsense'); $d->appendChild($root);
        $op=$d->createElement('OPNsense'); $root->appendChild($op);
        $zap=$d->createElement('Zapret'); $op->appendChild($zap);
        foreach(['general','strategy','hostlist'] as $group) {
            $g=$d->createElement($group); $zap->appendChild($g);
            foreach($this->stored[$group] as $name=>$value) {
                $f=$d->createElement($name);
                if (is_string($value)) $f->appendChild($d->createTextNode($value));
                $g->appendChild($f);
            }
        }
        return $d->saveXML();
    }
}
class G05Model {
    private G05Config $config;
    private ?string $pendingWan=null;
    public function __construct(G05Config $config) { $this->config=$config; }
    public function getNodes(): array { return $this->config->stored; }
    public function setNodeByReference(string $path,string $value): bool {
        g05must($this->config->locked,'WAN model write without Config lock');
        if ($path !== 'general.waninterface') return false;
        $this->pendingWan=$value;
        return true;
    }
    public function performValidation(bool $all): array {
        return $this->pendingWan !== null &&
            !in_array($this->pendingWan, ['','wan','lo0','opt0'],true)
            ? [new \Exception('invalid WAN')] : [];
    }
    public function serializeToConfig(bool $a=false,bool $b=true): bool {
        if($this->pendingWan!==null)
            $this->config->stored['general']['waninterface']=$this->pendingWan;
        return true;
    }
}
function g05factory(G05Config $config): callable {
    return static fn()=>new G05Model($config);
}
$empty=new G05Config();
$before=$empty->stored;
$token=g05form('wan');
$probe=WanOnlyConfig::execute('probe',$token,$empty,g05factory($empty));
g05must($probe['result']==='eligible' &&
    $probe['changed']===['general.waninterface'] &&
    $empty->saveCount===0 && $empty->stored===$before,
    'read-only fresh WAN preflight mutated Config');
$saved=WanOnlyConfig::execute('commit',$token,$empty,g05factory($empty));
g05must($saved['result']==='saved' && $saved['change_count']===1 &&
    $empty->saveCount===1 && !$empty->locked,
    'first WAN save did not reuse native Config persistence exactly once');
g05must($empty->stored['general']['waninterface']==='wan' &&
    $empty->stored['general']['enabled']==='0' &&
    $empty->stored['strategy']===$before['strategy'] &&
    $empty->stored['hostlist']===$before['hostlist'] &&
    $empty->stored['voice']===$before['voice'] &&
    $empty->stored['strategylab']===$before['strategylab'],
    'WAN change modified unrelated preferences/Voice/Lab or Enabled');

$nochange=WanOnlyConfig::execute('commit',$token,$empty,g05factory($empty));
g05must($nochange['result']==='unchanged' && $empty->saveCount===1,
    'repeating same WAN created a second Config revision');

$edited=$empty->stored;
$edited['strategy']['trafficargs']='INVALID_USER_SAVED_DRAFT';
$edited['hostlist']['youtubedomains']='intentionally-bad-domain';
$edited['general']['enabled']='0';
$other=new G05Config($edited);
$changed=WanOnlyConfig::execute('commit',g05form('lo0'),$other,g05factory($other));
g05must($changed['result']==='saved' && $other->saveCount===1 &&
    $other->stored['strategy']===$edited['strategy'] &&
    $other->stored['hostlist']===$edited['hostlist'],
    'saved invalid unrelated strategy/domain blocked or mutated WAN-only save');

foreach([
    ['bad-interface',g05form('missing;rm')],
    ['other-field',g05form('lo0','192.0.2.1',['strategy'=>['trafficargs'=>'fake']])],
    ['foreign-Voice',Envelope::encode('voice',[
        'voice'=>['telegram'=>['enabled'=>'1']]],
        ['snapshot'=>str_repeat('a',64)])],
    ['stale-tab',g05form('lo0','198.51.100.1')],
] as [$name,$bad]) {
    $c=new G05Config();
    g05refuse(fn()=>WanOnlyConfig::execute('commit',$bad,$c,g05factory($c)),
        $name);
    g05must($c->saveCount===0 && $c->stored===g05state() && !$c->locked,
        $name . ' changed Config');
}
$uncertain=new G05Config(); $uncertain->uncertain=true;
try {
    WanOnlyConfig::execute('commit',g05form('lo0'),$uncertain,
        g05factory($uncertain));
    g05must(false,'ambiguous Config save reported success');
} catch (SharedConfigSaveUncertain $expected) {
    g05must($uncertain->saveCount===1 && !$uncertain->locked,
        'ambiguous native save status was wrongly retried');
}
echo "PASS: G05 original Config writer WAN-only, empty drafts, stale/invalid refusal, uncertain save\n";
