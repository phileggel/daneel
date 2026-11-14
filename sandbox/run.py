#!/usr/bin/env python3
"""Run one scenario: a workflow, headless, on a fresh copy of the sandbox's app, then check
what it left.

Use:  python3 sandbox/run.py SCENARIO [--model M] [--max-budget-usd N] [--timeout S]
                                      [--permission-mode MODE] [--keep] [--report FILE]
      python3 sandbox/run.py SCENARIO --again FOLDER   check a kept run again, with no model call
Exit: 0 every expectation met · 1 an expectation not met · 2 the run did not finish (the
      session failed, hit its budget or the timeout) · 3 refused: wrong arguments, or a
      scenario that cannot be read

SCENARIO is a folder of `sandbox/scenarios/` holding `scenario.json`:

  prompt     what is typed, such as `/app:run-entry`
  answers    the fake `gh`'s answer file (`fake_gh.py`), a path from the scenario's folder
  branches   optional: the branches the copy starts with (`snapshot.py`), `files` a folder
             of the scenario
  expect     the outcomes checked, below

One run: `snapshot.py` restores the copy, `fake_gh.py` puts its `gh` first on `PATH`, and
`claude -p <prompt>` runs in the copy with this checkout's `flow` and `app` plugins
(`--plugin-dir`) and the project's settings only (`--setting-sources project`), so the
machine's own allow list grants nothing. The copy is a folder nobody trusted, whose allow
list Claude Code ignores, so the app's `.claude/settings.json` is also passed as
`--settings`: the grants are the skill's `allowed-tools` and the app's own, as in a
project its owner opened. It is a real model call: `--max-budget-usd`
(default 3) bounds it. The folder is thrown away afterwards unless `--keep`; a kept one
holds the session's `transcript.jsonl` and the fake `gh`'s `gh.jsonl`.

`expect` checks outcomes, never the words of the session; a key not listed is refused:

  gh_called        each pattern matches a logged `gh` command
  gh_not_called    no logged command matches any of these patterns
  gh_not_before    [[A, B], ...]: no command matching A comes before the first matching B
  gh_all_answered  true: no command went unanswered (the fake `gh`'s exits 97 and 98)
  local_branches, origin_branches   the exact branches of the copy, and of its `origin`
  origin_unchanged these branches of `origin` are on the commit they started on
  ran, not_ran     a Bash command of the session contains (does not contain) each text

The report (stdout, or `--report FILE`) is JSON: each check with what was found, the cost,
turns and duration the session reported, the commands it was denied, what `claude` wrote on
stderr, and the `gh` log.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fake_gh  # noqa: E402
import snapshot  # noqa: E402

MET, NOT_MET, NOT_FINISHED, REFUSED = 0, 1, 2, 3
PLUGINS = [HERE.parent / "plugins" / "flow", HERE.parent / "plugins" / "app"]
SCENARIO_KEYS = {"description", "prompt", "answers", "branches", "expect"}
EXPECT_KEYS = {
    "gh_called", "gh_not_called", "gh_not_before", "gh_all_answered",
    "local_branches", "origin_branches", "origin_unchanged", "ran", "not_ran",
}


class Refusal(Exception):
    pass


def read_scenario(folder: Path) -> dict:
    try:
        scenario = json.loads((folder / "scenario.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Refusal(f"cannot read {folder / 'scenario.json'}: {error}") from error
    unknown = sorted(set(scenario) - SCENARIO_KEYS) + sorted(set(scenario.get("expect", {})) - EXPECT_KEYS)
    if unknown:
        raise Refusal(f"{folder.name}: keys nothing reads: {', '.join(unknown)}")
    missing = sorted({"prompt", "answers", "expect"} - set(scenario))
    if missing:
        raise Refusal(f"{folder.name}: missing {', '.join(missing)}")
    return scenario


def matches(command: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(command, pattern) or fnmatch.fnmatchcase(f"{command} ", pattern)


def branches_of(repository: Path) -> dict[str, str]:
    listed = snapshot.git(repository, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads")
    return dict(line.split() for line in listed.splitlines())


def session(lines: list[str]) -> tuple[list[str], dict | None]:
    """The Bash commands of a `stream-json` session, in order, and its result line."""
    commands, result = [], None
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result":
            result = event
        message = event.get("message")  # a string on a `system` line, such as a denial
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Bash":
                commands.append(str((block.get("input") or {}).get("command", "")))
    return commands, result


def check(expect: dict, calls: list[dict], commands: list[str], local: dict, origin: dict, started: dict) -> list[dict]:
    """One entry per expectation: its name, whether it is met, and what was found."""
    logged = [call["command"] for call in calls]
    checks = []

    def add(name: str, met: bool, found: object) -> None:
        checks.append({"check": name, "met": bool(met), "found": found})

    for pattern in expect.get("gh_called", []):
        hits = [command for command in logged if matches(command, pattern)]
        add(f"gh_called: {pattern}", hits, hits[:3])
    for pattern in expect.get("gh_not_called", []):
        hits = [command for command in logged if matches(command, pattern)]
        add(f"gh_not_called: {pattern}", not hits, hits[:3])
    for early, anchor in expect.get("gh_not_before", []):
        first = next((position for position, command in enumerate(logged) if matches(command, anchor)), len(logged))
        hits = [command for command in logged[:first] if matches(command, early)]
        add(f"gh_not_before: {early} before {anchor}", not hits, hits[:3])
    if expect.get("gh_all_answered"):
        unanswered = [call["command"] for call in calls if call["exit"] in (fake_gh.NO_ANSWER, fake_gh.BAD_SCENARIO)]
        add("gh_all_answered", not unanswered, unanswered)
    if "local_branches" in expect:
        add("local_branches", sorted(local) == sorted(expect["local_branches"]), sorted(local))
    if "origin_branches" in expect:
        add("origin_branches", sorted(origin) == sorted(expect["origin_branches"]), sorted(origin))
    for branch in expect.get("origin_unchanged", []):
        add(f"origin_unchanged: {branch}", branch in started and origin.get(branch) == started[branch],
            {"started": started.get(branch), "ended": origin.get(branch)})
    for text in expect.get("ran", []):
        hits = [command for command in commands if text in command]
        add(f"ran: {text}", hits, hits[:3])
    for text in expect.get("not_ran", []):
        hits = [command for command in commands if text in command]
        add(f"not_ran: {text}", not hits, hits[:3])
    return checks


def claude_command(prompt: str, args: argparse.Namespace, work: Path) -> list[str]:
    command = ["claude", "-p", prompt]
    for plugin in PLUGINS:
        command += ["--plugin-dir", str(plugin)]
    # A folder nobody opened is not trusted, and Claude Code then ignores its allow list:
    # handing the app's own settings over stands for the owner's trust of their project.
    settings = work / ".claude" / "settings.json"
    if settings.is_file():
        command += ["--settings", str(settings)]
    command += [
        "--permission-mode", args.permission_mode, "--setting-sources", "project", "--strict-mcp-config",
        "--no-session-persistence", "--output-format", "stream-json", "--verbose",
        "--max-budget-usd", str(args.max_budget_usd),
    ]
    if args.model:
        command += ["--model", args.model]
    return command


def run(name: str, args: argparse.Namespace) -> tuple[int, dict]:
    folder = HERE / "scenarios" / name
    scenario = read_scenario(folder)
    branches = [dict(branch, files=str(folder / branch["files"])) for branch in scenario.get("branches", [])]
    began = time.monotonic()
    code, stopped = 0, ""
    if args.again:
        run_folder = args.again.resolve()
        if not (run_folder / snapshot.MARKER).is_file() or not (run_folder / "started.json").is_file():
            raise Refusal(f"{run_folder} is not a kept run")
        work, origin, log = run_folder / "acme", run_folder / "origin.git", run_folder / "gh.jsonl"
        started = json.loads((run_folder / "started.json").read_text(encoding="utf-8"))
    else:
        run_folder = snapshot.restore(Path(tempfile.mkdtemp(prefix=f"acme-{name}-")), branches=branches)
        work, origin, log = run_folder / "acme", run_folder / "origin.git", run_folder / "gh.jsonl"
        try:
            fake_gh.install(run_folder / "bin", folder / scenario["answers"], log)
        except fake_gh.Refused as refused:
            snapshot.discard(run_folder)
            raise Refusal(str(refused)) from refused
        started = branches_of(origin)
        (run_folder / "started.json").write_text(json.dumps(started), encoding="utf-8")
        env = snapshot.clean_env()
        env["PATH"] = f"{run_folder / 'bin'}{os.pathsep}{env['PATH']}"
        try:
            with (run_folder / "transcript.jsonl").open("w", encoding="utf-8") as transcript, \
                    (run_folder / "stderr.txt").open("w", encoding="utf-8") as errors:
                code = subprocess.run(claude_command(scenario["prompt"], args, work), cwd=work, env=env,
                                      stdin=subprocess.DEVNULL, stdout=transcript, stderr=errors,
                                      timeout=args.timeout).returncode
        except subprocess.TimeoutExpired:
            code, stopped = -1, f"timed out after {args.timeout:g} s"
        except OSError as error:
            code, stopped = -1, f"claude could not start: {error}"
    lines = (run_folder / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
    commands, result = session(lines)
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    if not stopped and result is None:
        stopped = f"the session gave no result (claude exited {code}): " \
                  + (run_folder / "stderr.txt").read_text(encoding="utf-8").strip()[-300:]
    elif not stopped and (result.get("is_error") or result.get("subtype") != "success"):
        stopped = f"the session ended with {result.get('subtype')}"
    checks = check(scenario["expect"], calls, commands, branches_of(work), branches_of(origin), started)
    result = result or {}
    report = {
        "scenario": name,
        "finished": not stopped,
        "stopped": stopped,
        "met": sum(entry["met"] for entry in checks),
        "of": len(checks),
        "checks": checks,
        "cost_usd": result.get("total_cost_usd"),
        "turns": result.get("num_turns"),
        "session_seconds": round(result["duration_ms"] / 1000) if "duration_ms" in result else None,
        "wall_seconds": round(time.monotonic() - began),
        "model": next(iter(result.get("modelUsage") or {}), args.model or "not reported"),
        "permission_mode": args.permission_mode,
        "denied": [denial.get("tool_input", {}).get("command", denial.get("tool_name"))
                   for denial in result.get("permission_denials", [])],
        "usage": result.get("usage"),
        "gh": [f"{call['exit']} {call['command']}" for call in calls],
        "bash": commands,
        "last_words": str(result.get("result", ""))[-1500:],
        "stderr": (run_folder / "stderr.txt").read_text(encoding="utf-8").strip()[-600:],
    }
    if args.keep or args.again:
        report["kept"] = str(run_folder)
    else:
        snapshot.discard(run_folder)
    if stopped:
        return NOT_FINISHED, report
    return (MET if all(entry["met"] for entry in checks) else NOT_MET), report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="run.py", description=__doc__.split("\n")[0])
    parser.add_argument("scenario")
    parser.add_argument("--model")
    parser.add_argument("--max-budget-usd", type=float, default=3)
    parser.add_argument("--timeout", type=float, default=1800, help="seconds (default 1800)")
    parser.add_argument("--permission-mode", default="acceptEdits")
    parser.add_argument("--keep", action="store_true", help="keep the run's folder and name it in the report")
    parser.add_argument("--report", type=Path, help="write the report there instead of stdout")
    parser.add_argument("--again", type=Path, metavar="FOLDER", help="check this kept run again; no model call")
    try:
        args = parser.parse_args(argv)
    except SystemExit as stopped:
        return REFUSED if stopped.code else 0
    try:
        code, report = run(args.scenario, args)
    except Refusal as refusal:
        print(f"run: {refusal}", file=sys.stderr)
        return REFUSED
    except SystemExit as refused:  # snapshot.py refused, and said why
        return REFUSED if refused.code else 0
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
