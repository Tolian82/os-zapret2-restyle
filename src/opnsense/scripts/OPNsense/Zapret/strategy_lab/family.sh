#!/bin/sh

# Migration Patch 5 retired shell ownership of Stage-50 family policy.
# The production strategy_lab_family_runner.sh delegates directly to Python 3.13
# strategy_lab_py/family.py. This file intentionally defines no screening fallback;
# it remains sourceable only until the shared stage adapter module list is simplified
# in a later shell-orchestration retirement patch.
