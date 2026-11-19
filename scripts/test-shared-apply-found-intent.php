<?php
/** Real 120KiB+ multipart contract; no OPNsense bootstrap or Config write. */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_found_intent.php';
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php';
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php';
use OPNsense\Zapret\Native\SharedApplyFoundIntent as Intent;
use OPNsense\Zapret\Api\SharedApplyEnvelope as Envelope;
use OPNsense\Zapret\Native\SharedApplyRequest as Request;
function must(bool $p, string $reason): void {
    if (!$p) { throw new RuntimeException($reason); }
}
function rejects(callable $f, string $reason): void {
    try { $f(); } catch (InvalidArgumentException $expected) { return; }
    throw new RuntimeException('accepted invalid '.$reason);
}
$digest = str_repeat('a', 64);
$source = static function (string $content, string $draft = '',
                          string $status = 'populated'): array {
    return ['base' => ['status' => $status,
             'revision' => hash('sha256',
                 $status === 'missing' ? "missing\0" : "present\0" . $content),
             'content' => $content], 'draft' => $draft];
};
$large = str_repeat('a', 40 * 1024);
$payload = ['schema_version' => 1, 'kind' => 'tz6v2-found-form-intent',
    'config_revision' => $digest, 'sources' => [
    'youtube' => $source($large, $large),
    'user' => $source($large, $large),
    'auto' => $source('', '', 'missing'),
]];
$json = json_encode($payload, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
must(strlen($json) > 65536 && strlen($json) < 320 * 1024,
     'multipart does not exceed bounded configd argument');
$plan = Intent::validateJson($json, $digest);
must($plan['sources'] === $payload['sources'] &&
     $plan['commit_authorized'] === false &&
     $plan['cross_source_validated'] === false, 'transport granted file authority');
$metadata = ['path' => '/var/lib/php/tmp/phpAbCd56', 'size' => strlen($json),
    'sha256' => hash('sha256', $json), 'owner_uid' => 100];
$token = Envelope::encode('strategies', [],
    ['telegramips_baseline' => '', 'found_upload' => $metadata]);
$decoded = Request::decode($token);
must(strlen($token) < 65536 && $decoded['sync']['found_upload'] === $metadata &&
     $decoded['page'] === 'strategies', 'existing root envelope lost short upload pointer');
rejects(fn() => Envelope::encode('voice', [],
    ['snapshot' => $digest, 'found_upload' => $metadata]), 'Voice upload');
rejects(fn() => Envelope::encode('strategies', [],
    ['telegramips_baseline' => '', 'found_upload' => null]), 'null upload encoded');
$nullTransport = rtrim(strtr(base64_encode(json_encode([
    'page' => 'strategies', 'fields' => [],
    'sync' => ['telegramips_baseline' => '', 'found_upload' => null],
], JSON_THROW_ON_ERROR)), '+/', '-_'), '=');
rejects(fn() => Request::decode($nullTransport), 'null upload decoded');
$bad = $payload;
$bad['config_revision'] = str_repeat('0', 64);
rejects(fn() => Intent::validateJson(json_encode($bad), $digest), 'stale Config');
$bad = $payload;
$bad['sources']['youtube']['base']['revision'] = str_repeat('0', 64);
rejects(fn() => Intent::validateJson(json_encode($bad), $digest), 'forged baseline');
$bad = $payload;
$bad['sources']['youtube']['base']['status'] = 'missing';
rejects(fn() => Intent::validateJson(json_encode($bad), $digest), 'missing known source');
$bad = $payload;
$bad['sources']['auto']['draft'] = '!bad.example.com';
$invalidDraft = Intent::validateJson(json_encode($bad), $digest);
must($invalidDraft['sources']['auto']['draft'] === '!bad.example.com' &&
     $invalidDraft['cross_source_validated'] === false, 'draft was silently normalized');
$bad = $payload;
$bad['sources']['auto']['draft'] = str_repeat('x', 40961);
rejects(fn() => Intent::validateJson(json_encode($bad), $digest), 'oversized draft');
$bad = $payload;
$bad['sources']['evil'] = $source('', '', 'empty');
rejects(fn() => Intent::validateJson(json_encode($bad), $digest), 'extra source');
$bad = $metadata; $bad['path'] = '/tmp/../etc/passwd';
rejects(fn() => Intent::metadata($bad), 'path traversal');
$bad = $metadata; $bad['path'] = '/tmp/phpAbCd56';
rejects(fn() => Intent::metadata($bad), 'non-native PHP upload dir');
$bad = $metadata; $bad['size'] = 999999;
rejects(fn() => Intent::metadata($bad), 'oversized body');
$bad = $metadata; $bad['owner_uid'] = -1;
rejects(fn() => Intent::metadata($bad), 'negative owner');
must(Intent::httpFileShape([]) === null, 'ordinary Apply altered by upload contract');
$nativeUpload = [
    'name' => 'found-intent.json', 'type' => 'application/json',
    'tmp_name' => '/var/lib/php/tmp/phpAaBbCc', 'error' => UPLOAD_ERR_OK,
    'size' => strlen($json), 'full_path' => 'found-intent.json',
];
must(Intent::httpFileShape(['found_intent' => $nativeUpload]) === $nativeUpload,
     'real PHP upload form field shape not preserved');
$longUpload = $nativeUpload;
$longUpload['tmp_name'] = '/var/lib/php/tmp/php0123456789abvAaBbCc';
must(Intent::httpFileShape(['found_intent' => $longUpload]) === $longUpload,
    'PHP upload with the base32 tempfile prefix was rejected');
$longMetadata = $metadata;
$longMetadata['path'] = $longUpload['tmp_name'];
must(Intent::metadata($longMetadata) === $longMetadata,
    'PHP tempfile prefix was rejected by root staging metadata');
$bad = $nativeUpload; $bad['error'] = UPLOAD_ERR_NO_FILE;
rejects(fn()=>Intent::httpFileShape(['found_intent'=>$bad]), 'upload error');
$bad = $nativeUpload; $bad['size'] = 320 * 1024 + 1;
rejects(fn()=>Intent::httpFileShape(['found_intent'=>$bad]), 'too large upload');
$bad = $nativeUpload; $bad['tmp_name'] = '/tmp/phpAaBbCc';
rejects(fn()=>Intent::httpFileShape(['found_intent'=>$bad]), 'wrong native upload path');
$bad = $nativeUpload; $bad['name'] = '../bad.json';
rejects(fn()=>Intent::httpFileShape(['found_intent'=>$bad]), 'foreign upload name');
$bad = $nativeUpload; $bad['full_path'] = '../found-intent.json';
rejects(fn()=>Intent::httpFileShape(['found_intent'=>$bad]), 'foreign full path');
$bad = $nativeUpload; $bad['tmp_name'] = ['phpAaBbCc'];
rejects(fn()=>Intent::httpFileShape(['found_intent'=>$bad]), 'multiple temp file');
rejects(fn()=>Intent::httpFileShape(['other'=>$nativeUpload]), 'foreign upload field');
rejects(fn()=>Intent::httpFileShape([
    'found_intent'=>$nativeUpload,'other'=>$nativeUpload
]), 'extra upload field');
rejects(fn()=>Intent::uploadedMetadata(['found_intent'=>$nativeUpload]),
    'fabricated CLI file is not genuine PHP HTTP uploaded file');
$controller = file_get_contents(__DIR__ .
    '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php');
$mvcControllerDir = dirname(__DIR__) .
    '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api';
must(is_file($mvcControllerDir .
    '/../../../../../../scripts/OPNsense/Zapret/shared_apply_found_intent.php'),
    'MVC upload helper resolution points outside installed OPNsense scripts');
$helperSource = file_get_contents(__DIR__ .
    '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_found_intent.php');
must(str_contains($helperSource, "function_exists('posix_geteuid')") &&
     str_contains($helperSource, 'is_uploaded_file($path)'),
     'Native HTTP upload depends unconditionally on optional PHP POSIX');
must(str_contains($controller, 'SharedApplyFoundIntent::uploadedMetadata(') &&
     str_contains($controller, "\$sync['found_upload'] = \$foundUpload;") &&
     str_contains($controller, "\$wanOnlyCandidate = \$foundUpload === null") &&
     str_contains($controller, "SharedApplyEnvelope::encode('strategies'"),
     'Existing Strategies Apply does not bind original PHP upload');
$run = file_get_contents(__DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh');
must(str_contains($run, 'shared_apply_native_config found-save') &&
     str_contains($run, "has(\"found_intent\")"),
     'Original FD9 can silently apply uncommitted found payload');
// TZ6v2 readonly stage: one inherited Config FD plus original FD9.
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_found_stage.php';
$stageSource = file_get_contents(__DIR__ .
    '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_found_stage.php');
$rootStageSource = file_get_contents(__DIR__ .
    '/../src/opnsense/scripts/OPNsense/Zapret/backend/shared_apply_found_stage.py');
$requestSource = file_get_contents(__DIR__ .
    '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_request.php');
must(str_contains($requestSource, 'SharedApplyFoundStage::prepare($config, $prepared[' .
     "'plan'])") &&
     str_contains($requestSource, "'found-batch'") &&
     str_contains($stageSource, '4 => $handle, 9 => $lifecycle') &&
     str_contains($stageSource, 'SharedApplyLifecycleLock::assertHeld()') &&
     str_contains($rootStageSource, 'assert_inherited_config_fd(4, CONFIG_PATH') &&
     str_contains($rootStageSource, 'exclusive_destination_lock(AUTO_LOCK, 0)') &&
     str_contains($rootStageSource, '"commit_authorized": False') &&
     str_contains($run, 'shared_apply_native_config found-save'),
     'native read-only batch lost original Config/FD9 authority');
try {
    \OPNsense\Zapret\Native\SharedApplyFoundStage::prepare(new stdClass(), []);
    throw new RuntimeException('new helper accepted absent original FD9');
} catch (RuntimeException $expected) {
    if ($expected->getMessage() === 'new helper accepted absent original FD9') {
        throw $expected;
    }
}

// Exercise the same native Python->PHP->plan JSON transport width.
$nativePins = '{"device":18446744073709551615,"inode":9223372036854775808,"mtime":1795122633000000000}';
$lossless = json_decode($nativePins, true, 12,
    JSON_THROW_ON_ERROR | JSON_BIGINT_AS_STRING);
must($lossless['device'] === '18446744073709551615' &&
     $lossless['inode'] === '9223372036854775808' &&
     is_int($lossless['mtime']), 'PHP silently rounded unsigned native stat IDs');
$planRoundtrip = json_decode(json_encode($lossless, JSON_THROW_ON_ERROR), true,
    12, JSON_THROW_ON_ERROR);
must($planRoundtrip === $lossless &&
     str_contains($stageSource, 'JSON_THROW_ON_ERROR | JSON_BIGINT_AS_STRING'),
     'original FD9 PHP stage lost exact unsigned file identity');

echo "PASS: PHP multipart >64KiB and lossless FreeBSD uint64 original FD9 pins\n";
