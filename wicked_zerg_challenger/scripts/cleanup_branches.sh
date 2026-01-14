#!/bin/bash
# Created: 2026-01-11 00:15:00 UTC
# Version: 1.0
# Description: Prunes merged and stale branches.

echo "? Cleaning up local branches merged into main..."
git fetch -p
git branch --merged main | grep -v "main" | xargs -n 1 git branch -d
echo "? Cleanup complete."
