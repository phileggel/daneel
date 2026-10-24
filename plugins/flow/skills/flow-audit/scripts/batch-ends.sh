#!/usr/bin/env bash
# batch-ends.sh — the last N batch ends of the project in the working directory,
# newest first: its releases (`v*` tags) and the `batch/<date>` tags of batches that
# ended without one.
#
# Use, from the project's checkout:   bash <skill>/scripts/batch-ends.sh [N]   (default 1)
set -euo pipefail
git fetch -q origin --tags
git for-each-ref --sort=-creatordate --count="${1:-1}" --format='%(refname:short)' 'refs/tags/v*' refs/tags/batch/
