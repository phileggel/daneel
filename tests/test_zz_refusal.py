"""Throwaway: a failing test, to prove the ruleset refuses this pull request. Never merged."""

import unittest


class Refusal(unittest.TestCase):
    def test_this_always_fails(self):
        self.fail("deliberate failure: the merge of this pull request must be refused")


if __name__ == "__main__":
    unittest.main()
