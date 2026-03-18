#!/bin/bash
# Check for new PRs and notify Kimi
# Run via cron every 5 minutes
# Requires: GITHUB_TOKEN environment variable

REPO="egeg23/Test-repos"
STATE_FILE="/tmp/coderabbit_prs.json"

# Check if token exists
if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN not set"
  exit 1
fi

# Get open PRs
PRS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO/pulls?state=open")

# Check if there are any PRs
COUNT=$(echo "$PRS" | jq length 2>/dev/null || echo "0")

if [ "$COUNT" -gt 0 ]; then
  # For each PR, check if we've seen it before
  echo "$PRS" | jq -c '.[]' 2>/dev/null | while read -r PR; do
    PR_NUMBER=$(echo "$PR" | jq -r '.number')
    PR_TITLE=$(echo "$PR" | jq -r '.title')
    PR_URL=$(echo "$PR" | jq -r '.html_url')
    
    # Check if already notified
    if [ -f "$STATE_FILE" ]; then
      LAST_PR=$(cat "$STATE_FILE")
      if [ "$LAST_PR" != "$PR_NUMBER" ]; then
        echo "[$(date)] NEW PR: #$PR_NUMBER - $PR_TITLE" >> /var/log/coderabbit_prs.log
        echo "$PR_NUMBER" > "$STATE_FILE"
      fi
    else
      echo "$PR_NUMBER" > "$STATE_FILE"
    fi
  done
fi