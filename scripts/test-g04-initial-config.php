<?php
/** Offline LC-05 native Config first-install model/save contract. */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/initialize_config.php';

use OPNsense\Zapret\Native\InitialConfig;

function must(bool $ok, string $message): void
{
    if (!$ok) {
        fwrite(STDERR, "FAIL G04: " . $message . "\n");
        exit(1);
    }
}

class G04Config
{
    public bool $locked = false;
    public bool $present;
    public array $fields;
    public array $foreign = ['system.hostname' => 'keep'];
    public int $saveCalls = 0;
    public int $lockCalls = 0;
    public bool $failSave = false;
    public function __construct(?array $fields = null)
    {
        $this->present = $fields !== null;
        $this->fields = $fields ?? [];
    }
    public function lock(): void
    {
        must(!$this->locked, 'Config lock acquired twice');
        ++$this->lockCalls;
        $this->locked = true;
    }
    public function unlock(): void { $this->locked = false; }
    public function xpath(string $path): object
    {
        must($this->locked && $path === '//OPNsense/Zapret',
             'Config root must be checked under native lock');
        return (object)['length' => $this->present ? 1 : 0];
    }
    public function save(array $meta): void
    {
        must($this->locked && isset($meta['description']),
             'Config save requires a lock and native revision description');
        ++$this->saveCalls;
        $this->locked = false; // OPNsense Config::save releases original flock.
        if ($this->failSave) {
            throw new RuntimeException('simulated uncertain native save');
        }
    }
}

class G04Model
{
    private G04Config $config;
    private array $changes = [];
    public bool $invalid = false;
    public bool $failSerialize = false;
    public function __construct(G04Config $config) { $this->config = $config; }
    public function setNodeByReference(string $reference, string $value): bool
    {
        must($this->config->locked, 'Model mutation without Config lock');
        if (!in_array($reference,
                ['strategy.trafficargs', 'hostlist.youtubedomains'], true)) {
            return false;
        }
        $this->changes[$reference] = $value;
        return true;
    }
    public function performValidation(bool $all): array
    {
        return $this->invalid ? ['bad-model'] : [];
    }
    public function serializeToConfig(bool $one = false, bool $two = true): bool
    {
        if ($this->failSerialize) {
            return false;
        }
        $this->config->present = true;
        $this->config->fields += $this->changes;
        return true;
    }
}

$clean = new G04Config();
$result = InitialConfig::initialize($clean, fn() => new G04Model($clean));
must($result === 'initialized' && $clean->saveCalls === 1,
     'truly absent Zapret root must save exactly once');
must($clean->fields['hostlist.youtubedomains'] === InitialConfig::YOUTUBE_DOMAINS,
     'initial YouTube domains not saved byte-for-byte');
must($clean->fields['strategy.trafficargs'] === InitialConfig::TRAFFIC_STRATEGY,
     'initial Traffic Strategy not saved byte-for-byte');
must(count(explode("\n", InitialConfig::YOUTUBE_DOMAINS)) === 10,
     'not exactly ten default YouTube domains');
must(substr_count(InitialConfig::TRAFFIC_STRATEGY, '--new') === 1 &&
     !str_ends_with(InitialConfig::TRAFFIC_STRATEGY, '--new'),
     'initial TCP/QUIC separator count incorrect');
must($clean->foreign === ['system.hostname' => 'keep'],
     'unrelated OPNsense section modified');

$saved = $clean->fields;
must(InitialConfig::initialize($clean, fn() => new G04Model($clean)) === 'preserved' &&
     $clean->saveCalls === 1 && $clean->fields === $saved,
     'ordinary reinstall overwrote existing initial preferences');

foreach ([
    [], // persisted but empty root
    ['strategy.trafficargs' => '', 'hostlist.youtubedomains' => ''],
    ['strategy.trafficargs' => 'my custom'], // other field missing
    ['hostlist.youtubedomains' => 'edited.example'],
] as $old) {
    $config = new G04Config($old);
    $before = $config->fields;
    must(InitialConfig::initialize($config, fn() => new G04Model($config)) === 'preserved' &&
         $config->fields === $before && $config->saveCalls === 0 && !$config->locked,
         'saved/empty Config root was silently populated');
}

foreach (['invalid', 'failSerialize', 'failSave'] as $failure) {
    $config = new G04Config();
    $config->failSave = $failure === 'failSave';
    try {
        InitialConfig::initialize($config, function () use ($config, $failure) {
            $model = new G04Model($config);
            $model->invalid = $failure === 'invalid';
            $model->failSerialize = $failure === 'failSerialize';
            return $model;
        });
        must(false, 'unsafe Config failure reported initial setup success');
    } catch (RuntimeException $expected) {
        must(!$config->locked, 'failed initial Config left lock held');
        if ($failure === 'failSave') {
            must(str_contains($expected->getMessage(), 'requires review') &&
                 $config->saveCalls === 1,
                 'uncertain Config save must not be retried or declared clean');
        } else {
            must($config->saveCalls === 0, 'invalid candidate reached Config save');
        }
    }
}
echo "PASS: G04 single native Config save on absent Zapret root; saved/empty and other settings preserved\n";
