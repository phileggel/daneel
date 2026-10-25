#!/usr/bin/env bash
set -euo pipefail

# branch.sh — Branch-base git operations, for the project in the working directory.
#
# Single source of truth for "where did this branch diverge from main" plus
# the operations that need that base: diff, log, and files.
#
# Use, from the project's checkout:
#   bash <plugin>/scripts/branch.sh base                      # print resolved BASE
#   bash <plugin>/scripts/branch.sh diff <path> [<path>...]   # git diff BASE..HEAD -- paths
#   bash <plugin>/scripts/branch.sh log                       # git log --oneline BASE..HEAD
#   bash <plugin>/scripts/branch.sh files [--match RE] [--exclude RE] [--uncommitted-only]
#
# `files` prints a sort-unique list of paths changed on the branch — the branch
# diff (BASE..HEAD) unioned with uncommitted work (staged, unstaged, untracked)
# — one path per line, no headers. A lane narrows the list with extended
# regular expressions: `--match` keeps the paths that match, `--exclude` drops
# those that match (`--match '\.(ts|tsx)$' --exclude '^e2e/'`). The layout is
# the project's, so the lane names it, never this script. `--uncommitted-only`
# drops the branch-diff source (in-flight files only). The options compose, in
# any order.
#
# Output: stdout-only. base prints a sha-or-sentinel; diff/log/files forward
# the underlying git output verbatim. Never fails on base resolution — falls
# back through merge-base → rev-parse → "HEAD" so detached HEAD / shallow clone
# / missing-main branches still get a usable BASE.
#
# Exit codes: 0 on success; 2 on a usage error (unknown subcommand/flag, or
# `diff` with no paths). Underlying git failures propagate their own status.
#
# Why a script (vs inline shell in agent prompts):
#   Compound shell ($(...), &&, ||, ;) cannot be safely allowlisted in
#   Claude Code's permission system, which matches by literal prefix. A
#   literal `bash <plugin>/scripts/branch.sh diff foo.ts` call is allowed by the
#   calling skill's `allowed-tools` (`Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/branch.sh *)`),
#   never by a leading-wildcard allow-list line.

usage() {
    echo "usage: bash branch.sh {base|diff <paths>|log|files [--match RE] [--exclude RE] [--uncommitted-only]}" >&2
    exit 2
}

resolve_base() {
    git merge-base HEAD main 2>/dev/null ||
        git rev-parse main 2>/dev/null ||
        echo "HEAD"
}

case "${1:-}" in
base)
    resolve_base
    ;;
diff)
    shift
    [ "$#" -ge 1 ] || usage
    BASE=$(resolve_base)
    git diff "$BASE"..HEAD -- "$@"
    ;;
log)
    shift
    # No pass-through flags: a CI reviewer may run this helper, and git log
    # takes options that write files (--output).
    [ "$#" -eq 0 ] || usage
    BASE=$(resolve_base)
    git log --oneline "$BASE"..HEAD
    ;;
files)
    shift
    MATCH='.'
    EXCLUDE=''
    UNCOMMITTED_ONLY=''
    while [ "$#" -gt 0 ]; do
        case "$1" in
        --uncommitted-only) UNCOMMITTED_ONLY=1 ;;
        --match)
            [ "$#" -ge 2 ] || usage
            MATCH="$2"
            shift
            ;;
        --exclude)
            [ "$#" -ge 2 ] || usage
            EXCLUDE="$2"
            shift
            ;;
        *) usage ;;
        esac
        shift
    done

    BASE=$(resolve_base)
    collect() {
        {
            [ -z "$UNCOMMITTED_ONLY" ] && git diff --name-only "$BASE"..HEAD
            git diff --name-only HEAD
            git diff --name-only --cached
            git ls-files --others --exclude-standard
        } | LC_ALL=C sort -u | grep -v '^$' || true
    }

    if [ -n "$EXCLUDE" ]; then
        collect | grep -E "$MATCH" | grep -v -E "$EXCLUDE" || true
    else
        collect | grep -E "$MATCH" || true
    fi
    ;;
*)
    usage
    ;;
esac
