#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_python_launcher.sh"
JQ=$(command -v jq || true)

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"
[ -x "${JQ}" ] || fail 'jq is unavailable'

"${PYTHON}" -m py_compile \
    "${SCRIPT_DIR}/strategy_lab_py/model_a.py" \
    "${SCRIPT_DIR}/strategy_lab_py/compat.py"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-model-a.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
JOBS="${TMP}/jobs"
JOB="job.MODELA1"
JOB_DIR="${JOBS}/${JOB}"
REPORT="${TMP}/model-a.json"
mkdir -p \
    "${JOB_DIR}/family-screening" \
    "${JOB_DIR}/parameter-expansion" \
    "${JOB_DIR}/stability/1-attempts" \
    "${JOB_DIR}/profile-replay"

cat > "${JOB_DIR}/status.json" <<'JSON'
{"job_id":"job.MODELA1","target":"example.test","target_type":"domain","mode":"standard","state":"completed","outcome":"SUCCESS","restoration":{"verified":true,"initial_state":"RUNNING","final_state":"RUNNING","strategy_unchanged":true,"temporary_runtime_clean":true}}
JSON
cat > "${JOB_DIR}/resource-inventory.json" <<'JSON'
{"schema":1,"inventory_id":"ri1-fixture","observed_at":"2026-08-10T00:00:00Z","lua_root":"/lua","fake_root":"/fake","lua_root_exists":true,"fake_root_exists":true,"lua":[],"external_blobs":[{"name":"fake_tls_7.bin","path":"/fake/fake_tls_7.bin","size":64,"mtime_ns":1}],"builtin_blobs":["fake_default_tls","fake_default_http","fake_default_quic"],"resource_classes":["blob-free","builtin","inline","external"],"inline":{"prefix":"0x","available":true}}
JSON
cat > "${JOB_DIR}/search-epoch.json" <<'JSON'
{"schema":1,"epoch_id":"se1-fixture","generation":1,"target":"example.test"}
JSON

write_sample()
{
    path="$1"; id="$2"; spec="$3"; family="$4"; classes="$5"; out_range="$6"; pass="$7"; total="$8"; rss="$9"
    "${JQ}" -n \
        --arg id "${id}" --arg spec "${spec}" --arg family "${family}" \
        --arg classes "${classes}" --arg out_range "${out_range}" \
        --argjson pass "${pass}" --argjson total "${total}" --argjson rss "${rss}" '
      {
        id:$id,
        family:$family,
        all_pass:$pass,
        search_epoch_id:"se1-fixture",
        resource_inventory_id:"ri1-fixture",
        candidate_spec:{
          candidate_id:$id,spec_id:$spec,family:$family,protocol:"tls13",transport:"tcp",port:443,
          resource_classes:($classes|split(",")),ranges:{in:null,out:(if $out_range=="<none>" then null else $out_range end)}
        },
        runtime:{rss_kb:$rss},
        endpoints:[{
          endpoint:"example.test",selected_ip:"203.0.113.10",remote_ip:"203.0.113.10",endpoint_match:true,
          firewall:{rule:19100,intercepted:true}
        }],
        timing:{
          pre_cleanup_ms:100,endpoint_binding_ms:20,candidate_prepare_ms:30,resource_render_ms:40,
          firewall_install_ms:50,resource_init_ms:null,launch_ms:60,readiness_ms:1000,probe_ms:200,
          cleanup_ms:300,total_ms:$total
        }
      }' > "${path}"
}

write_sample "${JOB_DIR}/family-screening/pass.json" pass-blobfree cs-pass pass "blob-free" "<none>" true 1800 12000
write_sample "${JOB_DIR}/parameter-expansion/fail-builtin.json" fail-builtin cs-fail-builtin fake "builtin" "-d10" false 1900 13000
write_sample "${JOB_DIR}/parameter-expansion/fail-external.json" fail-external cs-fail-external seqovl "external" "-d8" false 2100 14000
write_sample "${JOB_DIR}/stability/1-attempts/1.json" pass-blobfree cs-pass pass "blob-free" "<none>" true 1700 12100
write_sample "${JOB_DIR}/stability/1-attempts/2.json" pass-blobfree cs-pass pass "blob-free" "<none>" true 1800 12200
write_sample "${JOB_DIR}/stability/1-attempts/3.json" pass-blobfree cs-pass pass "blob-free" "<none>" true 2000 12300
write_sample "${JOB_DIR}/profile-replay/pass.deep.json" pass-blobfree cs-pass pass "blob-free" "<none>" true 2200 12400

STRATEGY_LAB_JOBS_DIR="${JOBS}" STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
    sh "${LAUNCHER}" model-a summarize "${REPORT}" "${JOB}"

"${JQ}" -e '
  .schema==1 and .model=="A-cold-reference" and .conclusion=="reference_collected" and
  .sample_count==7 and (.jobs|length)==1 and .jobs[0].job_id=="job.MODELA1" and
  .coverage.complete==true and .coverage.checks.known_pass_observed==true and
  .coverage.checks.known_fail_observed==true and
  .coverage.checks.repeated_candidate_observed==true and
  .coverage.checks.required_resource_classes_observed==true and
  .coverage.checks.out_range_d8_observed==true and
  .coverage.checks.overlapping_tls443_candidates_observed==true and
  .coverage.checks.rss_observed==true and
  .coverage.checks.restoration_verified_for_all_jobs==true and
  .coverage.resource_classes_observed==["blob-free","builtin","external"] and
  (.coverage.out_ranges_observed|index("-d8"))!=null and
  .phase_statistics_ms.total_ms.count==7 and
  .phase_statistics_ms.stop_cleanup_ms.median==300 and
  ([.candidate_statistics[]|select(.spec_id=="cs-pass")][0].sample_count)==5 and
  ([.samples[].rss_kb]|min)==12000 and
  (.limitations|map(select(contains("stop_ms")))|length)==1
' "${REPORT}" >/dev/null || {
    cat "${REPORT}" >&2
    fail 'Model A measurement report contract failed'
}

set +e
STRATEGY_LAB_JOBS_DIR="${JOBS}" STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
    sh "${LAUNCHER}" model-a summarize "${TMP}/bad.json" job.missing >/dev/null 2>&1
rc=$?
set -e
[ "${rc}" -eq 70 ] || fail "invalid Model A job returned ${rc}, expected 70"

sh -n "$0"
echo 'PASS: Strategy Lab Model A summarizes cold candidate timing, RSS, coverage, identity, and restoration evidence without changing lifecycle state'