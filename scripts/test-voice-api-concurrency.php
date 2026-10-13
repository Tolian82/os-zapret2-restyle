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
}
namespace OPNsense\Core {
    class Config {
        public static $instance;
        public int $locks = 0;
        public int $saves = 0;
        public static function getInstance() {
            return self::$instance ?? (self::$instance = new self());
        }
        public function lock(): void { $this->locks++; }
        public function unlock(): void { $this->locks--; }
        public function save($audit = []): void { $this->saves++; }
        // Production OPNsense Config::__toString() returns its independent
        // full XML serialization; this stub must expose that same read-only
        // API without simulating any persistence.
        public function __toString(): string {
            return '<?xml version="1.0" encoding="utf-8"?>' .
                '<opnsense><system><hostname>old</hostname></system>' .
                '<OPNsense><Zapret><voice/></Zapret></OPNsense></opnsense>';
        }
    }
    class Backend {
        public static bool $busy = false;
        public static bool $reconfigureOK = true;
        public static string $recoveryResponse = '';
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
                    $params[0] !== 'voice') {
                    throw new \RuntimeException('Unexpected native Apply page/parameters');
                }
                $raw = base64_decode(strtr($params[1], '-_', '+/'), true);
                $request = is_string($raw) ? json_decode($raw, true) : null;
                if (!is_array($request) || ($request['page'] ?? null) !== 'voice' ||
                    !is_array($request['fields'] ?? null) ||
                    !is_array($request['sync'] ?? null)) {
                    throw new \RuntimeException('Invalid native Apply envelope');
                }
                return self::$reconfigureOK
                    ? 'applied-id=' . str_repeat('d',32)
                    : 'ERROR: interrupted native Apply';
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
            if ($action === 'zapret voice_recovery_status') {
                if (Config::getInstance()->locks !== 0) {
                    throw new \RuntimeException('Config lock held across recovery status');
                }
                return self::$recoveryResponse;
            }
            if ($action === 'zapret strategy_lab_guard') {
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
        private ?array $pending = null;
        public function getNodes(): array { return $this->pending ?? self::$nodes; }
        public function setNodes(array $nodes): void { $this->pending = $nodes; }
        public function performValidation($full = false): array { return []; }
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

    use OPNsense\Core\Config;
    use OPNsense\Core\Backend;
    use OPNsense\Zapret\Zapret;
    use OPNsense\Zapret\Api\VoiceController;
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
        'voice' => ['waninterface' => 'WAN'],
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

    // A valid on-disk old rollback receipt is NOT boot-ready or Voice ON.
    $api->request = new FakeRequest('POST', []);
    Backend::$recoveryResponse = 'legacy-voice-boot-review=' . json_encode([
        'state' => 'legacy-whole-disk-valid-live-boot-recheck-required',
        'safe_to_mutate' => false, 'safe_to_start' => false,
        'public_voice_apply' => false, 'boot_recovery_validated' => false,
        'previous_five' => ['private' => 'do not expose'],
    ]);
    $review = $api->recoveryStatusAction();
    equal('legacy-whole-disk-valid-live-boot-recheck-required', $review['state'],
          'disk receipt mapped to nonauthorizing recovery label');
    equal(false, $review['public_voice_apply'], 'disk receipt cannot grant Voice Apply');
    equal(false, isset($review['previous_five']), 'journal internals redacted from API');
    Backend::$recoveryResponse = 'legacy-voice-boot-review=' . json_encode([
        'state' => 'legacy-whole-disk-valid-live-boot-recheck-required',
        'safe_to_mutate' => true, 'safe_to_start' => false,
        'public_voice_apply' => false, 'boot_recovery_validated' => false,
    ]);
    equal('unavailable', $api->recoveryStatusAction()['state'],
          'unsafe claimed permissions rejected');
    Backend::$recoveryResponse = 'ERROR: corrupt evidence';
    equal('unavailable', $api->recoveryStatusAction()['state'],
          'untrusted configd output rejected');
    $api->request = new FakeRequest('GET', []);
    equal('unavailable', $api->recoveryStatusAction()['state'],
          'recovery status only accepts POST');

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

    echo "PASS: shared native FD9 Voice ON/OFF Apply, envelope, Config lock and Strategy Lab guards\n";
}
