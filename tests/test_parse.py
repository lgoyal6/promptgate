"""The output-contract contradiction, and what it costs, with no model involved.

Parahelp's published manager prompt states its output contract four times.

    line  7   <manager_feedback>reject</manager_feedback>
    line 13   <manager_verify>reject</manager_verify>
    line 22   <manager_verify>reject</manager_verify>
    line 47   <manager_verify>reject</manager_verify>

Three say one tag, one says another. A caller writing a parser will read the
contract in whichever place they happen to look. These tests show what happens
to each choice, deterministically, so the claim does not rest on how any
particular model behaves on any particular day.
"""
import re
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import parse as PA  # noqa: E402
import prompt as P  # noqa: E402

VERIFY_REJECT = "<manager_verify>reject</manager_verify><feedback_comment>outside the 14 day window</feedback_comment>"
FEEDBACK_REJECT = "<manager_feedback>reject</manager_feedback><feedback_comment>outside the 14 day window</feedback_comment>"
VERIFY_ACCEPT = "<manager_verify>accept</manager_verify>"


class TestPublishedPromptIsContradictory(unittest.TestCase):
    """Read the shipped file and confirm the contradiction is really there."""

    def setUp(self):
        self.lines = P.SRC.read_text().split("\n")

    def test_reject_contract_stated_four_times(self):
        stated = [i + 1 for i, ln in enumerate(self.lines)
                  if "reject" in ln and ("manager_verify" in ln or "manager_feedback" in ln)]
        self.assertEqual(len(stated), 4, f"expected 4 statements, found at lines {stated}")

    def test_three_say_manager_verify_one_says_manager_feedback(self):
        verify, feedback = [], []
        for i, ln in enumerate(self.lines, start=1):
            if "reject</manager_verify>" in ln:
                verify.append(i)
            if "reject</manager_feedback>" in ln:
                feedback.append(i)
        self.assertEqual(verify, [13, 22, 47])
        self.assertEqual(feedback, [7])

    def test_the_fix_is_one_word(self):
        before = P.build("full")
        after = P.build("fix_tag")
        self.assertIn("manager_feedback", before)
        self.assertNotIn("manager_feedback", after)
        self.assertEqual(len(before) - len(after), 4)  # "feed" -> "veri" is 4 chars shorter


class TestConsequenceForCallers(unittest.TestCase):
    """A parser built from the majority statement cannot see the minority form."""

    def test_strict_parser_reads_the_majority_form(self):
        self.assertEqual(PA.parse_strict(VERIFY_REJECT), "reject")
        self.assertEqual(PA.parse_strict(VERIFY_ACCEPT), "accept")

    def test_strict_parser_is_blind_to_the_line_7_form(self):
        self.assertIsNone(PA.parse_strict(FEEDBACK_REJECT))

    def test_a_dropped_reject_is_indistinguishable_from_silence(self):
        """The failure mode that matters.

        A reject in the line-7 form and a response containing no verdict at all
        produce the same thing from a strict parser: None. A gate cannot tell
        'the manager objected' from 'the manager said nothing', so unless the
        caller treats a missing verdict as fatal, the tool call proceeds.
        """
        self.assertIsNone(PA.parse_strict(FEEDBACK_REJECT))
        self.assertIsNone(PA.parse_strict("I think this looks fine to me."))

    def test_tolerant_parser_recovers_it_and_says_which_tag(self):
        verdict, tag = PA.parse_tolerant(FEEDBACK_REJECT)
        self.assertEqual(verdict, "reject")
        self.assertEqual(tag, "manager_feedback")

    def test_accepts_are_never_affected(self):
        """Both forms of the contract agree on accept, so only rejects can be lost.

        This is why the bug is asymmetric: the tag that is stated inconsistently
        is only ever used to decline a tool call.
        """
        for text in (VERIFY_ACCEPT, "<manager_verify>accept</manager_verify>"):
            self.assertEqual(PA.parse_strict(text), "accept")
            self.assertEqual(PA.parse_tolerant(text)[0], "accept")

    def test_classify_flags_the_silent_drop(self):
        r = PA.classify(FEEDBACK_REJECT, expected="reject")
        self.assertTrue(r["strict_missed"])
        self.assertTrue(r["silently_dropped_reject"])
        self.assertTrue(r["correct_tolerant"])
        self.assertFalse(r["correct_strict"])


class TestCaseSetIsBalanced(unittest.TestCase):
    def test_fourteen_each_way(self):
        import cases as C
        acc = sum(1 for c in C.CASES if c["expected"] == "accept")
        rej = sum(1 for c in C.CASES if c["expected"] == "reject")
        self.assertEqual(acc, 14)
        self.assertEqual(rej, 14)

    def test_no_duplicate_ids(self):
        import cases as C
        ids = [c["id"] for c in C.CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_case_states_why(self):
        import cases as C
        for c in C.CASES:
            self.assertTrue(c["why"].strip(), f"{c['id']} has no rationale")


if __name__ == "__main__":
    unittest.main(verbosity=2)
