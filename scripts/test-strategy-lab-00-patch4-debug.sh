#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec sh -x "${ROOT_DIR}/scripts/test-strategy-lab-e2e.sh"
