#!/usr/local/bin/php
<?php
declare(strict_types=1);

/**
 * Disposable OPNsense 26.7 P3 locale fixture. NOT part of the plugin package.
 * Mutates only the logged-in root user's language through native OPNsense
 * Config::save(). Never run on an owner appliance or outside the CI guest.
 */
// FreeBSD's stock OPNsense PHP CLI is not required to install the optional
// POSIX extension. Do not fail a disposable native guest solely because
// posix_geteuid() is absent; prove root Config write access and the unique
// CI-generated SSH guest key instead. Keep each refusal class explicit.
if (getenv('GITHUB_ACTIONS') !== 'true' ||
    getenv('ZAPRET2_P3_NATIVE_LOCALE') !== '1') {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_NON_DISPOSABLE\n");
    exit(2);
}
if (PHP_OS_FAMILY !== 'BSD') {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_NOT_FREEBSD\n");
    exit(2);
}
// Each identity/precondition guard has a distinct, non-sensitive refusal
// receipt. A combined "root Config access" code hid the actual native cause.
// Prove actual root identity even without the optional PHP POSIX module.
$effectiveUid = function_exists('posix_geteuid')
    ? (string)posix_geteuid()
    : (function_exists('shell_exec')
        ? trim((string)@shell_exec('/usr/bin/id -u 2>/dev/null'))
        : '');
if ($effectiveUid !== '0') {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_NOT_ROOT\n");
    exit(2);
}
if (!is_file('/conf/config.xml') || is_link('/conf/config.xml')) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_CONFIG_NOT_REGULAR\n");
    exit(2);
}
$fileUid = fileowner('/conf/config.xml');
if ($fileUid !== 0) {
    // OPNsense 26.7 Core AppConfig specifies wwwonly:wheel as its
    // legitimate Config owner. Refuse arbitrary owners: the target must be
    // root or the exact native wwwonly account, independently resolved.
    $nativeUid = null;
    if (function_exists('posix_getpwnam')) {
        $account = posix_getpwnam('wwwonly');
        if (is_array($account) && isset($account['uid'])) {
            $nativeUid = (int)$account['uid'];
        }
    }
    if ($nativeUid === null && function_exists('shell_exec')) {
        $result = @shell_exec('/usr/bin/id -u wwwonly 2>/dev/null');
        if (is_string($result) && preg_match('/^[0-9]+$/D', trim($result))) {
            $nativeUid = (int)trim($result);
        }
    }
    if ($fileUid === false || $nativeUid === null || $fileUid !== $nativeUid ||
        $nativeUid <= 0) {
        fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_CONFIG_OWNER_UNEXPECTED\n");
        exit(2);
    }
}
if (!is_writable('/conf/config.xml')) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_CONFIG_NOT_WRITABLE\n");
    exit(2);
}
// Stage 5 generated this runner-only key and installed the same key into the
// disposable OPNsense guest. No normal plugin package contains that marker.
$guestMarker = 'stage5-browser-wan-ci.pub';
if (!is_file($guestMarker) || is_link($guestMarker) ||
    !is_readable($guestMarker) ||
    !is_file('/root/.ssh/authorized_keys') ||
    !is_readable('/root/.ssh/authorized_keys')) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_GUEST_WITNESS_MISSING\n");
    exit(2);
}
$publicKey = trim((string)file_get_contents($guestMarker));
$authorizedKeys = (string)file_get_contents('/root/.ssh/authorized_keys');
if (!preg_match('/^ssh-ed25519 [A-Za-z0-9+\/=]+(?: [^\r\n]+)?$/D', $publicKey) ||
    !in_array($publicKey, array_map('trim', explode("\n", $authorizedKeys)), true)) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_GUEST_WITNESS_INVALID\n");
    exit(2);
}
$locale = $argv[1] ?? '';
if (count($argv) !== 2 || !in_array($locale, ['en_US', 'ru_RU'], true)) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_INVALID_LOCALE\n");
    exit(2);
}
require_once 'script/load_phalcon.php';
$config = \OPNsense\Core\Config::getInstance();
$root = $config->object();
if (!isset($root->OPNsense->Zapret) || !isset($root->system->user)) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_GUEST_CONFIG_MISSING\n");
    exit(2);
}
$before = hash('sha256', (string)$root->OPNsense->Zapret->asXML());
$found = false;
foreach ($root->system->user as $user) {
    if ((string)$user->name === 'root') {
        if ($found) {
            fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_DUPLICATE_ROOT\n");
            exit(2);
        }
        $user->language = $locale;
        $found = true;
    }
}
if (!$found) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_ROOT_NOT_FOUND\n");
    exit(2);
}
$config->save([
    'description' => 'Disposable P3 CI user language smoke test'
]);
$config->forceReload();
$afterRoot = $config->object();
$after = hash('sha256', (string)$afterRoot->OPNsense->Zapret->asXML());
if (!hash_equals($before, $after)) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_ZAPRET_CHANGED\n");
    exit(2);
}
$matched = 0;
foreach ($afterRoot->system->user as $user) {
    if ((string)$user->name === 'root') {
        if ((string)$user->language !== $locale) {
            fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_LOCALE_NOT_SAVED\n");
            exit(2);
        }
        ++$matched;
    }
}
if ($matched !== 1) {
    fwrite(STDERR, "P3_PROFILE_LOCALE=REFUSED_USER_IDENTITY\n");
    exit(2);
}
echo "PASS_P3_DISPOSABLE_ROOT_LOCALE=" . $locale . "\n";
