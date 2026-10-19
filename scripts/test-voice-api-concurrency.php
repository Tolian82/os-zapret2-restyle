<?php
/**
 * Native Voice validation, concurrency and OFF-only Config save with isolated stubs.
 * No OPNsense Config, configd, IPFW or running service are modified.
 */
namespace OPNsense\Base {
    class ApiControllerBase {
        public $request;
        public static bool $denyWrites = false;
        protected function throwReadOnly(): void {
            if (self::$denyWrites) { throw new \RuntimeException('read-only user'); }
        }
    }
    class ApiMutableModelControllerBase extends ApiControllerBase {}
    class UserException extends \RuntimeException {}
}
namespace OPNsense\Core {
    class Config {
        public static $instance;
        public int $locks = 0;
        public int $saves = 0;
        public bool $throwInvalidAfterSave = false;
        public static bool $malformedXml = false;
        public static function getInstance() {
            return self::$instance ?? (self::$instance = new self());
        }
        public function lock(): void { $this->locks++; }
        public function unlock(): void { $this->locks--; }
        public function save($audit = []): void {
            // Model and save counter already reflect a durable write before
            // an error whose PHP class looks like form validation.
            $this->saves++;
            if ($this->throwInvalidAfterSave) {
                throw new \InvalidArgumentException('simulated post-save exception');
            }
        }
        // Production OPNsense Config::__toString() returns its independent
        // full XML serialization; this stub must expose that same read-only
        // API without simulating any persistence.
        public function __toString(): string {
            if (self::$malformedXml) return '<opnsense broken XML';
            return '<?xml version="1.0" encoding="utf-8"?>' .
                '<opnsense><system><hostname>old</hostname></system>' .
                '<OPNsense><Zapret><voice/></Zapret></OPNsense></opnsense>';
        }
    }
    class Backend {
        public static bool $busy = false;
        public static bool $reconfigureOK = true;
        public static bool $postNativeCommitInvalid = false;
        public static ?string $preflightReceipt = null;
        public static int $nativeCommits = 0;
        public static string $inspectResponse = '';
        public static bool $inspectThrows = false;
        public static bool $guardThrows = false;
        public static array $calls = [];
        public static array $params = [];
        public function configdpRun($action, $params, ...$args) {
            self::$calls[] = $action;
            self::$params = $params;
            if ($action === 'zapret shared_apply') {
                if (Config::getInstance()->locks !== 0) {
                    throw new \RuntimeException('GUI Config lock held during native FD9 Apply');
                }
                if (!is_array($params) || count($params) !== 2 ||
                    !in_array($params[0], ['voice', 'strategies'], true)) {
                    throw new \RuntimeException('Unexpected native Apply page/parameters');
                }
                $raw = base64_decode(strtr($params[1], '-_', '+/'), true);
                $request = is_string($raw) ? json_decode($raw, true) : null;
                if (!is_array($request) || ($request['page'] ?? null) !== $params[0] ||
                    !is_array($request['fields'] ?? null) ||
                    !is_array($request['sync'] ?? null)) {
                    throw new \RuntimeException('Invalid native Apply envelope');
                }
                if (self::$preflightReceipt !== null) {
                    // Root-stage negative receipt: no Config/runtime mutation.
                    return self::$preflightReceipt;
                }
                if (self::$reconfigureOK) {
                    self::$nativeCommits++;
                    // Native work has already produced its receipt. The
                    // transport/PHP boundary may still throw InvalidArgument.
                    if (self::$postNativeCommitInvalid) {
                        throw new \InvalidArgumentException('synthetic invalid after native Apply');
                    }
                    return 'applied-id=' . str_repeat('d',32);
                }
                return 'ERROR: interrupted native Apply';
            }
            if ($action !== 'zapret voice_preview_draft') {
                throw new \RuntimeException('unexpected parameterized configd action');
            }
            if (Config::getInstance()->locks !== 0) {
                throw new \RuntimeException('GUI Config lock held during FD9 preview');
            }
            return json_encode([
                'state' => 'native-voice-saved-draft-preview',
                'selected_profiles' => substr_count($params[0], '1'),
                'saved_xml_sha256' => str_repeat('b', 64),
                'safe_to_enable_voice' => false,
                'public_voice_apply' => false,
            ]);
        }
        public function configdRun($action, ...$args) {
            self::$calls[] = $action;
            if ($action === 'zapret voice_inspect') {
                if (Config::getInstance()->locks !== 0) {
                    throw new \RuntimeException('Config lock held across voice status');
                }
                if (self::$inspectThrows) {
                    throw new \RuntimeException('simulated configd Voice inspection outage');
                }
                return self::$inspectResponse;
            }
            if ($action === 'zapret strategy_lab_guard') {
                if (self::$guardThrows) {
                    throw new \RuntimeException('synthetic read-only guard failure');
                }
                return json_encode(['busy' => self::$busy]);
            }
            if ($action === 'zapret reconfigure') {
                return self::$reconfigureOK ? 'OK' : 'ERROR';
            }
            throw new \RuntimeException('unexpected configd action: ' . $action);
        }
    }
}
namespace OPNsense\Zapret {
    class Zapret {
        public static $nodes = [];
        public static int $serializations = 0;
        public static bool $validationThrows = false;
        private ?array $pending = null;
        public function getNodes(): array { return $this->pending ?? self::$nodes; }
        public function setNodes(array $nodes): void { $this->pending = $nodes; }
        public function setNodeByReference(string $reference, $value): bool {
            if ($this->pending === null) $this->pending = self::$nodes;
            $node = &$this->pending;
            foreach (explode('.', $reference) as $part) {
                if (!is_array($node) || !array_key_exists($part, $node)) return false;
                $node = &$node[$part];
            }
            $node = $value;
            unset($node);
            return true;
        }
        public function performValidation($full = false): array {
            if (self::$validationThrows) {
                throw new \RuntimeException('synthetic detached candidate validation failure');
            }
            return [];
        }
        public function serializeToConfig($full = false, $disable = false): bool {
            if ($this->pending === null) return false;
            self::$nodes = $this->pending;
            self::$serializations++;
            return true;
        }
    }
}
namespace {
    require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceController.php';
    require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php';

