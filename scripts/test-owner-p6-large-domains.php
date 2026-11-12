<?php
/** Owner P6: large actually CHANGED User Domains must apply, not just refuse. */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SharedApplyEnvelope.php';
use OPNsense\Zapret\Api\SharedApplyEnvelope as E;

function demand(bool $ok, string $reason): void {
    if (!$ok) { fwrite(STDERR, "FAIL: $reason\n"); exit(1); }
}
function refuses(callable $call, string $reason): void {
    try { $call(); }
    catch (\InvalidArgumentException $expected) { return; }
    demand(false, $reason);
}
$old = implode("\n", array_map(static fn($n) =>
    sprintf('domain%05d.example.org', $n), range(1, 4400)));
$new = $old . "\n^t.me";
$previous = ['hostlist' => ['userdomains' => $old, 'youtubedomains' => 'youtube.com']];
$changed = ['hostlist' => ['userdomains' => $new, 'youtubedomains' => '^youtube.com']];
$sync = ['telegramips_baseline' => '91.108.0.0/16'];

// Existing bounded argv refusal must remain safe, but was not a functional PASS.
refuses(static fn() => E::encode('strategies', $changed, $sync),
    'Full changed User Domains unexpectedly fits the native argv');
try {
    $transport = method_exists(E::class, 'compactStrategies')
        ? E::compactStrategies($changed, $previous) : $changed;
    $encoded = E::encode('strategies', $transport, $sync);
    demand(strlen($encoded) <= 65536, 'Transport exceeds original configd argv limit');
    $decoded = json_decode(base64_decode(strtr($encoded, '-_', '+/')),
        true, 20, JSON_THROW_ON_ERROR);
    demand($decoded['page'] === 'strategies' && $decoded['sync'] === $sync,
        'Native page/sync identity lost');
    $restored = method_exists(E::class, 'expandStrategies')
        ? E::expandStrategies($decoded['fields'], $previous) : $decoded['fields'];
    demand($restored === $changed,
        'User Domains + YouTube edits differ after real envelope round-trip');
    demand($transport['hostlist']['youtubedomains'] === '^youtube.com',
        'Small YouTube modifier unexpectedly rewritten');
    demand(!isset($transport['strategy']), 'Unrelated strategy touched');
    demand(isset($transport['hostlist']['userdomains']['__zapret_list_delta']),
        'Large actual edit was not compacted');
    $stale = $previous;
    $stale['hostlist']['userdomains'] .= "\nforeign.example.org";
    refuses(static fn() => E::expandStrategies($transport, $stale),
        'Stale native Config SHA-256 accepted');
    $bad = $transport;
    $bad['hostlist']['userdomains']['__zapret_list_delta']['delete'] = PHP_INT_MAX;
    refuses(static fn() => E::expandStrategies($bad, $previous),
        'Out-of-bounds splice accepted');
    $bad = $transport;
    $bad['hostlist']['userdomains']['__zapret_list_delta']['base'] = str_repeat('0', 64);
    refuses(static fn() => E::expandStrategies($bad, $previous),
        'Foreign saved Config digest accepted');
    $bad = $transport;
    $bad['hostlist']['userdomains']['__zapret_list_delta']['insert'] =
        str_repeat('z', 4 * 1024 * 1024 + 1);
    refuses(static fn() => E::expandStrategies($bad, $previous),
        'Oversized reconstructed field accepted');
    refuses(static fn() => E::expandStrategies(
        ['hostlist' => ['invented' => $transport['hostlist']['userdomains']]],
        $previous
    ), 'Foreign list delta accepted');
    $small = ['hostlist' => ['userdomains' => '^t.me']];
    demand(E::compactStrategies($small, $previous) === $small,
        'Unrelated small list behavior changed');
    $first = ['hostlist' => ['userdomains' => '!' . $old]];
    $firstToken = E::encode('strategies',
        E::compactStrategies($first, $previous), $sync);
    demand(strlen($firstToken) <= 65536, 'Prepending one modifier must fit');
    $firstRequest = json_decode(base64_decode(strtr($firstToken, '-_', '+/')),
        true, 20, JSON_THROW_ON_ERROR);
    demand(E::expandStrategies($firstRequest['fields'], $previous) === $first,
        'Prepending a modifier lost list bytes');
} catch (\Throwable $error) {
    fwrite(STDERR, 'FAIL: P6 changed User Domains still untransportable: ' .
        get_class($error) . "\n");
    exit(1);
}
echo "PASS: P6 large changed User Domains and combined YouTube/invalid/stale envelope\n";
