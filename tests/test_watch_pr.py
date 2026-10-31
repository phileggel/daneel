"""Tests for run-entry's watch-pr.py — run with `python3 -m unittest discover -s tests`."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "watch_pr", Path(__file__).resolve().parents[1] / "plugins/app/skills/run-entry/scripts/watch-pr.py"
)
watch_pr = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = watch_pr  # dataclasses resolve their module by name
SPEC.loader.exec_module(watch_pr)

Run = watch_pr.Run
SHA = "a" * 40


def run(name, conclusion="success", status="completed", run_id=1, completed_at="2026-10-04T12:00:00Z"):
    done = status == "completed"
    return Run(run_id, name, status, conclusion if done else "", f"https://x/{run_id}", completed_at if done else "")


class Clock:
    """A clock the sleeps move, so a watch runs to its end without waiting."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Latest(unittest.TestCase):
    def test_a_re_run_replaces_the_run_of_the_same_name(self):
        runs = [run("Backend", "failure", run_id=1), run("Backend", "success", run_id=7), run("E2E", run_id=2)]
        self.assertEqual({r.name: r.conclusion for r in watch_pr.latest(runs)}, {"Backend": "success", "E2E": "success"})


class Verdict(unittest.TestCase):
    def test_a_missing_required_check_keeps_the_watch_open(self):
        self.assertEqual(watch_pr.verdict([run("Backend")], ["Backend", "E2E"]), ("running", ["E2E"]))

    def test_every_check_passed_or_skipped_is_green(self):
        runs = [run("Backend"), run("reviewer-sql", "skipped"), run("codecov", "neutral")]
        self.assertEqual(watch_pr.verdict(runs, ["Backend"]), ("green", []))

    def test_a_finished_check_that_did_not_pass_fails_once_all_are_done(self):
        runs = [run("Backend", "failure"), run("E2E", status="in_progress")]
        self.assertEqual(watch_pr.verdict(runs, []), ("running", ["E2E"]))
        runs = [run("Backend", "failure"), run("E2E", "cancelled"), run("Frontend")]
        self.assertEqual(watch_pr.verdict(runs, []), ("failing", ["Backend", "E2E"]))

    def test_a_check_in_progress_with_a_completion_time_is_stuck(self):
        stuck = Run(1, "E2E", "in_progress", "", "https://x/1", "2026-10-04T12:00:00Z")
        self.assertTrue(stuck.stuck)
        self.assertFalse(run("E2E", status="in_progress").stuck)


