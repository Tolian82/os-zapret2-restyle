<?php
/**
 * Execute the real Voice read-only API with a private native Config/model
 * and inspector fixture. No OPNsense, kernel, process or network mutations.
 */
namespace OPNsense\Base {
    class ApiControllerBase { public $request; }
}
namespace OPNsense\Core {
    class Backend {
        public static string $response = '';
        public function configdRun(string $action, bool $wait = false, int $timeout = 0): string {
            if ($action !== 'zapret voice_inspect') {
                throw new \RuntimeException('Unexpected configd action');
            }
            return self::$response;
        }
    }
    class Config {
        public static array $model = [];
        public static int $locks = 0;
        public static function getInstance(): self { return new self(); }
        public function lock(): void { ++self::$locks; }
        public function unlock(): void { --self::$locks; }
    }
}
namespace OPNsense\Zapret {
    class Zapret {
        public function getNodes(): array { return \OPNsense\Core\Config::$model; }
    }
}
namespace {
    require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceController.php';

    use OPNsense\Core\Backend;
    use OPNsense\Core\Config;
    use OPNsense\Zapret\Api\VoiceController;
    use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

    class PostRequest { public function isPost(): bool { return true; } }
    function verify(bool $ok, string $message): void {
        if (!$ok) { fwrite(STDERR, "FAIL: {$message}\n"); exit(1); }
    }
    $voice = [];
    $hostlist = [];
    foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $name) {
        $voice[$name] = ['enabled' => $name === 'telegram' ? '1' : '0', 'args' => ''];
        $hostlist[$name . 'ips'] = $name === 'telegram' ? '91.108.13.10' : '';
    }
    Config::$model = [
        'general' => ['waninterface' => 'WAN', 'enabled' => '1'],
        'strategy' => [], 'voice' => ['waninterface' => 'WAN'] + $voice,
        'hostlist' => $hostlist,
    ];
    $digest = VoiceSettingsSnapshot::digest(Config::$model);
    $services = [];
    foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $name) {
        $enabled = $name === 'telegram';
        $services[$name] = [
            'configured' => $enabled, 'capture_verified' => $enabled,
            'runtime_state' => $enabled ? 'engine-present' : 'disabled',
            'media_verified' => false,
        ];
    }
    $native = [
        'state' => 'ready', 'source' => 'native-common',
        'config_digest' => $digest, 'can_activate' => false,
        'rule_count' => 2, 'table_count' => 1,
        'runtime' => [
            'state' => 'running', 'source_verified' => true,
            'engine_verified' => true, 'supervisor_verified' => true,
            'services' => $services,
        ],
    ];
    $controller = new VoiceController();
    $controller->request = new PostRequest();
    $inspect = static function (array $payload) use ($controller): array {
        Backend::$response = json_encode($payload, JSON_THROW_ON_ERROR);
        $answer = $controller->inspectAction();
        verify(Config::$locks === 0, 'Config lock leaked from read-only inspection');
        return $answer;
    };
    $ok = $inspect($native);
    verify($ok['state'] === 'ready' && count($ok['profiles']) === 5,
        'committed five-service snapshot was not exposed');
    verify($ok['profiles']['telegram'] === [
        'saved_enabled'=>true, 'runtime'=>'active',
        'media_verified'=>false, 'call_verified'=>false,
    ], 'Telegram was not separately and truthfully reported');
    verify($ok['profiles']['discord']['runtime'] === 'disabled' &&
        $ok['profiles']['discord']['saved_enabled'] === false,
        'disabled Voice service was fabricated as active');
    verify(!isset($ok['config_digest'], $ok['runtime']),
        'private/native inspector contents leaked to GUI');

    $stopped = $native;
    $stopped['state'] = 'stopped';
    $stopped['runtime']['state'] = 'stopped';
    $stopped['runtime']['engine_verified'] = false;
    $stopped['runtime']['supervisor_verified'] = false;
    $stopped['runtime']['services']['telegram']['runtime_state'] = 'engine-not-confirmed';
    $halted = $inspect($stopped);
    verify($halted['state'] === 'stopped' &&
        $halted['profiles']['telegram']['runtime'] === 'stopped',
        'saved ON must survive normal Stop without claiming live engine');

    $changed = $native;
    $changed['config_digest'] = str_repeat('0', 64);
    $drift = $inspect($changed);
    verify($drift['state'] === 'interrupted' &&
        $drift['condition'] === 'common-config-mismatch' &&
        !isset($drift['profiles']),
        'a changed saved Config must remove GUI readiness');

    $broken = $native;
    $broken['runtime']['services']['telegram']['capture_verified'] = false;
    $mismatch = $inspect($broken);
    verify($mismatch['state'] === 'interrupted' &&
        $mismatch['condition'] === 'common-profile-unverified' &&
        !isset($mismatch['profiles']),
        'runtime/Config disagreement must fail closed');

    $legacy = $native;
    $legacy['source'] = 'old-ledger';
    $legacyView = $inspect($legacy);
    verify(!isset($legacyView['profiles']),
        'legacy or unowned status must not authorize five-service readiness');

    $pending = ['state'=>'interrupted', 'can_activate'=>false,
                'condition'=>'shared-apply-activating'];
    verify(!isset($inspect($pending)['profiles']),
        'unfinished Apply must not expose committed profile readiness');
    echo "PASS: saved Config, common runtime, five Voice profiles and read-only GUI attestation\n";
}
