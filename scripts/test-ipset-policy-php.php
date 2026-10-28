<?php
/**
 * Real read-only PHP -> one Python IPSET parser; no OPNsense Config/FD9.
 */
require_once __DIR__ . '/../src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/IPSetPolicyBridge.php';
use OPNsense\Zapret\Api\IPSetPolicyBridge;

function must($valid, string $message): void {
    if (!$valid) {
        fwrite(STDERR, "FAIL: " . $message . "\n");
        exit(1);
    }
}
$lists = [
    'telegram' => "91.108.0.0/16\n2001:db8::1/128",
    'discord' => "91.108.13.10",
    'x' => '',
    'sip' => '',
    'custom' => '',
    'exclude' => "192.0.2.0/25\n192.0.2.128/25\n::",
];
$first = IPSetPolicyBridge::inspect($lists);
$second = IPSetPolicyBridge::inspect($lists);
must($first === $second, 'inspection is not deterministic');
must($first['schema_version'] === 1, 'wrong schema');
must($first['lists']['exclude']['normalized'] === "192.0.2.0/24\n::",
    'exclude collapse or IPv6 unspecified host failed');
must($first['lists']['telegram']['normalized'] === "91.108.0.0/16\n2001:db8::1",
    'IPv6 host CIDR not canonicalized');
must(in_array(['telegram', 'discord'], $first['overlaps'], true),
    'same-family overlap missing');
foreach (['telegram', 'discord', 'x', 'sip', 'custom', 'exclude'] as $name) {
    foreach (['0.0.0.0/0', '::/0', "0.0.0.0/1\n128.0.0.0/1",
              "::/1\n8000::/1", '2001:db8::1/64', 'fe80::1%vtnet1'] as $bad) {
        $invalid = $lists;
        $invalid[$name] = $bad;
        try {
            IPSetPolicyBridge::inspect($invalid);
            must(false, 'accepted invalid address ' . $name . ' ' . $bad);
        } catch (\InvalidArgumentException $error) {
            must(str_contains($error->getMessage(), 'IPSET'),
                'field-specific fail-closed error missing');
        }
    }
}
must(IPSetPolicyBridge::allFromHostlist([
    'telegramips' => "::\n", 'excludeipset' => "2001:db8::/32"
]) === [
    'telegram' => "::\n", 'discord' => '', 'x' => '', 'sip' => '',
    'custom' => '', 'exclude' => '2001:db8::/32'
], 'legacy missing optional fields must map to empty');

echo "PASS: one native IPSET parser from PHP, IPv6, collapse, overlap, six-list /0 guards\n";
