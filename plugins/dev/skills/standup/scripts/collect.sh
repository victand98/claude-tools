#!/usr/bin/env bash
# Collects standup data: identity, time window, git commits, GitHub PRs,
# optional Linear activity and the previous standup. Read-only.
#
# Usage: collect.sh [--since YYYY-MM-DD] [--repos path1,path2] [--linear]
# Never exits non-zero, so a failure here never aborts the skill.

set -u

SINCE_DATE=""
EXTRA_REPOS=""
WITH_LINEAR=0
HISTORY_DIR="${STANDUP_HISTORY_DIR:-$HOME/.standup}"

while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE_DATE="${2:-}"; shift 2 ;;
    --repos) EXTRA_REPOS="${2:-}"; shift 2 ;;
    --linear) WITH_LINEAR=1; shift ;;
    *) shift ;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }

# ---- Dates (GNU date on Linux, BSD date on macOS) --------------------------
if date -d "2000-01-01" +%F >/dev/null 2>&1; then DATE_KIND=gnu; else DATE_KIND=bsd; fi

days_ago() { # $1 = number of days -> YYYY-MM-DD
  if [ "$DATE_KIND" = gnu ]; then date -d "-$1 days" +%F; else date -v-"$1"d +%F; fi
}

to_utc_iso() { # $1 = YYYY-MM-DD (local midnight) -> UTC ISO 8601
  if [ "$DATE_KIND" = gnu ]; then
    date -u -d "@$(date -d "$1 00:00" +%s)" +%Y-%m-%dT%H:%M:%SZ
  else
    date -u -r "$(date -j -f "%Y-%m-%d %H:%M:%S" "$1 00:00:00" +%s)" +%Y-%m-%dT%H:%M:%SZ
  fi
}

TODAY=$(date +%F)
DOW=$(date +%u) # 1 = Monday ... 7 = Sunday
OFFSET=$(date +%z)
TZ_NAME="${TZ:-$(readlink /etc/localtime 2>/dev/null | sed 's#.*/zoneinfo/##')}"

if [ -z "$SINCE_DATE" ]; then
  case "$DOW" in
    1) SINCE_DATE=$(days_ago 3) ;; # Monday -> Friday
    7) SINCE_DATE=$(days_ago 2) ;; # Sunday -> Friday
    *) SINCE_DATE=$(days_ago 1) ;;
  esac
fi
SINCE_UTC=$(to_utc_iso "$SINCE_DATE" 2>/dev/null || echo "${SINCE_DATE}T00:00:00Z")

echo "## Window"
echo "today: $TODAY ($(date +%A)) · timezone: ${TZ_NAME:-unknown} ($OFFSET)"
echo "since: $SINCE_DATE 00:00 local ($SINCE_UTC)"
echo

# ---- Identity --------------------------------------------------------------
EMAIL=$(git config user.email 2>/dev/null || true)
NAME=$(git config user.name 2>/dev/null || true)
GH_LOGIN=""
if have gh; then GH_LOGIN=$(gh api user --jq .login 2>/dev/null || true); fi

echo "## Me"
echo "git: ${NAME:-?} <${EMAIL:-?}> · github: ${GH_LOGIN:-unavailable}"
echo

# ---- Repositories ----------------------------------------------------------
REPOS="."
if [ -n "$EXTRA_REPOS" ]; then
  REPOS="$REPOS $(echo "$EXTRA_REPOS" | tr ',' ' ')"
fi

