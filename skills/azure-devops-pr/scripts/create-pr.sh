#!/usr/bin/env bash
# Create a squash-merge PR for the current branch and print it as JSON.
# Usage: create-pr.sh [--title T] [--description D] [--target-branch B] [--work-items "1 2"]
#
# Without --title, a branch exactly one commit ahead of the target uses that
# commit's subject; anything else is refused, because no single commit's subject
# describes the whole change. Without --work-items, a trailing -<id> or /<id>
# in the branch name is linked.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

TARGET_BRANCH="main"
TITLE=""
DESCRIPTION=""
WORK_ITEMS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="$2"; shift 2 ;;
    --description) DESCRIPTION="$2"; shift 2 ;;
    --target-branch) TARGET_BRANCH="$2"; shift 2 ;;
    --work-items) WORK_ITEMS="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

SOURCE_BRANCH="$(git branch --show-current)"

if [[ -z "$TITLE" ]]; then
  COMMIT_COUNT="$(git rev-list --count "origin/${TARGET_BRANCH}..HEAD" 2>/dev/null || true)"
  if [[ "$COMMIT_COUNT" != "1" ]]; then
    echo "No --title given, and '$SOURCE_BRANCH' is not exactly one commit ahead of '$TARGET_BRANCH'." >&2
    echo "Read 'git log origin/${TARGET_BRANCH}..HEAD', the diff and the linked work item, then pass one title for the whole change with --title." >&2
    exit 1
  fi
  TITLE="$(git log -1 --pretty=%s)"
fi

# Delimited, so a bare trailing number that is part of a name is not guessed as an id.
if [[ -z "$WORK_ITEMS" && "$SOURCE_BRANCH" =~ [-/]([0-9]+)$ ]]; then
  WORK_ITEMS="${BASH_REMATCH[1]}"
fi

ARGS=(
  --org "$AZDO_ORG_URL"
  --project "$AZDO_PROJECT"
  --repository "$AZDO_REPO"
  --source-branch "$SOURCE_BRANCH"
  --target-branch "$TARGET_BRANCH"
  --title "$TITLE"
  --squash true
  --output json
)
[[ -n "$DESCRIPTION" ]] && ARGS+=(--description "$DESCRIPTION")
# shellcheck disable=SC2206  # word-splitting the id list is the point
[[ -n "$WORK_ITEMS" ]] && ARGS+=(--work-items $WORK_ITEMS)

az repos pr create "${ARGS[@]}"
