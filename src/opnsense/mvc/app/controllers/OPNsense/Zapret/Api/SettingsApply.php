<?php

/**
 * Shared, side-effect-free candidate boundary for the Strategies and Voice
 * forms. The public controllers keep their own field whitelists, but both
 * must submit a whole-model candidate to the same future native Apply worker.
 *
 * A dependency token is a witness for the generation used to prepare the
 * candidate, never an authorization to save or activate it. The privileged
 * worker must re-read the native Config under FD9 and a fresh Config lock,
 * repeat this comparison, then revalidate its full runtime before mutation.
 */
namespace OPNsense\Zapret\Api;

require_once __DIR__ . '/StrategySettingsPayload.php';
require_once __DIR__ . '/VoiceSettingsPayload.php';
require_once __DIR__ . '/VoiceApplyCandidate.php';
require_once __DIR__ . '/VoiceSettingsSnapshot.php';
require_once __DIR__ . '/VoiceCandidateXml.php';
require_once __DIR__ . '/VoiceModelValues.php';
require_once __DIR__ . '/WanRequirement.php';

final class SettingsApply
{
    private static function sameText(string $left, string $right): bool
    {
        return str_replace(["\r\n", "\r"], "\n", $left) ===
            str_replace(["\r\n", "\r"], "\n", $right);
    }

    /**
     * Build a full Strategies candidate without changing Voice or any other
     * fields outside the Strategies whitelist. The shared Telegram IPSET
     * requires the existing browser baseline as an additional stale-tab guard.
     */
    public static function prepareStrategies(array $previous, array $submitted, $telegramBaseline): array
    {
        StrategySettingsPayload::requireFreshTelegram($previous, $telegramBaseline);
        $candidate = StrategySettingsPayload::overlay($previous, $submitted);
        $changed = [];
        foreach ($submitted as $group => $fields) {
            foreach ($fields as $name => $_) {
                $before = VoiceModelValues::text($previous[$group][$name] ?? '');
                $after = VoiceModelValues::text($candidate[$group][$name]);
                if (!self::sameText($before, $after)) {
                    $changed[] = $group . '.' . $name;
                } elseif (isset($previous[$group]) &&
                    array_key_exists($name, $previous[$group])) {
                    // getNodes() represents InterfaceField/OptionField as
                    // selected-option arrays, while HTML forms POST scalars.
                    // They are the SAME saved value: retain the native
                    // structure for the untouched leaf. Otherwise a no-op
                    // Apply appears to modify an unlisted model field during
                    // the strict native Config preflight.
                    $candidate[$group][$name] = $previous[$group][$name];
                }
            }
        }
        return [
            'result' => 'prepared',
            'candidate' => $candidate,
            'changed_fields' => $changed,
            'dependencies' => VoiceSettingsSnapshot::digest($previous),
        ];
    }

