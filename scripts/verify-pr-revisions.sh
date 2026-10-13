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
# Exactly six immutable legacy PR commits accidentally used docs:/tests:
# subjects after the prospective marker. GH-014 forbids history rewriting.
# Accept ONLY the exact SHA + literal subject; all other commits, including
# future identically worded subjects, retain the full strict candidate gate.
legacy_subject_allowed() {
  case "$1|$2" in
    '02bd7df0a7d33a533223e93f56851d8fb7b77fe8|docs: Record v0.5.2_8 native save merge milestone and handoff') return 0 ;;
    '5fd82b7d05608db17e587fda6792c90dfc404784|docs: Document v0.5.2_9 native Config commit and fix CI test indentation') return 0 ;;
    'd65aa90fcb29e121b05e748f4126eb33f60b6bf4|tests: Include common runtime module in Strategy Lab lifecycle mock') return 0 ;;
    'd6a5dddcca4fc34e7604635a171a2f505e696458|docs: Record v0.5.2_10 shared IPFW precommit fix') return 0 ;;
    'c2c4e04a33d513554e698d96324788c20b81194c|tests: Match the shared adapter's actual IPFW error class') return 0 ;;
    'e1e5cef8c04e9a3c45bdc3cf4ffbfa5056bd6734|docs: Record v0.5.2_11 shared native Apply transaction boundary') return 0 ;;
  esac
  return 1
}
expected="$(identity_at "$HEAD_SHA")"
if [[ "$PR_TITLE" != "$expected: "* ]]; then
  echo "Invalid PR title: $PR_TITLE; required $expected: ..." >&2; exit 1
fi
count=0
legacy_count=0
while IFS= read -r commit; do
  ((count+=1))
  actual="$(git show -s --format=%s "$commit")"
  candidate="$(identity_at "$commit")"
  if [[ "$actual" != "$candidate: "* ]]; then
    if legacy_subject_allowed "$commit" "$actual"; then
      ((legacy_count+=1))
      echo "AUDIT: exact immutable historical subject grandfathered at $commit" >&2
    else
      echo "Invalid historical commit $commit: $actual; expected $candidate: ..." >&2; exit 1
    fi
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
echo "PASS: $count commits, $legacy_count exact historical subjects, strict new revision guard, PR $expected"
