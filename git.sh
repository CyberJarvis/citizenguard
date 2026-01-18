#!/bin/bash
echo "Current branch: $(git branch --show-current)"
git status

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
MESSAGE="UI Improvement Auto – $TIMESTAMP"

git add .

if git diff --cached --quiet; then
    echo "No changes to commit."
    exit 0
fi

git commit -m "$MESSAGE"

git push origin UI_beta

echo "Push complete!"