    use OPNsense\Core\Config;
    use OPNsense\Core\Backend;
    use OPNsense\Zapret\Zapret;
    use OPNsense\Zapret\Api\VoiceController;
    use OPNsense\Zapret\Api\SettingsController;
    use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

    class FakeRequest {
        public $fields;
        public $method;
        public function __construct($method, $fields = null) {
            $this->method = $method;
            $this->fields = $fields;
        }
        public function isGet(): bool { return $this->method === 'GET'; }
        public function isPost(): bool { return $this->method === 'POST'; }
        public function getPost($name) { return $name === 'zapret' ? $this->fields : null; }
    }
    function equal($want, $actual, $message): void {
        if ($want !== $actual) {
            fwrite(STDERR, "FAIL: {$message}\n" . var_export($actual, true) . "\n");
            exit(1);
        }
    }

    Zapret::$nodes = [
        'general' => ['enabled' => '1', 'waninterface' => 'WAN', 'divertport' => '989'],
        'strategy' => ['trafficargs' => '--filter-tcp=443', 'extraargs' => ''],
        'voice' => ['waninterface' => 'WAN'],
        'hostlist' => [
            'telegramips' => '91.108.0.0/16',
            'discordips' => '',
            'xips' => '',
            'sipips' => '',
            'customips' => '',
        ],
    ];
    $candidate = [
        'voice' => [],
        'hostlist' => [],
    ];
    foreach (['telegram','discord','x','sip','custom'] as $service) {
        Zapret::$nodes['voice'][$service] = ['enabled' => '0', 'args' => ''];
        $candidate['voice'][$service] = ['enabled' => '0', 'args' => ''];
        $candidate['hostlist'][$service . 'ips'] =
            Zapret::$nodes['hostlist'][$service . 'ips'];
    }

    $api = new VoiceController();
    $api->request = new FakeRequest('GET');
    $loaded = $api->loadAction();
    equal(Zapret::$nodes, $loaded['zapret'], 'atomic native load must use one saved model');
    equal(64, strlen($loaded['snapshot']), 'baseline digest length');
    equal(0, Config::getInstance()->locks, 'load must release configuration lock');


