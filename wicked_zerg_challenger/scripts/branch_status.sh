#!/bin/bash
# Created: 2026-01-11 00:15:00 UTC
# Version: 1.0
# Description: Checks the health and sync status of the current branch.

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "? Status for branch: $CURRENT_BRANCH"

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo "??  You have uncommitted changes."
else
    echo "? Working tree is clean."
fi

# Check sync status with origin
git fetch origin > /dev/null 2>&1
BEHIND=$(git rev-list --count HEAD..origin/"$CURRENT_BRANCH" 2>/dev/null)
AHEAD=$(git rev-list --count origin/"$CURRENT_BRANCH"..HEAD 2>/dev/null)

if [[ -z "$BEHIND" ]]; then
    echo "??  Branch not pushed to origin yet."
else
    echo "? Sync Status: $AHEAD commits ahead, $BEHIND commits behind origin."
fi
