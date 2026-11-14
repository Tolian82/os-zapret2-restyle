<?php
/**
 * P2k8f fixture: actual PHP original-file Config flock and native PHP/Python
 * proc_open descriptor mapping. Synthetic Model only; no real config.xml
 * writer, no native dvtws2 discovery and no pending acknowledgment.
 */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/auto_detect_config_snapshot.php';

use OPNsense\Zapret\Native\AutoDetectConfigSnapshot as Snapshot;

final class OriginalTestConfig
{
    private $config_file;
    private $config_file_handle;
    private bool $unlocked;
    public function __construct(string $path, bool $unlocked)
    {
        $this->config_file = $path;
        $this->config_file_handle = fopen($path, 'r+');
        $this->unlocked = $unlocked;
    }
    public function lock($reload=true): void
    {
        if (!$this->unlocked && !flock($this->config_file_handle, LOCK_EX)) {
            throw new \RuntimeException('test flock failed');
        }
    }
    public function unlock(): void
    {
        if (!$this->unlocked) {
            flock($this->config_file_handle, LOCK_UN);
        }
    }
    public function save(): void
    {
        throw new \RuntimeException('test must not write config');
    }
}
final class OriginalTestModel
{
    public function getNodes(): array
    {
        return ['hostlist' => [
            'youtubedomains' => "youtube.com\n",
            'userdomains' => "",
            'excludedomains' => "!blocked.example\n",
        ]];
    }
}

