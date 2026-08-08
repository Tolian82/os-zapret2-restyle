#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}

STRATEGY_LAB_TEST_PYTHON="${PYTHON}" sh "${ROOT_DIR}/scripts/strategy-lab-python-search-extended-core.sh"
STRATEGY_LAB_TEST_PYTHON="${PYTHON}" sh "${ROOT_DIR}/scripts/test-strategy-lab-python-final-results.sh"

echo 'PASS: Python 3.13 migration continuity gate covers search/extended orchestration and final-result ownership'
