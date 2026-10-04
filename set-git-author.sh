#!/usr/bin/env bash
#
# Put YOUR name on the whole commit history.
#
# The commits in this repository were made while building the project and are
# authored "Your Name <you@example.com>" - a placeholder. Run this once and
# every commit is re-attributed to you.
#
#     bash tools/set-git-author.sh "Your Name" "you@example.com"
#
# It rewrites history, which is fine here: nothing has been pushed anywhere
# yet. Do NOT run it after you have pushed to GitHub, or your local history
# will no longer match the remote and pushing will be refused.
#
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: bash tools/set-git-author.sh \"Your Name\" \"you@example.com\""
    echo
    echo "example: bash tools/set-git-author.sh \"Aman Sharma\" \"aman@gmail.com\""
    exit 1
fi

NAME="$1"
EMAIL="$2"

cd "$(dirname "$0")/.."

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "This is not a git repository. Nothing to do."
    exit 1
fi

CURRENT="$(git log -1 --format='%an <%ae>' 2>/dev/null || echo '(no commits)')"
COUNT="$(git rev-list --count HEAD 2>/dev/null || echo 0)"

echo "Repository : $(pwd)"
echo "Commits    : $COUNT"
echo "Currently  : $CURRENT"
echo "Rewriting  : $NAME <$EMAIL>"
echo

git -c user.name="$NAME" -c user.email="$EMAIL" \
    filter-branch -f --env-filter "
        export GIT_AUTHOR_NAME='$NAME'
        export GIT_AUTHOR_EMAIL='$EMAIL'
        export GIT_COMMITTER_NAME='$NAME'
        export GIT_COMMITTER_EMAIL='$EMAIL'
    " -- --all > /dev/null 2>&1

# filter-branch leaves the original refs behind; tidy up
rm -rf .git/refs/original
git -c user.name="$NAME" -c user.email="$EMAIL" reflog expire --expire=now --all
git gc --prune=now --quiet

# and set it as the default for any future commits
git config user.name "$NAME"
git config user.email "$EMAIL"

echo "Done."
echo
git log --oneline | head -5
echo "..."
echo
echo "Every commit is now authored by: $(git log -1 --format='%an <%ae>')"
echo
echo "Next: push it to GitHub (see SUBMISSION.md)."
