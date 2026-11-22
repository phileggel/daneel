#!/usr/bin/env bash
# publish.sh — publish an accepted spec change to the spec's own repository.
#
# Use, from the project's checkout:
#   bash <skill>/scripts/publish.sh <owner/name> <clone> <id>
#     <owner/name>  the spec repository (`spec-proposal.repo`)
#     <clone>       a clone of it, on `main`, holding the accepted change uncommitted
#     <id>          the issue number, or the slug of a chat request
# Commits every change of <clone> as `spec: <project>#<id>` (`spec: <id>` for a slug),
# <project> the project's own `owner/name`, pushes the clone's `main`, prints the sha.
# Exit: 0 published · 1 refused or failed, the reason printed · 2 a usage error
#
# It refuses a clone of another repository, the project itself (a project's `main` takes
# no push), a clone that is not on `main`, and a clone with nothing to publish. Nothing
# checks the owner's yes: the skill runs this only after it.
set -euo pipefail

usage() { echo "usage: publish.sh <owner/name> <clone> <id>" >&2; exit 2; }
refuse() { echo "publish: $*" >&2; exit 1; }

origin_of() { git -C "$1" config remote.origin.url | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##'; }

[ $# -eq 3 ] || usage
repo=$1 clone=$2 id=$3
[ -d "$clone/.git" ] || refuse "$clone is not a clone"
[ "$(origin_of "$clone")" = "$repo" ] || refuse "$clone is not a clone of $repo"
project=$(origin_of .)
[ "$project" != "$repo" ] || refuse "$repo is the project itself; it takes no push to main"
[ "$(git -C "$clone" branch --show-current)" = main ] || refuse "$clone is not on main"
[ -n "$(git -C "$clone" status --porcelain)" ] || refuse "$clone holds no change to publish"
case "$id" in
*[!0-9]*) title="spec: $id" ;;
*) title="spec: $project#$id" ;;
esac
git -C "$clone" add -A
git -C "$clone" commit -q -m "$title"
git -C "$clone" push -q origin main
git -C "$clone" rev-parse HEAD
