<?php
/**
 * TEST ONLY: localhost PHP upload engine -> ORIGINAL FD9 Service Apply.
 *
 * No installed GUI, config, P1 source, journal, service or IPFW file is
 * replaced by this handler. The actual multipart upload is kept alive
 * until the original production service completes synchronously.
 */
declare(strict_types=1);

try {
    if (PHP_SAPI !== 'cli-server' || PHP_OS_FAMILY !== 'BSD' ||
        getenv('GITHUB_ACTIONS') !== 'true' ||
        getenv('ZAPRET2_G03_COLD_PREPARED') !== '1' ||
        getenv('ZAPRET2_G03_BOUND_FOUND') !== '1' ||
        getenv('ZAPRET2_G03_FIRST_DISABLED') !== '1' ||
        ($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' ||
        ($_SERVER['REMOTE_ADDR'] ?? '') !== '127.0.0.1' ||
        (function_exists('posix_geteuid') && posix_geteuid() !== 0)) {
        throw new \RuntimeException('G03_HTTP_SCOPE_REFUSED');
    }
    require_once '/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_found_intent.php';
    require_once '/usr/local/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php';
    $upload = \OPNsense\Zapret\Native\SharedApplyFoundIntent::uploadedMetadata($_FILES);
    if (!is_array($upload)) {
        throw new \RuntimeException('G03_HTTP_UPLOAD_MISSING');
    }
    require_once 'script/load_phalcon.php';
    $model = (new \OPNsense\Zapret\Zapret())->getNodes();
    $saved = $model['general']['autorestart'] ?? null;
    $baseline = $model['hostlist']['telegramips'] ?? null;
    if (($model['general']['enabled'] ?? null) !== '0' ||
        !is_string($saved) ||
        !in_array($saved, ['off', 'hourly', 'daily', 'weekly', 'monthly'], true) ||
        !is_string($baseline)) {
        throw new \RuntimeException('G03_HTTP_SAVED_MODEL_REFUSED');
    }
    $next = $saved === 'off' ? 'hourly' : 'off';
    $encoded = \OPNsense\Zapret\Api\SharedApplyEnvelope::encode(
        'strategies', ['general'=>['autorestart'=>$next]],
        ['telegramips_baseline'=>$baseline, 'found_upload'=>$upload]
    );
    $service = '/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh';
    $pipes = [];
    $proc = @proc_open(
        [$service, 'shared-apply-run', 'strategies', $encoded],
        [0=>['file','/dev/null','r'], 1=>['pipe','w'],
         2=>['file','/dev/null','a']],
        $pipes, '/usr/local/opnsense',
        ['GITHUB_ACTIONS'=>'true', 'ZAPRET2_G03_COLD_PREPARED'=>'1',
         'PATH'=>'/usr/local/bin:/usr/bin:/bin', 'LC_ALL'=>'C']
    );
    if (!is_resource($proc)) {
        throw new \RuntimeException('G03_HTTP_ORIGINAL_SERVICE_UNAVAILABLE');
    }
    try {
        $answer = stream_get_contents($pipes[1], 1024);
        fclose($pipes[1]);
        $pipes = [];
        $rc = proc_close($proc);
        $proc = null;
        if ($rc !== 0 || !is_string($answer) ||
            preg_match('/^applied-id=[a-f0-9]{32}\n$/D', $answer) !== 1) {
            throw new \RuntimeException('G03_HTTP_ORIGINAL_SERVICE_REFUSED');
        }
    } finally {
        foreach ($pipes as $pipe) {
            if (is_resource($pipe)) { fclose($pipe); }
        }
        if (is_resource($proc)) { @proc_terminate($proc); @proc_close($proc); }
    }
    header('Content-Type: text/plain; charset=US-ASCII');
    header('Cache-Control: no-store');
    echo $answer;
} catch (\Throwable $e) {
    // No raw upload, native model, Config data, stdout or HOSTLIST in HTTP.
    error_log('G03_NATIVE_HTTP_UPLOAD_REFUSED:' . get_class($e));
    http_response_code(409);
    header('Content-Type: text/plain; charset=US-ASCII');
    echo "G03_HTTP_UPLOAD_REFUSED\n";
}
