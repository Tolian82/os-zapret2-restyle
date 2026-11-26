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

function stage($config, bool $partial = false, bool $withConfig = false): string {
    $current = (new \OPNsense\Zapret\Zapret())->getNodes();
    $xml = @file_get_contents('/conf/config.xml');
    required(is_string($xml), 'G03_COLD_CONFIG_UNREADABLE');
    if ($withConfig) {
        // A genuine, scoped SettingsApply candidate: toggles ONLY the
        // Auto Restart preference on the disposable OPNsense. No fake XML.
        $saved = \OPNsense\Zapret\Api\VoiceModelValues::text(
            $current['general']['autorestart'] ?? 'off'
        );
        required(in_array($saved, ['off','hourly','daily','weekly','monthly'], true),
                 'G03_CONFIG_NATIVE_SAVED_INTERVAL_INVALID');
        $next = $saved === 'off' ? 'hourly' : 'off';
        $prepared = SharedApplyRequest::prepare([
            'page'=>'strategies',
            'fields'=>['general'=>['autorestart'=>$next]],
            'sync'=>['telegramips_baseline'=>
                (string)($current['hostlist']['telegramips'] ?? '')],
        ], $current, $xml);
        required($prepared['plan']['changed_fields'] === ['general.autorestart'],
                 'G03_CONFIG_SINGLE_NATIVE_CHANGE_REQUIRED');
    } else {
        $prepared = SharedApplyRequest::prepareSavedUnchanged($current, $xml);
    }
    $base = $prepared['plan']['dependencies'];
    $sources = [];
    foreach ([
        'youtube'=>'/var/db/zapret2/auto-detect-owned/youtube.txt',
        'user'=>'/var/db/zapret2/auto-detect-owned/user.txt',
        'auto'=>'/usr/local/etc/zapret2/ipset/auto-domains.txt',
    ] as $name=>$path) {
        $view = image($path, $name === 'auto');
        $draft = $view['content'];
        if ($partial && in_array($name, ['youtube', 'user'], true)) {
            // Disposable crash fixture: require TWO genuine protected edits.
            $domain = $name === 'youtube'
                ? 'native-partial-youtube-proof.org' : 'native-partial-user-proof.org';
            $draft = rtrim($draft, "\n") . "\n" . $domain . "\n";
        }
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
    required($batch['auto']['before'] !== $batch['auto']['after'] &&
             (!$partial || (
                $batch['youtube']['before'] !== $batch['youtube']['after'] &&
                $batch['user']['before'] !== $batch['user']['after'])),
             'G03_COLD_NO_ACTUAL_EDIT_CANDIDATE');
    return SharedApplyRequest::materialize($prepared);
}

function durable($config, string $id, string $action = 'durable'): void {
    $attest = $action !== 'durable';
    $bind = $action === 'bind';
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
    if ($attest) {
        // Disposable G03: attest source/CAS, optionally stage/bind only.
        // Neither route may change Config, P1 files, IPFW or runtime.
        $script = <<<'PY'
import json, subprocess, sys
sys.path.insert(0, "/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
from shared_apply_operation import SharedApplyOperation
from neutral_shared_apply_source_gate import (
    native_attest_found_prepared_fd9, native_bind_found_prepared_fd9,
    decode_pipe, MAX_PIPE)
from auto_detect_destination_commit import (
    DestinationRefused, shared_apply_found_files_original_fd9)
from shared_apply_operation import committed_manifest, SharedOperationError
from voice_ipfw_adapter import require_lifecycle_lock
op = sys.argv[1]
require_lifecycle_lock()
before = SharedApplyOperation(owner=0).read()
script = r"""
set -eu
base=/usr/local/opnsense/scripts/OPNsense/Zapret
work="/var/db/zapret2/shared-work/$1"
. "$base/backend/config.sh"
config_load "$work/templates/usr/local/etc/zapret2/zapret.conf"
{
    printf 'S10C2B1_ORIGINAL_INPUT_V1\0'
    printf '%s\0' "${TRAFFIC_ARGS:-}" "${YOUTUBE_DOMAINS:-}" "${USER_DOMAINS:-}" \
      "${TELEGRAM_IPS:-}" "${DISCORD_IPS:-}" "${X_IPS:-}" \
      "${SIP_IPS:-}" "${CUSTOM_IPS:-}" "${EXCLUDE_DOMAINS:-}" \
      "${EXCLUDE_IPSET:-}" "${HOSTLIST_MODE:-}" "${DIVERT_PORT:-}" "${WAN_IF:-}"
}
"""
wire = subprocess.run(["/bin/sh", "-c", script, "g03-found-wire", op],
                      capture_output=True, timeout=30, check=False)
if wire.returncode or not wire.stdout or len(wire.stdout) > MAX_PIPE:
    raise RuntimeError("G03_FOUND_NATIVE_WIRE_REFUSED")
decode_pipe(wire.stdout)
action = sys.argv[4]
store = SharedApplyOperation(owner=0)
if action == "bind":
    witness, staged = native_bind_found_prepared_fd9(
        op, wire.stdout, 4, config_digest=sys.argv[3])
    expected = dict(before, manifest={
        "schema": 2 if (witness.source.mode == "auto" and
                       witness.source.requested_enabled) else 1,
        "generation": op, "root_sha256": staged.root_sha256,
        "seal_sha256": staged.original_seal_sha256,
        "candidate_sha256": sys.argv[2]})
    if (store.read() != expected or committed_manifest(expected) is not None or
            staged.authorization != "NONE" or staged.physical_transition_allowed or
            staged.promotion_allowed or staged.reattest_under_original_fd9 is not True):
        raise RuntimeError("G03_FOUND_NATIVE_BIND_NOT_PREPARED")
    # Exercise the actual native physical entrypoint: refuse BEFORE the
    # first P2 write, even though both the source and candidate are sealed.
    try:
        shared_apply_found_files_original_fd9(op, 4)
    except DestinationRefused as exc:
        if str(exc) != "original_found_dual_root_not_bound":
            raise RuntimeError("G03_FOUND_NATIVE_WRITER_WRONG_REFUSAL")
    else:
        raise RuntimeError("G03_FOUND_NATIVE_WRITER_NOT_FENCED")
    try:
        store.advance("activating", before["detail"])
    except SharedOperationError:
        pass
    else:
        raise RuntimeError("G03_FOUND_NATIVE_GENERIC_ACTIVATION_NOT_FENCED")
    if store.read() != expected:
        raise RuntimeError("G03_FOUND_NATIVE_FENCE_CHANGED_WAL")
    result = "original-found-prepared-root-bound-only"
    root_sha = staged.root_sha256
else:
    witness = native_attest_found_prepared_fd9(op, wire.stdout, 4)
    if store.read() != before:
        raise RuntimeError("G03_FOUND_NATIVE_ATTEST_CHANGED_WAL")
    result = "original-found-prepared-source-cas-only"
    root_sha = None
if (witness.authorization != "NONE" or witness.physical_transition_allowed or
        witness.promotion_allowed or witness.final_original_fd9_reattest_required is not True or
        witness.source.authorization != "NONE" or witness.source.physical_transition_allowed):
    raise RuntimeError("G03_FOUND_NATIVE_ATTEST_NOT_READONLY")
print(json.dumps({"result":result,
    "generation":op, "base":witness.config_base_sha256,
    "candidate":witness.config_candidate_sha256,
    "source_status":witness.source.status,
    "authorization":witness.authorization,
    "final_reattest":witness.final_original_fd9_reattest_required,
    "root_sha256":root_sha},
    sort_keys=True,separators=(",",":")))
PY;
    }
    $pipes = [];
    $proc = null;
    try {
        $proc = @proc_open(
            ['/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
             '-c', $script, $id, $candidate, $base, $action],
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
        if ($attest) {
            required($rc === 0 && is_array($result) &&
                     ($result['result'] ?? null) === ($bind
                         ? 'original-found-prepared-root-bound-only'
                         : 'original-found-prepared-source-cas-only') &&
                     (!$bind || preg_match('/^[a-f0-9]{64}$/D',
                         (string)($result['root_sha256'] ?? '')) === 1) &&
                     ($result['generation'] ?? null) === $id &&
                     ($result['base'] ?? null) === $base &&
                     ($result['candidate'] ?? null) === $candidate &&
                     ($result['source_status'] ?? null) ===
                         'ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY' &&
                     ($result['authorization'] ?? null) === 'NONE' &&
                     ($result['final_reattest'] ?? null) === true,
                     'G03_S10_FOUND_SOURCE_CAS_REFUSED');
        } else {
        required($rc === 0 && is_array($result) &&
                 ($result['result'] ?? null) === 'original-found-intent-durable' &&
                 ($result['phase'] ?? null) === 'prepared' &&
                 ($result['commit_authorized'] ?? null) === false &&
                 ($result['restore_authorized'] ?? null) === false,
                 'G03_COLD_DURABLE_INTENT_REFUSED');
        }
    } finally {
        foreach ($pipes as $pipe) { if (is_resource($pipe)) { fclose($pipe); } }
        if (is_resource($proc)) { @proc_terminate($proc); @proc_close($proc); }
        fclose($fd9);
    }
}

/**
 * DISPOSABLE ONLY: kill the ORIGINAL three-file WAL child just after its
 * first real, fsynced rename and installed-inode journal checkpoint.
 * No fake file writer, second Config owner or product fault switch.
 */
function crashFirstFoundFile($config, string $id): void {
    required(preg_match('/^[a-f0-9]{32}$/D', $id) === 1,
             'G03_PARTIAL_BAD_OPERATION');
    $reflect = new \ReflectionObject($config);
    required($reflect->hasProperty('config_file_handle') &&
             $reflect->hasProperty('config_file'), 'G03_PARTIAL_CONFIG_FD_MISSING');
    $handle = $reflect->getProperty('config_file_handle')->getValue($config);
    $path = $reflect->getProperty('config_file')->getValue($config);
    $named = @lstat('/conf/config.xml');
    $opened = is_resource($handle) ? @fstat($handle) : false;
    required($path === '/conf/config.xml' && is_array($named) &&
             is_array($opened) && $named['dev'] === $opened['dev'] &&
             $named['ino'] === $opened['ino'],
             'G03_PARTIAL_FOREIGN_CONFIG_FD');
    $fd9 = @fopen('php://fd/9', 'r+b');
    required(is_resource($fd9), 'G03_PARTIAL_FD9_MISSING');
    $script = <<<'PY'
import os,sys
sys.path.insert(0,"/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
import auto_detect_destination_commit as writer
original=writer._replace
count=[0]
def interrupted(*args,**kwargs):
    result=original(*args,**kwargs)
    count[0]+=1
    if count[0]==1:
        os._exit(73)
    return result
writer._replace=interrupted
writer.shared_apply_found_files_original_fd9(sys.argv[1],4)
os._exit(74)
PY;
    $pipes = [];
    $proc = null;
    try {
        $proc = @proc_open(
            ['/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
             '-c', $script, $id],
            [0=>['file','/dev/null','r'],1=>['pipe','w'],
             2=>['file','/dev/null','a'],4=>$handle,9=>$fd9],
            $pipes, null, ['LC_ALL'=>'C','PATH'=>'/usr/bin:/bin:/usr/local/bin']
        );
        required(is_resource($proc), 'G03_PARTIAL_PYTHON_UNAVAILABLE');
        $output = @stream_get_contents($pipes[1], 512);
        fclose($pipes[1]);
        $pipes = [];
        $rc = proc_close($proc);
        $proc = null;
        required($rc === 73 && $output === '',
                 'G03_PARTIAL_NOT_CRASHED_AFTER_FIRST_ATOMIC_FILE');
    } finally {
        foreach ($pipes as $pipe) { if (is_resource($pipe)) { fclose($pipe); } }
        if (is_resource($proc)) { @proc_terminate($proc); @proc_close($proc); }
        fclose($fd9);
    }
}


/**
 * TEST ONLY, disposable OPNsense: delegate to the ONE real native Config
 * singleton, then terminate the original PHP *after the actual save returned*
 * but before the PHP/P2 post-save handshake. No XML writer is invented.
 */
final class G03NativeConfigSaveCrash {
    public $config_file_handle = null;
    public $config_file = null;
    private object $real;

    public function __construct(object $real) { $this->real = $real; }
    public function lock(): void {
        $this->real->lock();
        $r = new \ReflectionObject($this->real);
        required($r->hasProperty('config_file_handle') &&
                 $r->hasProperty('config_file'),
                 'G03_CONFIG_NATIVE_LOCK_INCOMPLETE');
        $this->config_file_handle = $r->getProperty('config_file_handle')
            ->getValue($this->real);
        $this->config_file = $r->getProperty('config_file')
            ->getValue($this->real);
    }
    public function unlock(): void { $this->real->unlock(); }
    public function save(array $audit): void {
        $this->real->save($audit);
        // Exact fault boundary: real OPNsense Config::save returned.
        // Do not release a fake success receipt or fsync a saved WAL.
        exit(73);
    }
}

function crashAfterActualConfigSave($config, string $id): void {
    required(preg_match('/^[a-f0-9]{32}$/D', $id) === 1,
             'G03_CONFIG_BAD_OPERATION');
    $plan = SharedApplyConfigWorker::readPlan($id);
    required(($plan['page'] ?? null) === 'strategies' &&
             ($plan['changed_fields'] ?? null) === ['general.autorestart'] &&
             isset($plan['found_intent'], $plan['found_batch']) &&
             count($plan['found_batch']) === 3,
             'G03_CONFIG_PLAN_NOT_ACTUAL_NATIVE_CHANGE');
    $m = new \ReflectionMethod(SharedApplyConfigWorker::class, 'saveFoundNative');
    $m->invoke(null, $plan, $id, '1', new G03NativeConfigSaveCrash($config),
               static fn() => new \OPNsense\Zapret\Zapret());
    throw new \RuntimeException('G03_CONFIG_NO_ACTUAL_SAVE_CRASH');
}

try {
    required(PHP_SAPI === 'cli' && PHP_OS_FAMILY === 'BSD' &&
             getenv('GITHUB_ACTIONS') === 'true' &&
             getenv('ZAPRET2_G03_COLD_PREPARED') === '1' &&
             SharedApplyLifecycleLock::effectiveUid() === 0 &&
             in_array(($argv[1] ?? ''), ['stage','stage-partial','stage-config',
                                         'durable','attest','bind','crash-partial','crash-config-save','stage-ordinary'], true) &&
             count($argv) === (in_array(($argv[1] ?? ''),
                ['stage','stage-partial','stage-config','stage-ordinary'], true) ? 2 : 3),
             'G03_COLD_DISPOSABLE_ONLY');
    SharedApplyLifecycleLock::assertHeld();
    require_once 'script/load_phalcon.php';
    $config = \OPNsense\Core\Config::getInstance();
    if ($argv[1] === 'crash-config-save') {
        // The original Config lock must be acquired ONCE by the real
        // SharedConfigCommit, via the test-only delegating crash adapter.
        crashAfterActualConfigSave($config, $argv[2]);
    } else {
        $config->lock();
        try {
            if ($argv[1] === 'stage-ordinary') {
                $current = (new \OPNsense\Zapret\Zapret())->getNodes();
                $xml = @file_get_contents('/conf/config.xml');
                required(is_string($xml), 'G03_BOUND_NATIVE_CONFIG_UNREADABLE');
                $prepared = SharedApplyRequest::prepareSavedUnchanged($current, $xml);
                required(!isset($prepared['plan']['found_intent']) &&
                         !isset($prepared['plan']['found_batch']) &&
                         $prepared['plan']['page'] === 'strategies',
                         'G03_BOUND_NATIVE_ORDINARY_PLAN_REQUIRED');
                echo 'prepared-id=' . SharedApplyRequest::materialize($prepared) . "\n";
            } elseif (in_array($argv[1], ['stage','stage-partial','stage-config'], true)) {
                echo 'prepared-id=' . stage($config,
                    $argv[1] !== 'stage', $argv[1] === 'stage-config') . "\n";
            } elseif (in_array($argv[1], ['durable', 'attest', 'bind'], true)) {
                durable($config, $argv[2], $argv[1]);
                echo ($argv[1] === 'bind'
                    ? "original-found-prepared-root-bound\n"
                    : ($argv[1] === 'attest'
                        ? "original-found-prepared-source-cas-attested\n"
                        : "original-found-prepared-durable\n"));
            } else {
                crashFirstFoundFile($config, $argv[2]);
                echo "original-partial-first-atomic-file-crashed\n";
            }
        } finally {
            $config->unlock();
        }
    }
} catch (\Throwable $error) {
    // In this disposable-only witness a wrapped save exception otherwise
    // hides the root phase failure (and forces another complete native VM).
    // Emit only its bounded A-Z0-9 diagnostic code; never print XML/domains.
    $cause = $error;
    while ($cause->getPrevious() instanceof \Throwable) {
        $cause = $cause->getPrevious();
    }
    fwrite(STDERR, "G03_COLD_PREPARED=REFUSED:" .
        preg_replace('/[^A-Z0-9_]/','',strtoupper(substr($cause->getMessage(),0,85))) .
        "\n");
    exit(69);
}
