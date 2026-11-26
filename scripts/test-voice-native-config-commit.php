<?php
/**
 * Native Config::save boundary tests without OPNsense or a real router.
 * The stub releases flock on save just like the current OPNsense Core.
 */
namespace {
    require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsApply.php';
    require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php';

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
        public bool $relockFailsAfterSave = false;
        public function __construct(array $state) { $this->disk = $state; }
        public function lock(): void {
            if ($this->relockFailsAfterSave && $this->saves > 0) {
                throw new \RuntimeException('simulated post-save Config relock IO failure');
            }
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
        public function setNodes(array $new): void {
            throw new \LogicException('Whole-model setNodes is invalid for OPNsense option dictionaries');
        }
        public function setNodeByReference(string $reference, string $value): bool {
            $next = $this->pending ?? self::$state;
            $node = &$next;
            foreach (explode('.', $reference) as $part) {
                if (!is_array($node) || !array_key_exists($part, $node)) {
                    return false;
                }
                $node = &$node[$part];
            }
            if (!is_string($node)) {
                return false;
            }
            $node = $value;
            unset($node);
            $this->pending = $next;
            return true;
        }
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
    $guarded = new FakeConfig($prior);
    foreach ([$strategyPlan, SettingsApply::prepareStrategies($prior, [], '91.108.0.0/16')] as $guardedPlan) {
        $calls = 0;
        try {
            SharedConfigCommit::persist($guardedPlan, 'strategies', $guarded, static fn()=>new FakeModel(),
                static function (string $base, string $candidate) use ($guarded, $guardedPlan, &$calls): bool {
                    $calls++;
                    verify($guarded->locks === 1 && $guarded->saves === 0,
                        'ordinary journal witness must precede save under Config lock');
                    verify($base === VoiceSettingsSnapshot::digest($guarded->disk) &&
                        $candidate === VoiceSettingsSnapshot::digest($guardedPlan['candidate']),
                        'ordinary journal witness did not receive exact locked model digests');
                    return false;
                }
            );
            verify(false, 'ordinary Config writer bypassed a refused journal witness');
        } catch (\RuntimeException $error) {
            verify(get_class($error) === \RuntimeException::class &&
                str_contains($error->getMessage(), 'witness refused'), 'refusal wrongly classified as post-save');
        }
        verify($calls === 1 && $guarded->saves === 0 && $guarded->locks === 0 &&
            $guarded->disk === $prior && FakeModel::$state === $prior,
            'refused ordinary journal witness mutated original Config');
    }
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

    // Real OPNsense getNodes() represents InterfaceField and OptionField as
    // option maps; passing that complete tree back through setNodes() raises
    // "Invalid input type for waninterface: expected a single value".
    // The owner observed this on the installed 0.5.3_26 Telegram ON.
    $optionWan = [
        'wan' => ['value' => 'WAN', 'selected' => 1],
        'lan' => ['value' => 'LAN', 'selected' => 0],
    ];
    $options = state();
    $options['general']['waninterface'] = $optionWan;
    $options['voice']['waninterface'] = $optionWan;
    $options['hostlist']['mode'] = [
        'all' => ['value' => 'All', 'selected' => 0],
        'list' => ['value' => 'List', 'selected' => 1],
    ];
    $voiceCandidate = $options;
    $voiceCandidate['voice']['telegram']['enabled'] = '1';
    $voicePlan = [
        'result' => 'prepared',
        'candidate' => $voiceCandidate,
        'changed_fields' => ['voice.telegram.enabled'],
        'dependencies' => VoiceSettingsSnapshot::digest($options),
    ];
    FakeModel::$state = $options;
    $previewModel = new FakeModel();
    $preview = \OPNsense\Zapret\Native\SharedApplyConfigWorker::preflight(
        $voicePlan, $options, 'voice', $previewModel
    );
    verify($preview['result'] === 'prepared' && $preview['enabled'] === '1',
        'production native preflight failed owned Voice leaf');
    verify($previewModel->getNodes()['general']['waninterface'] === $optionWan &&
        $previewModel->getNodes()['hostlist']['mode'] === $options['hostlist']['mode'] &&
        $previewModel->getNodes()['voice']['telegram']['enabled'] === '1',
        'native preflight touched unrelated option-map fields');
    FakeModel::$reject = true;
    try {
        \OPNsense\Zapret\Native\SharedApplyConfigWorker::preflight(
            $voicePlan, $options, 'voice', new FakeModel()
        );
        verify(false, 'model validation error survived preflight');
    } catch (\InvalidArgumentException $expected) {}
    FakeModel::$reject = false;
    $voiceConfig = new FakeConfig($options);
    $voiceSaved = SharedConfigCommit::persist(
        $voicePlan, 'voice', $voiceConfig, static fn()=>new FakeModel()
    );
    verify($voiceSaved['result'] === 'saved' && $voiceConfig->saves === 1 &&
        $voiceConfig->disk['voice']['telegram']['enabled'] === '1' &&
        $voiceConfig->disk['general']['waninterface'] === $optionWan &&
        $voiceConfig->disk['voice']['waninterface'] === $optionWan &&
        $voiceConfig->disk['hostlist']['mode'] === $options['hostlist']['mode'],
        'Voice ON changed foreign InterfaceField/OptionField or did not persist');

    $noChange=SettingsApply::prepareStrategies(
        $config->disk, [], $config->disk['hostlist']['telegramips']
    );
    $same=SharedConfigCommit::persist(
        $noChange,'strategies',$config,static fn()=>new FakeModel()
    );
    verify($same['result']==='unchanged' && $config->saves===1 &&
        $config->locks===0, 'repeated Config save created revision');
    // A found-only draft (or one with other Config changes) MUST NOT reach
    // the original Config writer until the single joint Config/P2 transaction
    // is proven. Otherwise the native model would save XML without all three
    // physical HOSTLIST sources, creating an unrecoverable split receipt.
    $foundOnly = $noChange;
    $foundOnly['found_intent'] = ['commit_authorized'=>false];
    $forbidden = new FakeConfig($config->disk);
    try {
        SharedConfigCommit::persist(
            $foundOnly, 'strategies', $forbidden, static fn()=>new FakeModel()
        );
        verify(false, 'found-only intent saved Config without three HOSTLISTs');
    } catch (\InvalidArgumentException $expected) {}
    verify($forbidden->saves === 0 && $forbidden->locks === 0 &&
           $forbidden->disk === $config->disk,
           'found-only split Config commit mutated native state');
    $changedFound = $strategyPlan;
    $changedFound['found_intent'] = ['commit_authorized'=>false];
    try {
        SharedConfigCommit::persist(
            $changedFound, 'strategies', $forbidden, static fn()=>new FakeModel()
        );
        verify(false, 'mixed Config+found intent saved only native Config');
    } catch (\InvalidArgumentException $expected) {}
    verify($forbidden->saves === 0 && $forbidden->locks === 0,
           'mixed found intent changed Config before three-file transaction');

    // Internal original owner: same Config::save writer, with P2 held
    // over the native save, but released BEFORE the second Config lock.
    $nativeFound = SettingsApply::prepareStrategies(
        $config->disk,
        ['strategy'=>['trafficargs'=>'--filter-tcp=443']],
        $config->disk['hostlist']['telegramips']
    );
    $nativeFound['found_intent'] = ['commit_authorized'=>false];
    $nativeFound['found_batch'] = ['youtube'=>[], 'user'=>[], 'auto'=>[]];
    $orig = new FakeConfig($config->disk);
    $sequence = [];
    $p2Held = false;
    $observedDigests = [];
    $originalBase = VoiceSettingsSnapshot::digest($orig->disk);
    $withP2 = static function (callable $scope, string $observedDigest) use (
        &$sequence, &$p2Held, &$observedDigests, $orig
    ): string {
        verify(hash_equals(VoiceSettingsSnapshot::digest($orig->disk), $observedDigest),
               'Found transport did not pass fresh locked Config digest');
        $observedDigests[] = $observedDigest;
        verify($orig->locks === 1 && !$p2Held,
               'P2 attempted before Config lock or still held at relock');
        $p2Held = true;
        $sequence[] = 'p2-lock';
        try { return $scope(); }
        finally { $p2Held = false; $sequence[] = 'p2-unlock'; }
    };
    $attest = static function (string $stage, string $digest) use (
        &$sequence, &$p2Held, $orig
    ): bool {
        verify($orig->locks === 1 && $p2Held && strlen($digest) === 64,
               'native file witness did not hold original Config->P2');
        $sequence[] = $stage;
        return true;
    };
    $journal = static function (string $phase) use (
        &$sequence, &$p2Held
    ): bool {
        verify($p2Held, 'found Config phase not under P2 lock');
        $sequence[] = $phase;
        return true;
    };
    $foundResult = SharedConfigCommit::persistFoundUnderOriginalOwner(
        $nativeFound, 'strategies', $orig, static fn()=>new FakeModel(),
        $withP2, $attest, $journal
    );
    verify($foundResult['result'] === 'found-config-saved-nonterminal' &&
        $foundResult['saved'] && !$foundResult['applied'] &&
        !$foundResult['commit_authorized'] &&
        $orig->saves === 1 && $orig->locks === 0 &&
        $orig->disk['strategy']['trafficargs'] === '--filter-tcp=443',
        'original found Config writer failed to persist or falsely applied');
    verify($sequence === [
        'p2-lock','before-config-save','found-config-saving','p2-unlock',
        'p2-lock','after-config-save','found-config-saved','p2-unlock'
    ], 'original Config->P2 lock order or durable phase order changed');
    verify($observedDigests === [$originalBase, VoiceSettingsSnapshot::digest($orig->disk)] &&
        $observedDigests[0] !== $observedDigests[1],
        'Found pre-save and readback Config identities were conflated');

    // Found-only edit must still pass through one sealed nonterminal WAL,
    // but it must not manufacture a new native XML revision.
    $unchangedFound = SettingsApply::prepareStrategies(
        $orig->disk, [], $orig->disk['hostlist']['telegramips']
    );
    $unchangedFound['found_intent'] = ['commit_authorized'=>false];
    $unchangedFound['found_batch'] = ['youtube'=>[], 'user'=>[], 'auto'=>[]];
    $noop = new FakeConfig($orig->disk);
    $noopSteps = [];
    $resultNoop = SharedConfigCommit::persistFoundUnderOriginalOwner(
        $unchangedFound, 'strategies', $noop, static fn()=>new FakeModel(),
        static function (callable $run) use ($noop): string {
            verify($noop->locks === 1, 'found-only original Config lock lost');
            return $run();
        },
        static fn(string $stage, string $digest): bool => strlen($digest) === 64,
        static function (string $phase) use (&$noopSteps): bool {
            $noopSteps[] = $phase;
            return true;
        }
    );
    verify($resultNoop['saved'] === false && $noop->saves === 0 &&
        $noopSteps === ['found-config-saving', 'found-config-saved'],
        'found-only Apply incorrectly created a Config revision');


    // Cold inspection is PURE: compare the complete locked native model,
    // never infer Config::save success merely because the candidate matches.
    $coldBase = $config->disk;
    $coldCandidate = $coldBase;
    $coldCandidate['strategy']['trafficargs'] = '--filter-tcp=80,443';
    $coldPlan = [
        'result' => 'prepared',
        'page' => 'strategies',
        'dependencies' => VoiceSettingsSnapshot::digest($coldBase),
        'candidate' => $coldCandidate,
        'changed_fields' => ['strategy.trafficargs'],
        'found_intent' => [
            'config_revision' => VoiceSettingsSnapshot::digest($coldBase),
            'commit_authorized' => false,
        ],
        'found_batch' => ['youtube'=>[], 'user'=>[], 'auto'=>[]],
    ];
    $classify = static fn(array $live, string $phase, ?array $plan = null): array =>
        \OPNsense\Zapret\Native\SharedApplyConfigWorker::classifyFoundConfigImage(
            $plan ?? $coldPlan, $live, $phase);
    $beforeCold = $classify($coldBase, 'found-files-written');
    verify($beforeCold['image'] === 'base-image' &&
        !$beforeCold['commit_authorized'] && !$beforeCold['restore_authorized'] &&
        !$beforeCold['save_attested'] && !$beforeCold['runtime_attested'],
        'cold found BEFORE classified as an authorized Apply');
    $uncertainBefore = $classify($coldBase, 'found-config-saving');
    $uncertainAfter = $classify($coldCandidate, 'found-config-saving');
    verify($uncertainBefore['image'] === 'base-image' &&
        $uncertainAfter['image'] === 'candidate-image' &&
        !$uncertainAfter['commit_authorized'] && !$uncertainAfter['save_attested'],
        'save-attempted uncertainty was converted into a confirmed native save');
    $savedReadback = $classify($coldCandidate, 'found-config-saved');
    verify($savedReadback['image'] === 'candidate-image' &&
        !$savedReadback['commit_authorized'] && !$savedReadback['restore_authorized'],
        'saved Config image incorrectly terminalized joint Apply');
    foreach ([
        [$coldCandidate, 'found-files-written'],
        [$coldBase, 'found-config-saved'],
    ] as [$live, $phase]) {
        try {
            $classify($live, $phase);
            verify(false, 'impossible Config-image/journal phase accepted');
        } catch (\RuntimeException $expected) {}
    }
    $foreignCold = $coldCandidate;
    $foreignCold['general']['divertport'] = '777';
    foreach (['found-files-written', 'found-config-saving', 'found-config-saved']
             as $phase) {
        try {
            $classify($foreignCold, $phase);
            verify(false, 'foreign Config state accepted for cold terminalization');
        } catch (\RuntimeException $expected) {}
    }
    $noopCold = $coldPlan;
    $noopCold['candidate'] = $coldBase;
    $noopCold['changed_fields'] = [];
    foreach (['found-files-written', 'found-config-saving', 'found-config-saved']
             as $phase) {
        $receipt = $classify($coldBase, $phase, $noopCold);
        verify($receipt['image'] === 'base-equals-candidate' &&
            !$receipt['commit_authorized'] && !$receipt['save_attested'],
            'found-only no-op Config image invented a durable save');
    }
    $invalidCold = $coldPlan;
    $invalidCold['found_intent']['config_revision'] = '0' . substr(
        $coldPlan['dependencies'], 1
    );
    try {
        $classify($coldBase, 'found-config-saving', $invalidCold);
        verify(false, 'mismatched original sealed Config dependency accepted');
    } catch (\RuntimeException $expected) {}
    verify($config->saves === 1 && $config->locks === 0 &&
        $config->disk === $coldBase,
        'read-only cold Config classifier performed a write or held a lock');


    // The *same* native Config snapshot and original physically locked
    // P2 reader may be projected together, but never become an Apply
    // or permission to restore based solely on image equivalence.
    // Unlike the Config-only classifier fixtures, joint inspection must
    // bind physical rows to the immutable three-source after/before plan.
    $jointPlan = $coldPlan;
    $jointPlan['found_batch'] = [
        'youtube'=>['before'=>"before.example\n", 'after'=>"after.example\n"],
        'user'=>['before'=>"same.example\n", 'after'=>"same.example\n"],
        'auto'=>['before'=>'', 'after'=>''],
    ];
    $coldFileBase = [
        'schema' => 1, 'result' => 'read-only-cold-image-classification',
        'journal_phase' => 'prepared', 'image' => 'all-before',
        'states' => ['youtube'=>'before','user'=>'before','auto'=>'before'],
        'stage_evidence' => null,
        'previous_runtime' => ['state'=>'no-predecessor-proof', 'id'=>null],
        'commit_authorized' => false, 'restore_authorized' => false,
    ];
    $joint = \OPNsense\Zapret\Native\SharedApplyConfigWorker::
        classifyFoundJointImages($jointPlan, $coldBase, $coldFileBase);
    // The native Python command encodes sort_keys=True recursively. Check
    // the ACTUAL wire-shaped source map, not just manually ordered PHP data.
    $wireStates = $coldFileBase;
    $wireStates['states'] = [
        'auto'=>'before', 'user'=>'before', 'youtube'=>'before',
    ];
    $wireJoint = \OPNsense\Zapret\Native\SharedApplyConfigWorker::
        classifyFoundJointImages($jointPlan, $coldBase, $wireStates);
    verify($wireJoint['file_image'] === 'all-before' &&
        !$wireJoint['restore_authorized'],
        'sorted native Python cold source-map keys incorrectly rejected');
    verify($joint['config_image'] === 'base-image' &&
        $joint['file_image'] === 'all-before' &&
        !$joint['commit_authorized'] && !$joint['restore_authorized'] &&
        !$joint['save_attested'] && !$joint['runtime_attested'],
        'cold pristine Config+file pair fabricated terminal Apply');
    $coldFilesWriting = $coldFileBase;
    $coldFilesWriting['journal_phase'] = 'found-files-writing';
    $coldFilesWriting['stage_evidence'] = [
        'youtube'=>'ready-but-before', 'user'=>'unchanged-before',
        'auto'=>'unchanged-before',
    ];
    $jointWriting = \OPNsense\Zapret\Native\SharedApplyConfigWorker::
        classifyFoundJointImages($jointPlan, $coldBase, $coldFilesWriting);
    verify($jointWriting['journal_phase'] === 'found-files-writing' &&
        !$jointWriting['restore_authorized'],
        'found-files-writing was treated as terminal recovery');
    $coldFilesSaving = $coldFilesWriting;
    $coldFilesSaving['journal_phase'] = 'found-config-saving';
    $coldFilesSaving['image'] = 'contains-unattributed-after';
    $coldFilesSaving['states']['youtube'] = 'after-image';
    $coldFilesSaving['stage_evidence']['youtube'] = 'installed-after';
    $jointSaving = \OPNsense\Zapret\Native\SharedApplyConfigWorker::
        classifyFoundJointImages($jointPlan, $coldCandidate, $coldFilesSaving);
    // Python builds staged evidence in changed-file order, which may
    // differ from the full canonical three-source order. This is a
    // shape check, not permission to fabricate a real native stage.
    $reorderedStages = $coldFilesSaving;
    $reorderedStages['stage_evidence'] = [
        'auto'=>'unchanged-before', 'user'=>'unchanged-before',
        'youtube'=>'installed-after',
    ];
    $reordered = \OPNsense\Zapret\Native\SharedApplyConfigWorker::
        classifyFoundJointImages($jointPlan, $coldCandidate, $reorderedStages);
    verify($reordered['stage_evidence']['youtube'] === 'installed-after' &&
        !$reordered['restore_authorized'],
        'reordered native staged source keys incorrectly rejected');
    verify($jointSaving['config_image'] === 'candidate-image' &&
        !$jointSaving['save_attested'] && !$jointSaving['commit_authorized'],
        'matching candidate during uncertain save falsely authorized Apply');
    foreach ([
        ['schema'=>2],
        ['commit_authorized'=>true],
        ['states'=>['youtube'=>'before']],
        ['states'=>[
            'auto'=>'before', 'user'=>'before', 'youtube'=>'before',
            'foreign'=>'before',
        ]],
        ['stage_evidence'=>['youtube'=>'installed-after']],
        ['journal_phase'=>'unexpected'],
        ['previous_runtime'=>['state'=>'ready', 'id'=>null]],
        ['previous_runtime'=>['state'=>'no-predecessor-proof', 'id'=>str_repeat('f',32)]],
        ['previous_runtime'=>['state'=>'ready', 'id'=>'foreign']],
    ] as $tamper) {
        try {
            \OPNsense\Zapret\Native\SharedApplyConfigWorker::
                classifyFoundJointImages($jointPlan, $coldBase,
                    array_replace($coldFilesWriting, $tamper));
            verify(false, 'malformed original physical cold proof accepted');
        } catch (\RuntimeException $expected) {}
    }
    try {
        \OPNsense\Zapret\Native\SharedApplyConfigWorker::
            classifyFoundJointImages($jointPlan, $coldCandidate, $coldFileBase);
        verify(false, 'prepared files with candidate XML accepted');
    } catch (\RuntimeException $expected) {}

    // Physically contradictory but otherwise well-shaped evidence MUST
    // refuse, including unsupported writer stage for an unchanged file.
    $jointContradictions = [];
    $wrong = $coldFilesWriting;
    $wrong['image'] = 'contains-unattributed-after';
    $jointContradictions[] = $wrong;
    $wrong = $coldFilesWriting;
    $wrong['stage_evidence']['youtube'] = 'installed-after';
    $jointContradictions[] = $wrong;
    $wrong = $coldFilesWriting;
    $wrong['stage_evidence']['user'] = 'ready-but-before';
    $jointContradictions[] = $wrong;
    $wrong = $coldFilesWriting;
    $wrong['states']['youtube'] = 'after-image';
    $wrong['image'] = 'contains-unattributed-after';
    $jointContradictions[] = $wrong;
    $wrong = $coldFilesSaving;
    $wrong['stage_evidence']['youtube'] = 'ready-but-after';
    $jointContradictions[] = $wrong;
    foreach ($jointContradictions as $contradiction) {
        try {
            \OPNsense\Zapret\Native\SharedApplyConfigWorker::
                classifyFoundJointImages($jointPlan, $coldBase, $contradiction);
            verify(false, 'well-shaped contradictory joint proof was accepted');
        } catch (\RuntimeException $expected) {}
    }
    verify($config->saves === 1 && $config->locks === 0 &&
        $config->disk === $coldBase,
        'joint cold classification attempted an extra native Config save');

    // Durable phase recording failure MUST prevent the first save call.
    $refused = new FakeConfig($config->disk);
    try {
        SharedConfigCommit::persistFoundUnderOriginalOwner(
            $nativeFound, 'strategies', $refused, static fn()=>new FakeModel(),
            static fn(callable $run): string => $run(),
            static fn(string $stage, string $digest): bool => true,
            static fn(string $phase): bool => false
        );
        verify(false, 'undurable Config intent crossed save');
    } catch (\RuntimeException $expected) {}
    verify($refused->saves === 0 && $refused->locks === 0,
           'Config changed despite absent found-save WAL');

    // Native IO error after the durable intent: no automatic rollback or
    // invented restored. The saved outcome is uncertain.
    $uncertain = new FakeConfig($config->disk);
    $uncertain->saveFails = true;
    $savedPhases = [];
    try {
        SharedConfigCommit::persistFoundUnderOriginalOwner(
            $nativeFound, 'strategies', $uncertain, static fn()=>new FakeModel(),
            static fn(callable $run): string => $run(),
            static fn(string $stage, string $digest): bool => true,
            static function (string $phase) use (&$savedPhases): bool {
                $savedPhases[] = $phase;
                return true;
            }
        );
        verify(false, 'native Config failure was marked saved');
    } catch (\OPNsense\Zapret\Native\SharedConfigSaveUncertain $expected) {}
    verify($uncertain->saves === 1 && $uncertain->locks === 0 &&
           $savedPhases === ['found-config-saving'],
           'native Config failure erased unresolved original WAL');

    // Config::save unlocks; a foreign edit between save and relock
    // must remain uncertain before the post-save found journal.
    $raced = new FakeConfig($config->disk);
    $raced->raceAfterSave = true;
    $racePhases = [];
    try {
        SharedConfigCommit::persistFoundUnderOriginalOwner(
            $nativeFound, 'strategies', $raced, static fn()=>new FakeModel(),
            static fn(callable $run): string => $run(),
            static fn(string $stage, string $digest): bool => true,
            static function (string $phase) use (&$racePhases): bool {
                $racePhases[] = $phase;
                return true;
            }
        );
        verify(false, 'raced saved Config accepted as original owner');
    } catch (\OPNsense\Zapret\Native\SharedConfigSaveUncertain $expected) {}
    verify($racePhases === ['found-config-saving'] &&
           $raced->locks === 0, 'saved Config race was not isolated');

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

// A valid Config::save followed by failure to re-lock/verify must NEVER
// cause the shared shell to misread 69 (pre-save) and roll back runtime.
$postFailure = new FakeConfig(state());
$postIntent = SettingsApply::prepareStrategies(
    $postFailure->disk,['strategy'=>['trafficargs'=>'--filter-tcp=80']],
    '91.108.0.0/16'
);
$postFailure->relockFailsAfterSave = true;
try {
    SharedConfigCommit::persist(
        $postIntent, 'strategies', $postFailure, static fn()=>new FakeModel()
    );
    verify(false, 'post-save relock failure falsely reported success');
} catch (\OPNsense\Zapret\Native\SharedConfigSaveUncertain $error) {
    verify(str_contains($error->getMessage(), 'readback failed after save'),
        'post-save relock IO error was not classified as uncertainty');
}
verify($postFailure->saves === 1 && $postFailure->locks === 0,
    'post-save relock failure must not roll back native Config');

// Stage-3 FD9 owner sequencing: the common record MUST be durable before
// any switch, then the native Config revision precedes IPFW commit.
$seed = state();
$events = [];
$sample = new FakeConfig($seed);
$intent = SettingsApply::prepareStrategies(
    $seed, ['strategy'=>['trafficargs'=>'--filter-tcp=80']], '91.108.0.0/16'
);
$record = static function (string $phase, array $detail) use (&$events): bool {
    $events[] = "record:$phase";
    return $detail['page'] === 'strategies';
};
$activate = static function () use (&$events): bool {
    $events[] = 'runtime:activate';
    return true;
};
$rollback = static function () use (&$events): bool {
    $events[] = 'runtime:rollback';
    return true;
};
$commit = static function () use (&$events): bool {
    $events[] = 'runtime:commit';
    return true;
};
$run = SharedConfigCommit::transact($intent,'strategies',$sample,
    static fn()=>new FakeModel(), static fn()=>true,
    $record,$activate,$rollback,$commit);
verify($run['result']==='applied' && $run['applied'] &&
       $sample->disk['strategy']['trafficargs']==='--filter-tcp=80',
       'native shared transaction not committed');
verify($events === [
    'record:prepared','record:activating','runtime:activate',
    'record:activated','record:config-saved','runtime:commit','record:committed',
], 'native shared transaction order incorrect: '.implode(',', $events));
verify($sample->locks===0 && $sample->saves===1, 'FD9 save sequence leaked Config lock');

// A previously sealed three-file intent may not use the old callable
// coordinator, because it does not own Config+P2 file commit/recovery.
$events = [];
try {
    SharedConfigCommit::transact(
        $changedFound, 'strategies', new FakeConfig($seed),
        static fn()=>new FakeModel(), static fn()=>true,
        $record, $activate, $rollback, $commit
    );
    verify(false, 'legacy coordinator activated found draft without file WAL');
} catch (\InvalidArgumentException $expected) {}
verify($events === [], 'found intent crossed into legacy journal or runtime');

// Missing FD9 or failed durable intent is a hard refusal before activation.
$events = [];
try {
    SharedConfigCommit::transact($intent,'strategies',new FakeConfig($seed),
        static fn()=>new FakeModel(), static fn()=>false,
        $record,$activate,$rollback,$commit);
    verify(false, 'missing FD9 authorized mutation');
} catch (\RuntimeException $expected) {}
verify($events === [], 'FD9 failure modified runtime or record');
$events = [];
try {
    SharedConfigCommit::transact($intent,'strategies',new FakeConfig($seed),
        static fn()=>new FakeModel(), static fn()=>true,
        static function (string $phase, array $detail) use (&$events) {
            $events[] = "record:$phase";
            return false;
        }, $activate,$rollback,$commit);
    verify(false, 'missing durable prepared record authorized runtime');
} catch (\RuntimeException $expected) {}
verify($events === ['record:prepared'], 'bad record authorized runtime mutation');

// Pre-save Config validation fails after runtime activation -> true rollback.
$events = [];
$changed = new FakeConfig($seed);
FakeModel::$reject=true;
$failedRun=SharedConfigCommit::transact($intent,'strategies',$changed,
    static fn()=>new FakeModel(), static fn()=>true,
    $record,$activate,$rollback,$commit);
FakeModel::$reject=false;
verify($failedRun['result']==='failed' && $failedRun['restored'] &&
       !$failedRun['requires_review'] && $changed->saves===0 &&
       in_array('runtime:rollback',$events,true) &&
       end($events)==='record:restored',
       'pre-save failure not restored');

// A save exception/post-save conflict is ambiguous, never auto-rollback.
$events=[];
$changed=new FakeConfig($seed);
$changed->saveFails=true;
$uncertainRun=SharedConfigCommit::transact($intent,'strategies',$changed,
    static fn()=>new FakeModel(), static fn()=>true,
    $record,$activate,$rollback,$commit);
verify($uncertainRun['requires_review'] && !$uncertainRun['restored'] &&
       !in_array('runtime:rollback',$events,true) &&
       end($events)==='record:requires-review',
       'uncertain native save rolled back runtime without reconciliation');

// Post-save commit failure leaves durable review evidence.
$events=[];
$changed=new FakeConfig($seed);
$commitFailed=SharedConfigCommit::transact($intent,'strategies',$changed,
    static fn()=>new FakeModel(),static fn()=>true,$record,$activate,$rollback,
    static function () use (&$events): bool {
        $events[]='runtime:commit';
        return false;
    });
verify($commitFailed['requires_review'] &&
       $commitFailed['saved'] === true &&
       end($events)==='record:requires-review',
       'post-save cleanup failure falsely claimed success');

    echo "PASS: native Config::save/history seam, fresh overlay, no-op, stale guard, save failure and post-save race\n";
}
