#!/usr/bin/env python3
"""A `gh` that answers from a scenario's fixtures: a fixture, not a simulator.

Use:  python3 sandbox/fake_gh.py install BIN SCENARIO LOG   writes BIN/gh, to put first on PATH
      python3 sandbox/fake_gh.py answer ARG...              what BIN/gh runs: answers `gh ARG...`
Exit of `install`: 0 written · 1 refused (the reason is printed) · 2 wrong arguments
Exit of `answer`:  the answer's own (0 unless it says otherwise) · 97 no answer for this
                   command · 98 the scenario cannot be read or an answer file is missing

SCENARIO is a JSON object, one entry per command form, in the order they are tried:

    {
      "gh pr list *":     "one-open-pr.json",
      "gh pr checkout *": "ok",
      "gh pr checks *":   [{"stdout": "pending.txt", "exit": 8}, "green.txt"]
    }

A key is a pattern (`*` is any run of characters) matched against the whole command, its
arguments joined by one space; the first that matches answers. An answer is:

  "ok"                   nothing printed, exit 0
  "<file>"               the file printed as it is, exit 0; a path from SCENARIO's folder
  {"stdout": "<file>", "stderr": "<text>", "exit": <n>}   any of the three
  [<answer>, ...]        the first call gets the first, each later call the next, the last
                         one from then on

Every call is appended to LOG, one JSON object per line: `argv`, `command`, `pattern`,
`call` (which call of that pattern, from 1), `answer` and `exit`. A command no pattern
matches is logged with a null pattern, says so on stderr and exits 97: a scenario never
passes on an answer nobody wrote.

It has no logic and no state but the position in a list, which it counts from LOG. It
cannot show how the real `gh` behaves: the contract check does that, on the same answer files.
BIN/gh carries SCENARIO and LOG itself, so it needs no environment variable.
"""

from __future__ import annotations

import fcntl
import fnmatch
import json
import os
import shlex
import sys
from pathlib import Path

NO_ANSWER, BAD_SCENARIO = 97, 98
ANSWER_KEYS = {"stdout", "stderr", "exit"}


class Refused(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code


def read_scenario(path: Path) -> dict:
    try:
        scenario = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Refused(BAD_SCENARIO, f"cannot read the scenario {path}: {error}") from error
    if not isinstance(scenario, dict):
        raise Refused(BAD_SCENARIO, f"the scenario {path} is not a JSON object")
    return scenario


def normalise(answer: object, pattern: str) -> dict:
    """One answer as {"stdout": file or None, "stderr": text, "exit": code}."""
    if answer == "ok":
        return {"stdout": None, "stderr": "", "exit": 0}
    if isinstance(answer, str):
        return {"stdout": answer, "stderr": "", "exit": 0}
    if isinstance(answer, dict) and set(answer) <= ANSWER_KEYS and isinstance(answer.get("exit", 0), int) \
            and isinstance(answer.get("stderr", ""), str) and isinstance(answer.get("stdout", ""), str):
        return {"stdout": answer.get("stdout"), "stderr": answer.get("stderr", ""), "exit": answer.get("exit", 0)}
    raise Refused(BAD_SCENARIO, f"the answer to {pattern!r} is not \"ok\", a file or stdout/stderr/exit: {answer!r}")


def find(scenario: dict, command: str) -> str | None:
    """The first pattern the command matches, as `allowed-tools` reads one: `gh pr list *`
    also takes `gh pr list` alone."""
    for pattern in scenario:
        if fnmatch.fnmatchcase(command, pattern) or fnmatch.fnmatchcase(f"{command} ", pattern):
            return pattern
    return None


def answer(argv: list[str], scenario_path: Path, log_path: Path) -> int:
    command = " ".join(["gh", *argv])
    entry: dict = {"argv": ["gh", *argv], "command": command, "pattern": None, "call": None, "answer": None}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a+", encoding="utf-8") as log:
        fcntl.flock(log, fcntl.LOCK_EX)  # two calls at once still count their position right
        try:
            scenario = read_scenario(scenario_path)
            pattern = find(scenario, command)
            if pattern is None:
                raise Refused(NO_ANSWER, f"no answer for: {command}\n  the scenario is {scenario_path}")
            log.seek(0)
            call = 1 + sum(json.loads(line)["pattern"] == pattern for line in log if line.strip())
            answers = scenario[pattern] if isinstance(scenario[pattern], list) else [scenario[pattern]]
            if not answers:
                raise Refused(BAD_SCENARIO, f"the answer to {pattern!r} is an empty list")
            chosen = answers[min(call, len(answers)) - 1]
            given = normalise(chosen, pattern)
            entry.update(pattern=pattern, call=call, answer=chosen)
            out = b""
            if given["stdout"] is not None:
                file = scenario_path.parent / given["stdout"]
                try:
                    out = file.read_bytes()
                except OSError as error:
                    raise Refused(BAD_SCENARIO, f"the answer file of {pattern!r} is missing: {file}") from error
            code = given["exit"]
        except Refused as refused:
            print(f"fake gh: {refused}", file=sys.stderr)
            code, out, given = refused.code, b"", {"stderr": ""}
        entry["exit"] = code
        log.seek(0, os.SEEK_END)
        log.write(json.dumps(entry) + "\n")
    sys.stdout.buffer.write(out)
    sys.stdout.flush()
    sys.stderr.write(given["stderr"])
    return code


def install(bin_folder: Path, scenario: Path, log: Path) -> Path:
    """Writes `bin_folder/gh`, which answers from `scenario` and logs to `log`."""
    read_scenario(scenario)
    target = bin_folder / "gh"
    if target.exists():
        raise Refused(1, f"{target} is already there: nothing written")
    bin_folder.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve()
    target.write_text(
        "#!/bin/sh\n"
        f"FAKE_GH_SCENARIO={shlex.quote(str(scenario.resolve()))} "
        f"FAKE_GH_LOG={shlex.quote(str(log.resolve()))} "
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(here))} answer \"$@\"\n",
        encoding="utf-8",
    )
    target.chmod(0o755)
    return target


def main(argv: list[str]) -> int:
    if argv[:1] == ["answer"]:
        try:
            scenario, log = os.environ["FAKE_GH_SCENARIO"], os.environ["FAKE_GH_LOG"]
        except KeyError as missing:
            print(f"fake gh: {missing.args[0]} is not set; run the `gh` that `install` wrote", file=sys.stderr)
            return BAD_SCENARIO
        return answer(argv[1:], Path(scenario), Path(log))
    if argv[:1] == ["install"] and len(argv) == 4:
        try:
            print(install(Path(argv[1]), Path(argv[2]), Path(argv[3])))
        except Refused as refused:
            print(f"fake gh: {refused}", file=sys.stderr)
            return 1
        return 0
    print("usage: fake_gh.py install BIN SCENARIO LOG | fake_gh.py answer ARG...", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