    // New GUI -> read-only configdp FD9 preflight never stages PREPARED. It
    // accepts only previously saved OFF drafts plus new ON toggles.
    $savedBeforePreview = Zapret::$nodes;
    $telegramDraftArgs = "--filter-udp=*\n--filter-l7=stun\n--payload=stun";
    Zapret::$nodes['voice']['telegram']['args'] = $telegramDraftArgs;
    $previewForm = $candidate;
    $previewForm['voice']['telegram']['enabled'] = '1';
    $previewForm['voice']['telegram']['args'] = $telegramDraftArgs;
    $previewForm['sync'] = ['snapshot' => VoiceSettingsSnapshot::digest(Zapret::$nodes)];
    $previewApi = new class extends VoiceController {
        protected function originalConfigDigest(): string { return str_repeat('a', 64); }
    };
    $previewApi->request = new FakeRequest('POST', $previewForm);
    Backend::$calls = [];
    $preview = $previewApi->previewDraftAction();
    equal('previewed', $preview['result'], 'saved draft read-only FD9 preview must complete');
    equal(false, $preview['saved'], 'read-only preview must not persist the Config');
    equal(false, $preview['prepared'], 'read-only preview must not seal PREPARED');
    equal(false, $preview['applied'], 'read-only preview must not claim Voice ON');
    equal(1, $preview['selected_profiles'], 'native backend selected wrong Voice count');
    equal(['10000', str_repeat('a', 64)], Backend::$params,
        'only selected five-bit mask and exact original Config digest may go to configd');
    equal(['zapret voice_preview_draft'], Backend::$calls,
        'preview must not call runtime reconfigure or PREPARED');
    equal(0, Config::getInstance()->saves, 'preview changed Config');
    equal(0, Config::getInstance()->locks, 'preview leaked Config lock');
    $previewForm['voice']['telegram']['args'] .= "\n--out-range=n1-n2";
    $previewApi->request = new FakeRequest('POST', $previewForm);
    Backend::$calls = [];
    $badPreview = $previewApi->previewDraftAction();
    equal('failed', $badPreview['result'], 'unsaved Voice arguments cannot enter FD9');
    equal([], Backend::$calls, 'invalid saved draft should fail before calling configd');
    $previewForm['voice']['telegram']['args'] = $telegramDraftArgs;
    $previewForm['sync']['snapshot'] = str_repeat('0', 64);
    $previewApi->request = new FakeRequest('POST', $previewForm);
    equal('failed', $previewApi->previewDraftAction()['result'],
        'stale Voice snapshot cannot open FD9');
    equal([], Backend::$calls, 'stale GUI snapshot must not reach configd');
    Zapret::$nodes = $savedBeforePreview;

    $candidate['sync'] = ['snapshot' => $loaded['snapshot']];
    $api->request = new FakeRequest('POST', $candidate);
    $check = $api->validateAction();
    equal('validated', $check['result'], 'fresh Voice form should pass preflight');
    equal('detached-xml-preview-only', $check['scope'], 'preview must never report applied');
    equal(64, strlen($check['candidate_xml_sha256']), 'candidate XML witness missing');
    equal(false, $check['applied'], 'validated XML candidate cannot report Apply');
    equal(0, Config::getInstance()->saves, 'validation cannot persist native Voice');
    equal(0, Config::getInstance()->locks, 'successful validate must unlock config');

    // A read-only malformed source Config can reject candidate XML before
    // any shared Apply. Surface the phase, not an internal PHP exception.
    Config::$malformedXml = true;
    Backend::$calls = [];
    try {
        $badCandidate = $api->validateAction();
    } finally {
        Config::$malformedXml = false;
    }
    equal('failed', $badCandidate['result'], 'malformed candidate XML cannot validate');
    equal('Voice validation preflight rejected (candidate-xml)',
        $badCandidate['validations']['zapret.voice.waninterface'],
        'read-only candidate error must retain a safe, visible phase');
    equal([], Backend::$calls, 'read-only Validate must not invoke configd');
    equal(0, Config::getInstance()->locks, 'failed Validate leaked Config lock');
    equal(0, Config::getInstance()->saves, 'failed Validate persisted Config');

    // Same saved model, different PHP array field ordering: stable digest.
    $reordered = array_reverse(Zapret::$nodes, true);
    equal(VoiceSettingsSnapshot::digest(Zapret::$nodes),
        VoiceSettingsSnapshot::digest($reordered), 'field ordering must not change token');

    Zapret::$nodes['strategy']['trafficargs'] = '--filter-tcp=80';
    $api->request = new FakeRequest('POST', $candidate);
    $stale = $api->validateAction();
    equal('failed', $stale['result'], 'changed ordinary strategy must reject Voice draft');
    equal(true, str_contains($stale['validations']['zapret.voice.waninterface'],
        'changed in another tab'), 'stale form needs a reload message');
    equal(0, Config::getInstance()->locks, 'stale validation must unlock config');

    // Shared Telegram IPSET changed in Strategies tab (same source of truth).
    Zapret::$nodes['strategy']['trafficargs'] = '--filter-tcp=443';
    Zapret::$nodes['hostlist']['telegramips'] = '91.108.13.10';
    $stale2 = $api->validateAction();
    equal('failed', $stale2['result'], 'Telegram IPSET conflict must reject Voice draft');
    Zapret::$nodes['hostlist']['telegramips'] = '91.108.0.0/16';

    // No snapshot or arbitrary injected fields can be accepted even for OFF.
    unset($candidate['sync']);
    $api->request = new FakeRequest('POST', $candidate);
    $missing = $api->validateAction();
    equal('failed', $missing['result'], 'missing digest must not pass');
    equal(0, Config::getInstance()->locks, 'missing snapshot must unlock');

