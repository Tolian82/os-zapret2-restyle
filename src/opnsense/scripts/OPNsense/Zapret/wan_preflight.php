<?php
/** Read-only saved WAN probe: no engine, IPFW or Config mutations. */
require_once __DIR__ . '/../../../mvc/app/controllers/OPNsense/Zapret/Api/WanRequirement.php';
use OPNsense\Zapret\Api\WanRequirement;

$mode = $argv[1] ?? '';
if (PHP_SAPI !== 'cli' || !in_array($mode, ['require', 'if-start'], true)) exit(64);
try {
    require_once('script/load_phalcon.php');
    $config = \OPNsense\Core\Config::getInstance();
    $config->lock();
    try {
        $nodes = (new \OPNsense\Zapret\Zapret())->getNodes();
        $required = $mode === 'require' || WanRequirement::runtimeRequested($nodes);
        $wan = WanRequirement::effectiveWan($nodes);
    } finally {
        $config->unlock();
    }
    if (!$required) echo "wan-not-required\n";
    elseif ($wan === '') echo "wan-required\n";
    elseif (!preg_match('/^[A-Za-z][A-Za-z0-9_.:-]{0,31}$/D', $wan)) echo "wan-invalid\n";
    else echo "wan-selected=" . $wan . "\n";
} catch (\Throwable $error) {
    error_log('Native WAN preflight unavailable: ' . get_class($error));
    exit(69);
}
