#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
git init -q
git config user.name "Revision Test"
git config user.email "test@example.invalid"
echo 0.6.1 > VERSION
printf 'PLUGIN_REVISION=    12\n' > Makefile
mkdir -p src .github
echo original > src/code.py
echo active > .github/REVISION_GUARD
git add .
git commit -qm "v0.6.1_12: Initial main"
base="$(git rev-parse HEAD)"

# Even documentation-only PRs MUST increment the source revision.
echo docs > notes.md
git add notes.md
git commit -qm "v0.6.1_12: Docs without increment"
if bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" HEAD "v0.6.1_12: Docs" >/dev/null 2>&1; then
  echo "FAIL: unchanged revision passed for docs-only PR" >&2; exit 1
fi
git reset --hard -q "$base"

sed 's/REVISION=    12/REVISION=    13/' Makefile > Makefile.new
mv Makefile.new Makefile
echo docs > notes.md
git add .
git commit -qm "v0.6.1_13: Docs-only increments main identity"
good="$(git rev-parse HEAD)"
bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$good" "v0.6.1_13: Docs"

# Additional commits on the SAME pending PR must not consume another main revision.
echo fixup >> notes.md
git add notes.md
git commit -qm "v0.6.1_13: Fix docs in the same PR"
fixed="$(git rev-parse HEAD)"
bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$fixed" "v0.6.1_13: Docs"

# Packaged code in a later fixup of that SAME PR stays one candidate.
echo correction >> src/code.py
git add src
git commit -qm "v0.6.1_13: Correct packaged source in the same PR"
current="$(git rev-parse HEAD)"
bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$current" "v0.6.1_13: Product"

if bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" "$current" "v0.6.1_12: Stale" >/dev/null 2>&1; then
  echo "FAIL: stale PR title passed" >&2; exit 1
fi

# A second main PR from _13 needs _14; it cannot reuse _13.
echo next > second.md
git add second.md
git commit -qm "v0.6.1_13: New docs PR without bump"
if bash "$ROOT/scripts/verify-pr-revisions.sh" "$current" HEAD "v0.6.1_13: No bump" >/dev/null 2>&1; then
  echo "FAIL: next PR reused prior revision" >&2; exit 1
fi
git reset --hard -q "$current"
sed 's/REVISION=    13/REVISION=    15/' Makefile > Makefile.new
mv Makefile.new Makefile
git add Makefile
git commit -qm "v0.6.1_15: Skipped a main revision"
if bash "$ROOT/scripts/verify-pr-revisions.sh" "$current" HEAD "v0.6.1_15: Skip" >/dev/null 2>&1; then
  echo "FAIL: skipped _14 passed" >&2; exit 1
fi
git reset --hard -q "$current"

# A true new development stage resets to _1, not a continuous _14.
echo 0.6.2 > VERSION
sed 's/REVISION=    13/REVISION=    1/' Makefile > Makefile.new
mv Makefile.new Makefile
git add VERSION Makefile
git commit -qm "v0.6.2_1: Approved new development stage"
bash "$ROOT/scripts/verify-pr-revisions.sh" "$current" HEAD "v0.6.2_1: Stage"

# No generic escape hatch for unversioned commit messages.
git reset --hard -q "$good"
echo bad > bad.md
git add bad.md
git commit -qm "docs: New unversioned message"
if bash "$ROOT/scripts/verify-pr-revisions.sh" "$base" HEAD "v0.6.1_13: Docs" >/dev/null 2>&1; then
  echo "FAIL: new unversioned commit passed" >&2; exit 1
fi

echo "PASS: docs-only bump, source fixup, stale/skip/reuse refusal, stage reset and commit-title policy"
