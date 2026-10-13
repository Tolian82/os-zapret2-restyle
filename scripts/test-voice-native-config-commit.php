<?php
/**
 * Native Config::save boundary tests without OPNsense or a real router.
 * The stub releases flock on save just like the current OPNsense Core.
 */
namespace {
    require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';
    require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/apply_settings.php';

    use OPNsense\Zapret\Api\SettingsApply;
    use OPNsense\Zapret\Api\VoiceSettingsSnapshot;
    use OPNsense\Zapret\Native\SharedConfigCommit;

    function verify(bool $value, string $why): void {
        if (!$value) { fwrite(STDERR, "FAIL: $why\n"); exit(1); }
    }
    final class FakeConfig {
        public array $disk;
        public int $locks = 0;
        public int $saves = 0;
        public bool $saveFails = false;
        public bool $raceAfterSave = false;
        public function __construct(array $state) { $this->disk = $state; }
        public function lock(): void {
            verify($this->locks === 0, 'overlapping Config lock');
            $this->locks = 1;
            FakeModel::$state = $this->disk; // Native Config::lock(reload=true)
        }
        public function unlock(): void { $this->locks = 0; }
        public function save(array $audit): void {
            verify($this->locks === 1, 'native save without Config lock');
            $this->saves++;
            if ($this->saveFails) { throw new \RuntimeException('IO error'); }
            $this->disk = FakeModel::$state;
            $this->locks = 0; // Current OPNsense Core releases flock.
            if ($this->raceAfterSave) {
                $this->disk['general']['divertport'] = '990';
            }
        }
    }
    final class FakeModel {
        public static array $state = [];
        private ?array $pending = null;
        public static bool $reject = false;
        public function getNodes(): array { return $this->pending ?? self::$state; }
        public function setNodes(array $new): void { $this->pending = $new; }
        public function performValidation(bool $full = false): array {
            return self::$reject ? ['rejected'] : [];
        }
        public function serializeToConfig(bool $full = false, bool $disable = true): bool {
            verify($this->pending !== null, 'serialize without candidate');
            self::$state = $this->pending;
            return true;
        }
    }
    function state(): array {
        $voice = ['waninterface'=>'WAN'];
        $ipsets = [];
        foreach (['telegram','discord','x','sip','custom'] as $name) {
            $voice[$name] = ['enabled'=>'0','args'=>''];
            $ipsets[$name.'ips'] = '';
        }
        return [
            'general'=>['enabled'=>'1','waninterface'=>'WAN','divertport'=>'989'],
            'strategy'=>['trafficargs'=>'--filter-tcp=443','extraargs'=>''],
            'hostlist'=>[
                'telegramips'=>'91.108.0.0/16',
                'mode'=>'list','userdomains'=>'example.org',
                'youtubedomains'=>'','excludedomains'=>'',
            ]+$ipsets,
            'voice'=>$voice,
            'strategylab'=>['enablequic'=>'1'],
        ];
    }
    $config = new FakeConfig(state());
    $prior = $config->disk;
    $strategyPlan = SettingsApply::prepareStrategies($prior, [
        'strategy'=>['trafficargs'=>'--filter-tcp=80'],
    ], '91.108.0.0/16');
    $config->disk['strategylab']['enablequic'] = '0';
    $result = SharedConfigCommit::persist(
        $strategyPlan,'strategies',$config,static fn()=>new FakeModel()
    );
    verify($result['result']==='saved' && $result['saved'] &&
        !$result['applied'], 'native save must be persistence only');
    verify($config->saves===1 && $config->locks===0, 'native save lock/revision count');
    verify($config->disk['strategylab']['enablequic']==='0' &&
        $config->disk['voice']===$prior['voice'] &&
        $config->disk['strategy']['trafficargs']==='--filter-tcp=80',
        'native save lost unrelated or Voice data');
    $noChange=SettingsApply::prepareStrategies(
        $config->disk, [], $config->disk['hostlist']['telegramips']
    );
    $same=SharedConfigCommit::persist(
        $noChange,'strategies',$config,static fn()=>new FakeModel()
    );
    verify($same['result']==='unchanged' && $config->saves===1 &&
        $config->locks===0, 'repeated Config save created revision');

    $stale=SettingsApply::prepareStrategies(
        $config->disk,['strategy'=>['trafficargs'=>'--filter-tcp=443']],
        $config->disk['hostlist']['telegramips']
    );
    $config->disk['hostlist']['telegramips']='91.108.13.10';
    try {
        SharedConfigCommit::persist($stale,'strategies',$config,static fn()=>new FakeModel());
        verify(false,'stale shared IPSET saved');
    } catch (\InvalidArgumentException $expected) {}
    verify($config->saves===1 && $config->locks===0, 'stale save mutated Config');
    $config->disk['hostlist']['telegramips']='91.108.0.0/16';

    FakeModel::$reject=true;
    try {
        SharedConfigCommit::persist($stale,'strategies',$config,static fn()=>new FakeModel());
        verify(false,'native model rejection ignored');
    } catch (\InvalidArgumentException $expected) {}
    FakeModel::$reject=false;
    verify($config->saves===1 && $config->locks===0, 'validation failure saved Config');

    $config->saveFails=true;
    try {
        SharedConfigCommit::persist($stale,'strategies',$config,static fn()=>new FakeModel());
        verify(false,'native save exception swallowed');
    } catch (\RuntimeException $expected) {
        verify(str_contains($expected->getMessage(),'explicit review'), 'IO error marked restored');
    }
    $config->saveFails=false;
    verify($config->saves===2 && $config->locks===0, 'save failure lock cleanup');
    $config->raceAfterSave=true;
    try {
        SharedConfigCommit::persist($stale,'strategies',$config,static fn()=>new FakeModel());
        verify(false,'post-save concurrent edit was ignored');
    } catch (\RuntimeException $expected) {
        verify(str_contains($expected->getMessage(),'reconciliation'), 'post-save conflict hidden');
    }
    verify($config->saves===3 && $config->locks===0, 'post-save lock cleanup');
    echo "PASS: native Config::save/history seam, fresh overlay, no-op, stale guard, save failure and post-save race\n";
}
