<?php
/**
 * TEST ONLY: original native Config + FD9 + P2 PREPARED evidence on G03.
 * Not part of the pkg, configd, GUI or any installed recovery entry.
 */
namespace OPNsense\Zapret\Native;

require_once '/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php';
require_once '/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php';

use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

function required(bool $valid, string $why): void {
    if (!$valid) { throw new \RuntimeException($why); }
}

function image(string $path, bool $canMiss): array {
    $st = @lstat($path);
    if ($st === false) {
        required($canMiss && !is_link($path), 'G03_COLD_MISSING_SOURCE');
        return ['status'=>'missing', 'revision'=>hash('sha256',"missing\0"), 'content'=>''];
    }
    required(($st['mode'] & 0170000) === 0100000 &&
             $st['uid'] === 0 && $st['nlink'] === 1 &&
             ($st['mode'] & 0022) === 0 && $st['size'] <= 40960,
             'G03_COLD_FOREIGN_SOURCE');
    $text = @file_get_contents($path);
    $after = @lstat($path);
    required(is_string($text) && strlen($text) === $st['size'] &&
             is_array($after) && $st['dev'] === $after['dev'] &&
             $st['ino'] === $after['ino'] && $st['mtime'] === $after['mtime'] &&
             $st['ctime'] === $after['ctime'], 'G03_COLD_SOURCE_RACE');
    return ['status'=>$text === '' ? 'empty' : 'populated',
            'revision'=>hash('sha256',"present\0" . $text), 'content'=>$text];
}

function stage($config): string {
    $current = (new \OPNsense\Zapret\Zapret())->getNodes();
    $xml = @file_get_contents('/conf/config.xml');
    required(is_string($xml), 'G03_COLD_CONFIG_UNREADABLE');
    $prepared = SharedApplyRequest::prepareSavedUnchanged($current, $xml);
    $base = $prepared['plan']['dependencies'];
    $sources = [];
    foreach ([
        'youtube'=>'/var/db/zapret2/auto-detect-owned/youtube.txt',
        'user'=>'/var/db/zapret2/auto-detect-owned/user.txt',
        'auto'=>'/usr/local/etc/zapret2/ipset/auto-domains.txt',
    ] as $name=>$path) {
        $view = image($path, $name === 'auto');
        $draft = $view['content'];
        if ($name === 'auto') {
            $draft .= "native-cold-prepared-proof.org\n";
        }
        $sources[$name] = ['base'=>$view, 'draft'=>$draft];
    }
    $json = json_encode([
        'schema_version'=>1, 'kind'=>'tz6v2-found-form-intent',
        'config_revision'=>$base, 'sources'=>$sources
    ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
    $prepared['plan']['found_intent'] =
        SharedApplyFoundIntent::validateJson($json, $base);
    $prepared['plan']['found_batch'] =
        SharedApplyFoundStage::prepare($config, $prepared['plan']);
    $batch = $prepared['plan']['found_batch'];
    required($batch['auto']['before'] !== $batch['auto']['after'],
             'G03_COLD_NO_ACTUAL_EDIT_CANDIDATE');
    return SharedApplyRequest::materialize($prepared);
}

function durable($config, string $id): void {
    required(preg_match('/^[a-f0-9]{32}$/D', $id) === 1,
             'G03_COLD_BAD_OPERATION_ID');
    $planFile = "/var/db/zapret2/shared-work/$id/plan.json";
    $plan = json_decode((string)@file_get_contents($planFile), true, 20,
                        JSON_THROW_ON_ERROR);
    $current = (new \OPNsense\Zapret\Zapret())->getNodes();
    $base = VoiceSettingsSnapshot::digest($current);
    required(hash_equals($base, $plan['dependencies']) &&
             ($plan['page'] ?? null) === 'strategies',
             'G03_COLD_MODEL_BASE_DRIFT');
    $candidate = VoiceSettingsSnapshot::digest($plan['candidate']);
    $reflect = new \ReflectionObject($config);
    required($reflect->hasProperty('config_file_handle') &&
             $reflect->hasProperty('config_file'), 'G03_COLD_CONFIG_FD_MISSING');
    $handle = $reflect->getProperty('config_file_handle')->getValue($config);
    $path = $reflect->getProperty('config_file')->getValue($config);
    $named = @lstat('/conf/config.xml');
    $fd = is_resource($handle) ? @fstat($handle) : false;
    required($path === '/conf/config.xml' && is_array($named) &&
             is_array($fd) && $named['dev'] === $fd['dev'] &&
             $named['ino'] === $fd['ino'], 'G03_COLD_CONFIG_FD_FOREIGN');
    $fd9 = @fopen('php://fd/9', 'r+b');
    required(is_resource($fd9), 'G03_COLD_FD9_MISSING');
    $script = <<<'PY'
import json,sys
sys.path.insert(0,"/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
from auto_detect_effective_known import prepare_native_found_intent
receipt=prepare_native_found_intent(sys.argv[1],4,sys.argv[2],runtime_mode="1")
print(json.dumps(receipt,sort_keys=True,separators=(",",":")))
PY;
    $pipes = [];
    $proc = null;
    try {
        $proc = @proc_open(
            ['/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
             '-c', $script, $id, $candidate],
            [0=>['file','/dev/null','r'],1=>['pipe','w'],
             2=>['file','/dev/null','a'],4=>$handle,9=>$fd9],
            $pipes, null, ['LC_ALL'=>'C','PATH'=>'/usr/bin:/bin:/usr/local/bin']);
        required(is_resource($proc), 'G03_COLD_PYTHON_MISSING');
        $text = @stream_get_contents($pipes[1], 4096);
        fclose($pipes[1]);
        $pipes = [];
        $rc = proc_close($proc);
        $proc = null;
        $result = is_string($text) ? json_decode($text, true) : null;
        required($rc === 0 && is_array($result) &&
                 ($result['result'] ?? null) === 'original-found-intent-durable' &&
                 ($result['phase'] ?? null) === 'prepared' &&
                 ($result['commit_authorized'] ?? null) === false &&
                 ($result['restore_authorized'] ?? null) === false,
                 'G03_COLD_DURABLE_INTENT_REFUSED');
    } finally {
        foreach ($pipes as $pipe) { if (is_resource($pipe)) { fclose($pipe); } }
        if (is_resource($proc)) { @proc_terminate($proc); @proc_close($proc); }
        fclose($fd9);
    }
}

try {
    required(PHP_SAPI === 'cli' && PHP_OS_FAMILY === 'BSD' &&
             getenv('GITHUB_ACTIONS') === 'true' &&
             getenv('ZAPRET2_G03_COLD_PREPARED') === '1' &&
             SharedApplyLifecycleLock::effectiveUid() === 0 &&
             in_array(($argv[1] ?? ''), ['stage','durable'], true) &&
             count($argv) === (($argv[1] ?? '') === 'stage' ? 2 : 3),
             'G03_COLD_DISPOSABLE_ONLY');
    SharedApplyLifecycleLock::assertHeld();
    require_once 'script/load_phalcon.php';
    $config = \OPNsense\Core\Config::getInstance();
    $config->lock();
    try {
        if ($argv[1] === 'stage') {
            echo 'prepared-id=' . stage($config) . "\n";
        } else {
            durable($config, $argv[2]);
            echo "original-found-prepared-durable\n";
        }
    } finally {
        $config->unlock();
    }
} catch (\Throwable $error) {
    fwrite(STDERR, "G03_COLD_PREPARED=REFUSED:" .
        preg_replace('/[^A-Z0-9_]/','',strtoupper(substr($error->getMessage(),0,85))) .
        "\n");
    exit(69);
}
