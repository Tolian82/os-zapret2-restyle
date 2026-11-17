<?php
/**
 * TZ6v2: one bounded transport from PHP's existing multipart upload into
 * original native FD9 candidate staging. NOT another Config/target writer.
 */
namespace OPNsense\Zapret\Native;

final class SharedApplyFoundIntent
{
    private const MAX_TEXT = 40960;
    private const MAX_JSON = 320 * 1024;
    private const SHA = '/^[a-f0-9]{64}$/D';
    private const PYTHON = '/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh';
    private const READER = '/usr/local/opnsense/scripts/OPNsense/Zapret/backend/shared_apply_found_upload.py';

    /** Structural transport only: domain semantics belong to Python P1. */
    public static function validateJson(string $raw, string $configRevision): array
    {
        if (strlen($raw) > self::MAX_JSON ||
            preg_match(self::SHA, $configRevision) !== 1) {
            throw new \InvalidArgumentException('Unqualified found intent length/revision');
        }
        try {
            $payload = json_decode($raw, true, 12, JSON_THROW_ON_ERROR);
        } catch (\JsonException $error) {
            throw new \InvalidArgumentException('Invalid found intent JSON', 0, $error);
        }
        if (!is_array($payload) || array_keys($payload) !==
            ['schema_version', 'kind', 'config_revision', 'sources'] ||
            $payload['schema_version'] !== 1 ||
            $payload['kind'] !== 'tz6v2-found-form-intent' ||
            !is_string($payload['config_revision']) ||
            !hash_equals($configRevision, $payload['config_revision']) ||
            !is_array($payload['sources']) ||
            array_keys($payload['sources']) !== ['youtube', 'user', 'auto']) {
            throw new \InvalidArgumentException('Unqualified found intent schema or Config');
        }
        foreach ($payload['sources'] as $name => $source) {
            if (!is_array($source) || array_keys($source) !== ['base', 'draft'] ||
                !is_array($source['base']) ||
                array_keys($source['base']) !== ['status', 'revision', 'content'] ||
                !is_string($source['base']['status']) ||
                !is_string($source['base']['content']) ||
                !is_string($source['draft']) ||
                strlen($source['base']['content']) > self::MAX_TEXT ||
                strlen($source['draft']) > self::MAX_TEXT ||
                !is_string($source['base']['revision']) ||
                preg_match(self::SHA, $source['base']['revision']) !== 1) {
                throw new \InvalidArgumentException('Unqualified found source shape');
            }
            $status = $source['base']['status'];
            if (!in_array($status, $name === 'auto'
                    ? ['missing', 'empty', 'populated'] : ['empty', 'populated'], true) ||
                ($status !== 'populated' && $source['base']['content'] !== '') ||
                ($status === 'populated' && $source['base']['content'] === '')) {
                throw new \InvalidArgumentException('Unqualified found source status');
            }
            $revision = hash('sha256', $status === 'missing'
                ? "missing\0" : "present\0" . $source['base']['content']);
            if (!hash_equals($revision, $source['base']['revision'])) {
                throw new \InvalidArgumentException('Unqualified found source revision');
            }
        }
        return ['schema_version' => 1, 'kind' => 'tz6v2-found-intent',
                'sources' => $payload['sources'],
                'config_revision' => $configRevision,
                'cross_source_validated' => false, 'commit_authorized' => false];
    }

    public static function metadata(array $data): array
    {
        if (array_keys($data) !== ['path', 'size', 'sha256', 'owner_uid'] ||
            !is_string($data['path']) ||
            preg_match('#^/var/lib/php/tmp/php[A-Za-z0-9]{6,16}$#D', $data['path']) !== 1 ||
            !is_int($data['size']) || $data['size'] < 1 ||
            $data['size'] > self::MAX_JSON ||
            !is_string($data['sha256']) ||
            preg_match(self::SHA, $data['sha256']) !== 1 ||
            !is_int($data['owner_uid']) || $data['owner_uid'] < 0) {
            throw new \InvalidArgumentException('Unqualified native PHP upload metadata');
        }
        return $data;
    }

