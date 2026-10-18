<?php

/**
 * Build the actual OPNsense config.xml candidate WITHOUT modifying Config.
 *
 * This is NOT a persistence/Apply mechanism. The caller holds Config::lock(),
 * has verified the optimistic Voice snapshot and has run
 * VoiceApplyCandidate::prepare(). Never serialize the MVC model back to the
 * singleton just to obtain XML: doing so would mutate the active document
 * before the native FD9 cutover owns Config, IPFW and runtime together.
 */
namespace OPNsense\Zapret\Api;

require_once __DIR__ . '/VoiceModelValues.php';

final class VoiceCandidateXml
{
    private const SERVICES = ['telegram', 'discord', 'x', 'sip', 'custom'];
    private const MAX_XML_BYTES = 16 * 1048576;

    private static function allowed(string $scope): array
    {
        if ($scope === 'strategies') {
            // Exactly the Strategies form whitelist; Voice IPSETs other than
            // shared Telegram and all native Voice fields are foreign here.
            $mapping = [
                'general' => ['enabled', 'waninterface', 'divertport'],
                'strategy' => ['trafficargs', 'extraargs'],
                'hostlist' => [
                    'mode', 'youtubedomains', 'telegramips',
                    'userdomains', 'excludedomains',
                ],
            ];
            $allowed = [];
            foreach ($mapping as $group => $fields) {
                foreach ($fields as $field) {
                    $allowed[$group . '.' . $field] = [$group, $field];
                }
            }
            return $allowed;
        }
        if ($scope !== 'voice') {
            throw new \InvalidArgumentException('Unknown shared candidate scope');
        }
        // Saved legacy Voice WAN is read-only and has no Voice write authority.
        $allowed = [];
        foreach (self::SERVICES as $service) {
            $allowed['voice.' . $service . '.enabled'] = ['voice', $service, 'enabled'];
            $allowed['voice.' . $service . '.args'] = ['voice', $service, 'args'];
            $allowed['hostlist.' . $service . 'ips'] = ['hostlist', $service . 'ips'];
        }
        return $allowed;
    }

    private static function child(\DOMDocument $doc, \DOMElement $parent, string $name, bool $create): ?\DOMElement
    {
        $matches = [];
        foreach ($parent->childNodes as $node) {
            if ($node instanceof \DOMElement && $node->nodeName === $name) {
                $matches[] = $node;
            }
        }
        if (count($matches) > 1) {
            throw new \InvalidArgumentException('Ambiguous native Voice configuration path');
        }
        if ($matches === []) {
            if (!$create) {
                return null;
            }
            $new = $doc->createElement($name);
            $parent->appendChild($new);
            return $new;
        }
        return $matches[0];
    }

    private static function value(array $model, array $path): string
    {
        $source = $model;
        foreach ($path as $key) {
            if (!is_array($source) || !array_key_exists($key, $source)) {
                throw new \InvalidArgumentException('Shared model candidate is incomplete');
            }
            $source = $source[$key];
        }
        // Native getNodes() emits a selected-option dictionary for dropdowns.
        // Resolve it without changing the original, full OPNsense model.
        return VoiceModelValues::text($source);
    }

    /**
     * Full original opnsense XML + approved Voice-only changes.
     * Every byte in the original Config remains in memory; no disk or API
     * side effects. The only output is a separate candidate XML string.
     */
    public static function render(
        string $activeXml, array $previous, array $candidate, array $changedFields
    ): string {
        return self::renderScoped($activeXml, $previous, $candidate, $changedFields, 'voice');
    }

    /** The other form renders the same complete OPNsense XML without Voice writes. */
    public static function renderStrategies(
        string $activeXml, array $previous, array $candidate, array $changedFields
    ): string {
        return self::renderScoped($activeXml, $previous, $candidate, $changedFields, 'strategies');
    }