if (count($argv) !== 4 || $argv[1] !== 'commit-with-fds' ||
    preg_match('/^[0-9]+$/D', $argv[2]) !== 1 ||
    preg_match('/^[0-9a-f]{32}-[0-9a-f]{32}\.txt$/D', $argv[3]) !== 1) {
    exit(64);
}
$nativeStep = 'preflight';
try {
    $nativeConfig = getenv('P2K8G_USE_NATIVE_CONFIG') === '1';
    if ($nativeConfig) {
        // This fixture may use the REAL OPNsense Config handle only in
        // the existing disposable, explicitly gated native VM.
        $conditions = [
            'bsd' => PHP_OS_FAMILY === 'BSD',
            // Reuse the production proof: POSIX is optional on OPNsense.
            'root' => Snapshot::nativeRootAllowed(),
            'github' => getenv('GITHUB_ACTIONS') === 'true',
            'disposable' => getenv('ZAPRET2_P2K8G_DISPOSABLE_NATIVE') === '1',
            'original_path' => getenv('P2K8F_CONFIG_PATH') === '/conf/config.xml',
            'locked_mode' => getenv('P2K8F_UNLOCKED_CONFIG') === '0',
        ];
        foreach ($conditions as $name => $passed) {
            if (!$passed) {
                // These are fixed known gate names only, never environment
                // values, Config data or user Hostlists.
                fwrite(STDERR, "P2K8G_NATIVE_GUARD_REFUSED=" . $name . "\n");
                exit(69);
            }
        }
        $nativeStep = 'original-phalcon-bootstrap';
        require_once('script/load_phalcon.php');
        $config = \OPNsense\Core\Config::getInstance();
        $nativeStep = 'original-config-ready';
    } else {
        $config = new OriginalTestConfig(
            getenv('P2K8F_CONFIG_PATH'),
            getenv('P2K8F_UNLOCKED_CONFIG') === '1'
        );
    }
    $factory = static function () use ($config, $nativeConfig): OriginalTestModel {
        if ($nativeConfig && getenv('P2K8G_SIMULATE_CONFIG_UNLOCK') === '1') {
            // Simulate the loss of the real Config flock caused by save(),
            // without calling save() or changing the guest's config.xml.
            $config->unlock();
        }
        return new OriginalTestModel();
    };
    // The production bridge intentionally launches children with LC_ALL=C
    // and NO inherited environment. In this disposable test only, the
    // absolute, no-shell /usr/bin/env wrapper injects exactly the policy
    // paths and hold markers required by the checkout Python shim. The
    // production invocation remains unchanged and cannot receive these.
    $child = [getenv('P2K8F_PYTHON'), getenv('P2K8F_TEST_SCRIPT'),
              '--child-probe', getenv('P2K8F_QUEUE_ROOT'),
              getenv('P2K8F_CONFIG_PATH')];
    if ($nativeConfig) {
        $nativeStep = 'test-only-runtime-environment';
        $queueRoot = (string)getenv('P2K8F_QUEUE_ROOT');
        $testRoot = dirname($queueRoot);
        $runner = (string)getenv('P2K8F_PYTHON');
        $testScript = (string)getenv('P2K8F_TEST_SCRIPT');
        $pythonBin = (string)getenv('ZAPRET_PYTHON_BIN');
        $pythonPolicy = (string)getenv('ZAPRET_PYTHON_POLICY');
        if (!str_starts_with($testRoot, '/tmp/p2k8g-original-') ||
            !is_dir($testRoot) || !is_dir($queueRoot) ||
            !str_ends_with($runner, '/python_runtime.sh') ||
            !is_file($runner) || !is_executable($runner) ||
            !str_ends_with($testScript, '/test-auto-detect-original-lock-handoff.py') ||
            !is_file($testScript) ||
            $pythonBin !== '/usr/local/bin/python3' ||
            !str_ends_with($pythonPolicy, '/compatibility.json') ||
            !is_file($pythonPolicy) || !is_executable('/usr/bin/env')) {
            throw new \RuntimeException('Unqualified disposable runtime wrapper');
        }
        $nativeEnv = ['/usr/bin/env',
                      'ZAPRET_PYTHON_BIN=' . $pythonBin,
                      'ZAPRET_PYTHON_POLICY=' . $pythonPolicy];
        foreach (['P2K8G_CHILD_DIAG' => 'child-refusal',
                  'P2K8G_HOLD_READY' => 'child-ready',
                  'P2K8G_HOLD_RELEASE' => 'child-release'] as $name => $suffix) {
            $value = getenv($name);
            if ($value !== false) {
                if ($value !== $testRoot . '/' . $suffix) {
                    throw new \RuntimeException('Unqualified disposable test marker');
                }
                $nativeEnv[] = $name . '=' . $value;
            }
        }
        $child = array_merge($nativeEnv, $child);
    }
    $nativeStep = 'original-locked-callback';
    $done = Snapshot::commitWithInheritedOriginalLocks(
        $config, $factory,
        (int)$argv[2],
        getenv('P2K8F_QUEUE_PATH'), getenv('P2K8F_CONFIG_PATH'),
        $child
    );
    echo json_encode($done, JSON_THROW_ON_ERROR), "\n";
    exit(0);
} catch (\Throwable $error) {
    // In a DISPOSABLE guest, a PHP exception *type* is useful diagnostic
    // evidence without revealing any config.xml content or user domains.
    if (getenv('P2K8G_USE_NATIVE_CONFIG') === '1' &&
        getenv('ZAPRET2_P2K8G_DISPOSABLE_NATIVE') === '1') {
        $known = [
            'Unqualified original queue/Config bridge',
            'Original Config handle unavailable',
            'Original Config descriptor replaced',
            'Inherited original queue descriptor unavailable',
            'Foreign original queue descriptor',
            'Original locked Python child unavailable',
            'Original Model transport oversized',
            'Original Model transport interrupted',
            'Original locked child timed out',
            'Original locked child I/O failure',
            'Original locked child read failure',
            'Original locked child refused',
            'Unqualified original child result',
            'Unqualified destination checkpoint',
            'Original Config model invalid',
            'Original Config model unavailable',
        ];
        $kind = in_array($error->getMessage(), $known, true)
            ? preg_replace('/[^A-Za-z0-9]+/', '_', $error->getMessage())
            : 'OTHER';
        fwrite(STDERR, "P2K8G_NATIVE_STAGE=" . $nativeStep .
            ";CLASS=" . get_class($error) . ";KIND=" . $kind .
            ";CODE_LINE=" . $error->getLine() . "\n");
    }
    exit(69);
}
