<?php
/**
 * Reproduce the OPNsense Config::lock()/Config::save() flock lifetime hazard.
 * Only private temporary files: NO appliance config.xml or service writes.
 */
function insist(bool $condition, string $reason): void {
    if (!$condition) {
        fwrite(STDERR, "FAIL: " . $reason . "\n");
        exit(1);
    }
}
$path = tempnam(sys_get_temp_dir(), 'voice-flock-');
insist($path !== false, 'cannot create test file');
$owner = null;
$other = null;
try {
    $owner = fopen($path, 'c+');
    $other = fopen($path, 'c+');
    insist($owner !== false && $other !== false, 'cannot open separate file descriptions');

    // OPNsense Config::lock(): separate writer must be unable to enter.
    insist(flock($owner, LOCK_EX), 'outer Config lock');
    insist(!flock($other, LOCK_EX | LOCK_NB), 'parallel writer must block');

    // Config::save() re-locks and unlocks the SAME file description.
    insist(flock($owner, LOCK_EX), 'nested Config save lock');
    insist(flock($owner, LOCK_UN), 'Config save unlock');
    insist(flock($other, LOCK_EX | LOCK_NB),
        'Config save makes original lock available to a competing writer');

    // Calling Config::unlock() later cannot undo that interleaving.
    insist(!flock($owner, LOCK_EX | LOCK_NB), 'foreign writer owns Config');
    insist(flock($other, LOCK_UN), 'foreign writer release');
    insist(flock($owner, LOCK_EX | LOCK_NB), 'caller can only reacquire later');
    insist(flock($owner, LOCK_UN), 'cleanup outer lock');
    echo "PASS: same-handle Config save unlock allows competing flock writer\n";
} finally {
    if (is_resource($other)) fclose($other);
    if (is_resource($owner)) fclose($owner);
    @unlink($path);
}
