#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: scripts/commit_and_push.sh <branch-name>"
  exit 1
fi
BR="$1"
git checkout -b "$BR"
git add .
git commit -m "chore: infra + docker + ci"
git push -u origin "$BR"
echo "Now open a PR from $BR -> dev"
