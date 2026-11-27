<?php
/**
 * TEST ONLY: localhost PHP upload engine -> ORIGINAL FD9 Service Apply.
 *
 * No installed GUI, config, P1 source, journal, service or IPFW file is
 * replaced by this handler. The actual multipart upload is kept alive
 * until the original production service completes synchronously.
 */
declare(strict_types=1);

// Test-only bounded diagnostics; no Config, upload path or domain echoes.
$phase = 'scope';
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
    $phase = 'multipart';
    require_once '/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_found_intent.php';
    require_once '/usr/local/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php';
    $upload = \OPNsense\Zapret\Native\SharedApplyFoundIntent::uploadedMetadata($_FILES);
    if (!is_array($upload)) {
        throw new \RuntimeException('G03_HTTP_UPLOAD_MISSING');
    }
    $phase = 'model';
    require_once '/usr/local/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/VoiceModelValues.php';
    require_once 'script/load_phalcon.php';
    $model = (new \OPNsense\Zapret\Zapret())->getNodes();
    // BaseListField::getNodeData() returns selected options, not a raw
    // string. Use the SAME native model normalizer as the original FD9
    // request fixture, never cast an option array to "Array".
    $saved = \OPNsense\Zapret\Api\VoiceModelValues::text(
        $model['general']['autorestart'] ?? 'off');
    $baseline = $model['hostlist']['telegramips'] ?? null;
    if (($model['general']['enabled'] ?? null) !== '0' ||
        !is_string($saved) ||
        !in_array($saved, ['off', 'hourly', 'daily', 'weekly', 'monthly'], true) ||
        !is_string($baseline)) {
        throw new \RuntimeException('G03_HTTP_SAVED_MODEL_REFUSED');
    }
    $phase = 'envelope';
    $next = $saved === 'off' ? 'hourly' : 'off';
    $encoded = \OPNsense\Zapret\Api\SharedApplyEnvelope::encode(
        'strategies', ['general'=>['autorestart'=>$next]],
        ['telegramips_baseline'=>$baseline, 'found_upload'=>$upload]
    );
    $service = '/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh';
    $phase = 'service-launch';
    $pipes = [];
    $proc = @proc_open(
        [$service, 'shared-apply-run', 'strategies', $encoded],
        [0=>['file','/dev/null','r'], 1=>['pipe','w'],
         2=>['file','/dev/null','a']],
        $pipes, '/usr/local/opnsense',
        ['GITHUB_ACTIONS'=>'true', 'ZAPRET2_G03_COLD_PREPARED'=>'1',
         // The original service resolves its assigned kernel WAN using
         // base ifconfig(8), installed in FreeBSD /sbin. Do not make a
         // disposable HTTP harness less capable than the real root CLI.
         'PATH'=>'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
         'LC_ALL'=>'C']
    );
    if (!is_resource($proc)) {
        throw new \RuntimeException('G03_HTTP_ORIGINAL_SERVICE_UNAVAILABLE');
    }
    try {
        $phase = 'service-result';
        $answer = stream_get_contents($pipes[1], 1024);
        fclose($pipes[1]);
        $pipes = [];
        $rc = proc_close($proc);
        $proc = null;
        if ($rc !== 0 || !is_string($answer) ||
            preg_match('/^applied-id=[a-f0-9]{32}\n$/D', $answer) !== 1) {
            $phase = match ($rc) {
                0 => 'service-receipt', 64 => 'service-rc64',
                69 => 'service-rc69', 70 => 'service-rc70',
                75 => 'service-rc75', default => 'service-rcother',
            };
            // The original service can intentionally return rc=0 with a
            // fixed preflight-rejected receipt. Reveal ONLY an enumerated
            // public stage, never the raw stdout, upload or Config bytes.
            if ($rc === 0 && is_string($answer) &&
                preg_match('/^preflight-rejected=([a-z0-9-]{1,64})\\n?$/D',
                    $answer, $matches) === 1) {
                $allowed = [
                    'root-gate','bootstrap','model','decode','candidate',
                    'wan-required','candidate-plan','candidate-validation',
                    'candidate-xml','candidate-size','workspace','render',
                    'runtime-build','seal','found-intent',
                    'found-intent-config-changed','found-intent-upload-metadata',
                    'found-intent-upload-path','found-intent-upload-directory',
                    'found-intent-upload-inode','found-intent-upload-missing',
                    'found-intent-upload-reader','found-intent-upload-changed',
                    'found-batch','found-source-drift','runtime-preflight',
                    'owned-baseline','manifest-unbound','config-preflight',
                    'observer-generation','profile-source-drift',
                ];
                $phase = 'service-preflight-' .
                    (in_array($matches[1], $allowed, true)
                        ? $matches[1] : 'unknown');
            }
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
    $code = match (get_class($e)) {
        \RuntimeException::class => 'runtime',
        \InvalidArgumentException::class => 'argument',
        \Error::class => 'php-error', default => 'other',
    };
    error_log("G03_NATIVE_HTTP_UPLOAD_REFUSED:$phase:$code");
    http_response_code(409);
    header('Content-Type: text/plain; charset=US-ASCII');
    echo "G03_HTTP_UPLOAD_REFUSED:$phase:$code\n";
}
