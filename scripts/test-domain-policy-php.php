<?php
/** Read-only PHP-to-Python domain policy regression; no Config/IPFW. */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/DomainSetPolicyBridge.php';
use OPNsense\Zapret\Api\DomainSetPolicyBridge;
function must(bool $ok, string $message): void {
    if (!$ok) {
        fwrite(STDERR, "FAIL: " . $message . "\n");
        exit(1);
    }
}
$module = __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/backend/domain_policy.py';
$python = '/usr/bin/python3';
$first = DomainSetPolicyBridge::inspect("^!Example.com\n^!example.com\nYouTube.com\n", 'youtubedomains', $python, $module);
must($first['normalized'] === "!^example.com\nyoutube.com", 'canonical flags');
must($first['duplicates'] === 1 && $first['entry_count'] === 2, 'deduplication');
must($first === DomainSetPolicyBridge::inspect("^!Example.com\n^!example.com\nYouTube.com\n", 'youtubedomains', $python, $module), 'determinism');
must(DomainSetPolicyBridge::inspect("HTTP://Example.com/x\n", 'userdomains', $python, $module)['normalized'] === 'example.com', 'legacy URL');
must(DomainSetPolicyBridge::inspect("*.Example.com\n", 'excludedomains', $python, $module)['normalized'] === 'example.com', 'global exclude legacy wildcard');
foreach ([
    ['^*.example.com', 'youtubedomains', 1],
    ["example.com\n!example.com", 'userdomains', 2],
    ['!example.com', 'excludedomains', 1],
    ['!!example.com', 'userdomains', 1],
] as [$text, $field, $line]) {
    try {
        DomainSetPolicyBridge::inspect($text, $field, $python, $module);
        must(false, 'invalid domain accepted');
    } catch (\InvalidArgumentException $error) {
        must(str_contains($error->getMessage(), 'line ' . $line), 'line-specific error');
    }
}
try {
    DomainSetPolicyBridge::inspect('example.com', 'telegramips', $python, $module);
    must(false, 'accepted IPSET field');
} catch (\InvalidArgumentException $expected) {}
$controller = file_get_contents(__DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php');
must($controller !== false && str_contains($controller, 'DomainSetPolicyBridge::inspect('), 'controller must call Python domain policy');
must(!str_contains($controller, 'function normalizeDomainList('), 'duplicate PHP grammar remains');
echo "PASS: PHP bridge delegates canonical domain semantics and errors to Python\n";
