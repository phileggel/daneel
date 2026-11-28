#!/usr/bin/env bash
# review-prepare.sh — makes a CI checkout ready for a reviewer's session: what judges the
# pull request comes from the base branch, so a pull request cannot loosen its own review.
#
# Use, from the project's checkout, on the commit under review:
#   bash <plugin>/scripts/review-prepare.sh <base> <tree>
#     <base>  the base branch as git names it there (`origin/main`)
#     <tree>  a folder that does not exist yet, outside the checkout
# Exit: 0 prepared · 1 refused, the reason printed, nothing changed · 2 a usage error
#
# For a CI checkout only: it replaces files. It refuses a checkout with uncommitted work.
#
# What it does:
#   1. `main` is a local branch at <base>: `branch.sh` measures the branch from it.
#   2. The plugin's own folder, when it sits in the checkout, is ignored by git, so
#      `branch.sh files` does not list it.
#   3. <tree> gets the commit under review as pushed, without its `.claude/skills` and
#      `.claude/agents`: the session reads the files under review there, and loads none
#      of them as its own.
#   4. `.review/` exists: the report's first write creates no folder.
#   5. These come from <base>, and one that <base> does not have is removed:
#        `CLAUDE.md` and `.claude/`, the session's own instructions and settings;
#        every document `.claude/daneel.json` on <base> names under `review.rules`,
#        `review.glossary`, `review.owners` and `review.setup`;
#        the README of each kind `review.rules` does not name (defaults
#        `docs/spec/README.md`, `docs/contracts/README.md`, `docs/adr/README.md`).
#      A file the pull request changed still shows in its diff (protocol.md rule 6).
#   6. A spec kept in a repository of its own (`spec-proposal.repo` on <base>) is read
#      when the project's workflow checked that repository out at the spec folder, the
#      folder of the first path of `review.rules.spec` (default `docs/spec`), before this
#      runs. Its files are the spec repository's, not the pull request's: step 5 leaves
#      them, and the folder is copied into <tree>, beside the files under review. Its
#      `.git` is removed from both, so the session reaches no credential of that
#      checkout. With no such folder (a pull request that gets no secret), nothing of
#      this happens. A folder git does not ignore is refused.
# Each path of step 5 is printed with what happened to it.
set -euo pipefail

refuse() {
    echo "review-prepare: $1" >&2
    exit 1
}

if [ "$#" -ne 2 ]; then
    echo "usage: bash review-prepare.sh <base> <tree>" >&2
    exit 2
fi
base=$1
tree=$2

root=$(git rev-parse --show-toplevel 2>/dev/null) || refuse "the working directory is not a git checkout"
[ "$(pwd -P)" = "$(cd "$root" && pwd -P)" ] || refuse "run it from the checkout's root, $root"
git rev-parse --verify --quiet "$base^{commit}" >/dev/null || refuse "$base is not a commit here: fetch the base branch first"
[ ! -e "$tree" ] || refuse "$tree exists already: give a folder that does not"
parent=$(cd "$(dirname "$tree")" 2>/dev/null && pwd -P) || refuse "the folder that holds $tree does not exist"
case "$parent/" in
"$(pwd -P)/"*) refuse "$tree is inside the checkout: give a folder outside it" ;;
esac
[ "$(git rev-parse --abbrev-ref HEAD)" != main ] || refuse "the checkout is on main: check out the commit under review"

# The paths step 5 takes from <base>, read from <base>'s settings before anything changes.
paths=$(git show "$base:.claude/daneel.json" 2>/dev/null | python3 -c '
import json, sys
text = sys.stdin.read()
try:
    settings = json.loads(text) if text.strip() else {}
except json.JSONDecodeError as error:
    sys.exit(f".claude/daneel.json on the base branch is not JSON: {error}")
review = settings.get("review", {})
rules = review.get("rules", {})
named = [path for paths in rules.values() for path in paths]
named += [review[key] for key in ("glossary", "owners", "setup") if review.get(key)]
defaults = {"spec": "docs/spec/README.md", "contract": "docs/contracts/README.md", "adr": "docs/adr/README.md"}
named += [default for kind, default in defaults.items() if not rules.get(kind)]
for path in ["CLAUDE.md", ".claude"] + named:
    parts = path.split("/") if isinstance(path, str) else [".."]
    if not path or path.startswith("/") or ".." in parts or parts[0] == ".git":
        sys.exit(f".claude/daneel.json on the base branch names a path outside the checkout: {path!r}")
# The first line: the spec folder when the spec has a repository of its own, else nothing.
own = settings.get("spec-proposal")
first = (rules.get("spec") or [defaults["spec"]])[0]
elsewhere = isinstance(own, dict) and own.get("repo") and "/" in first
print("spec " + first.rsplit("/", 1)[0] if elsewhere else "spec")
seen = []
for path in ["CLAUDE.md", ".claude"] + named:
    if path not in seen:
        seen.append(path)
        print(path)
') || refuse "the base branch's settings could not be read"
spec=$(sed -n '1s/^spec *//p' <<<"$paths")
paths=$(sed '1d' <<<"$paths")
# Read only when the workflow checked the spec repository out there.
[ -n "$spec" ] && [ -d "$spec" ] || spec=
[ -z "$spec" ] || git check-ignore -q "$spec" || refuse "git does not ignore the spec folder $spec: the project's .gitignore lists it"

# The plugin's folder, when inside the checkout, is not the project's work.
plugin=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
inside=$(python3 -c '
import os, sys
relative = os.path.relpath(sys.argv[1], sys.argv[2])
print("" if relative.startswith("..") or relative == "." else relative.split(os.sep)[0] + "/")
' "$plugin" "$(pwd -P)")
if [ -n "$inside" ]; then
    dirty=$(git status --porcelain -- . ":(exclude)$inside")
else
    dirty=$(git status --porcelain)
fi
[ -z "$dirty" ] || refuse "the checkout has uncommitted work, which this would replace: it prepares a CI checkout only"

if [ -n "$inside" ] && ! grep -qxF "$inside" .git/info/exclude 2>/dev/null; then
    mkdir -p .git/info
    echo "$inside" >>.git/info/exclude
fi

git branch -f main "$base" >/dev/null
git worktree add --quiet --detach "$tree" HEAD
rm -rf "$tree/.claude/skills" "$tree/.claude/agents"
mkdir -p .review

while IFS= read -r path; do
    if [ -n "$spec" ] && [[ "$path" == "$spec"/* ]]; then
        if [ -e "$path" ]; then
            echo "from the spec repository: $path"
        else
            echo "not in the spec repository: $path"
        fi
        continue
    fi
    rm -rf -- "$path"
    if git cat-file -e "$base:$path" 2>/dev/null; then
        git checkout --quiet "$base" -- "$path"
        echo "from the base branch: $path"
    else
        echo "not on the base branch, removed: $path"
    fi
done <<<"$paths"

if [ -n "$spec" ]; then
    rm -rf -- "$spec/.git"
    mkdir -p "$tree/$spec"
    cp -R "$spec/." "$tree/$spec/"
    echo "the spec repository's files, beside the files under review: $spec"
fi
