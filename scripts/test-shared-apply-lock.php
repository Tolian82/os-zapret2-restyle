<?php
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_lock.php';
use OPNsense\Zapret\Native\SharedApplyLifecycleLock as TestLock;
if (count($argv)!==3 || !in_array($argv[1], ['held','refuse'], true)) exit(64);
try {
    TestLock::assertHeld(false, $argv[2]);
    if ($argv[1] !== 'held') { fwrite(STDERR, "FAIL: foreign FD9 accepted\n"); exit(1); }
} catch (\RuntimeException $error) {
    if ($argv[1] !== 'refuse') { fwrite(STDERR,"FAIL: expected FD9: ".$error->getMessage()."\n"); exit(1); }
}
echo "PASS: FD9 witness match\n";
