#!/usr/bin/env bash
# review-lanes.sh — the reviewers a change needs, and only those, for the project in the
# working directory.
#
# Reads changed paths on stdin (one per line) and prints one lane per line, in this order:
# backend, frontend, arch, sql, infra, security, e2e, spec, contract, adr, guides. Nothing
# for a change no reviewer reads. `--json` prints {"backend":true,...} for CI.
#
# A lane fires only on files its reviewer takes (its `branch.sh files` filter, or the files
# its agent names), so it never starts on a change it would refuse. Defaults, for a
# Tauri + React app:
#   backend   any .rs                                       reviewer-backend
#   frontend  src/**/*.ts(x)                                reviewer-frontend
#   arch      backend or frontend                           reviewer-arch
#   sql       (src-tauri/)migrations/**/*.sql               reviewer-sql
#   infra     workflows, hooks, scripts/*.{sh,bat,py,mjs}, justfile, package.json,
#             Cargo.toml, tauri.conf.json, capabilities, required-checks.json,
#             arch-allowlist.json, coverage-gates.json, .claude/settings.json
#                                                           reviewer-infra
#   security  the IPC boundary: api.rs, capabilities, the command registry
#             (specta_builder.rs)                           reviewer-security
#   e2e       e2e/**/*.test.ts                              reviewer-e2e
#   spec      docs/spec/*.md but README.md                  spec-reviewer
#   contract  docs/contracts/*.md but README.md             contract-reviewer
#   adr       docs/adr/*.md                                 adr-reviewer
#   guides    the `flow-audit.guides` globs (reviewer-guides reads the same list)
#
# The project adds its own paths per lane in `.claude/daneel.json`, under `review.lanes`:
# extended regular expressions, matched against the path from the repository root
# (`{"review": {"lanes": {"infra": ["^tools/[^/]*\\.sh$"]}}}`). A pattern only adds:
# a lane's defaults always hold. A lane name not listed above is an error (exit 2).
#
# Use, from the project's checkout:
#   bash <plugin>/scripts/branch.sh files | bash <plugin>/scripts/review-lanes.sh
# In CI, give it the base branch's `.claude/daneel.json`, so a pull request cannot turn its
# own reviewers off.
set -euo pipefail

LANES=(backend frontend arch sql infra security e2e spec contract adr guides)

ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# The project's part: "<lane> <regex>" per line, the guides globs turned into regexes
# (`*` crosses `/`, as flow-audit's fnmatch does).
extras=$(python3 -c '
import json, re, sys
from pathlib import Path
lanes = sys.argv[2].split()
path = Path(sys.argv[1]) / ".claude" / "daneel.json"
settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
own = settings.get("review", {}).get("lanes", {})
unknown = sorted(set(own) - set(lanes))
if unknown:
    sys.exit(f"review-lanes: unknown lanes in {path} review.lanes: {chr(44).join(unknown)}")
for lane, patterns in own.items():
    for pattern in patterns:
        print(lane, pattern)
guides = settings.get("flow-audit", {}).get("guides") or [
    "CLAUDE.md", ".claude/skills/*/SKILL.md", ".claude/agents/*.md", ".claude/rules/*.md"]
for glob in guides:
    ere = "".join(".*" if c == "*" else "." if c == "?" else re.sub(r"([][.^$+(){}|\\])", r"\\\1", c) for c in glob)
    print("guides", "^" + ere + "$")
' "$ROOT" "${LANES[*]}") || exit 2

files=$(cat)

# The lane fires when a path matches its default or one of the project's patterns.
fires() {
    local lane=$1 pattern=$2 paths=${3-$files} extra
    while IFS=' ' read -r name extra; do
        [[ "$name" == "$lane" ]] && pattern="$pattern|($extra)"
    done <<<"$extras"
    grep -Eq "$pattern" <<<"$paths" && echo true || echo false
}

NEVER='^$.'
backend=$(fires backend '\.rs$')
frontend=$(fires frontend '^src/.*\.(ts|tsx)$')
arch=$(fires arch "$NEVER")
if [[ "$backend" == true || "$frontend" == true ]]; then arch=true; fi
sql=$(fires sql '^(src-tauri/)?migrations/.*\.sql$')
infra=$(fires infra '^(\.github/workflows/[^/]*\.ya?ml|\.githooks/.*|scripts/[^/]*\.(sh|bat|py|mjs)|justfile|package\.json|required-checks\.json|arch-allowlist\.json|coverage-gates\.json|\.claude/settings\.json|src-tauri/Cargo\.toml|src-tauri/tauri\.conf\.json|src-tauri/capabilities/.*\.json)$')
security=$(fires security '^src-tauri/(src/.*/api\.rs|src/(.*/)?specta_builder\.rs|capabilities/.*\.json)$')
e2e=$(fires e2e '^e2e/.*\.test\.ts$')
# A folder's README.md is its conventions, not a spec or a contract.
not_readme=$(grep -Ev '^docs/(spec|contracts)/README\.md$' <<<"$files" || true)
spec=$(fires spec '^docs/spec/.*\.md$' "$not_readme")
contract=$(fires contract '^docs/contracts/.*\.md$' "$not_readme")
adr=$(fires adr '^docs/adr/[^/]*\.md$')
guides=$(fires guides "$NEVER")

if [[ "${1:-}" == "--json" ]]; then
    sep='{'
    for lane in "${LANES[@]}"; do
        printf '%s"%s":%s' "$sep" "$lane" "${!lane}"
        sep=','
    done
    printf '}\n'
    exit 0
fi
for lane in "${LANES[@]}"; do
    if [[ "${!lane}" == true ]]; then echo "$lane"; fi
done