    $candidate['sync'] = ['snapshot' => $loaded['snapshot']];
    $candidate['general'] = ['enabled' => '0'];
    $api->request = new FakeRequest('POST', $candidate);
    equal('failed', $api->validateAction()['result'], 'Voice cannot send global settings');
    unset($candidate['general']);

    $candidate['voice']['telegram']['enabled'] = '1';
    $candidate['voice']['telegram']['args'] =
        "--filter-udp=*\n--filter-l7=stun\n--payload=stun";
    $api->request = new FakeRequest('POST', $candidate);
    $onPreview = $api->validateAction();
    equal('validated', $onPreview['result'],
        'valid enabled Telegram can produce isolated XML without saving');
    equal(64, strlen($onPreview['candidate_xml_sha256']),
        'ON XML preview must return a deterministic digest');
    equal(false, $onPreview['applied'], 'ON preview is not a live Apply');
    equal('0', Zapret::$nodes['voice']['telegram']['enabled'],
        'read-only validation must not mutate persisted Voice checkbox');
    equal(0, Config::getInstance()->locks, 'all paths must release config lock');

    // The new real save endpoint can persist OFF-only drafts without
    // altering active runtime. A checked service must NEVER be persisted
    // while the old staged-only boot guard still rejects native ON.
    $onBlocked = $api->saveDraftAction();
    equal('failed', $onBlocked['result'], 'ON service must not be saved before Apply exists');
    equal(0, Config::getInstance()->saves, 'ON must not write config');
    equal(0, Zapret::$serializations, 'ON must not serialize the model');
    equal(0, Config::getInstance()->locks, 'blocked ON must unlock config');

    $candidate['voice']['telegram']['enabled'] = '0';
    $candidate['voice']['telegram']['args'] = "--filter-udp=*\n--filter-l7=stun\n--payload=stun";
    $candidate['voice']['discord']['args'] = "future STUN candidate, still OFF";
    $candidate['hostlist']['discordips'] = '1.2.3.4';
    $api->request = new FakeRequest('POST', $candidate);
    $saved = $api->saveDraftAction();
    equal('saved', $saved['result'], 'valid OFF draft persists');
    equal(false, $saved['applied'], 'OFF draft must never claim runtime Apply');
    equal(1, Config::getInstance()->saves, 'persist exact one revision');
    equal(1, Zapret::$serializations, 'persist via native model');
    equal('future STUN candidate, still OFF', Zapret::$nodes['voice']['discord']['args'],
        'OFF drafts keep editable arguments across reload');
    equal('1.2.3.4', Zapret::$nodes['hostlist']['discordips'],
        'OFF drafts persist managed shared IPSET inputs');
    equal('--filter-tcp=443', Zapret::$nodes['strategy']['trafficargs'],
        'Voice save must leave ordinary Strategies untouched');
    equal('0', Zapret::$nodes['voice']['telegram']['enabled'],
        'Voice save must not enable native Telegram');
    equal(0, Config::getInstance()->locks, 'successful save unlocks config');
    $api->request = new FakeRequest('GET');
    $newLoad = $api->loadAction();
    equal($saved['snapshot'], $newLoad['snapshot'], 'saved snapshot matches loaded Config');

    $api->request = new FakeRequest('POST', $candidate);
    $staleSave = $api->saveDraftAction();
    equal('failed', $staleSave['result'], 'old browser snapshot must reject second write');
    equal(false, $staleSave['requires_review'] ?? false,
        'pre-write stale-form rejection must remain editable');
    equal(1, Config::getInstance()->saves, 'stale browser cannot overwrite Config');
    $candidate['sync']['snapshot'] = $newLoad['snapshot'];
    $api->request = new FakeRequest('POST', $candidate);
    $same = $api->saveDraftAction();
    equal('saved', $same['result'], 'same OFF draft can be saved idempotently');
    equal(0, $same['change_count'], 'unchanged draft is a no-op');
    equal(1, Config::getInstance()->saves, 'no-op must not create revision');

    // Existing unexpected persisted ON is never overwritten or treated as
    // an inactive safe state by this separate save path.
    Zapret::$nodes['voice']['sip']['enabled'] = '1';
    $candidate['sync']['snapshot'] = VoiceSettingsSnapshot::digest(Zapret::$nodes);
    $api->request = new FakeRequest('POST', $candidate);
    $existingOn = $api->saveDraftAction();
    equal('failed', $existingOn['result'], 'existing ON cannot be saved as OFF draft');
    equal(1, Config::getInstance()->saves, 'existing ON guard cannot write');
    Zapret::$nodes['voice']['sip']['enabled'] = '0';