    private static function renderScoped(
        string $activeXml, array $previous, array $candidate, array $changedFields,
        string $scope
    ): string {
        if ($activeXml === '' || strlen($activeXml) > self::MAX_XML_BYTES ||
            preg_match('/<!\s*(?:DOCTYPE|ENTITY)\b/i', $activeXml)
        ) {
            throw new \InvalidArgumentException('Unsafe active Config XML');
        }
        $allowed = self::allowed($scope);
        $expected = [];
        foreach ($changedFields as $field) {
            if (!is_string($field) || !isset($allowed[$field]) ||
                isset($expected[$field])) {
                throw new \InvalidArgumentException('Foreign or repeated form field');
            }
            $expected[$field] = true;
        }

        // The model overlay must account for EVERY change, including fields
        // of another page; silent global/Strategy edits are forbidden here.
        $rebuilt = $previous;
        foreach (array_keys($allowed) as $field) {
            $parts = $allowed[$field];
            $before = self::value($previous, $parts);
            $after = self::value($candidate, $parts);
            if (str_replace(["\r\n", "\r"], "\n", $before) !==
                str_replace(["\r\n", "\r"], "\n", $after)) {
                if (!isset($expected[$field])) {
                    throw new \InvalidArgumentException('Shared change map omits candidate field');
                }
            } elseif (isset($expected[$field])) {
                throw new \InvalidArgumentException('Shared change map includes unchanged field');
            }
            $pointer = &$rebuilt;
            foreach ($parts as $part) {
                $pointer = &$pointer[$part];
            }
            $pointer = $after;
            unset($pointer);
        }
        if ($rebuilt !== $candidate) {
            throw new \InvalidArgumentException('Candidate changes fields outside the owning form');
        }

        $xml = new \DOMDocument('1.0', 'UTF-8');
        $xml->resolveExternals = false;
        $xml->substituteEntities = false;
        $prior = libxml_use_internal_errors(true);
        try {
            if (!$xml->loadXML($activeXml, LIBXML_NONET) ||
                $xml->doctype !== null ||
                !$xml->documentElement ||
                $xml->documentElement->tagName !== 'opnsense'
            ) {
                throw new \InvalidArgumentException('Invalid active Config XML');
            }
        } finally {
            libxml_clear_errors();
            libxml_use_internal_errors($prior);
        }
        if (!$expected) {
            return $activeXml;
        }
        $root = $xml->documentElement;
        $opnsense = self::child($xml, $root, 'OPNsense', false);
        if ($opnsense === null) {
            throw new \InvalidArgumentException('Missing OPNsense config mount');
        }
        $zapret = self::child($xml, $opnsense, 'Zapret', false);
        if ($zapret === null) {
            throw new \InvalidArgumentException('Missing Zapret model mount');
        }
        // OPNsense getNodes() returns default TextField values even when
        // config.xml has no corresponding leaf. A checkbox-only ON change
        // used to omit default STUN args from detached XML; Python then
        // rejected the missing --filter-udp before runtime build.
        // Materialize only enabled services' already-validated Voice fields.
        // The ownership and changed-field checks above still govern inputs.
        $materialized = $expected;
        if ($scope === 'voice') {
            foreach (self::SERVICES as $service) {
                if (self::value($candidate, ['voice', $service, 'enabled']) === '1') {
                    $materialized['voice.' . $service . '.args'] = true;
                    $materialized['hostlist.' . $service . 'ips'] = true;
                }
            }
        }
        foreach ($materialized as $field => $_) {
            $path = $allowed[$field];
            $node = $zapret;
            foreach ($path as $part) {
                $node = self::child($xml, $node, $part, true);
            }
            if ($node->hasAttributes() || $node->getElementsByTagName('*')->length > 0) {
                throw new \InvalidArgumentException('Unsafe nested Voice leaf');
            }
            while ($node->firstChild !== null) {
                $node->removeChild($node->firstChild);
            }
            $node->appendChild($xml->createTextNode(self::value($candidate, $path)));
        }
        $serialized = $xml->saveXML();
        if (!is_string($serialized) || strlen($serialized) > self::MAX_XML_BYTES) {
            throw new \InvalidArgumentException('Shared candidate XML serialization failed');
        }
        $verify = new \DOMDocument();
        if (!$verify->loadXML($serialized, LIBXML_NONET) || $verify->doctype !== null) {
            throw new \InvalidArgumentException('Shared candidate XML is not well formed');
        }
        return $serialized;
    }
}
