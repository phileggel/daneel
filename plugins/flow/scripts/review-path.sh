#!/usr/bin/env bash
# Compute and print the next available reviewer report path for a given reviewer slug,
# in the project of the working directory.
# Usage: bash <plugin>/scripts/review-path.sh <reviewer-slug>
# Output: .review/<slug>-YYYY-MM-DD-NN.md  (NN is zero-padded, auto-incremented)
#
# In CI a reviewer calls this and writes its report there: the project's review
# workflow posts it on the pull request (protocol.md § The report). Locally the
# reviewer's reply is the report and nothing is written. The project gitignores
# `.review/`.
#
# Concurrency: the script reads-then-prints without locking, so two parallel
# callers can both compute -NN before either writes the file, and the second
# writer will clobber the first. Callers MUST serialize reviewer invocations
# within one checkout.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <reviewer-slug>" >&2
    exit 1
fi

SLUG="$1"
mkdir -p .review
DATE=$(date +%Y-%m-%d)

MAX=0
for f in .review/"${SLUG}-${DATE}"-*.md; do
    [[ -e "$f" ]] || continue
    NN="${f##*-}"
    NN="${NN%.md}"
    NN=$((10#$NN))
    ((NN > MAX)) && MAX=$NN
done

printf ".review/%s-%s-%02d.md\n" "$SLUG" "$DATE" $((MAX + 1))