    // One root original-FD9 native Apply endpoint, for OFF and ON alike.
    // The GUI itself must not serialize/Config::save before kernel commit.
    $candidate['sync']['snapshot'] = VoiceSettingsSnapshot::digest(Zapret::$nodes);
    $api->request = new FakeRequest('POST', $candidate);
    Backend::$calls = [];
    $offApply = $api->applyAction();
    equal('saved', $offApply['result'], 'all-OFF native Voice Apply should succeed');
    equal(true, $offApply['applied'], 'native receipt must confirm Apply');
    equal(['zapret strategy_lab_guard','zapret shared_apply'], Backend::$calls,
        'OFF Voice must use only the common native Apply');
    equal('voice', Backend::$params[0], 'FD9 Apply page not pinned');
    equal(1, Config::getInstance()->saves, 'GUI must not pre-save native Config');
    equal(0, Config::getInstance()->locks, 'FD9 must run outside GUI Config lock');

    $candidate['voice']['telegram']['enabled'] = '1';
    $candidate['voice']['telegram']['args'] =
        "--filter-udp=*\n--filter-l7=stun\n--payload=stun\n" .
        "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2";
    Backend::$calls = [];
    $api->request = new FakeRequest('POST', $candidate);
    $onApply = $api->applyAction();
    equal('saved', $onApply['result'],
        'enabled native Voice must enter full common Apply instead of legacy OFF guard');
    equal(true, $onApply['applied'], 'confirmed ON must be reported');
    equal(['zapret strategy_lab_guard','zapret shared_apply'], Backend::$calls,
        'ON must never call legacy reconfigure');
    $decoded = json_decode(base64_decode(strtr(Backend::$params[1], '-_', '+/')), true);
    equal('1', $decoded['fields']['voice']['telegram']['enabled'],
        'ON setting lost between unchanged GUI and original FD9 backend');
    equal(1, Config::getInstance()->saves,
        'native ON cannot be pre-saved by the browser-side controller');
    $candidate['voice']['telegram']['enabled'] = '0';
    $candidate['voice']['telegram']['args'] =
        "--filter-udp=*\n--filter-l7=stun\n--payload=stun";

    $candidate['hostlist']['discordips'] = '1.2.3.5';
    $candidate['sync']['snapshot'] = VoiceSettingsSnapshot::digest(Zapret::$nodes);
    Backend::$busy = true;
    $api->request = new FakeRequest('POST', $candidate);
    $busy = $api->applyAction();
    equal('failed', $busy['result'], 'Strategy Lab must block Voice native Apply');
    equal(1, Config::getInstance()->saves, 'busy runtime must not write GUI Config');
    Backend::$busy = false;

    // A Throwable raised while checking the read-only guard occurs BEFORE
    // dispatch. There is no Config write or shared FD9 Apply to review.
    // Previously this falsely marked the outcome "unknown" in the GUI.
    Backend::$guardThrows = true;
    Backend::$calls = [];
    $api->request = new FakeRequest('POST', $candidate);
    try {
        $guardFault = $api->applyAction();
    } finally {
        Backend::$guardThrows = false;
    }
    equal('failed', $guardFault['result'], 'pre-FD9 Throwable must be explicit failed');
    equal(false, $guardFault['applied'], 'pre-FD9 Throwable must not claim Apply');
    equal(false, $guardFault['requires_review'] ?? false,
        'read-only guard failure must not masquerade as uncertain Apply');
    equal('Voice preflight rejected before native Apply (guard)',
        $guardFault['validations']['zapret.voice.waninterface'],
        'safe diagnostic stage must be available without leaking raw errors');
    equal(['zapret strategy_lab_guard'], Backend::$calls,
        'guard failure must never dispatch shared_apply');
    equal(1, Config::getInstance()->saves,
        'guard failure cannot save Config');

    // The privileged worker may fail after it has touched Config/kernel.
    // Browser MUST NOT claim saved, applied, or rollback merely from HTTP.
    Backend::$reconfigureOK = false;
    $failed = $api->applyAction();
    equal('failed', $failed['result'], 'failed native Apply must be visible');
    equal(false, $failed['applied'], 'interrupted native Apply cannot report success');
    equal(true, $failed['requires_review'], 'ambiguous native Apply needs review');
    equal('1.2.3.4', Zapret::$nodes['hostlist']['discordips'],
        'GUI cannot pre-save candidate before FD9 transaction');
    equal(1, Config::getInstance()->saves,
        'native failure cannot cause browser-side Config writes');
    Backend::$reconfigureOK = true;
    $candidate['sync']['snapshot'] = VoiceSettingsSnapshot::digest(Zapret::$nodes);
    $api->request = new FakeRequest('POST', $candidate);
    $retried = $api->applyAction();
    equal('saved', $retried['result'], 'native Apply retry with same snapshot accepted');
    equal(true, $retried['applied'], 'native confirmed receipt reports Applied');
    equal(1, Config::getInstance()->saves,
        'GUI does not re-persist native Config');

