<?php

/**
 * TZ6v3: read-only catalogue of editable Strategies HOSTLIST sources.
 *
 * This UI/API registry does NOT replace the protected runtime target registry.
 * It has no configuration writer or OPNsense Model dependencies.
 */
namespace OPNsense\Zapret\Api;

final class StrategiesHostlistCatalog
{
    private const SOURCES = [
        'youtube_manual' => [
            'kind' => 'hostlist', 'owner' => 'config', 'target' => 'youtube',
            'storage_kind' => 'config', 'model_field' => 'youtubedomains',
        ],
        'youtube_found' => [
            'kind' => 'hostlist', 'owner' => 'auto-owned', 'target' => 'youtube',
            'storage_kind' => 'file', 'model_field' => null,
        ],
        'user_manual' => [
            'kind' => 'hostlist', 'owner' => 'config', 'target' => 'user',
            'storage_kind' => 'config', 'model_field' => 'userdomains',
        ],
        'user_found' => [
            'kind' => 'hostlist', 'owner' => 'auto-owned', 'target' => 'user',
            'storage_kind' => 'file', 'model_field' => null,
        ],
        'shared_found' => [
            'kind' => 'hostlist', 'owner' => 'shared-auto', 'target' => 'auto',
            'storage_kind' => 'file', 'model_field' => null,
        ],
    ];

    public static function sources(): array
    {
        return self::SOURCES;
    }

    public static function editorIds(): array
    {
        return array_keys(self::SOURCES);
    }

    public static function editorOwners(): array
    {
        $owners = [];
        foreach (self::SOURCES as $id => $source) {
            $owners[$id] = $source['owner'];
        }
        return $owners;
    }

    /** @return array<string,string> original model field => runtime target */
    public static function manualModelFields(): array
    {
        $fields = [];
        foreach (self::SOURCES as $source) {
            if ($source['owner'] === 'config') {
                $fields[$source['model_field']] = $source['target'];
            }
        }
        return $fields;
    }

    public static function manualTargets(): array
    {
        return array_values(self::manualModelFields());
    }

    public static function ownedTargets(): array
    {
        $targets = [];
        foreach (self::SOURCES as $source) {
            if ($source['owner'] === 'auto-owned') {
                $targets[] = $source['target'];
            }
        }
        return $targets;
    }
}
