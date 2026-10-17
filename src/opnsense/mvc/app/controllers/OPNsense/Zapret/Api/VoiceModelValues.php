<?php

/**
 * Convert an OPNsense MVC list field's display options to its saved value.
 * BaseListField::getNodeData() returns options with "selected" markers;
 * Config XML, native Voice Apply and WAN comparisons need the selected key.
 * Never cast the options array to the literal string "Array".
 */
namespace OPNsense\Zapret\Api;

final class VoiceModelValues
{
    public static function text($value): string
    {
        if (is_string($value)) {
            return $value;
        }
        if (!is_array($value) || $value === []) {
            throw new \InvalidArgumentException('Shared model candidate is not normalized');
        }
        $selected = [];
        foreach ($value as $name => $option) {
            if (!is_array($option) || !array_key_exists('selected', $option) ||
                !in_array($option['selected'], [0, 1, false, true, '0', '1'], true)
            ) {
                throw new \InvalidArgumentException('Invalid shared model option');
            }
            if ($option['selected'] == 1) {
                $selected[] = (string)$name;
            }
        }
        if (count($selected) !== 1) {
            throw new \InvalidArgumentException('Ambiguous shared model option');
        }
        return $selected[0];
    }
}