    /**
     * LC-06D/LC-06E: a *passive* Strategies Apply requires the upstream service
     * even if the package seeded standard YouTube strategy/hostlist defaults or
     * the user submitted edits to clear those fields. This is NOT a proof that
     * user fields are empty. Only existing native Config state is inspected.
     *
     * A single WAN-only change remains an independent no-runtime Save. A
     * START/Voice activation retains WAN-first and normal lifecycle checks.
     */
    public static function isPassiveStrategiesPlan(array $plan): bool
    {
        if (($plan['result'] ?? null) !== 'prepared' ||
            !isset($plan['changed_fields']) || !is_array($plan['changed_fields']) ||
            in_array('general.waninterface', $plan['changed_fields'], true) ||
            !isset($plan['candidate']) || !is_array($plan['candidate'])) {
            return false;
        }
        $node = $plan['candidate'];
        foreach (['general', 'strategy', 'hostlist', 'voice'] as $section) {
            if (!isset($node[$section]) || !is_array($node[$section])) {
                return false;
            }
        }
        if (!array_key_exists('enabled', $node['general'])) {
            return false;
        }
        foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
            if (!isset($node['voice'][$service]) ||
                !is_array($node['voice'][$service]) ||
                !array_key_exists('enabled', $node['voice'][$service])) {
                return false;
            }
        }
        try {
            if (VoiceModelValues::text($node['general']['enabled']) !== '0') {
                return false;
            }
            foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
                if (VoiceModelValues::text($node['voice'][$service]['enabled']) !== '0') {
                    return false;
                }
            }
        } catch (\InvalidArgumentException $error) {
            return false;
        }
        return true;
    }

    /**
     * LC-06E: inactive Strategies requests are diagnostic-only when the
     * selected WAN is unchanged. Check before overlay/validation: a native
     * clean Config has seeded YouTube data and may omit optional Voice nodes.
     */
    public static function isPassiveStrategiesRequest(array $current, array $submitted): bool
    {
        if (!isset($current['general']) || !is_array($current['general']) ||
            (isset($submitted['general']) && !is_array($submitted['general'])) ||
            WanRequirement::effectiveWan($current) !==
                WanRequirement::effectiveWan($current, $submitted)) {
            return false;
        }
        // Unknown/ambiguous enabled fields must never authorize a shortcut.
        foreach ([$current, $submitted] as $state) {
            $values = [$state['general']['enabled'] ?? null];
            foreach (['telegram', 'discord', 'x', 'sip', 'custom'] as $service) {
                $values[] = $state['voice'][$service]['enabled'] ?? null;
            }
            foreach ($values as $raw) {
                if ($raw === null) {
                    continue;
                }
                try {
                    if (!in_array(VoiceModelValues::text($raw), ['0', '1'], true)) {
                        return false;
                    }
                } catch (\InvalidArgumentException $error) {
                    return false;
                }
            }
        }
        return !WanRequirement::runtimeRequested($current) &&
            !WanRequirement::runtimeRequested($current, $submitted);
    }

    /**
     * Accept only a complete, unambiguous native setup_status receipt with
     * installed=0 and busy=0. Persisted setup.status can legitimately contain
     * ready/failed/unknown from an earlier attempt, while the real dvtws2
     * binary is absent. Do not trust missing, duplicated or busy receipts.
     */
    public static function isVerifiedMissingUpstream(string $receipt): bool
    {
        $lines = preg_split('/\R/u', trim($receipt));
        if (!is_array($lines) || count($lines) !== 5) {
            return false;
        }
        $seen = [];
        foreach ($lines as $line) {
            if (!preg_match('/^(installed|service|version|setup|busy)=(.*)$/D', $line, $m) ||
                array_key_exists($m[1], $seen)) {
                return false;
            }
            $seen[$m[1]] = $m[2];
        }
        return count($seen) === 5 &&
            $seen['installed'] === '0' &&
            $seen['service'] === 'error' &&
            $seen['version'] === '' &&
            $seen['busy'] === '0' &&
            in_array($seen['setup'], ['unknown', 'ready', 'failed'], true);
    }

    /** All five Voice services, with the original full-model snapshot gate. */
    public static function prepareVoice(array $previous, array $submitted, $snapshot): array
    {
        $plan = VoiceApplyCandidate::prepare($previous, $submitted, $snapshot);
        if (($plan['result'] ?? null) === 'prepared') {
            $plan['dependencies'] = VoiceSettingsSnapshot::digest($previous);
        }
        return $plan;
    }

    /**
     * Render one whole detached OPNsense candidate for EITHER form. The
     * whitelist is enforced a second time by the scoped XML serializer.
     * No running Config, filesystem, process or firewall write is performed.
     */
    public static function renderCandidateXml(
        string $activeXml, array $previous, array $plan, string $page
    ): string {
        self::requireUnchanged($plan, $previous);
        if (!isset($plan['candidate'], $plan['changed_fields']) ||
            !is_array($plan['candidate']) || !is_array($plan['changed_fields'])) {
            throw new \InvalidArgumentException('Incomplete shared XML candidate');
        }
        if ($page === 'voice') {
            return VoiceCandidateXml::render(
                $activeXml, $previous, $plan['candidate'], $plan['changed_fields']
            );
        }
        if ($page === 'strategies') {
            return VoiceCandidateXml::renderStrategies(
                $activeXml, $previous, $plan['candidate'], $plan['changed_fields']
            );
        }
        throw new \InvalidArgumentException('Unknown shared form');
    }


    /**
     * A native save must merge ONLY this form's changed fields into the
     * freshly loaded model, never setNodes() on an obsolete whole candidate.
     * In particular unrelated Strategy Lab settings may change meanwhile.
     * Pure precommit helper; validation, Config::save and FD9 belong to worker.
     */
    public static function mergeForCommit(array $live, array $plan, string $page): array
    {
        self::requireUnchanged($plan, $live);
        if (!in_array($page, ['voice', 'strategies'], true) ||
            !isset($plan['candidate'], $plan['changed_fields']) ||
            !is_array($plan['candidate']) || !is_array($plan['changed_fields'])) {
            throw new \InvalidArgumentException('Invalid shared commit candidate');
        }
        $submitted = [];
        $seen = [];
        foreach ($plan['changed_fields'] as $name) {
            if (!is_string($name) ||
                !preg_match('/^[a-z]+(?:\.[a-z]+){1,2}$/D', $name) ||
                isset($seen[$name])) {
                throw new \InvalidArgumentException('Malformed shared changed field');
            }
            $seen[$name] = true;
            $parts = explode('.', $name);
            $planned = $plan['candidate'];
            $before = $live;
            foreach ($parts as $part) {
                if (!is_array($planned) || !array_key_exists($part, $planned) ||
                    !is_array($before) || !array_key_exists($part, $before)) {
                    throw new \InvalidArgumentException('Incomplete changed field');
                }
                $planned = $planned[$part];
                $before = $before[$part];
            }
            // A changed native InterfaceField/OptionField has an option
            // dictionary on the live model but a scalar from the GUI.
            // Compare selected values without broadening form ownership.
            if (!is_string($planned) ||
                self::sameText(VoiceModelValues::text($before), $planned)) {
                throw new \InvalidArgumentException('Changed map contains unchanged field');
            }
            $entry = &$submitted;
            foreach ($parts as $part) {
                if (!isset($entry[$part])) {
                    $entry[$part] = [];
                }
                $entry = &$entry[$part];
            }
            $entry = $planned;
            unset($entry);
        }
        // Reuse each page's real whitelist. Do not create a second one.
        $merged = $page === 'voice'
            ? VoiceSettingsPayload::overlay($live, $submitted)
            : StrategySettingsPayload::overlay($live, $submitted);
        $expected = $plan['candidate'];
        foreach ($live as $group => $value) {
            if (!in_array($group, ['general', 'strategy', 'voice', 'hostlist'], true)) {
                $expected[$group] = $value;
            }
        }
        if ($merged !== $expected) {
            throw new \InvalidArgumentException('Candidate changes a foreign field');
        }
        return $merged;
    }

    /**
     * Re-check the entire relevant shared Zapret generation immediately
     * before the future runtime switch. An unrelated OPNsense subsystem edit
     * is not included, but changed ordinary, WAN, Voice or shared IPSET input
     * requires a fresh candidate. Never write the older full Config XML.
     */
    public static function requireUnchanged(array $plan, array $live): void
    {
        if (($plan['result'] ?? null) !== 'prepared' ||
            !isset($plan['dependencies']) || !is_string($plan['dependencies'])) {
            throw new \InvalidArgumentException('Incomplete shared Apply candidate');
        }
        VoiceSettingsSnapshot::requireFresh($live, $plan['dependencies']);
    }
}
