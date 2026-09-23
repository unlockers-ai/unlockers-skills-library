#!/usr/bin/env bash
# Gather candidate seeds and siblings for the review-drift skill into .design/.
# Run from the repository root. Every tool is optional: a missing one is
# recorded in .design/tools.txt, which the reviewer copies into its report as
# "what I did not check" — a skipped tool must never look like a clean result.
#
# Usage: design-candidates.sh [PATH ...]      (default: the whole tree)
# Env:   DESIGN_DIR=.design   COCHANGE_SINCE="90 days ago"
#        DESIGN_LINT="<command>"  a project's own design linter or ratchet, if it has one
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${DESIGN_DIR:-.design}"
PATHS=("$@"); [[ ${#PATHS[@]} -eq 0 ]] && PATHS=(.)

rm -rf "$OUT" && mkdir -p "$OUT"
TOOLS="$OUT/tools.txt"
: > "$TOOLS"
ran()     { echo "ran      $1" >> "$TOOLS"; }
missing() { echo "missing  $1 — $2" >> "$TOOLS"; }

# Duplication, any language.
if command -v npx >/dev/null; then
  npx --yes jscpd@4 "${PATHS[@]}" --min-lines 6 --min-tokens 50 \
      --ignore '**/node_modules/**,**/.venv/**,**/dist/**,**/build/**,**/.design/**' \
      --reporters json --output "$OUT/jscpd" --silent >/dev/null 2>&1 \
    && ran "jscpd (clone pairs) → jscpd/jscpd-report.json" \
    || missing jscpd "npx jscpd@4 failed"
else
  missing jscpd "no npx: clone pairs not computed"
fi

# Python-specific: duplication and complexity, only where there is Python.
if git ls-files '*.py' | grep -q .; then
  if command -v pylint >/dev/null; then
    pylint --disable=all --enable=duplicate-code -f json --exit-zero "${PATHS[@]}" \
        > "$OUT/pylint-dup.json" 2>/dev/null && ran "pylint duplicate-code → pylint-dup.json"
  else
    missing pylint "no second opinion on duplication"
  fi
  if command -v ruff >/dev/null; then
    ruff check "${PATHS[@]}" --select C901,PLR0912,PLR0913,PLR0915,PLR0917 \
        --output-format json --exit-zero > "$OUT/ruff.json" 2>/dev/null \
      && ran "ruff complexity and argument counts → ruff.json"
  else
    missing ruff "no complexity or argument-count hits"
  fi
fi

# Files that change together, from git alone.
python3 "$HERE/cochange.py" --since "${COCHANGE_SINCE:-90 days ago}" --json "${PATHS[@]}" \
    > "$OUT/cochange.json" \
  && ran "co-change pairs → cochange.json" \
  || missing cochange "git log failed"

# A project's own design linter or ratchet: its hits are seeds too.
if [[ -n "${DESIGN_LINT:-}" ]]; then
  bash -c "$DESIGN_LINT" > "$OUT/lint-design.txt" 2>&1; ran "$DESIGN_LINT → lint-design.txt"
fi

cat "$TOOLS"
