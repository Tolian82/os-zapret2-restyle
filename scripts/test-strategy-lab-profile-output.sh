#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
STAGE_ADAPTER="${SCRIPT_DIR}/strategy_lab_stage_adapter.sh"
TMP=$(mktemp -d /tmp/strategy-lab-profile.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test" "${TMP}/lua"

cat > "${TMP}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK
cat > "${TMP}/bin/profile-runner" <<'MOCK'
#!/bin/sh
[ "${STRATEGY_LAB_ENDPOINT_PROBE_MODE:-}" = sequential ] || exit 90
result=$3
profile=$6
target=$7
target_type=$8
count_file="${MOCK_PROFILE_REPLAY_COUNT:?}"
count=0
[ ! -r "${count_file}" ] || count=$(cat "${count_file}")
count=$((count + 1))
printf '%s\n' "${count}" > "${count_file}"
jq -n --rawfile profile "${profile}" --arg target "${target}" --arg target_type "${target_type}" '
{
  strategy:$profile,
  profile:$profile,
  target:$target,
  target_type:$target_type,
  profile_exact:true,
  endpoints:[{endpoint:$target,selected_ip:"203.0.113.10",remote_ip:"203.0.113.10",status:"PASS"}],
  all_pass:true
}' > "${result}"
MOCK
chmod +x "${TMP}/bin/"*

export SCRIPT_DIR MODULE_DIR
export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout"
export STRATEGY_LAB_PROFILE_ENV_BIN=$(command -v env)
export STRATEGY_LAB_PROFILE_REPLAY_RUNNER="${TMP}/bin/profile-runner"
export MOCK_PROFILE_REPLAY_COUNT="${TMP}/replays"
export STRATEGY_LAB_LUA_DIR="${TMP}/lua"
export STRATEGY_LAB_DIVERT_PORT=9989

. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/target.sh"
. "${MODULE_DIR}/profile.sh"

printf '%s\n' \
    '--lua-desync=multisplit:pos=1' \
    '--lua-desync=syndata:blob=0x1603' > "${TMP}/fragment.args"
strategy_lab_profile_build telegram.org domain "${TMP}/fragment.args" "${TMP}/profile.args"
strategy_lab_profile_validate telegram.org domain "${TMP}/profile.args"
grep -Fqx -- '--hostlist-domains=telegram.org' "${TMP}/profile.args"
grep -Fqx -- '--filter-tcp=443' "${TMP}/profile.args"
grep -Fqx -- '--filter-l7=tls' "${TMP}/profile.args"
grep -Fqx -- '--out-range=-d10' "${TMP}/profile.args"
! grep -Eq '^--(port|lua-init|sockarg|user)=' "${TMP}/profile.args"

printf '%s\n' '--port=9989' '--lua-desync=multisplit:pos=1' > "${TMP}/bad.args"
if strategy_lab_profile_build telegram.org domain "${TMP}/bad.args" "${TMP}/bad-profile.args"; then
    echo 'runtime-only argument was accepted' >&2
    exit 1
fi

printf '%s\n' telegram.org > "${TMP}/run/jobs/job.test/endpoints.txt"
cat > "${TMP}/run/jobs/job.test/status.json" <<'JSON'
{"target":"telegram.org","target_type":"domain"}
JSON
cat > "${TMP}/run/jobs/job.test/stability.json" <<'JSON'
{"candidates":[
 {"id":"c1","family":"multisplit","strategy":"--lua-desync=multisplit:pos=1\n","stable":true,"line_count":1,"character_count":32},
 {"id":"c2","family":"fake","strategy":"--lua-desync=fake:blob=fake_default_tls\n","stable":false,"line_count":1,"character_count":41}
]}
JSON
strategy_lab_shortlist_build \
    "${TMP}/run/jobs/job.test/stability.json" \
    "${TMP}/run/jobs/job.test/shortlist.json"
jq -e '
 .count==1 and
 .recommendation.id=="c1" and
 .recommendation.target=="telegram.org" and
 .recommendation.target_type=="domain" and
 .recommendation.protocol=="tls13" and
 .recommendation.port==443 and
 .recommendation.profile_replay.attempt_count==3 and
 .recommendation.profile_replay.pass_count==3 and
 .recommendation.profile_replay.verified==true and
 (.recommendation.profile | contains("--hostlist-domains=telegram.org")) and
 (.recommendation.strategy | contains("--lua-desync=multisplit"))
' "${TMP}/run/jobs/job.test/shortlist.json" >/dev/null
[ "$(cat "${TMP}/replays")" -eq 3 ]

. "${MODULE_DIR}/runtime.sh"
. "${MODULE_DIR}/profile_runtime.sh"
STRATEGY_LAB_PROFILE_TARGET=telegram.org
STRATEGY_LAB_PROFILE_TARGET_TYPE=domain
export STRATEGY_LAB_PROFILE_TARGET STRATEGY_LAB_PROFILE_TARGET_TYPE
strategy_lab_candidate_prepare_files \
    job.test "${TMP}/run/jobs/job.test/endpoints.txt" "${TMP}/profile.args" 1
PROFILE_ARGS=$(strategy_lab_candidate_args_file job.test)
grep -Fqx -- '--port=9989' "${PROFILE_ARGS}"
grep -Fqx -- "--hostlist=$(strategy_lab_candidate_hostlist_file job.test)" "${PROFILE_ARGS}"
! grep -Fq -- '--hostlist-domains=' "${PROFILE_ARGS}"
grep -Fqx -- '--lua-desync=multisplit:pos=1' "${PROFILE_ARGS}"

# Patch 3 moved stage progression out of the production worker. Stage 85 still owns
# shortlist/profile construction through the explicit shell stage adapter until Patch 7.
grep -Fq '85)' "${STAGE_ADAPTER}" || exit 1
grep -Fq 'strategy_lab_shortlist_build "${STABILITY_FILE}" "${SHORTLIST_FILE}"' "${STAGE_ADAPTER}" || exit 1
grep -Fq 'strategy_lab_profile_replay_runner.sh' "${MODULE_DIR}/profile.sh"
grep -Fq 'profile_runtime' "${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh"

echo 'PASS: complete Traffic Strategy profiles are exact-replayed 3 of 3 before shortlist publication and stage 85 retains explicit adapter ownership'
