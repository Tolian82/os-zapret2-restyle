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
try {
    $config = new OriginalTestConfig(getenv('P2K8F_CONFIG_PATH'),
                                     getenv('P2K8F_UNLOCKED_CONFIG') === '1');
    $done = Snapshot::commitWithInheritedOriginalLocks(
        $config, static fn() => new OriginalTestModel(),
        (int)$argv[2],
        getenv('P2K8F_QUEUE_PATH'), getenv('P2K8F_CONFIG_PATH'),
        [getenv('P2K8F_PYTHON'), getenv('P2K8F_TEST_SCRIPT'),
         '--child-probe', getenv('P2K8F_QUEUE_ROOT'), getenv('P2K8F_CONFIG_PATH')]
    );
    echo json_encode($done, JSON_THROW_ON_ERROR), "\n";
    exit(0);
} catch (\Throwable $error) {
    // Never print potential domains/Config from a child on a failure.
    exit(69);
}
