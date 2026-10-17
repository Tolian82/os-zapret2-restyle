<?php
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/shared_apply_lock.php';
use OPNsense\Zapret\Native\SharedApplyLifecycleLock;
if (count($argv) !== 2 || !preg_match('/^(0|[1-9][0-9]{0,9})$/D', $argv[1])) exit(64);
if (function_exists('posix_geteuid')) {
    fwrite(STDERR, "FAIL: php -n still has POSIX\n");
    exit(1);
}
if (SharedApplyLifecycleLock::effectiveUid() !== (int)$argv[1]) {
    fwrite(STDERR, "FAIL: base UID differs\n");
    exit(1);
}
echo "PASS: native UID without PHP POSIX\n";