    // A pre-dispatch InvalidArgumentException (stale snapshot) is still an
    // editable form error and MUST NOT invoke the privileged worker.
    $candidate['sync']['snapshot'] = str_repeat('0', 64);
    $api->request = new FakeRequest('POST', $candidate);
    Backend::$calls = [];
    $staleApply = $api->applyAction();
    equal('failed', $staleApply['result'], 'stale native Apply baseline must fail');
    equal(false, $staleApply['requires_review'],
        'pre-dispatch validation must not incorrectly demand post-Apply review');
    equal(['zapret strategy_lab_guard'], Backend::$calls,
        'stale native Apply cannot reach privileged mutation');
    $candidate['sync']['snapshot'] = VoiceSettingsSnapshot::digest(Zapret::$nodes);

    // Native Apply may fully finish but PHP/transport still raises the
    // InvalidArgumentException class, despite a committed Config/runtime.
    // The response MUST require inspection instead of inviting a blind retry.
    $api->request = new FakeRequest('POST', $candidate);
    Backend::$calls = [];
    $beforeNativeCommit = Backend::$nativeCommits;
    Backend::$postNativeCommitInvalid = true;
    try {
        $postApplyFault = $api->applyAction();
    } finally {
        Backend::$postNativeCommitInvalid = false;
    }
    equal('failed', $postApplyFault['result'],
        'exception after native Apply must never report success');
    equal(false, $postApplyFault['applied'],
        'post-commit exception must not assert Applied without a PHP receipt');
    equal(true, $postApplyFault['requires_review'],
        'post-commit InvalidArgumentException requires explicit runtime review');
    equal($beforeNativeCommit + 1, Backend::$nativeCommits,
        'regression must simulate completion before InvalidArgumentException');
    equal(['zapret strategy_lab_guard', 'zapret shared_apply'], Backend::$calls,
        'regression must exercise real common FD9 Apply entrypoint');
    equal(0, Config::getInstance()->locks,
        'post-commit error cannot leave GUI Config lock held');

    // The Voice status widget is read-only and must always fail closed.
    // An unowned bare "ready" (without an attested native-common source)
    // cannot become readiness merely because configd returned HTTP success.
    // The valid five-service native-common case is covered by
    // test-voice-inspect-config-runtime.php, not this concurrency fixture.
    Backend::$inspectResponse = json_encode([
        'state' => 'ready', 'can_activate' => true,
        'condition' => 'verified', 'service' => 'telegram',
        'rule_count' => 3, 'table_count' => 1,
    ]);
    $api->request = new FakeRequest('POST', []);
    Backend::$calls = [];
    $inspection = $api->inspectAction();
    equal('interrupted', $inspection['state'],
          'unowned Voice status must not report ready');
    equal('common-profile-unverified', $inspection['condition'],
          'unowned Voice status did not explain the missing native owner');
    equal(false, $inspection['can_activate'],
          'unowned Voice status authorized activation');
    equal(false, isset($inspection['profiles']),
          'unowned Voice status fabricated service profiles');
    equal(['zapret voice_inspect'], Backend::$calls,
          'Voice status did not use the existing common backend');
    Backend::$inspectResponse = '{malformed';
    $badStatus = $api->inspectAction();
    equal('inspection-error', $badStatus['state'],
          'invalid Voice status accepted');
    equal(false, $badStatus['can_activate'],
          'invalid Voice status authorized activation');
    Backend::$inspectThrows = true;
    $unavailable = $api->inspectAction();
    equal('inspection-error', $unavailable['state'],
          'configd inspection exception escaped Voice API');
    equal(false, $unavailable['can_activate'],
          'configd inspection exception authorized activation');
    equal('status-unavailable', $unavailable['remedy'],
          'configd exception did not return actionable status');
    Backend::$inspectThrows = false;
    $api->request = new FakeRequest('GET', []);
    $deniedStatus = $api->inspectAction();
    equal('inspection-error', $deniedStatus['state'],
          'Voice status must require POST');
    equal(false, $deniedStatus['can_activate'],
          'GET bypassed Voice status guard');

