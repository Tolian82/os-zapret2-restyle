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
$metadata = ['path' => '/tmp/phpAbCd56', 'size' => strlen($json),
    'sha256' => hash('sha256', $json), 'owner_uid' => 100];
$token = Envelope::encode('strategies', [],
    ['telegramips_baseline' => '', 'found_upload' => $metadata]);
$decoded = Request::decode($token);
must(strlen($token) < 65536 && $decoded['sync']['found_upload'] === $metadata &&
     $decoded['page'] === 'strategies', 'existing root envelope lost short upload pointer');
rejects(fn() => Envelope::encode('voice', [],
    ['snapshot' => $digest, 'found_upload' => $metadata]), 'Voice upload');
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
$bad = $metadata; $bad['size'] = 999999;
rejects(fn() => Intent::metadata($bad), 'oversized body');
$bad = $metadata; $bad['owner_uid'] = -1;
rejects(fn() => Intent::metadata($bad), 'negative owner');
$run = file_get_contents(__DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh');
must(str_contains($run, 'preflight-rejected=found-transaction-pending') &&
     str_contains($run, "has(\"found_intent\")"),
     'Original FD9 can silently apply uncommitted found payload');
echo "PASS: PHP multipart >64KiB into original sealed FD9 form, no write/success\n";
