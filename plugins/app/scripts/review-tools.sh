#!/usr/bin/env bash
# review-tools.sh — the tools a reviewer's CI session is granted, for the project in the
# working directory.
#
# Use, from the project's checkout:
#   bash <plugin>/scripts/review-tools.sh <lane>
# Prints one line for `--allowedTools`: each entry in double quotes, a space between two.
# The project's workflow passes it as is, and adds after it what its own rules documents
# make a lane run.
# Exit: 0 printed · 2 a usage error, or a lane `review-lanes.sh` does not know
#
# What is granted, and why:
#   Read, Grep, Glob       the reviewer reads; it never edits what it reviews
#   Edit(.review/**)       the report, the only file a reviewer writes (protocol.md § The
#                          report). An `Edit` rule also grants the Write tool. A rule
#                          without a leading slash reads from the session's current
#                          folder, which a `cd` moves, so the folder is granted a second
#                          time from the filesystem root (`//` before an absolute path):
#                          a session that changed folder still writes its report.
#   the two helpers        `branch.sh` and `review-path.sh` of this plugin, spelled both
#                          ways a session runs them: from the checkout, and absolute
#   git, read only         the subcommands the lanes and the protocol name
#   grep, ls, wc, head, tail
#   infra only             `git ls-remote --tags https://github.com/*`: the lane judges an
#                          action's pin against its tags
# No interpreter, test runner or build tool: once one runs, this list constrains nothing.
set -euo pipefail

LANES=(backend frontend arch sql infra security e2e spec contract adr guides)

usage() {
    echo "usage: bash review-tools.sh <lane>   (${LANES[*]})" >&2
    exit 2
}

[ "$#" -eq 1 ] || usage
lane=$1
known=false
for name in "${LANES[@]}"; do
    [ "$name" = "$lane" ] && known=true
done
[ "$known" = true ] || usage

plugin=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
here=$(pwd -P)
relative=$(python3 -c 'import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$plugin" "$here")

tools=(
    "Read" "Grep" "Glob"
    "Edit(.review/**)" "Edit(/$here/.review/**)"
    "Bash(bash $relative/scripts/branch.sh *)" "Bash(bash $relative/scripts/review-path.sh *)"
    "Bash(bash $plugin/scripts/branch.sh *)" "Bash(bash $plugin/scripts/review-path.sh *)"
    "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)"
    "Bash(git status)" "Bash(git status *)" "Bash(git rev-parse *)" "Bash(git merge-base *)"
    "Bash(git cat-file *)" "Bash(git ls-files)" "Bash(git ls-files *)"
    "Bash(grep *)" "Bash(ls)" "Bash(ls *)" "Bash(wc *)" "Bash(head *)" "Bash(tail *)"
)
if [ "$lane" = infra ]; then
    tools+=("Bash(git ls-remote --tags https://github.com/*)")
fi

line=""
for tool in "${tools[@]}"; do
    line+="\"$tool\" "
done
printf '%s\n' "${line% }"
