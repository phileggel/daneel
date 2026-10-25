#!/usr/bin/env bash
# batch-end.sh — end a batch with no `feat` or `fix`: tag the fresh `main` of the project in
# the working directory `batch/<UTC date>` and push the tag. Nothing is published.
#
# Use, from the project's checkout:   bash <skill>/scripts/batch-end.sh
set -euo pipefail
git fetch -q origin main --tags
if [ "$(git rev-parse --abbrev-ref HEAD)" != main ] || [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    echo "batch-end: check out a fresh main first" >&2
    exit 1
fi
tag="batch/$(date -u +%F)"
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
    echo "batch-end: $tag already exists — a batch already ended today" >&2
    exit 1
fi
git tag -a "$tag" -m "Batch ended without a release"
git push -q origin "refs/tags/$tag"
echo "batch-end: $tag pushed"