    // Read-only GUI/API credentials must not gain a write path.
    $candidate['sync']['snapshot'] = VoiceSettingsSnapshot::digest(Zapret::$nodes);
    $api->request = new FakeRequest('POST', $candidate);
    \OPNsense\Base\ApiControllerBase::$denyWrites = true;
    try {
        $api->saveDraftAction();
        fwrite(STDERR, "FAIL: read-only caller was allowed to save Voice draft\n");
        exit(1);
    } catch (\RuntimeException $expected) {
        equal('read-only user', $expected->getMessage(), 'read-only access rejected');
    } finally {
        \OPNsense\Base\ApiControllerBase::$denyWrites = false;
    }
    equal(1, Config::getInstance()->saves, 'denied write did not touch Config');

    // Functional offline draft path: before WAN setup, all five switches are
    // OFF. Saving changes neither the running engine nor configd ownership.
    Zapret::$nodes['general']['waninterface'] = '';
    Zapret::$nodes['voice']['waninterface'] = 'WAN2';
    foreach (['telegram','discord','x','sip','custom'] as $service) {
        Zapret::$nodes['voice'][$service]['enabled'] = '0';
    }
    $offlineForm = ['voice' => array_diff_key(Zapret::$nodes['voice'], ['waninterface' => true]), 'hostlist' => []];
    foreach (['telegram','discord','x','sip','custom'] as $service) {
        $offlineForm['hostlist'][$service . 'ips'] = Zapret::$nodes['hostlist'][$service . 'ips'];
    }
    $offlineForm['voice']['custom']['args'] = 'offline custom STUN draft';
    $offlineForm['hostlist']['customips'] = '203.0.113.0/24';
    $offlineForm['sync'] = ['snapshot' => VoiceSettingsSnapshot::digest(Zapret::$nodes)];
    $api->request = new FakeRequest('POST', $offlineForm);
    Backend::$calls = [];
    $priorOfflineSaves = Config::getInstance()->saves;
    $offlineSaved = $api->saveDraftAction();
    equal('saved', $offlineSaved['result'],
          'all-OFF Voice drafts must save before configuring Strategies WAN');
    equal(false, $offlineSaved['applied'], 'offline drafts cannot claim live Apply');
    equal($priorOfflineSaves + 1, Config::getInstance()->saves,
          'offline draft must persist once through native Config');
    equal('offline custom STUN draft', Zapret::$nodes['voice']['custom']['args'],
          'offline draft parameters were not persisted');
    equal('203.0.113.0/24', Zapret::$nodes['hostlist']['customips'],
          'offline draft IPSET was not persisted');
    equal([], Backend::$calls, 'offline SaveDraft must never invoke runtime/configd');
    equal(0, Config::getInstance()->locks, 'offline draft must release Config lock');

    // A native Config write may complete and THEN report an InvalidArgumentException.
    // Never classify it as a harmless pre-write validation failure: the GUI
    // must refuse blind retry even when the exception type is "validation".
    $uncertain = $offlineForm;
    $uncertain['sync']['snapshot'] = VoiceSettingsSnapshot::digest(Zapret::$nodes);
    $uncertain['voice']['custom']['args'] = 'new uncertain saved custom draft';
    $api->request = new FakeRequest('POST', $uncertain);
    $beforeUncertainSaves = Config::getInstance()->saves;
    Config::getInstance()->throwInvalidAfterSave = true;
    try {
        $afterWriteFault = $api->saveDraftAction();
    } finally {
        Config::getInstance()->throwInvalidAfterSave = false;
    }
    equal('failed', $afterWriteFault['result'],
        'post-save InvalidArgumentException must not claim a confirmed save');
    equal(true, $afterWriteFault['requires_review'] ?? false,
        'post-save InvalidArgumentException must require manual review');
    equal('Voice draft could not be saved',
        $afterWriteFault['validations']['zapret.voice.waninterface'] ?? null,
        'post-save failure must not leak an apparently editable validation error');
    equal($beforeUncertainSaves + 1, Config::getInstance()->saves,
        'test must reach native Config save before throwing');
    equal('new uncertain saved custom draft', Zapret::$nodes['voice']['custom']['args'],
        'test must prove Config was changed despite failed API response');
    equal(0, Config::getInstance()->locks,
        'post-save error must release native Config lock');

    // A Strategies XML candidate validates ALL ordinary model leaves.
    // The earlier Voice-only stub intentionally omitted these four fields.
    Zapret::$nodes['hostlist'] += [
        'mode' => 'auto', 'youtubedomains' => '',
        'userdomains' => '', 'excludedomains' => '',
    ];
    // Strategies shares the SAME FD9 worker. Post-dispatch exceptions must
    // never masquerade as safe field errors on that second GUI.
    $strategy = new SettingsController();
    $strategyFields = [
        'sync' => ['telegramips_baseline' => Zapret::$nodes['hostlist']['telegramips']],
        // Ordinary settings are unchanged; exercise the actual endpoint
        // without introducing unrelated Strategy Lab/model fixtures.
        'strategy' => ['trafficargs' => Zapret::$nodes['strategy']['trafficargs']],
    ];
    $strategy->request = new FakeRequest('POST', $strategyFields);
    Backend::$calls = [];
    $safeStrategy = $strategy->applyAction();
    equal('saved', $safeStrategy['result'],
        'baseline native Strategies shared Apply must succeed');