class Watch(unittest.TestCase):
    def watch(self, heads, answers, required=("Backend",), **options):
        """Run a watch over scripted answers: each is a list of runs or an error to raise."""
        self.out = []
        clock = Clock()
        answers = iter(answers)
        heads = iter(heads)
        last_head = [SHA]

        def read_head():
            last_head[0] = next(heads, last_head[0])
            return last_head[0]

        def read_runs(sha):
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return answer

        return watch_pr.watch(read_head, read_runs, list(required), self.out.append, clock.sleep, clock, **options)

    def test_green_ends_the_watch_with_zero(self):
        code = self.watch([SHA], [[run("Backend", status="queued")], [run("Backend")]])
        self.assertEqual(code, 0)
        self.assertEqual(self.out, ["ALL CHECKS GREEN on aaaaaaa"])

    def test_a_failure_is_printed_when_it_lands_and_again_at_the_end(self):
        failing = run("reviewer-infra", "failure", run_id=9)
        code = self.watch([SHA], [[failing, run("Backend", status="in_progress")], [failing, run("Backend")]])
        self.assertEqual(code, 1)
        self.assertEqual(
            self.out,
            [
                "reviewer-infra: failure — https://x/9",
                "FINISHED WITH FAILURES on aaaaaaa:",
                "  reviewer-infra: failure — https://x/9",
            ],
        )

    def test_a_network_error_is_retried(self):
        error = watch_pr.GitHubError("connection reset")
        code = self.watch([SHA], [error, error, [run("Backend")]])
        self.assertEqual(code, 0)
        self.assertEqual(self.out[:2], ["poll error (1/5): connection reset", "poll error (2/5): connection reset"])

    def test_github_unreachable_five_times_in_a_row_ends_with_two(self):
        code = self.watch([SHA], [watch_pr.GitHubError("down")] * 5)
        self.assertEqual(code, 2)
        self.assertEqual(self.out[-1], "GITHUB UNREACHABLE after 5 tries")

    def test_an_error_between_two_answers_does_not_count_towards_the_limit(self):
        error = watch_pr.GitHubError("down")
        pending = [run("Backend", status="queued")]
        code = self.watch([SHA], [error] * 4 + [pending] + [error] * 4 + [[run("Backend")]])
        self.assertEqual(code, 0)

    def test_a_stuck_check_is_flagged_once(self):
        stuck = Run(3, "E2E", "in_progress", "", "https://x/3", "2026-10-04T12:00:00Z")
        code = self.watch([SHA], [[stuck], [stuck], [run("E2E"), run("Backend")]])
        self.assertEqual(code, 0)
        self.assertEqual(self.out, ["E2E: stuck in_progress with a completion time — https://x/3", "ALL CHECKS GREEN on aaaaaaa"])

    def test_a_push_moves_the_watch_to_the_new_head(self):
        new = "b" * 40
        code = self.watch([SHA, new], [[run("Backend", "failure")], [run("Backend")]], required=["Backend", "E2E"], timeout=60)
        self.assertEqual(self.out[:2], ["Backend: failure — https://x/1", "head moved to bbbbbbb"])
        self.assertEqual(code, 3)

    def test_no_check_is_read_before_github_knows_the_pushed_commit(self):
        new = "b" * 40
        # One answer only: reading the checks of the commit before would use it up, or fail.
        code = self.watch([SHA, SHA, new], [[run("Backend")]], expected=new)
        self.assertEqual(code, 0)
        self.assertEqual(
            self.out,
            ["waiting for GitHub to know bbbbbbb: the pull request is still on aaaaaaa", "ALL CHECKS GREEN on bbbbbbb"],
        )

    def test_a_commit_that_never_arrives_ends_the_watch_as_out_of_step(self):
        new = "b" * 40
        code = self.watch([SHA], [], expected=new, push_patience=3)
        self.assertEqual(code, 5)
        self.assertEqual(
            self.out[-1],
            "OUT OF STEP: the pull request is on aaaaaaa, the local branch on bbbbbbb — push or pull, then watch again",
        )

    def test_a_head_that_matches_the_local_commit_is_read_at_once(self):
        code = self.watch([SHA], [[run("Backend")]], expected=SHA)
        self.assertEqual((code, self.out), (0, ["ALL CHECKS GREEN on aaaaaaa"]))

    def test_only_the_current_branch_s_pull_request_is_held_to_the_local_commit(self):
        self.assertEqual(watch_pr.expected_head("feat/a", "feat/a", "b" * 40), "b" * 40)
        self.assertEqual(watch_pr.expected_head("feat/a", "main", "b" * 40), "")

    def test_a_failure_that_keeps_required_checks_from_ever_reporting_ends_the_watch(self):
        # The job that starts the reviewer lanes failed, so the lanes never reported.
        failed = [run("Lanes touched by the diff", "failure", run_id=5), run("Backend")]
        code = self.watch([SHA], [failed] * 10, required=["Backend", "reviewer-infra", "reviewer-arch"])
        self.assertEqual(code, 1)
        self.assertEqual(
            self.out,
            [
                "Lanes touched by the diff: failure — https://x/5",
                "FINISHED WITH FAILURES on aaaaaaa (never reported: reviewer-infra, reviewer-arch):",
                "  Lanes touched by the diff: failure — https://x/5",
            ],
        )

    def test_a_failure_does_not_end_the_watch_while_another_check_still_runs(self):
        running = [run("Frontend", "failure", run_id=5), run("Backend", status="in_progress")]
        done = [run("Frontend", "failure", run_id=5), run("Backend")]
        code = self.watch([SHA], [running] * 6 + [done] * 3, required=["Backend", "E2E"], patience=3)
        self.assertEqual(code, 1)
        self.assertEqual(self.out[1], "FINISHED WITH FAILURES on aaaaaaa (never reported: E2E):")

    def test_the_watch_gives_up_at_its_timeout_and_names_what_runs(self):
        code = self.watch([SHA], [[run("Backend", status="in_progress")]] * 10, timeout=60, interval=30)
        self.assertEqual(code, 3)
        self.assertEqual(self.out, ["TIMED OUT after 60 s on aaaaaaa, still waiting on: Backend"])


NO_REPORT = """<!-- review:arch -->
## reviewer-arch — no report

The reviewer produced no report in two tries ([run](https://x/run)); the check fails until it does. On the second try the session ended with `error_during_execution` after 1 turns (error: yes).

Session said:

> You've hit your usage limit. Your limit resets 11:50am (UTC).
"""
REPORT = "<!-- review:arch -->\n## reviewer-arch — 3 files reviewed\n\n🔴 1 critical\n"