    /**
     * Accept only a real PHP multipart file in this very HTTP request.
     * Never trust client-supplied temp paths or file metadata in POST.
     * This structural first gate is portable; the second checks PHP's
     * actual uploaded-file table and pins file content.
     */
    public static function httpFileShape(array $files): ?array
    {
        if ($files === []) {
            return null; // ordinary Strategies Apply is unchanged
        }
        if (array_keys($files) !== ['found_intent'] ||
            !is_array($entry = $files['found_intent'])) {
            throw new \InvalidArgumentException('Untrusted found upload field');
        }
        $allowed = ['name', 'type', 'tmp_name', 'error', 'size', 'full_path'];
        foreach (array_keys($entry) as $key) {
            if (!in_array($key, $allowed, true)) {
                throw new \InvalidArgumentException('Unexpected PHP upload shape');
            }
        }
        foreach (['name', 'tmp_name', 'error', 'size'] as $key) {
            if (!array_key_exists($key, $entry)) {
                throw new \InvalidArgumentException('Incomplete PHP upload');
            }
        }
        if ($entry['name'] !== 'found-intent.json' ||
            !is_string($entry['tmp_name']) ||
            !is_int($entry['error']) || $entry['error'] !== UPLOAD_ERR_OK ||
            !is_int($entry['size']) || $entry['size'] < 1 ||
            $entry['size'] > self::MAX_JSON ||
            (isset($entry['full_path']) &&
             $entry['full_path'] !== 'found-intent.json') ||
            (isset($entry['type']) && !is_string($entry['type'])) ||
            preg_match('#^/var/lib/php/tmp/php[A-Za-z0-9]{6,16}$#D',
                $entry['tmp_name']) !== 1) {
            throw new \InvalidArgumentException('Untrusted native PHP upload');
        }
        return $entry;
    }

    /** Read once within the original authenticated HTTP request. No writes. */
    public static function uploadedMetadata(array $files): ?array
    {
        $file = self::httpFileShape($files);
        if ($file === null) {
            return null;
        }
        $path = $file['tmp_name'];
        if (!is_uploaded_file($path)) {
            throw new \InvalidArgumentException('Not a native PHP upload');
        }
        $same = static function (array $left, array $right): bool {
            foreach (['dev', 'ino', 'mode', 'nlink', 'uid',
                      'size', 'mtime', 'ctime'] as $key) {
                if (($left[$key] ?? null) !== ($right[$key] ?? null)) {
                    return false;
                }
            }
            return true;
        };
        $before = @lstat($path);
        if (!is_array($before) ||
            ($before['mode'] & 0170000) !== 0100000 ||
            ($before['mode'] & 0777) !== 0600 ||
            $before['nlink'] !== 1 ||
            $before['uid'] !== posix_geteuid() ||
            $before['size'] !== $file['size']) {
            throw new \InvalidArgumentException('Invalid native PHP upload inode');
        }
        $fp = @fopen($path, 'rb');
        if ($fp === false) {
            throw new \InvalidArgumentException('Native PHP upload unreadable');
        }
        try {
            $opened = fstat($fp);
            $bytes = stream_get_contents($fp, self::MAX_JSON + 1);
            $finished = fstat($fp);
        } finally {
            fclose($fp);
        }
        $after = @lstat($path);
        if (!is_array($opened) || !is_array($finished) ||
            !is_array($after) || !is_string($bytes) ||
            strlen($bytes) !== $file['size'] ||
            !$same($before, $opened) || !$same($before, $finished) ||
            !$same($before, $after)) {
            throw new \InvalidArgumentException('Native PHP upload changed');
        }
        // Root independently verifies owner, nofollow inode, size and SHA.
        return self::metadata([
            'path' => $path, 'size' => $file['size'],
            'sha256' => hash('sha256', $bytes), 'owner_uid' => $before['uid'],
        ]);
    }

    /** Synchronously called only by original native FD9 request stage. */
    public static function consume(array $metadata, string $configRevision): array
    {
        $data = self::metadata($metadata);
        $pipes = [];
        $process = @proc_open(
            [self::PYTHON, self::READER, $data['path'], (string)$data['size'],
             $data['sha256'], (string)$data['owner_uid']],
            [0 => ['file', '/dev/null', 'r'], 1 => ['pipe', 'w'],
             2 => ['file', '/dev/null', 'a']],
            $pipes, null, ['LC_ALL' => 'C', 'PATH' => '/usr/bin:/bin:/usr/local/bin']
        );
        if (!is_resource($process)) {
            throw new \RuntimeException('Native found intent reader unavailable');
        }
        $raw = stream_get_contents($pipes[1], self::MAX_JSON + 1);
        fclose($pipes[1]);
        $status = proc_close($process);
        if (!is_string($raw) || $status !== 0 || strlen($raw) !== $data['size']) {
            throw new \RuntimeException('Native found intent read refused');
        }
        return self::validateJson($raw, $configRevision);
    }
}
