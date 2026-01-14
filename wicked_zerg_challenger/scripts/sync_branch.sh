#!/bin/bash
# Created: 2026-01-11 00:15:00 UTC
# Version: 1.0
# Description: Syncs the current branch with the base branch (main).

BASE_BRANCH="main"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$CURRENT_BRANCH" == "$BASE_BRANCH" ]]; then
    echo "? You are already on $BASE_BRANCH."
    exit 1
fi

echo "? Syncing $CURRENT_BRANCH with $BASE_BRANCH..."
git fetch origin $BASE_BRANCH
git merge origin/$BASE_BRANCH

if [[ $? -eq 0 ]]; then
    echo "? Successfully synced with $BASE_BRANCH."
else
    echo "? Merge conflicts detected. Please resolve them manually."
fi
