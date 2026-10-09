#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
git init -q
git config user.name "Revision Test"
git config user.email "test@example.invalid"
echo 0.5.1 > VERSION
printf 'PLUGIN_REVISION=    1\n' > Makefile
mkdir -p src
echo one > src/code.py
git add .
git commit -qm "v0.5.1_1: Initial candidate"
base="$(git rev-parse HEAD)"
echo legacy >> src/code.py
git add src
git commit -qm "v0.5.1_1: Historical unbumped code"
mkdir -p .github
echo 1 > .github/REVISION_GUARD
sed 's/REVISION=    1/REVISION=    2/' Makefile > Makefile.new
mv Makefile.new Makefile
git add .
git commit -qm "v0.5.1_2: Correct and enable revision enforcement"
echo docs > notes.md
git add notes.md
git commit -qm "v0.5.1_2: Docs-only"
good="$(git rev-parse HEAD)"
bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$good" "v0.5.1_2: Voice"
echo code >> src/code.py
git add src
git commit -qm "v0.5.1_2: Unbumped"
if bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$(git rev-parse HEAD)" "v0.5.1_2: Voice" >/dev/null 2>&1; then
  echo "FAIL: unbumped code passed" >&2; exit 1
fi
git reset --hard -q "$good"
echo code >> src/code.py
sed 's/REVISION=    2/REVISION=    3/' Makefile > Makefile.new
mv Makefile.new Makefile
git add .
git commit -qm "v0.5.1_3: Bumped code"
now="$(git rev-parse HEAD)"
bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$now" "v0.5.1_3: Voice"
if bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$now" "v0.5.1_2: Stale" >/dev/null 2>&1; then
  echo "FAIL: stale title passed" >&2; exit 1
fi
echo "PASS: version-boundary and forward revision-regression"
