<?php
/** TZ6v3 S3: five-source HTTP manifest contract; no Config or runtime writes. */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategiesListManifest.php';

use OPNsense\Zapret\Api\StrategiesListManifest as Manifest;
use OPNsense\Zapret\Api\StrategiesHostlistCatalog as Catalog;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot as Snapshot;

function checkManifest(bool $value, string $label): void
{
    if (!$value) {
        throw new \RuntimeException($label);
    }
}
function expectManifestRefusal(callable $fn, string $label): void
{
    try {
        $fn();
    } catch (\InvalidArgumentException $e) {
        return;
    }
    throw new \RuntimeException('Missing manifest rejection: ' . $label);
}
function encodeManifest(array $manifest): string
{
    return json_encode($manifest, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
}

$large = str_repeat("a.com\n", 295684) . "x.io\n";
checkManifest(strlen($large) === 1774109, 'Owner fixture byte count');
$saved = [
    'hostlist' => [
        'youtubedomains' => "youtube.com\n",
        'userdomains' => $large,
        'telegramips' => '',
        'excludedomains' => '',
    ],
    'general' => ['enabled' => '1'],
    'strategy' => ['trafficargs' => ''],
    'voice' => [],
];
$foundRevision = static fn(string $text): string => hash('sha256', "present\0" . $text);
$sources = [];
foreach (Catalog::sources() as $id => $entry) {
    if ($entry['owner'] === 'config') {
        $text = $saved['hostlist'][$entry['model_field']];
        $sources[$id] = [
            'owner' => 'config',
            'status' => $text === '' ? 'empty' : 'populated',
            'revision' => $foundRevision($text),
            'length_bytes' => strlen($text),
            'changed' => false,
        ];
    } else {
        $status = $id === 'shared_found' ? 'missing' :
            ($id === 'user_found' ? 'populated' : 'empty');
        $content = $id === 'user_found' ? "found.example\n" : '';
        $sources[$id] = [
            'owner' => $entry['owner'],
            'status' => $status,
            'revision' => $status === 'missing'
                ? hash('sha256', "missing\0") : $foundRevision($content),
            'changed' => false,
        ];
    }
}
$manifest = [
    'schema_version' => 1,
    'kind' => 'tz6v3-strategies-list-manifest',
    'config_revision' => Snapshot::digest($saved),
    'sources' => $sources,
];
$count = 0;
Manifest::validate(encodeManifest($manifest), $saved, [], false);
++$count;
checkManifest(array_keys($sources) === Catalog::editorIds(), 'Catalogue order');
checkManifest(strlen(encodeManifest($manifest)) < 8192, 'Bounded manifest');
++$count;

// Omission of unchanged 1.77 MB manual data is intentional; only the
// small metadata envelope crosses HTTP for such a field.
$edited = $manifest;
$edited['sources']['youtube_manual']['changed'] = true;
Manifest::validate(encodeManifest($edited), $saved,
    ['hostlist' => ['youtubedomains' => "changed.youtube\n"]], true);
++$count;
$edited = $manifest;
$edited['sources']['user_manual']['changed'] = true;
Manifest::validate(encodeManifest($edited), $saved,
    ['hostlist' => ['userdomains' => $large . "one-more.example\n"]], true);
++$count;

// A found-only edit retains the one preexisting protected found-intent upload.
$edited = $manifest;
$edited['sources']['youtube_found']['changed'] = true;
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($edited), $saved, [], false), 'found needs native upload');
Manifest::validate(encodeManifest($edited), $saved, [], true);
++$count;

// All invalid or forged HTTP declarations fail closed before FD9.
$invalid = $manifest;
$invalid['sources']['youtube_manual']['length_bytes']++;
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved, [], false), 'manual byte length');
++$count;
$invalid = $manifest;
$invalid['sources']['user_manual']['revision'] = str_repeat('a', 64);
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved, [], false), 'manual digest');
++$count;
$invalid = $manifest;
$invalid['sources']['youtube_manual']['changed'] = true;
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved, [], true), 'claimed edit without bytes');
++$count;
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($manifest), $saved,
    ['hostlist' => ['userdomains' => $large]], false), 'unchanged manual echoed');
++$count;
$invalid = $manifest;
$invalid['sources']['user_manual']['changed'] = true;
$invalid['config_revision'] = str_repeat('f', 64);
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved,
    ['hostlist' => ['userdomains' => "new.example\n"]], true), 'stale Config');
++$count;
$invalid = $manifest;
$invalid['sources']['shared_found']['revision'] = $foundRevision('');
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved, [], false), 'forged missing shared');
++$count;
$invalid = $manifest;
$invalid['sources']['unregistered'] = $invalid['sources']['user_manual'];
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved, [], false), 'unregistered source');
++$count;
$invalid = $manifest;
$invalid['sources']['youtube_manual']['owner'] = 'auto-owned';
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved, [], false), 'wrong owner');
++$count;
$invalid = $manifest;
$invalid['sources']['youtube_manual']['changed'] = 'true';
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved, [], false), 'changed flag type');
++$count;
$invalid = $manifest;
$invalid['sources']['user_manual']['changed'] = true;
expectManifestRefusal(fn() => Manifest::validate(
    encodeManifest($invalid), $saved,
    ['hostlist' => ['userdomains' => str_repeat('x', 4 * 1048576 + 1)]], true),
    'over 4MiB edited data');
++$count;
expectManifestRefusal(fn() => Manifest::validate(
    str_repeat('x', 8193), $saved, [], false), 'oversized JSON');
++$count;
expectManifestRefusal(fn() => Manifest::validate(
    ['schema_version' => 1], $saved, [], false), 'non-scalar manifest');
++$count;

// Existing WAN-first/native G03 clients with no established editor-read
// snapshot retain original preflight/FD9 behavior (no automatic migration).
Manifest::validate(null, $saved, [], false);
++$count;

echo 'PASS: TZ6v3 Strategies FormData+JSON list manifest ' . $count .
    " deterministic cases; owner 1774109 bytes kept out of untouched POST\n";
