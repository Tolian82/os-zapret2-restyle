#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v php >/dev/null 2>&1 || { echo "FAIL: PHP unavailable" >&2; exit 1; }
ZAPRET_API_TEST_ROOT="${ROOT_DIR}" php <<'PHP'
<?php
namespace OPNsense\Base { class ApiControllerBase {} }
namespace {
    require getenv('ZAPRET_API_TEST_ROOT') .
        '/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php';
    $method = new \ReflectionMethod(
        \OPNsense\Zapret\Api\StrategyLabController::class,
        'compactLargeEvidence'
    );
    $source = [
        'schema' => 2, 'job_id' => 'job.TestG09', 'state' => 'completed',
        'outcome' => 'NO_CANDIDATE', 'current_stage' => '99',
        'target' => '4.2.2.2', 'mode' => 'standard',
        'stages' => [['number' => '50','status' => 'PASS'],
                     ['number' => '60','status' => 'PASS'],
                     ['number' => '90','status' => 'PASS'],
                     ['number' => '99','status' => 'PASS']],
        'restoration' => ['verified' => true, 'final_state' => 'STOPPED'],
        'shortlist' => ['items' => []],
        'parameter_expansion' => [
            'completed' => 15, 'working' => [], 'stopped_reason' => 'graph_exhausted',
            'candidates' => [['id' => 'very-large', 'raw' => str_repeat('x', 200000)]],
            'parallel' => ['batches' => [['raw' => str_repeat('y', 150000)]],
                           'model_c_only' => true],
        ],
        'candidate_smoke' => ['completed' => 7, 'accepted' => [],
                              'families' => [['raw' => str_repeat('z', 150000)]]],
    ];
    $snapshot = $method->invoke(null, $source);
    if (strlen(json_encode($source)) <= 65536 ||
        strlen(json_encode($snapshot)) >= 65536 ||
        ($snapshot['api_evidence_compacted'] ?? false) !== true ||
        $snapshot['outcome'] !== 'NO_CANDIDATE' ||
        $snapshot['parameter_expansion']['completed'] !== 15 ||
        $snapshot['parameter_expansion']['stopped_reason'] !== 'graph_exhausted' ||
        isset($snapshot['parameter_expansion']['candidates']) ||
        isset($snapshot['candidate_smoke']['families']) ||
        count($snapshot['stages']) !== 4 ||
        $snapshot['restoration']['verified'] !== true ||
        !is_array($snapshot['shortlist']['items']) ||
        !isset($source['parameter_expansion']['candidates'][0]['raw'])) {
        fwrite(STDERR, "FAIL: HTTP snapshot did not retain the truthful bounded job contract\n");
        exit(1);
    }
    echo "PASS: G09 huge API evidence is bounded without altering source, stages, shortlist or restoration\n";
}
PHP
