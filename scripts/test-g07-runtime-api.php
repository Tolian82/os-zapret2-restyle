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
        public static string $releaseReceipt = "v1.0.7\n";
        public static string $reconfigureReceipt = 'OK';
        public static bool $reconfigureThrows = false;
        public static int $reconfigureCalls = 0;
        public function configdRun($key, ...$ignored): string {
            if ($key === 'zapret setup_status') return self::$receipt;
            if ($key === 'zapret setup_releases') return self::$releaseReceipt;
            if ($key === 'zapret reconfigure') {
                self::$reconfigureCalls++;
                if (self::$reconfigureThrows) {
                    throw new \RuntimeException('transport exception: /conf/config.xml SECRET_BACKEND');
                }
                return self::$reconfigureReceipt;
            }
            throw new \RuntimeException('Unexpected read-only action: ' . $key);
        }
        public function configdpRun($key, $args, ...$ignored): string {
            self::$mutations[] = [$key, $args];
            return 'OK';
        }
    }
}
// Inert stage-file hook: load the *actual* source controller while ensuring
// no test ever reads or mutates a real appliance /var/run record.
namespace OPNsense\Zapret\Api {
    class S05mStageProbe {
        public static bool $present = false;
        public static string $record = '';
        public static int $reads = 0;
    }
    function is_readable($path): bool {
        if ($path === '/var/run/zapret2-execution.status') {
            S05mStageProbe::$reads++;
            return S05mStageProbe::$present;
        }
        return \is_readable($path);
    }
    function file_get_contents($path) {
        if ($path === '/var/run/zapret2-execution.status') {
            S05mStageProbe::$reads++;
            return S05mStageProbe::$record;
        }
        return \file_get_contents($path);
    }
}
namespace {
    use OPNsense\Core\Backend;
    use OPNsense\Zapret\Api\S05mStageProbe;
    use OPNsense\Base\UserException;
    require dirname(__DIR__) .
        '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php';

    class FakeRequest {
        public static bool $post = true;
        public function isPost(): bool { return self::$post; }
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
    // Existing release-list refusal is a real pre-dispatch controller branch.
    // Empty/malformed configd data cannot become a selected release; the
    // fixed cause never reflects arbitrary backend output.
    Backend::$receipt = $clean;
    foreach (['', 'untrusted backend text'] as $unavailableList) {
        Backend::$releaseReceipt = $unavailableList;
        $before = Backend::$mutations;
        assertion(controller()->releasesAction() === ['status' => 'unavailable', 'releases' => []],
                  'invalid release list reported as available');
        try {
            controller()->installAction();
            throw new \RuntimeException('G07_FAIL:missing release list accepted');
        } catch (UserException $error) {
            assertion($error->getMessage() === 'No stable bol-van/zapret2 releases could be obtained.',
                      'fixed pre-dispatch release refusal missing');
        }
        assertion(Backend::$mutations === $before, 'release-list refusal dispatched setup');
    }
    Backend::$releaseReceipt = "v1.0.7\n";
    // The clean documented release path still allows exactly one native install.
    Backend::$receipt = $clean;
    $result = controller()->installAction();
    $operation = $result['operationid'] ?? '';
    assertion($result === ['status' => 'ok', 'version' => 'v1.0.7', 'operationid' => $operation] &&
              preg_match('/^[0-9a-f]{32}$/D', $operation),
              'genuine first install denied');
    assertion(Backend::$mutations === [['zapret setup_install_verified', ['v1.0.7', $operation]]],
              'unexpected configd mutation identity');
    assertion(controller()->installAction()['operationid'] !== $operation,
              'consecutive clicks reused an operation ID');
    Backend::$mutations = [];
    refusedInstall($installing);
    refusedInstall("installed=1\nservice=error\nversion=v1.0.7\nsetup=ready\nbusy=0");

    $knownFailure = str_replace('setup=unknown', 'setup=failed', $clean) .
        "\nlastsetupfailure=release-list-unavailable";
    $known = status($knownFailure);
    assertion($known['status'] === 'ok' && $known['setup'] === 'failed' &&
        $known['lastsetupfailure'] === 'release-list-unavailable' && !isset($known['lastsetupoperation']),
        'qualified last failure missing');
    $operationField = "\nlastsetupoperation=" . $operation;
    $correlated = status($knownFailure . $operationField);
    assertion($correlated['status'] === 'ok' && $correlated['lastsetupoperation'] === $operation,
              'qualified operation was not preserved');
    $malformed = [
        $clean . $operationField,
        $knownFailure . "\nlastsetupoperation=invalid",
        $knownFailure . $operationField . $operationField,
        $clean . "\nlastsetupfailure=release-list-unavailable",
        $running . "\nlastsetupfailure=release-list-unavailable",
        $installing . "\nlastsetupfailure=release-list-unavailable",
        $knownFailure . "\nlastsetupfailure=release-list-unavailable",
        str_replace('release-list-unavailable', 'arbitrary', $knownFailure),
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

    // S05m: execute actual ServiceController::reconfigureAction() with a
    // real method/Backend call and a synthetic stage from ANOTHER operation.
    // Previous source returned raw last-error bytes via HTTP UserException.
    // The stage has no operation or action ID, so even a recent timestamp
    // cannot prove it caused this specific failed reconfigure.
    $safe = 'Zapret2 reconfigure was not confirmed. Check service status and recovery before retrying.';
    foreach ([
        "1|13|config|failed|2026-11-24T00:00:00+0000|/conf/config.xml SECRET_BACKEND",
        "9|13|engine|failed|2026-11-24T00:00:00+0000|--hostlist=PRIVATE_DOMAIN",
        "non-stage|malformed|record"
    ] as $stage) {
        S05mStageProbe::$present = true;
        S05mStageProbe::$record = $stage;
        S05mStageProbe::$reads = 0;
        Backend::$reconfigureReceipt = 'NO: secret-transport-details';
        Backend::$reconfigureThrows = false;
        $calls = Backend::$reconfigureCalls;
        try {
            controller()->reconfigureAction();
            throw new \RuntimeException('S05M_FAIL:invalid reconfigure response accepted');
        } catch (UserException $error) {
            assertion($error->getMessage() === $safe, 'stale/hostile stage escaped into HTTP');
        }
        assertion(Backend::$reconfigureCalls === $calls + 1,
                  'original reconfigure configd action not called exactly once');
        assertion(S05mStageProbe::$reads === 0,
                  'unqualified legacy stage file read after configd failure');
    }
    Backend::$reconfigureThrows = true;
    try {
        controller()->reconfigureAction();
        throw new \RuntimeException('S05M_FAIL:unexpected backend success');
    } catch (UserException $error) {
        assertion($error->getMessage() === $safe &&
                  !str_contains($error->getMessage(), 'SECRET_BACKEND'),
                  'backend exception leaked or invented a verified result');
    }
    Backend::$reconfigureThrows = false;
    Backend::$reconfigureReceipt = 'OK';
    $ok = controller()->reconfigureAction();
    assertion($ok === ['status' => 'ok', 'response' => 'OK'],
              'positive original reconfigure response changed');
    FakeRequest::$post = false;
    $calls = Backend::$reconfigureCalls;
    assertion(controller()->reconfigureAction() === ['status' => 'failed'] &&
              Backend::$reconfigureCalls === $calls,
              'non-POST reconfigure reached backend');
    FakeRequest::$post = true;
    echo "S05M_ORIGINAL_RECONFIGURE_STAGE_UNCORRELATED_FAIL_CLOSED=PASS\n";
    echo "G07_NATIVE_STATUS_API_FAST=PASS\n";
}
