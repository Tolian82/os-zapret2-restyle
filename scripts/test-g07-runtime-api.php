<?php
/** G07 S0: execute the actual runtimeAction/installAction with isolated configd receipts. */
namespace OPNsense\Base {
    class ApiMutableServiceControllerBase { public $request; }
    class UserException extends \RuntimeException {
        public function __construct($message, $title = '') { parent::__construct($message); }
    }
}
namespace OPNsense\Core {
    class Backend {
        public static string $receipt = "installed=0\nservice=error\nversion=\nsetup=unknown\nbusy=0";
        public static array $mutations = [];
        public function configdRun($key, ...$ignored): string {
            if ($key === 'zapret setup_status') return self::$receipt;
            if ($key === 'zapret setup_releases') return "v1.0.7\n";
            throw new \RuntimeException('Unexpected read-only action: ' . $key);
        }
        public function configdpRun($key, $args, ...$ignored): string {
            self::$mutations[] = [$key, $args];
            return 'OK';
        }
    }
}
namespace {
    use OPNsense\Core\Backend;
    use OPNsense\Base\UserException;
    require dirname(__DIR__) .
        '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php';

    class FakeRequest {
        public function isPost(): bool { return true; }
        public function getPost($key) { return $key === 'version' ? 'v1.0.7' : ''; }
    }
    function assertion($check, $message): void {
        if (!$check) throw new \RuntimeException('G07_FAIL:' . $message);
    }
    function controller(): \OPNsense\Zapret\Api\ServiceController {
        $item = new \OPNsense\Zapret\Api\ServiceController();
        $item->request = new FakeRequest();
        return $item;
    }
    function status(string $fixture): array {
        Backend::$receipt = $fixture;
        return controller()->runtimeAction();
    }
    function refusedInstall(string $fixture): void {
        Backend::$receipt = $fixture;
        $before = count(Backend::$mutations);
        try {
            controller()->installAction();
        } catch (UserException $error) {
            assertion(str_contains($error->getMessage(), 'status cannot be verified') ||
                      str_contains($error->getMessage(), 'already in progress') ||
                      str_contains($error->getMessage(), 'error state'),
                      'wrong fail-closed message');
            assertion(count(Backend::$mutations) === $before, 'mutating configd called');
            return;
        }
        throw new \RuntimeException('G07_FAIL:unqualified new setup accepted');
    }

    $clean = "installed=0\nservice=error\nversion=\nsetup=unknown\nbusy=0";
    $running = "installed=1\nservice=started\nversion=v1.0.7\nsetup=ready\nbusy=0";
    $stopped = "installed=1\nservice=stopped\nversion=v1.0.7\nsetup=ready\nbusy=0";
    $installing = "installed=0\nservice=error\nversion=\nsetup=installing\nbusy=1";
    foreach ([
        [$clean, false, false, 'error'],
        [$running, true, false, 'started'],
        [$stopped, true, false, 'stopped'],
        [$installing, false, true, 'error']
    ] as [$receipt, $installed, $busy, $service]) {
        $actual = status($receipt);
        assertion($actual['status'] === 'ok' &&
            $actual['installed'] === $installed &&
            $actual['busy'] === $busy && $actual['service'] === $service,
            'valid genuine native receipt incorrectly refused');
    }
    // The clean documented release path still allows exactly one native install.
    Backend::$receipt = $clean;
    $result = controller()->installAction();
    assertion($result === ['status' => 'ok', 'version' => 'v1.0.7'],
              'genuine first install denied');
    assertion(Backend::$mutations === [['zapret setup_install', ['v1.0.7']]],
              'unexpected configd mutation identity');
    Backend::$mutations = [];
    refusedInstall($installing);
    refusedInstall("installed=1\nservice=error\nversion=v1.0.7\nsetup=ready\nbusy=0");

    $malformed = [
        '',
        "installed=0\nservice=error\nsetup=unknown\nbusy=0",
        "installed=0\nservice=error\nversion=\nsetup=unknown",
        $clean . "\ninstalled=0",
        "installed=2\nservice=error\nversion=\nsetup=unknown\nbusy=0",
        "installed=0\nservice=started\nversion=\nsetup=unknown\nbusy=0",
        "installed=0\nservice=error\nversion=v1.0.7\nsetup=unknown\nbusy=0",
        "installed=1\nservice=started\nversion=foo\nsetup=ready\nbusy=0",
        "installed=0\nservice=error\nversion=\nsetup=garbage\nbusy=0",
        "installed=0\nservice=error\nversion=\nsetup=unknown\nbusy=foo",
        "installed=0\nservice=error\nversion=\nsetup=installing\nbusy=0",
        "installed=0\nservice=error\nversion=\nsetup=unknown\nbusy=1",
        "installed=0\nservice=error\nversion=\nsetup=unknown\nbusy=0\nextra=1",
    ];
    foreach ($malformed as $fixture) {
        $actual = status($fixture);
        assertion($actual['status'] === 'unavailable' &&
                  $actual['installed'] === null &&
                  $actual['reason'] === 'status-unavailable',
                  'malformed status wrongly called clean installation');
        refusedInstall($fixture);
    }
    assertion(count(Backend::$mutations) === 0,
              'unverified receipt triggered a real setup mutation');
    echo "G07_NATIVE_STATUS_API_FAST=PASS\n";
}
