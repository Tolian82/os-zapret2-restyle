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
# Immutable history boundary of Draft PR #328. The old development chain
# predates consistent title/revision policy and cannot be rewritten under
# GH-014. Pin its EXACT commit SHA: rewriting or inserting an ancestor
# changes this commit ID and invalidates the bounded grandfathering.
# Any commit after the pinned tip is validated without exception. Other PRs
# lacking this exact ancestry are validated from BASE, with no bypass.
FROZEN_LEGACY_TIP=a7682c46c4071dfdbd33745f70b0278f05322833
frozen_prefix=0
if git cat-file -e "$FROZEN_LEGACY_TIP^{commit}" 2>/dev/null &&
   git merge-base --is-ancestor "$BASE_SHA" "$FROZEN_LEGACY_TIP" &&
   git merge-base --is-ancestor "$FROZEN_LEGACY_TIP" "$HEAD_SHA"; then
  frozen_prefix=1
fi
# Immutable one-time correction for the exact published _106 sequence:
# the native source and its test were mistakenly titled _106 while the
# immutable commits still carried _105; the immediately following Makefile
# commit performed the required _105 -> _106 bump. Never rebase or force
# push those three objects merely to rename their subjects (GH-014).
# This is NOT a general revision or title bypass: exact SHA, direct parent
# chain, exact changed paths and the package correction are all mandatory.
MISLABELED_SOURCE_106=42397b8b19a13a5efa3d93881e965e162969ecd9
MISLABELED_TEST_106=838372b80687961d1902b74793661903659f112f
CORRECTIVE_REVISION_106=c5c11ed5393042f5ee7b2e475794ab2f3ae8a244
immutable_106_correction=0
if git cat-file -e "$CORRECTIVE_REVISION_106^{commit}" 2>/dev/null &&
   git merge-base --is-ancestor "$CORRECTIVE_REVISION_106" "$HEAD_SHA" &&
   [[ "$(git rev-parse "$MISLABELED_TEST_106^")" == "$MISLABELED_SOURCE_106" ]] &&
   [[ "$(git rev-parse "$CORRECTIVE_REVISION_106^")" == "$MISLABELED_TEST_106" ]] &&
   [[ "$(identity_at "$MISLABELED_SOURCE_106")" == "v0.5.2_105" ]] &&
   [[ "$(identity_at "$MISLABELED_TEST_106")" == "v0.5.2_105" ]] &&
   [[ "$(identity_at "$CORRECTIVE_REVISION_106")" == "v0.5.2_106" ]] &&
   [[ "$(git diff --name-only "$MISLABELED_SOURCE_106^" "$MISLABELED_SOURCE_106")" == "src/opnsense/scripts/OPNsense/Zapret/backend/voice_native_legacy_predecessor_route.py" ]] &&
   [[ "$(git diff --name-only "$MISLABELED_TEST_106^" "$MISLABELED_TEST_106")" == "scripts/test-shared-apply-operation.py" ]] &&
   [[ "$(git diff --name-only "$CORRECTIVE_REVISION_106^" "$CORRECTIVE_REVISION_106")" == "Makefile" ]]; then
  immutable_106_correction=1
fi
# Immutable exact correction for ONE docs-only commit at the _121 tip.
# This commit introduced the owner's release-after-code-completion order and
# fixed two relative documentation links. Its immutable subject accidentally
# starts with "docs:" rather than the required "v0.5.2_121:".
# GH-014 prohibits rewriting this already-pushed object. Never broadly
# accept 'docs:' subjects: bind parent, SHA, identical package revision,
# exact previous message and all six documentation-only paths. All new
# commits, including later docs-only ones, still require versioned subjects.
DOCS_121_SUBJECT=a78658d735e69f2bcc71ecf2e083258a267e9ac6
DOCS_121_PARENT=ed5356712ac1e8d361fbc1b83a15030dbca8b49a
immutable_121_docs_subject=0
if git cat-file -e "$DOCS_121_SUBJECT^{commit}" 2>/dev/null &&
   git merge-base --is-ancestor "$DOCS_121_SUBJECT" "$HEAD_SHA" &&
   [[ "$(git rev-parse "$DOCS_121_SUBJECT^")" == "$DOCS_121_PARENT" ]] &&
   [[ "$(identity_at "$DOCS_121_SUBJECT")" == "v0.5.2_121" ]] &&
   [[ "$(identity_at "$DOCS_121_PARENT")" == "v0.5.2_121" ]] &&
   [[ "$(git show -s --format=%s "$DOCS_121_SUBJECT")" == "docs: Freeze live trial until Voice code completion; fix v0.5.2_121 CI links" ]] &&
   [[ "$(git diff --name-only "$DOCS_121_PARENT" "$DOCS_121_SUBJECT")" == "$(printf '%s\n' docs/PROJECT_STATE.md docs/ROADMAP.md docs/START_HERE.md docs/VOICE_CODE_COMPLETION_GATE.md docs/history/current/v0.5.x.md docs/releases/v0.5.2.md)" ]]; then
  immutable_121_docs_subject=1
fi
expected="$(identity_at "$HEAD_SHA")"
if [[ "$PR_TITLE" != "$expected: "* ]]; then
  echo "Invalid PR title: $PR_TITLE; required $expected: ..." >&2; exit 1
fi
count=0
frozen_count=0
while IFS= read -r commit; do
  ((count+=1))
  if (( frozen_prefix )); then
    ((frozen_count+=1))
    if [[ "$commit" == "$FROZEN_LEGACY_TIP" ]]; then
      frozen_prefix=0
    fi
    continue
  fi
  if (( immutable_106_correction )) && [[ "$commit" == "$MISLABELED_SOURCE_106" || "$commit" == "$MISLABELED_TEST_106" ]]; then
    # Only the two immutable, exact already-published objects above.
    continue
  fi
  if (( immutable_121_docs_subject )) && [[ "$commit" == "$DOCS_121_SUBJECT" ]]; then
    # EXACT one-object documentation exception; no global title relaxation.
    continue
  fi
  actual="$(git show -s --format=%s "$commit")"
  candidate="$(identity_at "$commit")"
  if [[ "$actual" != "$candidate: "* ]]; then
    echo "Invalid commit $commit: $actual; expected $candidate: ..." >&2; exit 1
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
echo "PASS: $count commits ($frozen_count immutable pre-policy commits), strict forward title/revision guard, PR $expected"
