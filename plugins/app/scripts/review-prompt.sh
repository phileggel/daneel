#!/usr/bin/env bash
# review-prompt.sh — the instruction a reviewer's CI session is given, for the project in
# the working directory, once `review-prepare.sh` has run there.
#
# Use, from the project's checkout:
#   bash <plugin>/scripts/review-prompt.sh <lane> <tree>
#     <lane>  one of `review-lanes.sh`'s
#     <tree>  the folder `review-prepare.sh` filled with the commit under review
# Prints the prompt. The project's workflow passes it as is, and may add lines after it.
# Exit: 0 printed · 2 a usage error, an unknown lane, settings that cannot be read, or an
#       unknown `spec-proposal` key
#
# It says which agent file the session follows and on what, what `${CLAUDE_PLUGIN_ROOT}`
# stands for (Claude Code fills it only for an installed plugin), what on disk is the base
# branch's, where the files under review are, and where the report goes. The spec,
# contract and ADR lanes are pointed at the changed files of their folder, the folder of
# the first path of `review.rules.<kind>` in `.claude/daneel.json` (defaults `docs/spec`,
# `docs/contracts`, `docs/adr`). When the project keeps its spec in its own repository
# (`spec-proposal.repo`), CI has no access to it: those three lanes are told so, and to
# check what needs no spec. A key of `spec-proposal` no piece reads is refused.
set -euo pipefail

LANES=(backend frontend arch sql infra security e2e spec contract adr guides)

usage() {
    echo "usage: bash review-prompt.sh <lane> <tree>   (${LANES[*]})" >&2
    exit 2
}

[ "$#" -eq 2 ] || usage
lane=$1
known=false
for name in "${LANES[@]}"; do
    [ "$name" = "$lane" ] && known=true
done
[ "$known" = true ] || usage
tree=${2%/}

plugin=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
relative=$(python3 -c 'import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$plugin" "$(pwd -P)")

# The lane's folder, then whether the spec is here or in a repository of its own.
answer=$(python3 -c '
import json, sys
from pathlib import Path
kind = sys.argv[1]
defaults = {"spec": "docs/spec", "contract": "docs/contracts", "adr": "docs/adr"}
path = Path(".claude/daneel.json")
try:
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
except json.JSONDecodeError as error:
    sys.exit(f"review-prompt: {path} is not JSON: {error}")
own = settings.get("spec-proposal", {})
strange = sorted(set(own) - {"repo"})
if strange:
    sys.exit(f"review-prompt: unknown spec-proposal settings in {path}: {chr(44).join(strange)}")
first = (settings.get("review", {}).get("rules", {}).get(kind) or [None])[0]
folder = first.rsplit("/", 1)[0] if first and "/" in first else defaults.get(kind, "-")
print(folder, "elsewhere" if own.get("repo") and kind in defaults else "here")
' "$lane") || exit 2
folder=${answer% *}
kept=${answer##* }

case "$lane" in
spec)
    agent=spec-reviewer
    target="on each file under \`$folder/\` that the pull request changed, its README aside, one after the other, in the protocol's changed-lines mode"
    ;;
contract)
    agent=contract-reviewer
    target="on each file under \`$folder/\` that the pull request changed, its README aside, one after the other, against its spec, in the protocol's changed-lines mode"
    ;;
adr)
    agent=adr-reviewer
    target="on each file under \`$folder/\` that the pull request changed, one after the other: a finding on what the pull request did not change is listed without a severity"
    ;;
*)
    agent=reviewer-$lane
    target="in its default changed-lines mode"
    ;;
esac

cat <<EOF
You are the \`$agent\` reviewer of this repository.
Read \`$relative/agents/$agent.md\` and follow it exactly, $target, against the current branch.
\`\${CLAUDE_PLUGIN_ROOT}\` in it is \`$relative\`, from the working directory: run the helpers exactly as \`bash $relative/scripts/<helper> …\`. \`bash $relative/scripts/branch.sh files\` gives the changed files, \`bash $relative/scripts/branch.sh diff <path> [<path> ...]\` the whole diff in one call.
The working directory's \`CLAUDE.md\`, \`.claude/\` and rules documents are the base branch's, and \`$relative\` is the pinned release: your instructions, not what you review.
Read, grep and glob the pull request's files, and the documents you check them against, in \`$tree/\`: the branch's tree as pushed, the same paths. Where a prompt says \`git show HEAD:<path>\`, read the file there.
Nobody answers a question here: a prompt that asks which document to review gets every file of its lane that \`branch.sh files\` lists.
Save the full report with the Write tool at the path \`bash $relative/scripts/review-path.sh reviewer-$lane\` prints, whatever the agent file says about where its output goes. Begin it with one headline: \`🔴 N critical, 🟡 N warning(s), 🔵 N suggestion(s)\`, or \`✅ No issues found.\` when there is none. One line per finding: location, claim, fix.
Post nothing yourself: the workflow posts the saved file.
EOF
if [ "$kept" = elsewhere ]; then
    echo "This project keeps its spec in a repository of its own, which is not in this checkout: say so on the line under the headline, check what needs no spec, and report no finding on its absence."
fi
