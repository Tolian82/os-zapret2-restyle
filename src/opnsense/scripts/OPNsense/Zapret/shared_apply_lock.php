<?php
/**
 * Attest original Zapret2 FD9, without any new runtime lock or Config writer.
 */
namespace OPNsense\Zapret\Native;

final class SharedApplyLifecycleLock
{
    private const LOCK = '/var/run/zapret2-lifecycle.lock';

    /**
     * OPNsense core PHP does not include the optional POSIX extension.
     * Use base /usr/bin/id without shell expansion; fail closed on malformed
     * output, non-zero status, missing PHP process support or missing binary.
     */
    public static function effectiveUid(): int
    {
        if (!\function_exists('proc_open') || !\is_executable('/usr/bin/id')) {
            throw new \RuntimeException('Native effective UID verification unavailable');
        }
        $pipes = [];
        $process = @\proc_open(
            ['/usr/bin/id', '-u'],
            [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
            $pipes,
            null,
            ['PATH' => '/usr/bin:/bin']
        );
        if (!\is_resource($process)) {
            throw new \RuntimeException('Native effective UID verification failed');
        }
        \fclose($pipes[0]);
        $output = \stream_get_contents($pipes[1], 32);
        \fclose($pipes[1]);
        \fclose($pipes[2]);
        $status = \proc_close($process);
        if ($status !== 0 || !\is_string($output) ||
            !\preg_match('/^(0|[1-9][0-9]{0,9})\n$/D', $output)) {
            throw new \RuntimeException('Native effective UID verification refused');
        }
        return (int)\trim($output);
    }

    /** Non-native path/platform override may be used ONLY by isolated CI. */
    public static function assertHeld(bool $nativeOnly = true, ?string $path = null): void
    {
        if ($nativeOnly && (PHP_OS_FAMILY !== 'BSD' || self::effectiveUid() !== 0 ||
            ($path !== null && $path !== self::LOCK))) {
            throw new \RuntimeException('Shared Apply requires native FreeBSD root FD9');
        }
        $path = $nativeOnly ? self::LOCK : ($path ?? self::LOCK);
        $fd = @fopen('php://fd/9', 'rb');
        if (!is_resource($fd)) {
            throw new \RuntimeException('Original lifecycle FD9 is missing');
        }
        try {
            $held = @fstat($fd);
            $named = @lstat($path);
            if (!is_array($held) || !is_array($named) ||
                ($held['mode'] & 0170000) !== 0100000 ||
                ($named['mode'] & 0170000) !== 0100000 ||
                $held['dev'] !== $named['dev'] || $held['ino'] !== $named['ino'] ||
                $named['uid'] !== ($nativeOnly ? 0 : self::effectiveUid()) ||
                ($named['mode'] & 0022) !== 0 || is_link($path)) {
                throw new \RuntimeException('Foreign native lifecycle descriptor');
            }
            $probe = @fopen($path, 'r+b');
            if (!is_resource($probe)) {
                throw new \RuntimeException('Cannot probe lifecycle lock');
            }
            try {
                $current = @fstat($probe);
                if (!is_array($current) || $current['dev'] !== $named['dev'] ||
                    $current['ino'] !== $named['ino']) {
                    throw new \RuntimeException('Lifecycle lock inode changed');
                }
                // Independent file description: EXCLUSIVE must be blocked by
                // original lockf -s -t timeout 9 in zapret_service.sh.
                if (@flock($probe, LOCK_EX | LOCK_NB)) {
                    flock($probe, LOCK_UN);
                    throw new \RuntimeException('Original lifecycle FD9 not locked');
                }
            } finally {
                fclose($probe);
            }
        } finally {
            fclose($fd);
        }
    }
}