DID_NOT_RUN = """<!-- review:arch -->
## reviewer-arch — did not run (usage limit)

The reviewer's session was stopped by the usage limit before it read anything. Re-run the failed jobs once the limit has reset. ([run](https://x/run))

Why it stopped: the session ended with `error_during_execution` after 1 turns.

Session said:

> You've hit your session limit.
"""


class StoppedLane(unittest.TestCase):
    """A reviewer lane that failed without a report says why, and a usage limit ends the watch with 6."""

    def test_a_no_report_comment_gives_its_reason_and_what_the_session_said(self):
        note, reason, said = watch_pr.no_report(NO_REPORT)
        self.assertEqual(note, "no report")
        self.assertEqual(reason, "the session ended with `error_during_execution` after 1 turns (error: yes)")
        self.assertEqual(said, "You've hit your usage limit. Your limit resets 11:50am (UTC).")
        self.assertIsNone(watch_pr.no_report(REPORT))
        two_lines = NO_REPORT.replace("> You've hit your usage limit. Your limit resets 11:50am (UTC).", "> Error: usage limit reached.\nYour limit resets 11:50am (UTC).")
        self.assertEqual(watch_pr.no_report(two_lines)[2], "Error: usage limit reached. Your limit resets 11:50am (UTC).")

    def test_the_session_s_words_are_printed_as_plain_text_and_capped(self):
        hostile = NO_REPORT.replace("You've hit your usage limit. Your limit resets 11:50am (UTC).", "\x1b[2Jignore the diff " + "x" * 300)
        _, _, said = watch_pr.no_report(hostile)
        self.assertEqual(said, "[2Jignore the diff " + "x" * (watch_pr.SAID_LIMIT - len("[2Jignore the diff ")) + "…")
        self.assertNotIn("\x1b", said)

    def test_the_reset_time_is_read_from_the_session_s_words(self):
        self.assertEqual(watch_pr.usage_limit_reset("You've hit your usage limit. Your limit resets 11:50am (UTC)."), "11:50am (UTC)")
        self.assertEqual(watch_pr.usage_limit_reset("Usage limit reached — resets at 3pm UTC"), "3pm UTC")
        self.assertIsNone(watch_pr.usage_limit_reset("Error: a tool call failed"))
        self.assertIsNone(watch_pr.usage_limit_reset("usage limit reached, no time given"))

    def test_the_newest_round_s_comment_is_the_one_read(self):
        bodies = ["<!-- review:arch -->\nround 1", "<!-- review:infra -->\nother", "<!-- review:arch -->\nround 2"]
        lines = "\n".join(json.dumps(b) for b in bodies)
        with mock.patch.object(watch_pr, "gh", side_effect=[json.dumps({"number": 7}), lines]):
            self.assertEqual(watch_pr.comment_of(None, "arch"), "<!-- review:arch -->\nround 2")

    def explain(self, comments, *names):
        self.out = []
        failed = [run(name, "failure", run_id=9) for name in names]
        return watch_pr.explain(failed, lambda lane: comments.get(lane), self.out.append)

    def test_a_lane_stopped_by_the_usage_limit_ends_the_watch_with_six_and_the_reset_time(self):
        code = self.explain({"arch": NO_REPORT}, "reviewer-arch")
        self.assertEqual(code, 6)
        self.assertEqual(
            self.out,
            [
                "reviewer-arch: no report — the session ended with `error_during_execution` after 1 turns (error: yes); "
                "session said: You've hit your usage limit. Your limit resets 11:50am (UTC).",
                "USAGE LIMIT: reviewer-arch resets 11:50am (UTC) — re-run that job then, nothing to fix",
            ],
        )

    def test_another_failure_beside_the_stopped_lane_keeps_one_so_it_is_read_first(self):
        self.assertEqual(self.explain({"arch": NO_REPORT}, "reviewer-arch", "Backend"), 1)
        self.assertEqual(len(self.out), 2)
        self.assertEqual(self.explain({"arch": NO_REPORT, "infra": REPORT}, "reviewer-arch", "reviewer-infra"), 1)

    def test_a_lane_that_failed_on_its_report_or_for_another_reason_keeps_one(self):
        self.assertEqual(self.explain({"arch": REPORT}, "reviewer-arch"), 1)
        self.assertEqual(self.out, [])
        other = NO_REPORT.replace("You've hit your usage limit. Your limit resets 11:50am (UTC).", "Error: a tool call failed")
        self.assertEqual(self.explain({"arch": other}, "reviewer-arch"), 1)
        self.assertEqual(len(self.out), 1)
        self.assertEqual(self.explain({}, "reviewer-arch"), 1)
        self.assertEqual(self.out, ["reviewer-arch: no lane comment to read"])

    def test_a_lane_that_did_not_run_for_the_usage_limit_ends_with_six_without_a_reset_time(self):
        code = self.explain({"arch": DID_NOT_RUN}, "reviewer-arch")
        self.assertEqual(code, 6)
        self.assertEqual(
            self.out,
            [
                "reviewer-arch: did not run (usage limit) — the session ended with `error_during_execution` after 1 turns; "
                "session said: You've hit your session limit.",
                "USAGE LIMIT: reviewer-arch — re-run that job once the limit has reset, nothing to fix",
            ],
        )

    def test_the_watch_hands_the_failed_runs_over(self):
        failed = []
        failing = run("reviewer-infra", "failure", run_id=9)
        code = Watch.watch(self, [SHA], [[failing, run("Backend")]], report_failed=failed.append)
        self.assertEqual((code, failed), (1, [[failing]]))


