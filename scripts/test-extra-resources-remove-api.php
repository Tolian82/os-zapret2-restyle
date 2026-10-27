<?php
/** Isolated authenticated Remove API contract (no OPNsense services run). */
namespace OPNsense\Base {
    class ApiMutableServiceControllerBase { public $request; }
    class UserException extends \RuntimeException {
        public function __construct($message, $title = '') {
            parent::__construct($message);
        }
    }
}
namespace OPNsense\Core {
    class Backend {
        public static string $service = 'started';
        public static string $extrasPhase = 'ready';
        public static bool $busy = false;
        public static int $total = 73;
        public static string $ack = 'OK';
        public static bool $throwAck = false;
        public static array $calls = [];
        public function configdRun($key, ...$ignored): string {
            if ($key === 'zapret setup_status') {
                return "installed=1\nservice=" . self::$service .
                    "\nsetup=ready\nbusy=" . (self::$busy ? '1' : '0');
            }
            if ($key === 'zapret extra_resources_status') {
                return "phase=" . self::$extrasPhase . "\ninstalled=1\nbusy=0\nlua=19\nbin=54";
            }
            if ($key === 'zapret extra_resources_remove_plan') {
                return 'extra-resources-remove-plan=' . json_encode([
                    'status' => 'dry_run_only', 'ready' => false,
                    'lua' => self::$total === 0 ? 0 : 19,
                    'bin' => self::$total === 0 ? 0 : self::$total - 19,
                    'total' => self::$total,
                    'inventory_sha256' => str_repeat('a', 64),
                ]);
            }
            throw new \RuntimeException('Unexpected configd ' . $key);
        }
        public function configdpRun($key, $args, ...$ignored): string {
            self::$calls[] = [$key, $args];
            if (self::$throwAck) throw new \RuntimeException('simulated configd timeout');
            return self::$ack;
        }
    }
}
namespace {
    use OPNsense\Core\Backend;
    use OPNsense\Base\UserException;
    require dirname(__DIR__) . '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php';
    class FakePost {
        public function __construct(public array $values = [], public bool $post = true) {}
        public function isPost(): bool { return $this->post; }
        public function getPost($key) { return $this->values[$key] ?? ''; }
    }
    function insist($condition, $message): void {
        if (!$condition) throw new \RuntimeException('FAIL: ' . $message);
    }
    function attempt($fields, bool $post = true): array {
        $controller = new \OPNsense\Zapret\Api\ServiceController();
        $controller->request = new FakePost($fields, $post);
        return $controller->resourcesRemoveAction();
    }
    function denied($fields, string $message): void {
        $before = count(Backend::$calls);
        try {
            $response = attempt($fields);
            insist(false, $message . ' unexpectedly returned ' . json_encode($response));
        } catch (UserException $e) {
            insist(count(Backend::$calls) === $before, $message . ' invoked configd');
        }
    }
    $correct = ['inventory_sha256' => str_repeat('a', 64), 'confirmation' => 'REMOVE 73'];
    insist(attempt($correct, false)['status'] === 'failed', 'GET accepted');
    denied([], 'missing witness');
    denied(['inventory_sha256' => str_repeat('b', 64), 'confirmation' => 'REMOVE 73'], 'stale witness');
    denied(['inventory_sha256' => str_repeat('a', 64), 'confirmation' => 'REMOVE 72'], 'wrong count');
    Backend::$total = 0;
    denied(['inventory_sha256' => str_repeat('a', 64), 'confirmation' => 'REMOVE 0'], 'zero extras');
    Backend::$total = 73;
    Backend::$service = 'stopped';
    denied($correct, 'stopped service');
    Backend::$service = 'started';
    Backend::$busy = true;
    denied($correct, 'setup busy');
    Backend::$busy = false;
    Backend::$extrasPhase = 'recovery_required';
    denied($correct, 'pending recovery');
    Backend::$extrasPhase = 'ready';
    $ok = attempt($correct);
    insist($ok['status'] === 'ok' && $ok['started'] === true &&
        preg_match('/^[0-9a-f]{32}$/D', $ok['operation']), 'operation receipt');
    $call = end(Backend::$calls);
    insist($call[0] === 'zapret extra_resources_remove' &&
        $call[1] === [$ok['operation'], str_repeat('a', 64), 'REMOVE_ADDITIONAL_RESOURCES'],
        'unexpected mutation parameters');
    Backend::$ack = 'not confirmed';
    insist(attempt($correct)['status'] === 'uncertain', 'ambiguous acknowledgement reported success');
    Backend::$ack = 'OK';
    Backend::$throwAck = true;
    $uncertain = attempt($correct);
    insist($uncertain['status'] === 'uncertain' &&
        preg_match('/^[a-f0-9]{32}$/D', $uncertain['operation']),
        'transport timeout lost operation correlation');
    echo "PASS: production Remove API confirmation, current witness, Started/busy, uncertain receipt\n";
}
