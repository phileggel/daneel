#!/usr/bin/env bash
# batch-end.sh — end a batch with no `feat` or `fix`: tag the fresh `main` of the project in
# the working directory `batch/<UTC date>` (`batch/<UTC date>.2` for a second batch that
# day) and push the tag. Nothing is published.
#
# Use, from the project's checkout:   bash <skill>/scripts/batch-end.sh
set -euo pipefail
git fetch -q origin main --tags
head=$(git rev-parse HEAD)
if [ "$(git rev-parse --abbrev-ref HEAD)" != main ] || [ "$head" != "$(git rev-parse origin/main)" ]; then
    echo "batch-end: check out a fresh main first" >&2
    exit 1
fi
ended=$(git tag --points-at "$head" --list 'v*' 'batch/*' | head -n 1)
if [ -n "$ended" ]; then
    echo "batch-end: $ended already ends a batch at this commit" >&2
    exit 1
fi
day="batch/$(date -u +%F)"
tag=$day
n=2
while git rev-parse -q --verify "refs/tags/$tag" >/dev/null; do
    tag="$day.$n"
    n=$((n + 1))
done
git tag -a "$tag" -m "Batch ended without a release"
git push -q origin "refs/tags/$tag"
echo "batch-end: $tag pushed"