for raw in $REPOS; do
  dir="${raw/#\~/$HOME}"
  if ! git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "## Repo: $raw"
    echo "(not a git repository, skipped)"
    echo
    continue
  fi
  top=$(git -C "$dir" rev-parse --show-toplevel)
  remote=$(git -C "$top" remote get-url origin 2>/dev/null || true)
  slug=$(echo "$remote" | sed -nE 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#p')

  echo "## Repo: $(basename "$top")${slug:+ ($slug)}"

  git -C "$top" fetch --all --prune --quiet 2>/dev/null || echo "(git fetch failed, using local data)"

  echo "### My commits (all branches, no merges)"
  repo_email=$(git -C "$top" config user.email 2>/dev/null || echo "$EMAIL")
  commits=$(git -C "$top" log --all --no-merges \
    --since="$SINCE_DATE 00:00 $OFFSET" --author="$repo_email" \
    --format="%ad | %s | %D" --date=format:'%a %H:%M' 2>/dev/null)
  echo "${commits:-(none)}"

  if [ -n "$slug" ] && [ -n "$GH_LOGIN" ]; then
    echo "### My PRs updated since START"
    prs=$(gh pr list -R "$slug" --author @me --state all \
      --search "updated:>=$SINCE_DATE" \
      --json number,title,state,isDraft,mergedAt,reviewDecision,headRefName \
      --template '{{range .}}#{{.number}} | {{.state}}{{if .isDraft}} (draft){{end}}{{if .mergedAt}} merged {{.mergedAt}}{{end}} | review: {{.reviewDecision}} | {{.headRefName}} | {{.title}}{{"\n"}}{{end}}' \
      2>/dev/null)
    if [ $? -ne 0 ]; then
      # Fallback for environments where GraphQL is blocked: REST API.
      prs=$(gh api "repos/$slug/pulls?state=all&sort=updated&direction=desc&per_page=50" \
        --jq ".[] | select(.user.login == \"$GH_LOGIN\" and .updated_at >= \"$SINCE_UTC\")
              | \"#\(.number) | \(.state)\(if .draft then \" (draft)\" else \"\" end)\(if .merged_at then \" merged \(.merged_at)\" else \"\" end) | \(.head.ref) | \(.title)\"" \
        2>/dev/null || echo "(GitHub unavailable)")
    fi
    echo "${prs:-(none)}"

    echo "### PRs I reviewed since START"
    reviewed=$(gh search prs --repo "$slug" --reviewed-by @me --updated ">=$SINCE_DATE" \
      --json number,title,author --template '{{range .}}#{{.number}} | by {{.author.login}} | {{.title}}{{"\n"}}{{end}}' 2>/dev/null)
    if [ $? -ne 0 ]; then
      reviewed=""
      for n in $(gh api "repos/$slug/pulls?state=all&sort=updated&direction=desc&per_page=20" \
          --jq ".[] | select(.user.login != \"$GH_LOGIN\" and .updated_at >= \"$SINCE_UTC\") | .number" 2>/dev/null); do
        hit=$(gh api "repos/$slug/pulls/$n/reviews" \
          --jq "[.[] | select(.user.login == \"$GH_LOGIN\" and .submitted_at >= \"$SINCE_UTC\")] | length" 2>/dev/null || echo 0)
        if [ "${hit:-0}" -gt 0 ]; then
          reviewed="$reviewed$(gh api "repos/$slug/pulls/$n" --jq '"#\(.number) | by \(.user.login) | \(.title)"' 2>/dev/null)"$'\n'
        fi
      done
    fi
    echo "${reviewed:-(none)}"
  fi
  echo
done

# ---- Linear ----------------------------------------------------------------
if [ "$WITH_LINEAR" = 1 ]; then
  echo "## Linear"
  if [ -n "${LINEAR_API_KEY:-}" ]; then
    query='query($s: DateTimeOrDuration!){ viewer { assignedIssues(first: 50, filter: {updatedAt: {gte: $s}}) { nodes { identifier title state { name type } } } } comments(first: 50, filter: {createdAt: {gte: $s}, user: {isMe: {eq: true}}}) { nodes { body issue { identifier title } } } }'
    payload=$(printf '{"query":"%s","variables":{"s":"%s"}}' "$(echo "$query" | sed 's/"/\\"/g')" "$SINCE_UTC")
    resp=$(curl -sS https://api.linear.app/graphql \
      -H "Content-Type: application/json" -H "Authorization: $LINEAR_API_KEY" \
      -d "$payload" 2>&1)
    if have jq && echo "$resp" | jq -e '.data' >/dev/null 2>&1; then
      echo "### Issues assigned to me, updated since START"
      echo "$resp" | jq -r '.data.viewer.assignedIssues.nodes[] | "\(.identifier) | \(.state.name) | \(.title)"'
      echo "### My comments since START"
      echo "$resp" | jq -r '.data.comments.nodes[] | "\(.issue.identifier) | \(.body | gsub("\n"; " ") | .[0:200])"'
    else
      echo "LINEAR_ERROR: $(echo "$resp" | head -c 400)"
    fi
  else
    echo "LINEAR_API_KEY not set (use the Linear MCP tools instead)"
  fi
  echo
fi

# ---- Previous standup -------------------------------------------------------
echo "## Previous standup"
prev=$(ls -1 "$HISTORY_DIR"/*.md 2>/dev/null | grep -v "/$TODAY.md$" | sort | tail -1)
if [ -n "$prev" ]; then
  echo "file: $(basename "$prev")"
  cat "$prev"
else
  echo "(none)"
fi
echo

# ---- Output formats ---------------------------------------------------------
formats="$(cd "$(dirname "$0")/.." && pwd)/formats.md"
if [ -f "$formats" ]; then
  echo "## Output formats"
  sed '1{/^# /d;}' "$formats" | sed 's/^## /### /'
fi

exit 0
