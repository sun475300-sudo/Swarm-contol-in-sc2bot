#!/bin/bash
# Created: 2026-01-11 00:15:00 UTC
# Version: 1.0
# Description: Creates a new Git branch with validation conforming to the project strategy.

TYPE=$1
NAME=$2

if [[ -z "$TYPE" || -z "$NAME" ]]; then
    echo "Usage: ./create_branch.sh <type> <name>"
    echo "Types: feature, bugfix, hotfix, experiment, release"
    exit 1
fi

BRANCH_NAME="${TYPE}/${NAME}"

# Validate branch name format
if [[ ! "$BRANCH_NAME" =~ ^(feature|bugfix|hotfix|experiment|release)/[a-z0-9-]+$ ]]; then
    echo "? Error: Invalid branch name format."
    echo "  - Type must be one of: feature, bugfix, hotfix, experiment, release"
    echo "  - Name must be lowercase, alphanumeric, with hyphens."
    exit 1
fi

git checkout -b "$BRANCH_NAME"
echo "? Branch '$BRANCH_NAME' created successfully."
