<?php
/**
 * Read-only full native Strategies candidate XML under ORIGINAL lifecycle FD9.
 * Only standard output is a private pipe to the P5c Python preview worker.
 * Config is never serialized back to the singleton or saved.
 */
namespace OPNsense\Zapret\Native;

require_once __DIR__ . '/shared_apply_request.php';
require_once __DIR__ . '/apply_settings.php';

use OPNsense\Zapret\Api\SettingsApply;
use OPNsense\Zapret\Api\SharedApplyEnvelope;

final class StrategyPreviewCandidate
{
    private const MAX_ENVELOPE = 65536;
    private const MAX_XML = 16777216;

    public static function produce(string $encoded): string
    {
        $request = SharedApplyRequest::decode($encoded);
        if ($request['page'] !== 'strategies') {
            throw new \InvalidArgumentException('Only Strategies preview is accepted');
        }
        $config = \OPNsense\Core\Config::getInstance();
        $config->lock();
        try {
            $model = new \OPNsense\Zapret\Zapret();
            $current = $model->getNodes();
            $fields = SharedApplyEnvelope::expandStrategies($request['fields'], $current);
            $plan = SettingsApply::prepareStrategies(
                $current, $fields, $request['sync']['telegramips_baseline']
            );
            if (($plan['result'] ?? null) !== 'prepared') {
                throw new \InvalidArgumentException('Strategies preview candidate refused');
            }
            // Existing one-model validator, on an in-memory model only.
            SharedConfigCommit::validateOwnedModelFields(
                $model, $plan['candidate'], $plan['changed_fields']
            );
            $activeXml = file_get_contents('/conf/config.xml');
            if (!is_string($activeXml)) {
                throw new \RuntimeException('Native Config unavailable');
            }
            $xml = SettingsApply::renderCandidateXml(
                $activeXml, $current, $plan, 'strategies'
            );
            if (strlen($xml) === 0 || strlen($xml) > self::MAX_XML) {
                throw new \InvalidArgumentException('Preview XML size invalid');
            }
            return $xml;
        } finally {
            $config->unlock();
        }
    }

    public static function main(array $argv): int
    {
        if (count($argv) !== 1) {
            return 64;
        }
        try {
            if (PHP_OS_FAMILY !== 'BSD' || SharedApplyLifecycleLock::effectiveUid() !== 0) {
                throw new \RuntimeException('Native OPNsense root required');
            }
            SharedApplyLifecycleLock::assertHeld();
            $encoded = stream_get_contents(STDIN, self::MAX_ENVELOPE + 1);
            if (!is_string($encoded) || strlen($encoded) > self::MAX_ENVELOPE) {
                throw new \InvalidArgumentException('Invalid preview request size');
            }
            require_once('script/load_phalcon.php');
            $xml = self::produce($encoded);
            if (fwrite(STDOUT, $xml) !== strlen($xml)) {
                throw new \RuntimeException('Preview pipe write failed');
            }
            return 0;
        } catch (\Throwable $error) {
            // Never log or return user fields, XML, or native stack traces.
            fwrite(STDERR, "P5C_PREVIEW_CANDIDATE_REFUSED\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' && isset($argv) && realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(StrategyPreviewCandidate::main($argv));
}
