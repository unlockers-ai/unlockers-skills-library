#!/usr/bin/env bash
# Nightly design-drift review: the review-drift skill, run only when main moved.
#
# If a merge landed on $DRIFT_REF since the last reviewed commit (the newest
# `drift/<date>` tag), gather the candidate seeds and run the skill in a
# throwaway worktree on each model, merge the reports, then hand the result to
# drift_publish.py: findings → issues (or comments on the issue that already
# covers them), a digest → the tracking issue, the reviewed commit → a new
# `drift/<date>` tag, the report → a secret gist. Nothing is committed; the
# reports stay under $DRIFT_CACHE.
#
# Needs git, gh and claude logged in, with the review-drift skill installed in the
# repository or in ~/.claude/skills. CodeScene is optional: if its MCP server is
# configured for claude, the skill uses it — and fails the review if it is
# configured but broken.
#
# Run from the repository, by hand or from cron/launchd/a CI schedule:
#   review-drift-nightly.sh [--force]
#
# Knobs (env), all optional:
#   DRIFT_MODELS="opus"         models to run, space-separated; several are merged afterwards
#   DRIFT_REF=origin/main       what to review (a branch, for a pre-merge smoke run)
#   DRIFT_BASE=<sha>            window start (default: newest drift/* tag, else REF~5)
#   DRIFT_TRACKING_ISSUE=<n>    issue that collects the digests (default: print only)
#   DRIFT_NO_PUBLISH=1          write the reports, run the publisher in --dry-run only
#   DRIFT_CACHE=~/.cache/review-drift/<repo>
#   DESIGN_LINT, COCHANGE_SINCE passed through to design-candidates.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git rev-parse --show-toplevel)"
CACHE="${DRIFT_CACHE:-$HOME/.cache/review-drift/$(basename "$REPO")}"
read -r -a MODELS <<< "${DRIFT_MODELS:-opus}"
DATE=$(date +%F)
OUT="$CACHE/reports/$DATE"
START=$(date +%s)
mkdir -p "$OUT"

say()  { echo "review-drift $(date '+%F %T'): $*"; }
fail() { say "RED — $*"; exit 1; }

# --- preconditions: red, never a skip -----------------------------------------
for t in git gh claude python3; do command -v "$t" >/dev/null || fail "$t not on PATH"; done

# --- did main move since the last reviewed commit? ---------------------------
cd "$REPO"
REF="${DRIFT_REF:-origin/main}"
git fetch -q origin "+refs/tags/drift/*:refs/tags/drift/*" 2>/dev/null || true
git fetch -q origin
NEW=$(git rev-parse "$REF")
LAST_TAG=$(git tag -l 'drift/*' --sort=-creatordate | head -1)
LAST=""; [[ -n "$LAST_TAG" ]] && LAST=$(git rev-parse "$LAST_TAG^{commit}")
if [[ "${1:-}" != "--force" && -n "$LAST" ]]; then
  [[ "$NEW" == "$LAST" ]] && { say "nothing new on $REF since $LAST_TAG"; exit 0; }
  # Squash-only histories have no merge commits: any first-parent commit counts.
  [[ -z "$(git log --first-parent --format=%h "$LAST..$NEW")" ]] && { say "nothing landed since $LAST_TAG"; exit 0; }
fi
BASE="${DRIFT_BASE:-${LAST:-$(git rev-parse "$REF~5")}}"
say "reviewing $BASE..$NEW ($REF) on ${MODELS[*]} → $OUT"

# --- throwaway detached worktree ---------------------------------------------
WT=$(mktemp -d "${TMPDIR:-/tmp}/review-drift-$DATE-XXXX")
git worktree add -q --detach "$WT" "$REF"
trap 'git -C "$REPO" worktree remove --force "$WT" 2>/dev/null || true' EXIT
cd "$WT"

# --- seeds once, one review per model, then the merge ------------------------
DESIGN_DIR=.design "$HERE/design-candidates.sh" || fail "design-candidates failed"

ALLOWED='Bash,Read,Grep,Glob,Write,Edit,ToolSearch,mcp__codescene__analyze_change_set,mcp__codescene__code_health_review,mcp__codescene__code_health_score'
PREV=$(ls -d "$CACHE"/reports/*/ 2>/dev/null | grep -v "/$DATE/" | sort | tail -1 || true)
PREV_NOTE=""; [[ -n "$PREV" && -f "$PREV/report.md" ]] && PREV_NOTE=" The previous report (for its not-findings ledger) is ${PREV}report.md."
for m in "${MODELS[@]}"; do
  if [[ -s "$OUT/report-$m.md" && -s "$OUT/report-$m.findings.json" ]]; then
    say "model $m already reviewed today — reusing $OUT/report-$m.md"; continue
  fi
  say "model $m"
  claude -p "/review-drift base=$BASE report=$OUT/report-$m.md$PREV_NOTE" \
      --model "$m" --allowedTools "$ALLOWED" --max-turns 200 \
      > "$OUT/$m.log" 2>&1 \
    || fail "claude ($m) exited non-zero — see $OUT/$m.log"
  [[ -s "$OUT/report-$m.md" ]] || fail "model $m wrote no report"
  # Accept the literal "<report>.findings.json" spelling rather than lose a finished review.
  [[ -s "$OUT/report-$m.md.findings.json" ]] && mv "$OUT/report-$m.md.findings.json" "$OUT/report-$m.findings.json"
  [[ -s "$OUT/report-$m.findings.json" ]] || fail "model $m wrote no findings.json"
done

if [[ ${#MODELS[@]} -gt 1 ]]; then
  claude -p "Merge the drift reports $OUT/report-*.md into one, $OUT/report.md, in the same shape: keep every distinct finding once (the fuller version, crediting which models found it), keep the union of the not-findings ledgers, rank by leverage. Merge the matching $OUT/report-*.findings.json the same way into $OUT/report.findings.json (same schema; 'models' lists every model that found the finding; a finding is the same finding when it names the same seed and siblings). Do not delete the per-model files. Do not run git." \
      --model "${MODELS[0]}" --allowedTools "Read,Write,Glob" --max-turns 40 \
      > "$OUT/merge.log" 2>&1 || fail "merge step failed — see $OUT/merge.log"
else
  cp "$OUT/report-${MODELS[0]}.md" "$OUT/report.md"
  cp "$OUT/report-${MODELS[0]}.findings.json" "$OUT/report.findings.json"
fi
[[ -s "$OUT/report.md" && -s "$OUT/report.findings.json" ]] || fail "no merged report"

# --- publish: deterministic, no model ----------------------------------------
DURATION="$(( ($(date +%s) - START) / 60 )) min"
ARGS=(--findings "$OUT/report.findings.json" --report "$OUT/report.md" --date "$DATE" --duration "$DURATION")
[[ -n "${DRIFT_TRACKING_ISSUE:-}" ]] && ARGS+=(--tracking-issue "$DRIFT_TRACKING_ISSUE")
[[ -n "${DRIFT_NO_PUBLISH:-}" ]] && ARGS+=(--dry-run)
python3 "$HERE/drift_publish.py" "${ARGS[@]}" 2>&1 | tee "$OUT/publish.log" \
  || fail "publish failed — see $OUT/publish.log"

say "done in $DURATION — $OUT"
