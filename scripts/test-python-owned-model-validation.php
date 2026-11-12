<?php
/** Narrow, write-free regression for the live P1 owner failure in _42. */
require_once __DIR__ . '/../src/opnsense/scripts/OPNsense/Zapret/apply_settings.php';
use OPNsense\Zapret\Native\SharedConfigCommit;

final class PolicyTestModel {
    public array $fields = [];
    public function setNodeByReference(string $name, string $value): bool {
        $this->fields[$name] = $value;
        return true;
    }
    public function performValidation(bool $full = false): array { return []; }
}
function check(bool $ok, string $reason): void {
    if (!$ok) { fwrite(STDERR, "FAIL: " . $reason . "\n"); exit(1); }
}
function candidate(string $field, string $value): array {
    $hostlist = [
        'youtubedomains'=>'', 'userdomains'=>'',
        'excludedomains'=>'', 'telegramips'=>'',
        'discordips'=>'', 'xips'=>'', 'sipips'=>'',
        'customips'=>'', 'excludeipset'=>''
    ];
    $hostlist[$field] = $value;
    return ['hostlist'=>$hostlist];
}
foreach ([
    ['youtubedomains', '!youtube.com'],
    ['youtubedomains', '^youtube.com'],
    ['youtubedomains', '!^youtube.com'],
    ['youtubedomains', '!^example.com'],
    ['userdomains', '^t.me'],
    ['userdomains', 'example.com'],
    ['excludedomains', 'example.com'],
] as [$field, $input]) {
    $model = new PolicyTestModel();
    SharedConfigCommit::validateOwnedModelFields(
        $model, candidate($field, $input), ['hostlist.' . $field]
    );
    check($model->fields['hostlist.' . $field] === $input,
        'Privileged boundary did not preserve canonical ' . $field);
}
foreach ([
    ['youtubedomains','!!youtube.com'],
    ['userdomains','^*.example.com'],
    ['excludedomains','!example.com'],
    ['youtubedomains','^!example.com'],
    ['telegramips','invalid-ip'],
] as [$field, $input]) {
    $model = new PolicyTestModel();
    try {
        SharedConfigCommit::validateOwnedModelFields(
            $model, candidate($field, $input), ['hostlist.' . $field]
        );
        check(false, 'Privileged root accepted invalid or unnormalized ' . $field);
    } catch (\InvalidArgumentException $expected) {
        check(!$model->fields, 'Privileged root touched model before rejection');
    }
}
// Non-list native scalar fields continue to use the native OPNsense Model.
$model = new PolicyTestModel();
SharedConfigCommit::validateOwnedModelFields(
    $model, ['general'=>['divertport'=>'989']], ['general.divertport']
);
check($model->fields['general.divertport']==='989', 'PortField model path regressed');
$modelXml = simplexml_load_file(
    __DIR__ . '/../src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml'
);
check($modelXml !== false, 'OPNsense XML malformed');
foreach (['youtubedomains','userdomains','excludedomains',
          'telegramips','discordips','xips','sipips','customips','excludeipset'] as $field) {
    check(count($modelXml->xpath('/model/items/hostlist/' . $field . '/Mask')) === 0,
        'Duplicate native Mask still blocks the Python policy for ' . $field);
}
foreach (['general/divertport','general/ports'] as $path) {
    check(count($modelXml->xpath('/model/items/' . $path . '/Mask')) === 1,
        'Native non-policy port/number mask changed');
}
echo "PASS: P1 root Python policy wins over native Model Regex without changing Config\n";
