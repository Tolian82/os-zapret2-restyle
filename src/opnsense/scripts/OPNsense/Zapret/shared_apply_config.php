<?php

/**
 * The single shared Strategies/Voice native Config commit command.
 *
 * A service shell process must already own the original FD9. The staged
 * plan and detached XML are produced by shared_apply_request.php and
 * the complete release by shared-apply-build before this point.
 *
 * preflight => freshly locked native model, no save (before runtime switch)
 * save      => the existing SharedConfigCommit::persist, NOT a second writer
 *
 * This command does not control IPFW, start engines or edit the journal.
 * A failed save after an attempted Config::save is categorically UNCERTAIN.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/apply_settings.php';
require_once __DIR__ . '/shared_apply_lock.php';

use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\VoiceSettingsSnapshot;

final class SharedApplyConfigWorker
{
    public const ROOT = '/var/db/zapret2/shared-work';
    private const MAX_PLAN = 4 * 1024 * 1024;

    private static function secureFile(string $path, bool $directory, int $owner): void
    {
        $s = @lstat($path);
        if ($s === false ||
            (($s['mode'] & 0170000) !== ($directory ? 0040000 : 0100000)) ||
            $s['uid'] !== $owner || ($s['mode'] & 0077) !== 0 ||
            (!$directory && ($s['nlink'] !== 1 || $s['size'] > self::MAX_PLAN))) {
            throw new \RuntimeException('Unsafe native common Apply evidence');
        }
    }

    public static function readPlan(string $id, string $root = self::ROOT, ?int $owner = null): array
    {
        if (!preg_match('/^[a-f0-9]{32}$/D', $id)) {
            throw new \InvalidArgumentException('Invalid common Apply ID');
        }
        $owner = $owner ?? SharedApplyLifecycleLock::effectiveUid();
        self::secureFile($root, true, $owner);
        $dir = rtrim($root, '/') . '/' . $id;
        self::secureFile($dir, true, $owner);
        $file = $dir . '/plan.json';
        self::secureFile($file, false, $owner);
        $fp = @fopen($file, 'rb');
        if ($fp === false) {
            throw new \RuntimeException('Unable to open shared Apply plan');
        }
        try {
            $handle = fstat($fp);
            $named = @lstat($file);
            if ($named === false || $handle['ino'] !== $named['ino'] ||
                $handle['dev'] !== $named['dev']) {
                throw new \RuntimeException('Shared Apply plan changed inode');
            }
            $json = stream_get_contents($fp, self::MAX_PLAN + 1);
            if (!is_string($json) || strlen($json) > self::MAX_PLAN) {
                throw new \RuntimeException('Unsafe shared Apply plan size');
            }
        } finally {
            fclose($fp);
        }
        try {
            $plan = json_decode($json, true, 32, JSON_THROW_ON_ERROR);
        } catch (\JsonException $error) {
            throw new \RuntimeException('Corrupt stored native shared plan', 0, $error);
        }
        if (!is_array($plan) || ($plan['result'] ?? null) !== 'prepared' ||
            !isset($plan['candidate'], $plan['changed_fields'], $plan['dependencies']) ||
            !is_array($plan['candidate']) || !is_array($plan['changed_fields']) ||
            !in_array($plan['page'] ?? null, ['voice','strategies'], true)) {
            throw new \RuntimeException('Malformed stored native shared candidate');
        }
        // The Config and full release must have been staged together; a
        // symlinked/missing XML is not authority to persist its plan.
        self::secureFile($dir . '/candidate.xml', false, $owner);
        return $plan;
    }

    public static function preflight(
        array $plan, array $current, string $page, ?object $model = null
    ): array {
        $target = SettingsApply::mergeForCommit($current, $plan, $page);
        if ($model !== null && count($plan['changed_fields']) > 0) {
            // Full getNodes() contains selection-option arrays not suitable
            // for native setNodes(). Validate only form-owned scalar leaves,
            // using exactly the same write method as Config persist.
            SharedConfigCommit::validateOwnedModelFields(
                $model, $target, $plan['changed_fields']
            );
        }
        $mode = (string)($target['general']['enabled'] ?? '0');
        if (!in_array($mode, ['0', '1'], true)) {
            throw new \InvalidArgumentException('Invalid shared candidate runtime mode');
        }
        return [
            'result' => 'prepared',
            'snapshot' => VoiceSettingsSnapshot::digest($target),
            'enabled' => $mode,
            'changes' => count($plan['changed_fields']),
            'base' => $plan['dependencies'],
            'candidate' => VoiceSettingsSnapshot::digest($plan['candidate']),
            'fields' => $plan['changed_fields'],
        ];
    }

    /**
     * Boot may only replay the *saved* common candidate; unlike preflight,
     * its previous generation is necessarily obsolete after Config::save.
     * Compare the entire live Voice/Strategies dependency snapshot under the
     * actual native Config lock, not a stale GUI baseline or an XML file.
     */
    /**
     * Pure, read-only Config outcome classifier for the INTERNAL original
     * FD9 found recovery. The caller must supply the fresh getNodes() tree
     * obtained under the ONE native Config lock; it must independently
     * bind the original sealed plan and journal before invoking this.
     *
     * Config::save() releases the lock. Consequently matching candidate
     * values are evidence only, NOT causal proof of our native save or
     * permission to commit, restore or restart any engine.
     * This deliberately registers no CLI/configd/GUI action.
     */
    public static function classifyFoundConfigImage(
        array $plan, array $current, string $phase
    ): array {
        if (!in_array($phase, [
            'prepared', 'found-files-writing', 'found-files-written',
            'found-config-saving', 'found-config-saved'
        ], true) ||
            ($plan['page'] ?? null) !== 'strategies' ||
            ($plan['result'] ?? null) !== 'prepared' ||
            !isset($plan['candidate']) || !is_array($plan['candidate']) ||
            !isset($plan['dependencies']) || !is_string($plan['dependencies']) ||
            !preg_match('/^[a-f0-9]{64}$/D', $plan['dependencies']) ||
            !isset($plan['found_intent']) || !is_array($plan['found_intent']) ||
            ($plan['found_intent']['commit_authorized'] ?? null) !== false ||
            ($plan['found_intent']['config_revision'] ?? null) !==
                $plan['dependencies'] ||
            !isset($plan['found_batch']) || !is_array($plan['found_batch']) ||
            array_keys($plan['found_batch']) !== ['youtube', 'user', 'auto'] ||
            !isset($plan['changed_fields']) || !is_array($plan['changed_fields']) ||
            !is_array($current)) {
            throw new \RuntimeException('Unqualified original cold Config evidence');
        }
        $base = $plan['dependencies'];
        $candidate = VoiceSettingsSnapshot::digest($plan['candidate']);
        $observed = VoiceSettingsSnapshot::digest($current);
        $isBase = hash_equals($base, $observed);
        $isCandidate = hash_equals($candidate, $observed);
        if (!$isBase && !$isCandidate) {
            throw new \RuntimeException('Foreign native Config image during found recovery');
        }
        if (in_array($phase, ['prepared', 'found-files-writing',
                'found-files-written'], true) && !$isBase) {
            throw new \RuntimeException('Found files-only phase already changed Config');
        }
        if ($phase === 'found-config-saved' && !$isCandidate) {
            throw new \RuntimeException('Found Config-saved WAL does not match native Config');
        }
        // "Both" includes a found-only edit with no XML save, and cannot
        // tell whether an uncertain native save was attempted.
        $state = $isBase && $isCandidate
            ? 'base-equals-candidate'
            : ($isCandidate ? 'candidate-image' : 'base-image');
        return [
            'result' => 'read-only-found-config-classification',
            'phase' => $phase,
            'image' => $state,
            'snapshot' => $observed,
            'commit_authorized' => false,
            'restore_authorized' => false,
            'save_attested' => false,
            'runtime_attested' => false,
        ];
    }

    /**
     * Compose an explicitly NON-authorizing witness from the original
     * FD9→native Config→P2 read-only inspection. This helper is also used
     * by fake-native tests: only inspectFoundColdNative() may obtain its
     * real file evidence, under the ORIGINAL inherited descriptor.
     */
    public static function classifyFoundJointImages(
        array $plan, array $current, array $files
    ): array {
        // Python serializes sorted JSON keys, while the original source
        // stage map may be constructed in changed-source order. Do not
        // confuse key order with missing/foreign evidence.
        $expected = ['schema', 'result', 'journal_phase', 'image',
            'states', 'stage_evidence', 'commit_authorized',
            'restore_authorized'];
        $keys = array_keys($files);
        sort($keys);
        sort($expected);
        if ($keys !== $expected) {
            throw new \RuntimeException('Unqualified original cold file evidence');
        }
        if (($files['schema'] ?? null) !== 1 ||
            ($files['result'] ?? null) !== 'read-only-cold-image-classification' ||
            !in_array($files['image'] ?? null,
                ['all-before', 'contains-unattributed-after'], true) ||
            ($files['commit_authorized'] ?? null) !== false ||
            ($files['restore_authorized'] ?? null) !== false ||
            !is_array($files['states'] ?? null) ||
            array_keys($files['states']) !== ['youtube', 'user', 'auto'] ||
            array_diff($files['states'], ['before', 'after-image']) ||
            (!is_array($files['stage_evidence'] ?? null) &&
                ($files['journal_phase'] ?? null) !== 'prepared')) {
            throw new \RuntimeException('Original cold files cannot be attributed');
        }
        $phase = $files['journal_phase'];
        if ($phase !== 'prepared') {
            $stages = $files['stage_evidence'];
            $stageKeys = array_keys($stages);
            sort($stageKeys);
            if ($stageKeys !== ['auto', 'user', 'youtube'] ||
                array_diff($stages, [
                    'ready-but-before', 'ready-but-after', 'installed-after',
                    'not-started', 'unchanged-before'
                ])) {
                throw new \RuntimeException('Original staged file proof incomplete');
            }
        } elseif ($files['stage_evidence'] !== null) {
            throw new \RuntimeException('Prepared Config has no staged file writes');
        }
        $config = self::classifyFoundConfigImage($plan, $current, $phase);
        return [
            'result' => 'read-only-original-joint-classification',
            'journal_phase' => $phase,
            'config_image' => $config['image'],
            'file_image' => $files['image'],
            'file_states' => $files['states'],
            'stage_evidence' => $files['stage_evidence'],
            'commit_authorized' => false,
            'restore_authorized' => false,
            'save_attested' => false,
            'runtime_attested' => false,
        ];
    }

    /**
     * Real cold inspection uses the ONE original PHP Config::lock and the
     * child inherited descriptors 4 + 9. No new lock owner and NO mutation.
     * It remains an unregistered internal FD9-only CLI, not a GUI Apply.
     */
    private static function originalFoundLockedFileEvidence(
        object $config, string $id
    ): array {
        SharedApplyLifecycleLock::assertHeld();
        $reflection = new \ReflectionObject($config);
        if (!$reflection->hasProperty('config_file_handle') ||
            !$reflection->hasProperty('config_file')) {
            throw new \RuntimeException('Native Config locked descriptor missing');
        }
        $handle = $reflection->getProperty('config_file_handle')->getValue($config);
        $path = $reflection->getProperty('config_file')->getValue($config);
        $named = @lstat('/conf/config.xml');
        $opened = is_resource($handle) ? @fstat($handle) : false;
        if ($path !== '/conf/config.xml' || !is_array($named) ||
            !is_array($opened) || $opened['dev'] !== $named['dev'] ||
            $opened['ino'] !== $named['ino']) {
            throw new \RuntimeException('Original native Config lock inode changed');
        }
        $fd9 = @fopen('php://fd/9', 'r+b');
        if (!is_resource($fd9)) {
            throw new \RuntimeException('Original FD9 descriptor missing');
        }
        try {
            $pipes = [];
            $proc = @proc_open(
                ['/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
                 '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_effective_known.py',
                 'classify-locked', $id],
                [0 => ['file', '/dev/null', 'r'],
                 1 => ['pipe', 'w'], 2 => ['file', '/dev/null', 'a'],
                 4 => $handle, 9 => $fd9],
                $pipes, null, ['LC_ALL' => 'C', 'PATH' => '/usr/bin:/bin:/usr/local/bin']
            );
            if (!is_resource($proc)) {
                throw new \RuntimeException('Original cold native child unavailable');
            }
            try {
                stream_set_blocking($pipes[1], false);
                $output = '';
                $deadline = microtime(true) + 40;
                while (!feof($pipes[1])) {
                    if (microtime(true) >= $deadline || strlen($output) > 16384) {
                        throw new \RuntimeException('Original cold native child timeout');
                    }
                    $read = [$pipes[1]];
                    $write = [];
                    $except = [];
                    $ready = @stream_select($read, $write, $except, 1);
                    if ($ready === false) {
                        throw new \RuntimeException('Original cold native child read failed');
                    }
                    if ($ready > 0) {
                        $piece = @fread($pipes[1], 16385 - strlen($output));
                        if ($piece === false) {
                            throw new \RuntimeException('Original cold native child interrupted');
                        }
                        $output .= $piece;
                    }
                }
                fclose($pipes[1]);
                unset($pipes[1]);
                $code = proc_close($proc);
                $proc = null;
                if ($code !== 0 || strlen($output) > 16384 || $output === '') {
                    throw new \RuntimeException('Original FD9/P2 staged image unknown');
                }
                $reply = json_decode($output, true, 12, JSON_THROW_ON_ERROR);
                if (!is_array($reply)) {
                    throw new \RuntimeException('Original native cold image malformed');
                }
                $namedAgain = @lstat('/conf/config.xml');
                $heldAgain = @fstat($handle);
                if (!is_array($namedAgain) || !is_array($heldAgain) ||
                    $namedAgain['dev'] !== $heldAgain['dev'] ||
                    $namedAgain['ino'] !== $heldAgain['ino'] ||
                    $namedAgain['dev'] !== $named['dev'] ||
                    $namedAgain['ino'] !== $named['ino']) {
                    throw new \RuntimeException('Native Config replaced during cold files proof');
                }
                SharedApplyLifecycleLock::assertHeld();
                return $reply;
            } finally {
                foreach ($pipes as $pipe) {
                    if (is_resource($pipe)) { fclose($pipe); }
                }
                if (is_resource($proc)) {
                    @proc_terminate($proc);
                    @proc_close($proc);
                }
            }
        } finally {
            fclose($fd9);
        }
    }

    private static function inspectFoundColdNative(
        array $plan, string $id, object $config, callable $factory
    ): array {
        SharedApplyLifecycleLock::assertHeld();
        $config->lock();
        try {
            $before = $factory()->getNodes();
            $files = self::originalFoundLockedFileEvidence($config, $id);
            $after = $factory()->getNodes();
            if (!is_array($before) || !is_array($after) ||
                VoiceSettingsSnapshot::digest($before) !==
                    VoiceSettingsSnapshot::digest($after)) {
                throw new \RuntimeException('Native Config changed during cold inspection');
            }
            $joint = self::classifyFoundJointImages($plan, $after, $files);
            // Re-attest the named original plan before allowing ANY receipt
            // out of the protected scope (not an Apply/restore receipt).
            if (self::readPlan($id, self::ROOT, 0) !== $plan) {
                throw new \RuntimeException('Original cold sealed plan changed');
            }
            return $joint;
        } finally {
            $config->unlock();
        }
    }

    public static function saved(array $plan, array $current): array
    {
        $expected = VoiceSettingsSnapshot::digest($plan['candidate']);
        $actual = VoiceSettingsSnapshot::digest($current);
        if (!hash_equals($expected, $actual)) {
            throw new \RuntimeException('Saved native Config differs from shared owner');
        }
        $enabled = (string)($current['general']['enabled'] ?? '0');
        if (!in_array($enabled, ['0','1'], true)) {
            throw new \RuntimeException('Invalid saved native runtime mode');
        }
        return ['result'=>'committed','snapshot'=>$actual,'enabled'=>$enabled];
    }

    /** The saved Config cannot be labelled pre-save if output encoding fails. */
    public static function postSaveReceipt(array $result): string
    {
        try {
            return json_encode(
                $result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES
            ) . "\n";
        } catch (\Throwable $error) {
            throw new SharedConfigSaveUncertain(
                'Native saved Config receipt encoding requires review', 0, $error
            );
        }
    }

    /**
     * Read the native persisted Auto Restart preference under the SAME
     * original FD9 and short standard OPNsense Config lock, without saving.
     * This is a scheduler gate, never a second Config writer.
     */
    public static function autoRestartPreference(): string
    {
        if (PHP_OS_FAMILY !== 'BSD' ||
            SharedApplyLifecycleLock::effectiveUid() !== 0) {
            throw new \RuntimeException('Native root scheduler owner required');
        }
        SharedApplyLifecycleLock::assertHeld();
        require_once('script/load_phalcon.php');
        $config = \OPNsense\Core\Config::getInstance();
        $config->lock();
        try {
            $model = new \OPNsense\Zapret\Zapret();
            // OptionField::getNodeData() (and thus getNodes()) is a GUI
            // options/selected map, NOT the saved enum. The stock OPNsense
            // getNodeContent() reads the exact underlying field values.
            $nodes = $model->getNodeContent();
            $general = $nodes['general'] ?? null;
            if (!is_array($general)) {
                throw new \RuntimeException('Native general Config unavailable');
            }
            $enabled = (string)($general['enabled'] ?? '');
            $interval = (string)($general['autorestart'] ?? 'off');
            if (!in_array($enabled, ['0', '1'], true) ||
                !in_array($interval, ['off', 'hourly', 'daily', 'weekly', 'monthly'], true)) {
                throw new \RuntimeException('Invalid native Auto Restart preference');
            }
            return $enabled . ':' . $interval;
        } finally {
            $config->unlock();
        }
    }

    public static function main(array $argv): int
    {
        if (count($argv) === 2 && $argv[1] === 'auto-restart') {
            try {
                echo self::autoRestartPreference(), "\n";
                return 0;
            } catch (\Throwable $error) {
                fwrite(STDERR, "ERROR: original native Auto Restart Config unavailable\n");
                return 69;
            }
        }
        if (count($argv) !== 4 || !in_array($argv[1],
                ['preflight', 'save', 'saved', 'found-cold'], true) ||
            !in_array($argv[3], ['voice','strategies'], true) ||
            ($argv[1] === 'found-cold' && $argv[3] !== 'strategies')) {
            fwrite(STDERR, "usage: shared_apply_config.php preflight|save ID voice|strategies\n");
            return 64;
        }
        try {
            if (PHP_OS_FAMILY !== 'BSD' || SharedApplyLifecycleLock::effectiveUid() !== 0) {
                throw new \RuntimeException('Root OPNsense native Config required');
            }
            SharedApplyLifecycleLock::assertHeld();
            require_once('script/load_phalcon.php');
            $plan = self::readPlan($argv[2], self::ROOT, 0);
            if ($plan['page'] !== $argv[3]) {
                throw new \InvalidArgumentException('Stored native Apply page differs from request');
            }
            $config = \OPNsense\Core\Config::getInstance();
            $factory = static fn() => new \OPNsense\Zapret\Zapret();
            if ($argv[1] === 'found-cold') {
                $joint = self::inspectFoundColdNative(
                    $plan, $argv[2], $config, $factory);
                echo json_encode($joint, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
                return 0;
            }
            if ($argv[1] === 'preflight' || $argv[1] === 'saved') {
                $config->lock();
                try {
                    $model = $factory();
                    $fresh = $model->getNodes();
                    $result = $argv[1] === 'preflight'
                        ? self::preflight($plan, $fresh, $argv[3], $model)
                        : self::saved($plan, $fresh);
                } finally {
                    $config->unlock();
                }
                echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
                return 0;
            }
            $result = SharedConfigCommit::persist($plan, $argv[3], $config, $factory);
            $receipt = self::postSaveReceipt($result);
            // Even a short response write is uncertain to the caller:
            // Config is already persisted and runtime must not be rolled back.
            if (fwrite(STDOUT, $receipt) !== strlen($receipt)) {
                throw new SharedConfigSaveUncertain(
                    'Native saved Config receipt could not be delivered'
                );
            }
            return 0;
        } catch (SharedConfigSaveUncertain $error) {
            fwrite(STDERR, "ERROR: native shared Config save uncertain; retain recovery evidence\n");
            return 70;
        } catch (\Throwable $error) {
            fwrite(STDERR, "ERROR: native shared Config refused before save: " .
                $error->getMessage() . "\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' && isset($argv) &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(SharedApplyConfigWorker::main($argv));
}
