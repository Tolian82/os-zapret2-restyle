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
            'states', 'stage_evidence', 'previous_runtime',
            'commit_authorized', 'restore_authorized'];
        $keys = array_keys($files);
        sort($keys);
        sort($expected);
        if ($keys !== $expected) {
            throw new \RuntimeException('Unqualified original cold file evidence');
        }
        // Python's classify-locked JSON is sort_keys=True recursively:
        // legitimate source maps arrive auto,user,youtube on the wire.
        // Require EXACTLY these three keys but never confuse JSON map order
        // with missing/foreign source evidence.
        $states = $files['states'] ?? null;
        $stateKeys = is_array($states) ? array_keys($states) : [];
        sort($stateKeys);
        if (($files['schema'] ?? null) !== 1 ||
            ($files['result'] ?? null) !== 'read-only-cold-image-classification' ||
            !in_array($files['image'] ?? null,
                ['all-before', 'contains-unattributed-after'], true) ||
            ($files['commit_authorized'] ?? null) !== false ||
            ($files['restore_authorized'] ?? null) !== false ||
            !is_array($states) ||
            $stateKeys !== ['auto', 'user', 'youtube'] ||
            array_diff($states, ['before', 'after-image']) ||
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

        // The parent must not trust a shaped JSON receipt alone. Bind every
        // file's BEFORE/AFTER and ready/installed state to the SAME sealed
        // found_batch and WAL phase before inspecting native Config. A
        // contradictory but well-formed child receipt must fail closed.
        $rows = $plan['found_batch'] ?? null;
        if (!is_array($rows) ||
            array_keys($rows) !== ['youtube', 'user', 'auto']) {
            throw new \RuntimeException('Original joint found plan incomplete');
        }
        $expectedImage = in_array('after-image', $files['states'], true)
            ? 'contains-unattributed-after' : 'all-before';
        if ($files['image'] !== $expectedImage) {
            throw new \RuntimeException('Original joint image summary contradicts sources');
        }
        foreach (['youtube', 'user', 'auto'] as $name) {
            $row = $rows[$name];
            if (!is_array($row) || !is_string($row['before'] ?? null) ||
                !is_string($row['after'] ?? null)) {
                throw new \RuntimeException('Original joint source not sealed');
            }
            $changed = $row['before'] !== $row['after'];
            $state = $files['states'][$name];
            $stage = $phase === 'prepared' ? null : $files['stage_evidence'][$name];
            if ($phase === 'prepared') {
                if ($state !== 'before') {
                    throw new \RuntimeException('Original prepared file was modified');
                }
            } elseif (!$changed) {
                if ($state !== 'before' || $stage !== 'unchanged-before') {
                    throw new \RuntimeException('Original unchanged source has staged mutation');
                }
            } elseif ($phase === 'found-files-writing') {
                $valid = ($state === 'before' && in_array(
                    $stage, ['not-started', 'ready-but-before'], true)) ||
                    ($state === 'after-image' && in_array(
                        $stage, ['ready-but-after', 'installed-after'], true));
                if (!$valid) {
                    throw new \RuntimeException('Original staged source contradicts physical image');
                }
            } elseif ($state !== 'after-image' || $stage !== 'installed-after') {
                throw new \RuntimeException('Original found checkpoint lacks installed source');
            }
        }
        // The child must have inspected the ORIGINAL previous sealed
        // common runtime and plugin IPFW through the existing Voice reader.
        // On an initial no-predecessor transaction, this does not prove
        // an empty machine; no mutation or terminalization is authorized.
        $prior = $files['previous_runtime'];
        if (!is_array($prior)) {
            throw new \RuntimeException('Original previous runtime evidence missing');
        }
        $priorKeys = array_keys($prior);
        sort($priorKeys);
        if ($priorKeys !== ['id', 'state'] ||
            !in_array($prior['state'] ?? null,
                ['ready', 'stopped', 'no-predecessor-proof'], true) ||
            (($prior['state'] === 'no-predecessor-proof') !== ($prior['id'] === null)) ||
            ($prior['id'] !== null && (
                !is_string($prior['id']) ||
                !preg_match('/^[a-f0-9]{32}$/D', $prior['id'])))) {
            throw new \RuntimeException('Unqualified previous native runtime owner');
        }
        $config = self::classifyFoundConfigImage($plan, $current, $phase);
        return [
            'result' => 'read-only-original-joint-classification',
            'journal_phase' => $phase,
            'config_image' => $config['image'],
            'file_image' => $files['image'],
            'file_states' => $files['states'],
            'stage_evidence' => $files['stage_evidence'],
            'previous_runtime' => $prior,
            'commit_authorized' => false,
            'restore_authorized' => false,
            'save_attested' => false,
            'runtime_attested' => false,
        ];
    }

    private static function openOriginalFoundQueue(int $fd)
    {
        if ($fd < 3 || $fd > 1024 || $fd === 9) {
            throw new \RuntimeException('Invalid original Found queue descriptor');
        }
        $stream = @fopen('php://fd/' . $fd, 'r+b');
        if (!is_resource($stream)) {
            throw new \RuntimeException('Original Found queue descriptor unavailable');
        }
        $held = @fstat($stream);
        $named = @lstat('/var/db/zapret2-auto-detect/worker.lock');
        if (!is_array($held) || !is_array($named) ||
            $held['dev'] !== $named['dev'] || $held['ino'] !== $named['ino'] ||
            $held['uid'] !== 0 || $held['gid'] !== 0 || $held['nlink'] !== 1 ||
            $named['nlink'] !== 1 || ($held['mode'] & 0177777) !== 0100600 ||
            ($named['mode'] & 0177777) !== 0100600) {
            fclose($stream);
            throw new \RuntimeException('Foreign original Found queue descriptor');
        }
        // Python independently verifies the same locked open description.
        return $stream;
    }

    /**
     * Real cold inspection uses the ONE original PHP Config::lock and the
     * child inherited descriptors 4 + 9. No new lock owner and NO mutation.
     * It remains an unregistered internal FD9-only CLI, not a GUI Apply.
     */
    /**
     * Mutation child: a deadline refuses the receipt, never kills the child.
     * Drain bounded output (discard excess) and join before Config::unlock.
     * No extra writer, detached worker or second lock. The child must join
     * its synchronous physical commands before returning.
     */
    private static function joinOrdinaryRestoreChild($proc, array &$pipes, float $budget = 40.0): array
    {
        $output = '';
        $failed = false;
        $deadline = hrtime(true) + (int)($budget * 1000000000);
        try {
            if (!stream_set_blocking($pipes[1], false)) {
                $failed = true;
            }
            while (!feof($pipes[1])) {
                if (hrtime(true) >= $deadline) {
                    $failed = true;
                }
                $read = [$pipes[1]];
                $write = [];
                $except = [];
                $ready = @stream_select($read, $write, $except, 1);
                if ($ready === false) {
                    // An interrupted read is not permission to terminate
                    // the child. Fall back to a blocking drain and join.
                    $failed = true;
                    stream_set_blocking($pipes[1], true);
                } elseif ($ready === 0) {
                    continue;
                }
                $piece = @fread($pipes[1], 4096);
                if ($piece === false) {
                    $failed = true;
                    break;
                }
                if (!$failed && strlen($output) + strlen($piece) <= 16384) {
                    $output .= $piece;
                } else {
                    $failed = true;
                }
            }
        } finally {
            // Closing a broken receipt pipe is safe only because the
            // original child writes its result AFTER physical commands.
            foreach ($pipes as $key => $pipe) {
                if (is_resource($pipe)) {
                    fclose($pipe);
                }
                unset($pipes[$key]);
            }
        }
        $code = proc_close($proc);
        return [$output, $failed || hrtime(true) >= $deadline, $code];
    }

    private static function originalFoundLockedFileEvidence(
        object $config, string $id, string $mode = 'classify-locked',
        ?string $configDigest = null, ?string $runtimeMode = null,
        ?callable $whileP2Held = null, $queueStream = null, ?string $baseDigest = null
    ): array {
        $begin = $mode === 'begin-found-save-locked';
        $ordinaryRestore = $mode === 'finish-ordinary-restore-locked';
        if (($mode === 'classify-locked' ? $configDigest !== null :
                (!is_string($configDigest) ||
                 !preg_match('/^[a-f0-9]{64}$/D', $configDigest))) ||
            ($begin ? (!in_array($runtimeMode, ['0', '1'], true) || $whileP2Held === null ||
                        $baseDigest === null || !preg_match('/^[a-f0-9]{64}$/D', $baseDigest))
                    : ($runtimeMode !== null || $whileP2Held !== null || $baseDigest !== null)) ||
            ($queueStream !== null && (!is_resource($queueStream) ||
                !in_array($mode, ['recover-found-locked', 'confirm-found-save-locked',
                    'finish-ordinary-restore-locked'], true)))) {
            throw new \RuntimeException('Unqualified original cold native mode');
        }
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
            $command = [
                '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh',
                '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_effective_known.py',
                $mode, $id
            ];
            if ($configDigest !== null) {
                $command[] = $configDigest;
            }
            if ($begin) {
                $command[] = $runtimeMode;
                $command[] = $baseDigest;
            }
            $descriptors = [0 => $begin ? ['pipe', 'r'] : ['file', '/dev/null', 'r'],
                1 => ['pipe', 'w'], 2 => ['file', '/dev/null', 'a'],
                4 => $handle, 9 => $fd9];
            if ($queueStream !== null) {
                $descriptors[3] = $queueStream;
                $command[] = '--inherited-queue';
            }
            $proc = @proc_open(
                $command, $descriptors,
                $pipes, null, ['LC_ALL' => 'C', 'PATH' => '/usr/bin:/bin:/usr/local/bin']
            );
            if (!is_resource($proc)) {
                throw new \RuntimeException('Original cold native child unavailable');
            }
            try {
                if ($ordinaryRestore) {
                    [$output, $failed, $code] = self::joinOrdinaryRestoreChild($proc, $pipes);
                    $proc = null;
                    if ($failed || $code !== 0 || $output === '') {
                        throw new \RuntimeException('Original ordinary restore outcome uncertain after join');
                    }
                } else {
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
                            if ($begin && $output === "ready\n" && isset($pipes[0])) {
                                // The original Python child keeps P2 held from
                                // physical writes through the only native save.
                                // Even a throwing save releases this scope.
                                try {
                                    $whileP2Held();
                                } finally {
                                    fclose($pipes[0]);
                                    unset($pipes[0]);
                                }
                            }
                        }
                    }
                    fclose($pipes[1]);
                    unset($pipes[1]);
                    $code = proc_close($proc);
                    $proc = null;
                    if ($code !== 0 || strlen($output) > 16384 || $output === '') {
                        throw new \RuntimeException('Original FD9/P2 staged image unknown');
                    }
                }
                $reply = $begin && $output === "ready\n" && !isset($pipes[0])
                    ? ['result' => 'ready']
                    : json_decode($output, true, 12, JSON_THROW_ON_ERROR);
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
                    if (!$ordinaryRestore) {
                        @proc_terminate($proc);
                    }
                    // Never release Config while a synchronous ordinary
                    // physical child is still running, even on read error.
                    @proc_close($proc);
                }
            }
        } finally {
            fclose($fd9);
        }
    }

    private static function saveFoundNative(
        array $plan, string $id, string $mode, object $config, callable $factory
    ): array {
        $scopes = 0;
        $candidate = VoiceSettingsSnapshot::digest($plan['candidate']);
        try {
            return SharedConfigCommit::persistFoundUnderOriginalOwner(
                $plan, 'strategies', $config, $factory,
                static function (callable $saveScope, string $observedDigest) use (
                    &$scopes, $config, $mode, $id, $candidate, $plan
                ): string {
                    if (++$scopes === 1) {
                        if (!hash_equals($plan['dependencies'], $observedDigest)) {
                            throw new \RuntimeException('Original Found base Config changed');
                        }
                        $status = null;
                        $ready = self::originalFoundLockedFileEvidence(
                            $config, $id, 'begin-found-save-locked', $candidate, $mode,
                            static function () use ($saveScope, &$status): void {
                                $status = $saveScope();
                            }, null, $observedDigest
                        );
                        if (($ready['result'] ?? null) !== 'ready' || !is_string($status)) {
                            throw new \RuntimeException('Original found save scope unavailable');
                        }
                        return $status;
                    }
                    if ($scopes !== 2 || !hash_equals($candidate, $observedDigest)) {
                        throw new \RuntimeException('Original Found saved Config changed');
                    }
                    $receipt = self::originalFoundLockedFileEvidence(
                        $config, $id, 'confirm-found-save-locked', $observedDigest
                    );
                    if ($receipt !== ['result' => 'found-config-saved', 'mode' => $mode]) {
                        throw new \RuntimeException('Original found save readback unavailable');
                    }
                    return $saveScope();
                },
                // The child proves the sealed files and fsyncs the relevant
                // phase before either callback can execute.
                static fn(string $stage, string $digest): bool =>
                    hash_equals($candidate, $digest),
                static fn(string $phase): bool => in_array(
                    $phase, ['found-config-saving', 'found-config-saved'], true
                )
            );
        } catch (\Throwable $error) {
            // Even an error before the ready handshake can leave PREPARED
            // or partial HOSTLIST bytes. Recovery reads the original WAL.
            throw new SharedConfigSaveUncertain(
                'Original found settings require joint recovery', 0, $error
            );
        }
    }

    private static function foundPhaseNative(
        string $action, string $id, object $config, callable $factory, $queueStream = null
    ): array {
        $config->lock();
        try {
            $digest = VoiceSettingsSnapshot::digest($factory()->getNodes());
            return self::originalFoundLockedFileEvidence(
                $config, $id, $action === 'found-recover' ? 'recover-found-locked' : $action,
                $digest, null, null, $queueStream
            );
        } finally {
            $config->unlock();
        }
    }

    private static function requireReadableConfig(): void
    {
        // Core Config initializes from a backup if the live XML is invalid.
        // An interrupted save must keep its evidence for native review.
        $xml = @simplexml_load_file('/conf/config.xml', \SimpleXMLElement::class,
            LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING);
        if ($xml === false || $xml->getName() !== 'opnsense') {
            throw new SharedConfigSaveUncertain('Native Config image is unreadable');
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

    /**
     * ORIGINAL native Config owner -> already held FD9 -> P2 -> SAME journal.
     *
     * This is a narrowly restricted cold no-write recovery of found PREPARED
     * with physically proven predecessor. Not wired to configd/GUI or normal
     * Apply/Start. No second Config writer and never call Config::save().
     */
    private static function recoverFoundPreparedNative(
        array $plan, string $id, object $config, callable $factory
    ): array {
        SharedApplyLifecycleLock::assertHeld();
        $config->lock();
        try {
            $fresh = $factory()->getNodes();
            if (!is_array($fresh) || !is_string($plan['dependencies'] ?? null) ||
                !preg_match('/^[a-f0-9]{64}$/D', $plan['dependencies'])) {
                throw new \RuntimeException('Original found Config baseline unavailable');
            }
            $base = VoiceSettingsSnapshot::digest($fresh);
            if (!hash_equals($plan['dependencies'], $base)) {
                throw new \RuntimeException('Original found pristine Config changed');
            }
            // Python independently checks the native inherited Config fd4,
            // original FD9, same sealed plan and PREPARED WAL, three exact
            // BEFORE files and same physical previous runtime/IPFW TWICE.
            // Its ONLY write is original operation.json restored fsync.
            $receipt = self::originalFoundLockedFileEvidence(
                $config, $id, 'recover-prepared-locked', $base);
            $keys = array_keys($receipt);
            sort($keys);
            $expected = ['config_saved', 'files_written', 'phase', 'previous_id',
                'result', 'runtime_state', 'service_restarted'];
            sort($expected);
            if ($keys !== $expected ||
                ($receipt['result'] ?? null) !==
                    'original-found-prepared-pristine-restored' ||
                ($receipt['phase'] ?? null) !== 'restored' ||
                !is_string($receipt['previous_id'] ?? null) ||
                !preg_match('/^[a-f0-9]{32}$/D', $receipt['previous_id']) ||
                !in_array($receipt['runtime_state'] ?? null, ['ready', 'stopped'], true) ||
                ($receipt['config_saved'] ?? null) !== false ||
                ($receipt['files_written'] ?? null) !== false ||
                ($receipt['service_restarted'] ?? null) !== false) {
                throw new \RuntimeException('Unqualified original found pristine terminal receipt');
            }
            $again = $factory()->getNodes();
            if (!is_array($again) ||
                !hash_equals($base, VoiceSettingsSnapshot::digest($again))) {
                throw new \RuntimeException('Native Config changed after pristine closure');
            }
            return $receipt;
        } finally {
            $config->unlock();
        }
    }

    /**
     * Classify only the original ordinary shared model image after interruption.
     * Equal base/candidate is deliberately ambiguous. Matching bytes are not
     * proof of a Config::save call, runtime ownership or permission to recover.
     */
    public static function classifyOrdinaryConfigImage(array $plan, array $current): array
    {
        if (($plan['result'] ?? null) !== 'prepared' ||
            !in_array($plan['page'] ?? null, ['strategies', 'voice'], true) ||
            !is_array($plan['candidate'] ?? null) ||
            !is_array($plan['changed_fields'] ?? null) ||
            !is_string($plan['dependencies'] ?? null) ||
            !preg_match('/^[a-f0-9]{64}$/D', $plan['dependencies']) ||
            array_key_exists('found_intent', $plan) ||
            array_key_exists('found_batch', $plan)) {
            throw new \RuntimeException('Unqualified ordinary cold Config plan');
        }
        $base = $plan['dependencies'];
        $candidate = VoiceSettingsSnapshot::digest($plan['candidate']);
        $observed = VoiceSettingsSnapshot::digest($current);
        $enabled = $current['general']['enabled'] ?? null;
        if (!in_array($enabled, ['0', '1'], true)) {
            throw new \RuntimeException('Unqualified ordinary cold enabled image');
        }
        $isBase = hash_equals($base, $observed);
        $isCandidate = hash_equals($candidate, $observed);
        if (!$isBase && !$isCandidate) {
            throw new \RuntimeException('Foreign ordinary cold Config image');
        }
        return [
            'result' => 'read-only-ordinary-config-classification',
            'image' => $isBase && $isCandidate ? 'base-equals-candidate'
                : ($isCandidate ? 'candidate-image' : 'base-image'),
            'base' => $base,
            'candidate' => $candidate,
            'snapshot' => $observed,
            'enabled' => $enabled,
            'commit_authorized' => false,
            'restore_authorized' => false,
            'save_attested' => false,
            'runtime_attested' => false,
        ];
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
        $action = $argv[1] ?? '';
        $foundActions = ['found-cold', 'found-recover-prepared', 'found-save', 'found-recover',
            'found-runtime-activating', 'found-runtime-activated', 'found-runtime-config-saved',
            'found-runtime-epoch-finalizing', 'found-runtime-committed'];
        $found = in_array($action, $foundActions, true);
        $queueFd = null;
        if (in_array($action, ['found-recover', 'ordinary-restore-finish'], true) &&
            count($argv) === 5 &&
            preg_match('/^--queue-fd=([1-9][0-9]{0,3})$/D', $argv[4], $matches) === 1) {
            $queueFd = (int)$matches[1];
        }
        if (count($argv) !== ($action === 'found-save' || $queueFd !== null ? 5 : 4) ||
            !in_array($action, ['preflight', 'save', 'saved', 'ordinary-cold', 'ordinary-restore-finish', ...$foundActions], true) ||
            !in_array($argv[3], $found ? ['strategies'] : ['voice', 'strategies'], true)) {
            fwrite(STDERR, "usage: shared_apply_config.php preflight|save ID voice|strategies\n");
            return 64;
        }
        $queueStream = null;
        try {
            if (PHP_OS_FAMILY !== 'BSD' || SharedApplyLifecycleLock::effectiveUid() !== 0) {
                throw new \RuntimeException('Root OPNsense native Config required');
            }
            SharedApplyLifecycleLock::assertHeld();
            if ($queueFd !== null) {
                $queueStream = self::openOriginalFoundQueue($queueFd);
            }
            if ($found || in_array($action, ['ordinary-cold', 'ordinary-restore-finish', 'saved'], true)) {
                // Core may repair unreadable Config from a backup on load.
                // A recovery reader must not trigger such implicit mutation.
                self::requireReadableConfig();
            }
            require_once('script/load_phalcon.php');
            $plan = self::readPlan($argv[2], self::ROOT, 0);
            if ($plan['page'] !== $argv[3]) {
                throw new \InvalidArgumentException('Stored native Apply page differs from request');
            }
            $config = \OPNsense\Core\Config::getInstance();
            $factory = static fn() => new \OPNsense\Zapret\Zapret();
            if ($action === 'found-save') {
                if (!in_array($argv[4], ['0', '1'], true) ||
                    ($argv[4] === '1' &&
                     (string)($plan['candidate']['general']['enabled'] ?? '') !== '1')) {
                    throw new \InvalidArgumentException('Invalid planned found runtime mode');
                }
                $result = self::saveFoundNative($plan, $argv[2], $argv[4], $config, $factory);
                echo self::postSaveReceipt($result);
                return 0;
            }
            if ($argv[1] === 'found-cold') {
                $joint = self::inspectFoundColdNative(
                    $plan, $argv[2], $config, $factory);
                echo json_encode($joint, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
                return 0;
            }
            if ($argv[1] === 'found-recover-prepared') {
                $receipt = self::recoverFoundPreparedNative(
                    $plan, $argv[2], $config, $factory);
                echo json_encode($receipt, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
                return 0;
            }
            if ($found) {
                echo self::postSaveReceipt(self::foundPhaseNative(
                    $action, $argv[2], $config, $factory, $queueStream
                ));
                return 0;
            }
            if ($action === 'ordinary-restore-finish') {
                // The outer original FD9 caller borrowed P2a first if
                // necessary. Keep Config locked during the SAME WAL fsync.
                $config->lock();
                try {
                    self::requireReadableConfig();
                    $image = self::classifyOrdinaryConfigImage($plan, $factory()->getNodes());
                    if (!in_array($image['image'], ['base-image', 'base-equals-candidate'], true) ||
                        self::readPlan($argv[2], self::ROOT, 0) !== $plan ||
                        self::classifyOrdinaryConfigImage($plan, $factory()->getNodes()) !== $image) {
                        throw new \RuntimeException('Original ordinary restore Config changed');
                    }
                    $reply = self::originalFoundLockedFileEvidence(
                        $config, $argv[2], 'finish-ordinary-restore-locked',
                        $image['snapshot'], null, null, $queueStream);
                    if ($reply !== ['result'=>'original-bound-cold-restored', 'id'=>$argv[2]] ||
                        self::classifyOrdinaryConfigImage($plan, $factory()->getNodes()) !== $image) {
                        throw new \RuntimeException('Original ordinary restore receipt changed');
                    }
                    self::requireReadableConfig();
                } finally {
                    $config->unlock();
                }
                echo json_encode($reply, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
                return 0;
            }
            if ($action === 'ordinary-cold') {
                // Internal original FD9 reader, not a configd action. The
                // caller checks the exact bound journal and both root pins.
                $config->lock();
                try {
                    self::requireReadableConfig();
                    $result = self::classifyOrdinaryConfigImage($plan, $factory()->getNodes());
                    $again = self::classifyOrdinaryConfigImage($plan, $factory()->getNodes());
                    if ($again !== $result || self::readPlan($argv[2], self::ROOT, 0) !== $plan) {
                        throw new \RuntimeException('Original ordinary cold Config changed');
                    }
                    self::requireReadableConfig();
                    SharedApplyLifecycleLock::assertHeld();
                } finally {
                    $config->unlock();
                }
                echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES), "\n";
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
        } finally {
            if (is_resource($queueStream)) {
                fclose($queueStream);
            }
        }
    }
}

if (PHP_SAPI === 'cli' && isset($argv) &&
    realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(SharedApplyConfigWorker::main($argv));
}
