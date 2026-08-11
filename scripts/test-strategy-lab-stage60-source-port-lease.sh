#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
MODULE_ROOT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
LEASE_MODULE="${MODULE_ROOT}/strategy_lab_py/stage60_source_port_lease.py"
ENTRY="${MODULE_ROOT}/strategy_lab_python.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
[ -s "${LEASE_MODULE}" ] || fail 'missing Stage-60 source-port lease module'
[ -s "${ENTRY}" ] || fail 'missing Strategy Lab Python entry point'

PYTHONPATH="${MODULE_ROOT}" "${PYTHON_BIN}" - <<'PY'
import os
from types import SimpleNamespace

from strategy_lab_py import model_b, stage60_model_c, stage60_parallel, stage60_source_port_lease as lease


def decision(candidate_id):
    return SimpleNamespace(node=SimpleNamespace(candidate_id=candidate_id))


decisions = (decision("alpha"), decision("beta"))
bindings = ({"endpoint": "one.example"}, {"endpoint": "two.example"})
indexes = {"alpha": 1, "beta": 2}
preferred = {(1, 1): 42000, (1, 2): 42001, (2, 1): 42002, (2, 2): 42003}

original_try = model_b._try_adapter
calls = []
busy = {42001}


def fake_try(action, *args, **kwargs):
    calls.append((action, args))
    assert action == "source-port-free"
    return int(args[0]) not in busy

model_b._try_adapter = fake_try
try:
    leased, evidence = lease.lease_batch_source_ports(decisions, bindings, preferred, indexes)
    assert leased[(1, 1)] == 42000
    assert leased[(1, 2)] == 42004
    assert leased[(2, 1)] == 42002
    assert leased[(2, 2)] == 42003
    assert len(set(leased.values())) == 4
    assert evidence["replacement_count"] == 1
    assert evidence["collisions"] == [{
        "candidate_id": "alpha",
        "endpoint": "two.example",
        "endpoint_index": 2,
        "preferred_port": 42001,
        "leased_port": 42004,
    }]
    assert evidence["foreign_port_action"] == "skip-only"
    assert all(action == "source-port-free" for action, _args in calls)

    # A Model-B fallback takes a fresh lease. If the first alternate was consumed in the
    # meantime, it must move again rather than inheriting Model C's failed concrete port.
    busy.add(42004)
    leased_again, evidence_again = lease.lease_batch_source_ports(
        decisions, bindings, preferred, indexes
    )
    assert leased_again[(1, 2)] == 42005
    assert evidence_again["replacement_count"] == 1
    assert 42001 not in leased_again.values()
    assert 42004 not in leased_again.values()

    # Bounded exhaustion fails closed instead of weakening attribution or touching owners.
    os.environ[lease.SCAN_LIMIT_ENV] = "2"
    busy.update({42000, 42001, 42002, 42003, 42004, 42005})
    try:
        lease.lease_batch_source_ports(decisions, bindings, preferred, indexes)
    except lease.SourcePortLeaseError:
        pass
    else:
        raise AssertionError("source-port lease exhaustion did not fail closed")
finally:
    os.environ.pop(lease.SCAN_LIMIT_ENV, None)
    model_b._try_adapter = original_try

original_c = stage60_model_c._bucket_batch
original_b = stage60_parallel._warm_batch
with lease.install():
    assert stage60_model_c._bucket_batch is not original_c
    assert stage60_parallel._warm_batch is not original_b
assert stage60_model_c._bucket_batch is original_c
assert stage60_parallel._warm_batch is original_b
PY

grep -Fq 'from strategy_lab_py import stage60_source_port_lease' "${ENTRY}" || fail 'entry point does not load source-port leasing'
grep -Fq 'with stage60_source_port_lease.install()' "${ENTRY}" || fail 'Stage 60 does not install source-port leasing'
grep -Fq 'foreign_port_action' "${LEASE_MODULE}" || fail 'lease evidence does not record foreign-port policy'
grep -Fq 'source-port-free' "${LEASE_MODULE}" || fail 'lease allocator does not prove source-port availability'
grep -Fq 'original_model_c_batch' "${LEASE_MODULE}" || fail 'Model C is not wrapped by the lease boundary'
grep -Fq 'original_model_b_batch' "${LEASE_MODULE}" || fail 'Model B fallback is not independently wrapped by the lease boundary'

echo 'PASS: Stage 60 keeps free preferred ports, skips foreign collisions, leases bounded alternates, gives Model B a fresh fallback lease, and fails closed on exhaustion'