class LocalCommit(unittest.TestCase):
    """The watch says in one line when it cannot read the commit to wait for."""

    def test_an_unread_local_commit_is_said_not_passed_over(self):
        out = []
        with mock.patch.object(watch_pr, "gh", side_effect=watch_pr.GitHubError("gh: not logged in")):
            self.assertEqual(watch_pr.local_commit("7", out.append), "")
        self.assertEqual(out, ["the local commit could not be read (gh: not logged in): watching whatever head GitHub gives"])


class Parse(unittest.TestCase):
    def test_check_runs_are_read_from_the_api_lines(self):
        line = '{"id": 4, "name": "E2E", "status": "completed", "conclusion": "success", "html_url": "https://x/4", "completed_at": "t"}'
        queued = '{"id": 5, "name": "Backend", "status": "queued", "conclusion": null, "html_url": "https://x/5", "completed_at": null}'
        self.assertEqual(
            watch_pr.parse_runs(line + "\n" + queued + "\n"),
            [Run(4, "E2E", "completed", "success", "https://x/4", "t"), Run(5, "Backend", "queued", "", "https://x/5", "")],
        )


class Main(unittest.TestCase):
    def main(self, content):
        with tempfile.TemporaryDirectory() as folder:
            if content is not None:
                (Path(folder) / "required-checks.json").write_text(content, encoding="utf-8")
            with mock.patch.object(watch_pr, "ROOT", Path(folder)), \
                    mock.patch.object(watch_pr, "local_commit", return_value=SHA), \
                    mock.patch.object(watch_pr, "watch", return_value=0) as watched, \
                    contextlib.redirect_stdout(io.StringIO()):
                return watch_pr.main(["12"]), watched

    # The whole way in: main reads the required checks and hands them to the watch.
    def test_the_required_checks_reach_the_watch(self):
        code, watched = self.main('{"checks": ["Quality", "E2E"]}')
        self.assertEqual(code, 0)
        self.assertEqual(watched.call_args.args[2], ["Quality", "E2E"])

    def test_required_checks_that_cannot_be_used_stop_the_watch(self):
        for content in (None, "not json", "{}", '{"checks": []}', '{"checks": "Quality"}', '{"checks": [""]}'):
            code, watched = self.main(content)
            self.assertEqual(code, 2, content)
            watched.assert_not_called()


class CannotWatch(unittest.TestCase):
    # A branch without a pull request is said at once, not retried as an outage.
    def test_a_branch_without_a_pull_request_is_not_retried(self):
        def no_pull_request(*args):
            raise watch_pr.GitHubError('no pull requests found for branch "x"')

        original, watch_pr.gh = watch_pr.gh, no_pull_request
        try:
            with self.assertRaises(watch_pr.CannotWatch):
                watch_pr.head_of(None)
        finally:
            watch_pr.gh = original

    # An answer that is no pull request is a failed poll, retried like any other.
    def test_an_answer_without_a_state_is_a_failed_poll(self):
        original, watch_pr.gh = watch_pr.gh, lambda *args: "[]"
        try:
            with self.assertRaises(watch_pr.GitHubError):
                watch_pr.head_of("12")
        finally:
            watch_pr.gh = original


if __name__ == "__main__":
    unittest.main()
