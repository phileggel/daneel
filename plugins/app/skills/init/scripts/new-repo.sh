#!/usr/bin/env bash
# new-repo.sh — give a project's spec or its mocks a repository of their own.
#
# Use, from the project's checkout:
#   bash <skill>/scripts/new-repo.sh spec <owner/name> <folder>
#   bash <skill>/scripts/new-repo.sh design <owner/name>
#     <owner/name>  the repository to hold the spec, or the mocks
#     <folder>      the project's spec folder, from the checkout's root
# Each step is done only when missing, and printed as `created` or `present`:
#   - the repository, private, with a README, so that its `main` exists;
#   - for `spec`: a clone of it at <folder>, and <folder> in the project's `.gitignore`.
# Then it prints what the project still owes: the key for `.claude/daneel.json` and, for
# `spec`, the deny line that only the owner adds to `.claude/settings.json`.
# Exit: 0 done · 1 refused or failed, the reason printed · 2 a usage error
#
# It refuses the project itself, a <folder> git tracks (a spec already in the project
# moves by hand: the plugin's README, § A spec in its own repository), a <folder> that
# is not a clone of <owner/name>, and a clone that is not on `main`. Every refusal that
# needs no repository comes before one is created. Nothing is deleted or overwritten.
set -euo pipefail

usage() { echo "usage: new-repo.sh spec <owner/name> <folder> | new-repo.sh design <owner/name>" >&2; exit 2; }
refuse() { echo "new-repo: $*" >&2; exit 1; }

origin_of() { git -C "$1" config remote.origin.url | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##'; }

kind=${1:-}
case "$kind" in
spec) [ $# -eq 3 ] || usage ;;
design) [ $# -eq 2 ] || usage ;;
*) usage ;;
esac
repo=$2
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || refuse "$repo is not <owner/name>"
cd "$(git rev-parse --show-toplevel)"
[ "$(origin_of .)" != "$repo" ] || refuse "$repo is the project itself"

folder=
if [ "$kind" = spec ]; then
    folder=${3%/}
    case "$folder" in "" | /* | *..*) refuse "${3:-''} is not a folder of the project" ;; esac
    [ -z "$(git ls-files -- "$folder")" ] ||
        refuse "git tracks $folder: a spec already in the project moves by hand (the plugin's README, § A spec in its own repository)"
    if [ -e "$folder" ]; then
        [ -d "$folder/.git" ] && [ "$(origin_of "$folder")" = "$repo" ] || refuse "$folder exists and is not a clone of $repo"
    fi
fi

if gh repo view "$repo" --json name >/dev/null 2>&1; then
    echo "present: the repository $repo"
else
    gh repo create "$repo" --private --add-readme >/dev/null || refuse "$repo could not be created"
    echo "created: the private repository $repo"
fi

if [ "$kind" = design ]; then
    echo "to add to .claude/daneel.json: \"design-proposal\": {\"repo\": \"$repo\"}"
    exit 0
fi

if [ -e "$folder" ]; then
    echo "present: the clone at $folder"
else
    gh repo clone "$repo" "$folder" >/dev/null 2>&1 || refuse "$repo could not be cloned at $folder"
    echo "created: the clone at $folder"
fi
branch=$(git -C "$folder" branch --show-current)
[ "$branch" = main ] || refuse "$folder is on '$branch': a spec is published to main"

if git check-ignore -q "$folder"; then
    echo "present: $folder in .gitignore"
else
    # A last line with no newline would swallow the new one.
    [ ! -s .gitignore ] || [ -z "$(tail -c1 .gitignore)" ] || echo >> .gitignore
    echo "/$folder/" >> .gitignore
    echo "created: /$folder/ in .gitignore"
fi

echo "to add to .claude/daneel.json: \"spec-proposal\": {\"repo\": \"$repo\"}"
echo "for the owner, under permissions.deny in .claude/settings.json: \"Edit(/$folder/**)\""