    $strategyFields['sync']['telegramips_baseline'] = '203.0.113.0/24';
    $strategy->request = new FakeRequest('POST', $strategyFields);
    Backend::$calls = [];
    $staleStrategy = $strategy->applyAction();
    equal('failed', $staleStrategy['result'],
        'stale Strategies Telegram baseline must be rejected');
    equal(false, $staleStrategy['requires_review'] ?? false,
        'pre-dispatch Strategies rejection remains editable');
    equal(false, in_array('zapret shared_apply', Backend::$calls, true),
        'stale Strategies form must not dispatch native work');

    $strategyFields['sync']['telegramips_baseline'] =
        Zapret::$nodes['hostlist']['telegramips'];
    $strategy->request = new FakeRequest('POST', $strategyFields);

    // A safe root preflight rejection never reaches durable transaction
    // phases and MUST NOT be misreported as an uncertain commit.
    foreach (['candidate-validation', 'runtime-build', 'seal'] as $phase) {
        Backend::$preflightReceipt = 'preflight-rejected=' . $phase;
        Backend::$calls = [];
        $commitsBefore = Backend::$nativeCommits;
        $rejected = $strategy->applyAction();
        equal('failed', $rejected['result'], 'safe preflight receipt must fail');
        equal(false, $rejected['requires_review'] ?? null,
            'preflight receipt is safe and must not freeze Strategies');
        equal(false, $rejected['applied'] ?? null,
            'preflight receipt cannot claim Apply');
        equal(true, strpos($rejected['message'] ?? '', $phase) !== false,
            'failed native stage must be visible in the GUI response');
        equal($commitsBefore, Backend::$nativeCommits,
            'preflight receipt must not simulate a native commit');
    }
    Backend::$preflightReceipt = null;

    // A guard exception BEFORE native dispatch may not be an unknown result.
    Backend::$guardThrows = true;
    Backend::$calls = [];
    try {
        $guardRejected = $strategy->applyAction();
    } finally {
        Backend::$guardThrows = false;
    }
    equal('failed', $guardRejected['result'],
        'pre-dispatch guard failure should have an API response');
    equal(false, $guardRejected['requires_review'] ?? null,
        'pre-dispatch guard failure cannot require runtime reconciliation');
    equal(true, strpos($guardRejected['message'] ?? '', 'lifecycle-guard') !== false,
        'guard failure must report the safe rejected stage');
    equal(false, in_array('zapret shared_apply', Backend::$calls, true),
        'guard failure must not dispatch native work');

    // Force an actual Throwable inside detached candidate validation,
    // before Config persistence and before root FD9 dispatch.
    Zapret::$validationThrows = true;
    Backend::$calls = [];
    try {
        $validationRejected = $strategy->applyAction();
    } finally {
        Zapret::$validationThrows = false;
    }
    equal('failed', $validationRejected['result'],
        'detached candidate validation exception must reject Strategies Apply');
    equal(false, $validationRejected['requires_review'] ?? null,
        'pre-dispatch candidate validation error cannot require recovery');
    equal(true, strpos($validationRejected['message'] ?? '', 'candidate-validation') !== false,
        'candidate validator exception must reveal safe failure stage');
    equal(false, in_array('zapret shared_apply', Backend::$calls, true),
        'detached candidate validation fault must not dispatch');

    Backend::$postNativeCommitInvalid = true;
    Backend::$calls = [];
    $commitsBefore = Backend::$nativeCommits;
    try {
        $uncertainStrategy = $strategy->applyAction();
    } finally {
        Backend::$postNativeCommitInvalid = false;
    }
    equal('failed', $uncertainStrategy['result'],
        'post-commit exception must never confirm Strategies Apply');
    equal(true, $uncertainStrategy['requires_review'] ?? false,
        'post-commit Strategies InvalidArgumentException demands review');
    equal(false, $uncertainStrategy['applied'] ?? null,
        'post-commit Strategies must not claim Applied');
    equal($commitsBefore + 1, Backend::$nativeCommits,
        'Strategies regression must simulate a completed native commit');
    equal(true, in_array('zapret shared_apply', Backend::$calls, true),
        'Strategies regression must use shared native FD9 worker');
    equal(0, Config::getInstance()->locks,
        'Strategies Apply must release the GUI Config lock');

    echo "PASS: shared native FD9 Voice/Strategies Apply, envelope, Config lock and review guards\n";
}
