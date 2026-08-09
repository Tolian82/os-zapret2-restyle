#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
CANDIDATE_SPEC="${SCRIPT_DIR}/strategy_lab_py/candidate_spec.py"
RESOURCES="${SCRIPT_DIR}/strategy_lab_py/resources.py"
CANDIDATE="${SCRIPT_DIR}/strategy_lab_py/candidate.py"
ADAPTER="${SCRIPT_DIR}/strategy_lab_candidate_adapter.sh"
PROFILE_ADAPTER="${SCRIPT_DIR}/strategy_lab_profile_candidate_adapter.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"
"${PYTHON}" -m py_compile "${CANDIDATE_SPEC}" "${RESOURCES}" "${CANDIDATE}"
sh -n "${ADAPTER}"
sh -n "${PROFILE_ADAPTER}"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-candidate-spec.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
LUA_DIR="${TMP}/lua"
FAKE_DIR="${TMP}/fake"
JOB_DIR="${TMP}/jobs/job.SPEC"
mkdir -p "${LUA_DIR}" "${FAKE_DIR}" "${JOB_DIR}"
for lua in zapret-lib.lua zapret-antidpi.lua zapret-auto.lua zapret-tests.lua
do
    printf '%s\n' '-- fixture' > "${LUA_DIR}/${lua}"
done
printf '%s\n' fake > "${FAKE_DIR}/fake_tls_7.bin"
printf '%s\n' unrelated > "${FAKE_DIR}/wireguard_initiation.bin"
: > "${LUA_DIR}/empty.lua"
: > "${FAKE_DIR}/empty.bin"

PYTHONPATH="${SCRIPT_DIR}" \
STRATEGY_LAB_LUA_DIR="${LUA_DIR}" \
STRATEGY_LAB_FAKE_DIR="${FAKE_DIR}" \
STRATEGY_LAB_SPEC_JOB_DIR="${JOB_DIR}" \
"${PYTHON}" - <<'PY'
import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

from strategy_lab_py.candidate_spec import CandidateSpec, CandidateSpecError
from strategy_lab_py.resources import ResourceInventoryError, ensure_job_inventory

job = Path(os.environ["STRATEGY_LAB_SPEC_JOB_DIR"])
inventory = ensure_job_inventory(job)
evidence = json.loads((job / "resource-inventory.json").read_text(encoding="utf-8"))
assert inventory.inventory_id.startswith("ri1-")
assert evidence["inventory_id"] == inventory.inventory_id
assert [item["name"] for item in evidence["lua"]] == [
    "empty.lua", "zapret-antidpi.lua", "zapret-auto.lua", "zapret-lib.lua", "zapret-tests.lua"
]
assert [item["name"] for item in evidence["external_blobs"]] == [
    "empty.bin", "fake_tls_7.bin", "wireguard_initiation.bin"
]
assert evidence["resource_classes"] == ["blob-free", "builtin", "inline", "external"]

# A job inventory is immutable evidence: later directory changes do not rewrite it.
(Path(os.environ["STRATEGY_LAB_FAKE_DIR"]) / "later.bin").write_bytes(b"later")
assert ensure_job_inventory(job).inventory_id == inventory.inventory_id
assert "later.bin" not in [item.name for item in ensure_job_inventory(job).external_blobs]

common = dict(
    family="test",
    protocol="tls13",
    transport="tcp",
    port=443,
    l7="tls",
    target_binding=True,
)

blob_free = CandidateSpec.from_strategy(
    candidate_id="blob-free", strategy="--payload=tls_client_hello\n--lua-desync=multisplit:pos=1\n", **common
)
assert blob_free.blob_requirements == ()
assert blob_free.to_dict()["resource_classes"] == ["blob-free"]
assert blob_free.to_dict()["lua_instances"][0]["arguments"] == [{"name": "pos", "value": "1"}]

builtin = CandidateSpec.from_strategy(
    candidate_id="builtin", strategy="--payload=tls_client_hello\n--lua-desync=fake:blob=fake_default_tls\n", **common
)
assert [(item.resource_class, item.name) for item in builtin.blob_requirements] == [
    ("builtin", "fake_default_tls")
]

inline = CandidateSpec.from_strategy(
    candidate_id="inline", strategy="--lua-desync=syndata:blob=0x1603\n", **common
)
assert [(item.resource_class, item.value) for item in inline.blob_requirements] == [
    ("inline", "0x1603")
]

