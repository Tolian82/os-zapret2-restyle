#!/usr/bin/env bash
set -euo pipefail
if (( $# != 3 )); then echo "Usage: verify-pr-revisions.sh BASE HEAD TITLE" >&2; exit 64; fi
BASE_SHA="$1"; HEAD_SHA="$2"; PR_TITLE="$3"
version_at() { git show "$1:VERSION" | tr -d '[:space:]'; }
revision_at() { git show "$1:Makefile" | sed -n 's/^PLUGIN_REVISION=[[:space:]]*//p' | head -1; }
identity_at() {
  local version revision
  version="$(version_at "$1")"; revision="$(revision_at "$1")"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && "$revision" =~ ^(0|[1-9][0-9]*)$ ]] || {
    echo "Invalid version/revision at $1" >&2; return 1;
  }
  printf 'v%s_%s' "$version" "$revision"
}
marker_at() { git cat-file -e "$1:.github/REVISION_GUARD" 2>/dev/null; }
expected="$(identity_at "$HEAD_SHA")"
if [[ "$PR_TITLE" != "$expected: "* ]]; then
  echo "Invalid PR title: $PR_TITLE; required $expected: ..." >&2; exit 1
fi
count=0
while IFS= read -r commit; do
  ((count+=1))
  actual="$(git show -s --format=%s "$commit")"
  candidate="$(identity_at "$commit")"
  if [[ "$actual" != "$candidate: "* ]]; then
    echo "Invalid historical commit $commit: $actual; expected $candidate: ..." >&2; exit 1
  fi
  # Prospective marker: older commits cannot be rewritten and keep their own identity.
  if marker_at "$commit" && marker_at "$commit^"; then
    old_version="$(version_at "$commit^")"; new_version="$(version_at "$commit")"
    old_revision="$(revision_at "$commit^")"; new_revision="$(revision_at "$commit")"
    changed="$(git diff --name-only "$commit^" "$commit")"
    if [[ "$old_version" != "$new_version" ]]; then
      [[ "$new_revision" == 1 ]] || { echo "Stage transition must reset revision at $commit" >&2; exit 1; }
    elif printf '%s\n' "$changed" | grep -Eq '^(src/|pkg/|repository/|Makefile$|VERSION$|scripts/build-pkg\.sh$)'; then
      if (( 10#$new_revision != 10#$old_revision + 1 )); then
        echo "Packaged code needs one revision bump at $commit: $old_revision -> $new_revision" >&2; exit 1
      fi
    elif [[ "$old_revision" != "$new_revision" ]]; then
      echo "Docs/CI-only commit cannot bump revision at $commit" >&2; exit 1
    fi
  fi
done < <(git rev-list --reverse "$BASE_SHA..$HEAD_SHA")
((count>0)) || { echo "Empty PR commit history" >&2; exit 1; }
echo "PASS: $count commits, per-commit identity, prospective revision guard, PR $expected"
