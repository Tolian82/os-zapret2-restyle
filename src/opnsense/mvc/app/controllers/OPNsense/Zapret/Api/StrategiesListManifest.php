<?php
/**
 * TZ6v3 Strategies-only FormData + JSON list-manifest validation.
 *
 * This validates the unprivileged HTTP declaration against the *same* native
 * Config snapshot used by the original Settings Apply. It never reads/writes
 * discovered source files, is not a Config writer and cannot authorize FD9.
 */
namespace OPNsense\Zapret\Api;

require_once __DIR__ . '/StrategiesHostlistCatalog.php';
require_once __DIR__ . '/VoiceSettingsSnapshot.php';

final class StrategiesListManifest
{
    private const MAX_JSON = 8192;
    private const MAX_MANUAL = 4 * 1024 * 1024;
    private const SHA = '/^[a-f0-9]{64}$/D';

    /**
     * @param string|null $raw Multipart text part; null supports the existing
     *                         first-setup/native clients that lack a read baseline.
     * @param array $saved Same Config-locked original Model read as Apply.
     * @param array $submitted Same allowlisted model POST as Apply.
     */
    public static function validate(
        $raw, array $saved, array $submitted, bool $foundUploaded
    ): void {
        if ($raw === null) {
            // The original original-FD9/Telegram/found-intent gates remain in
            // force for legacy clients and pre-initialized WAN-only forms.
            return;
        }
        if (!is_string($raw) || $raw === '' || strlen($raw) > self::MAX_JSON) {
            throw new \InvalidArgumentException('Invalid Strategies list manifest length');
        }
        try {
            $payload = json_decode($raw, true, 12, JSON_THROW_ON_ERROR);
        } catch (\JsonException $e) {
            throw new \InvalidArgumentException('Invalid Strategies list manifest JSON', 0, $e);
        }
        if (!is_array($payload) ||
            array_keys($payload) !== ['schema_version', 'kind', 'config_revision', 'sources'] ||
            $payload['schema_version'] !== 1 ||
            $payload['kind'] !== 'tz6v3-strategies-list-manifest' ||
            !is_string($payload['config_revision']) ||
            preg_match(self::SHA, $payload['config_revision']) !== 1 ||
            !is_array($payload['sources']) ||
            array_keys($payload['sources']) !== StrategiesHostlistCatalog::editorIds()) {
            throw new \InvalidArgumentException('Invalid Strategies list manifest schema');
        }
        $changedAny = false;
        $changedFound = false;
        foreach (StrategiesHostlistCatalog::sources() as $id => $spec) {
            $row = $payload['sources'][$id];
            $manual = $spec['owner'] === 'config';
            $required = $manual
                ? ['owner', 'status', 'revision', 'length_bytes', 'changed']
                : ['owner', 'status', 'revision', 'changed'];
            if (!is_array($row) || array_keys($row) !== $required ||
                $row['owner'] !== $spec['owner'] ||
                !is_bool($row['changed']) ||
                !is_string($row['revision']) ||
                preg_match(self::SHA, $row['revision']) !== 1 ||
                !in_array($row['status'],
                    $manual ? ['empty', 'populated'] :
                        ($spec['owner'] === 'shared-auto'
                            ? ['missing', 'empty', 'populated'] : ['empty', 'populated']), true)) {
                throw new \InvalidArgumentException('Invalid Strategies list source manifest');
            }
            $changedAny = $changedAny || $row['changed'];
            if ($manual) {
                $field = $spec['model_field'];
                $original = $saved['hostlist'][$field] ?? '';
                if (!is_int($row['length_bytes']) ||
                    $row['length_bytes'] < 0 ||
                    $row['length_bytes'] > self::MAX_MANUAL) {
                    throw new \InvalidArgumentException('Invalid manual source byte length');
                }
                // A WAN-only/non-list Apply must not become dependent on an
                // unrelated manual list changed in another browser tab. The
                // unchanged manual HTTP field is absent and cannot overwrite
                // that newer source. Enforce the exact saved baseline only
                // when this particular manual list is actually being edited.
                if ($row['changed'] &&
                    (!is_string($original) ||
                     strlen($original) > self::MAX_MANUAL ||
                     $row['length_bytes'] !== strlen($original) ||
                     $row['status'] !== ($original === '' ? 'empty' : 'populated') ||
                     !hash_equals(hash('sha256', "present\0" . $original), $row['revision']))) {
                    throw new \InvalidArgumentException('Stale Strategies manual source');
                }
                $sent = is_array($submitted['hostlist'] ?? null) &&
                    array_key_exists($field, $submitted['hostlist']);
                // The HTTP shape itself must agree with the declaration:
                // absent means unchanged, present means real user bytes.
                if ($row['changed'] !== $sent ||
                    ($sent && (!is_string($submitted['hostlist'][$field]) ||
                        strlen($submitted['hostlist'][$field]) > self::MAX_MANUAL))) {
                    throw new \InvalidArgumentException('Strategies manual edit manifest mismatch');
                }
            } else {
                if ($row['changed']) {
                    $changedFound = true;
                }
                if ($row['status'] === 'missing' &&
                    $row['revision'] !== hash('sha256', "missing\0")) {
                    throw new \InvalidArgumentException('Invalid missing shared source attestation');
                }
            }
        }
        if ($changedFound && !$foundUploaded) {
            throw new \InvalidArgumentException('Missing changed discovered list upload');
        }
        // Only a true source edit needs this additional entire-Config stale
        // check. Unchanged WAN-only/non-list forms keep their old behavior.
        if ($changedAny && !hash_equals(
            VoiceSettingsSnapshot::digest($saved), $payload['config_revision']
        )) {
            throw new \InvalidArgumentException('Strategies source Config changed; reload');
        }
    }
}
