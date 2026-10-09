<?php
/**
 * Native Voice API concurrency and read-only contract, with isolated stubs.
 * No OPNsense Config, configd, IPFW or running service are modified.
 */
namespace OPNsense\Base {
    class ApiControllerBase {
        public $request;
    }
}
namespace OPNsense\Core {
    class Config {
        public static $instance;
        public int $locks = 0;
        public static function getInstance() {
            return self::$instance ?? (self::$instance = new self());
        }
        public function lock(): void { $this->locks++; }
        public function unlock(): void { $this->locks--; }
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
        public function getNodes(): array {
            return self::$nodes;
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

    echo "PASS: atomic Voice load, stale-tab rejection, strict form ownership and no writes\n";
}
