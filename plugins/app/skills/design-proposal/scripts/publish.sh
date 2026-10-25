#!/usr/bin/env bash
# publish.sh — publish a design proposal's mocks and note, never on the project's `main`.
#
#   publish.sh repo <owner/name> <clone> <id>   commit <clone>/<id> and push the clone's
#                                               `main`; the clone's origin must be
#                                               <owner/name>, never the project's own
#   publish.sh branch <id>                      from the project's `main`: commit
#                                               screenshots/design on `design/<id>`, push
#                                               it, and switch back to `main`
#
# The capture's `.console-errors.json` is never committed. Prints the commit's sha.
# Exit codes: 0 published; 1 refused or failed; 2 usage error.
set -euo pipefail

usage() { echo "usage: publish.sh repo <owner/name> <clone> <id> | publish.sh branch <id>" >&2; exit 2; }
refuse() { echo "publish: $*" >&2; exit 1; }

origin_of() { git -C "$1" config remote.origin.url | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##'; }

case "${1:-}" in
repo)
    [ $# -eq 4 ] || usage
    repo=$2 clone=$3 id=$4
    [ -d "$clone/$id" ] || refuse "$clone/$id does not exist"
    [ "$(origin_of "$clone")" = "$repo" ] || refuse "$clone is not a clone of $repo"
    [ "$(origin_of .)" != "$repo" ] || refuse "$repo is the project itself; it takes no push to main"
    [ "$(git -C "$clone" branch --show-current)" = main ] || refuse "$clone is not on main"
    git -C "$clone" add -- "$id" ":!$id/.console-errors.json"
    git -C "$clone" commit -q -m "design: $id"
    git -C "$clone" push -q origin main
    git -C "$clone" rev-parse HEAD
    ;;
branch)
    [ $# -eq 2 ] || usage
    id=$2
    [ "$(git branch --show-current)" = main ] || refuse "start from main"
    git switch -q -c "design/$id"
    if git add -- screenshots/design ":!screenshots/design/.console-errors.json" &&
        git commit -q -m "design: $id" &&
        git push -q -u origin "refs/heads/design/$id"; then
        git rev-parse HEAD
        git switch -q main
    else
        git switch -q main
        refuse "design/$id was not published"
    fi
    ;;
*) usage ;;
esac
