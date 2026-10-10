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
    }
    class Backend {
        public function configdRun() {
            throw new \RuntimeException('Voice draft validation must not call configd');
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

    $candidate['sync'] = ['snapshot' => $loaded['snapshot']];
    $api->request = new FakeRequest('POST', $candidate);
    $check = $api->validateAction();
    equal('validated', $check['result'], 'fresh Voice form should pass preflight');
    equal('syntax-only', $check['scope'], 'preflight must never report applied');
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
    equal('validated', $api->validateAction()['result'],
        'valid enabled Telegram can be syntax-checked without saving');
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
    $newLoad = $api->loadAction();
    equal($saved['snapshot'], $newLoad['snapshot'], 'saved snapshot matches loaded Config');

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

    echo "PASS: locked Voice load/validate, OFF-only native persisted draft, stale-tab guard, no unsafe ON save\n";
}