external = CandidateSpec.from_strategy(
    candidate_id="external-range",
    strategy=(
        "--blob=fake_tls_7\n"
        "--payload=tls_client_hello\n"
        "--lua-desync=fake:blob=fake_default_tls\n"
        "--lua-desync=multisplit:pos=2,midsld-2:seqovl=1:seqovl_pattern=fake_tls_7\n"
    ),
    out_range="-d8",
    **common,
)
rendered = external.render_runtime_arguments(
    inventory, divert_port=9989, hostlist_path=job / "candidate-runtime/hostlist.txt"
)
assert rendered[:4] == (
    "--port=9989",
    f"--lua-init=@{Path(os.environ['STRATEGY_LAB_LUA_DIR']).resolve() / 'zapret-lib.lua'}",
    f"--lua-init=@{Path(os.environ['STRATEGY_LAB_LUA_DIR']).resolve() / 'zapret-antidpi.lua'}",
    "--filter-tcp=443",
)
assert "--out-range=-d8" in rendered and "--out-range=-d10" not in rendered
assert f"--blob=fake_tls_7:@{Path(os.environ['STRATEGY_LAB_FAKE_DIR']).resolve() / 'fake_tls_7.bin'}" in rendered
assert [item.function for item in external.lua_instances] == ["fake", "multisplit"]
assert [item.resource_class for item in external.blob_requirements] == ["external", "builtin"]
assert external.spec_id.startswith("cs1-")

inline_alias = CandidateSpec.from_strategy(
    candidate_id="inline-alias",
    strategy="--blob=custom:0x1603\n--lua-desync=fake:blob=custom\n",
    l3="ipv6",
    **common,
)
assert inline_alias.l3 == "ipv6"
assert [(item.name, item.resource_class, item.value) for item in inline_alias.blob_requirements] == [
    ("custom", "inline", "0x1603")
]

no_range = CandidateSpec.from_strategy(
    candidate_id="no-range",
    strategy="--lua-desync=multisplit:pos=1\n",
    out_range=None,
    **common,
)
assert not any(line.startswith("--out-range=") for line in no_range.render_runtime_arguments(
    inventory, divert_port=9989, hostlist_path=job / "candidate-runtime/hostlist.txt"
))

profile = CandidateSpec.from_strategy(
    candidate_id="profile",
    strategy=(
        "--filter-tcp=443\n--filter-l7=tls\n--hostlist-domains=example.com\n"
        "--out-range=-d8\n--lua-desync=multisplit:pos=1\n"
    ),
    out_range=None,
    render_mode="profile",
    target_selector="--hostlist-domains=example.com",
    provenance="profile-replay",
    **common,
)
profile_args = profile.render_runtime_arguments(
    inventory, divert_port=9989, hostlist_path=job / "candidate-runtime/hostlist.txt"
)
assert "--hostlist-domains=example.com" not in profile_args
assert f"--hostlist={job / 'candidate-runtime/hostlist.txt'}" in profile_args
assert profile_args.count("--out-range=-d8") == 1

missing = CandidateSpec.from_strategy(
    candidate_id="missing",
    strategy="--blob=missing_tls\n--lua-desync=fake:blob=missing_tls\n",
    **common,
)
try:
    missing.render_runtime_arguments(inventory, divert_port=9989, hostlist_path=job / "hostlist.txt")
except ResourceInventoryError:
    pass
else:
    raise AssertionError("missing external BLOB was accepted")

empty_external = CandidateSpec.from_strategy(
    candidate_id="empty-external",
    strategy="--blob=empty\n--lua-desync=fake:blob=empty\n",
    **common,
)
try:
    empty_external.render_runtime_arguments(
        inventory, divert_port=9989, hostlist_path=job / "hostlist.txt"
    )
except ResourceInventoryError:
    pass
else:
    raise AssertionError("empty external BLOB was accepted")

empty_lua = CandidateSpec.from_strategy(
    candidate_id="empty-lua",
    strategy="--lua-desync=multisplit:pos=1\n",
    lua_dependencies=("empty.lua",),
    **common,
)
try:
    empty_lua.render_runtime_arguments(
        inventory, divert_port=9989, hostlist_path=job / "hostlist.txt"
    )
except ResourceInventoryError:
    pass
else:
    raise AssertionError("empty Lua dependency was accepted")

try:
    blob_free.candidate_id = "changed"
except FrozenInstanceError:
    pass
else:
    raise AssertionError("CandidateSpec is mutable")

try:
    CandidateSpec.from_strategy(candidate_id="control", strategy="--payload=tls_client_hello\n", **common)
except CandidateSpecError:
    pass
else:
    raise AssertionError("candidate without a Lua action was accepted as bypass")
PY

if grep -Eq -- '--lua-init|--out-range|STRATEGY_LAB_LUA_DIR|find .*\.lua' "${ADAPTER}" "${PROFILE_ADAPTER}"; then
    fail 'candidate shell adapters still own Lua/resource/range policy'
fi
grep -Fq 'resources.ensure_job_inventory' "${CANDIDATE}" ||
    fail 'Python candidate runtime does not consume the job resource inventory'
grep -Fq 'render_runtime_arguments' "${CANDIDATE}" ||
    fail 'Python CandidateSpec does not render the exact runtime arguments'

echo 'PASS: Python CandidateSpec preserves ordered native actions/ranges/resources, ResourceInventory snapshots installed resources once per job, and shell adapters contain no candidate resource policy'
