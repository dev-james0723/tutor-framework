"""Independent implementation-owner acceptance: original scenarios, no source questions.

These tests exercise responses, not case-ID matching or documentation promises.
"""
import unittest

from tutor_framework.domains.music.global_theory import LearnerContext, route, terminology


class OwnerContextAcceptance(unittest.TestCase):
    def test_minim_is_answered_without_onboarding(self):
        result = route("What is a minim?", LearnerContext())
        self.assertEqual(result["mode"], "direct")
        self.assertEqual(result["questions"], [])
        self.assertIn("half note", result["answer"].casefold())

    def test_quaver_is_answered_without_onboarding(self):
        result = route("What is a quaver?", LearnerContext())
        self.assertEqual(result["mode"], "direct")
        self.assertIn("eighth note", result["answer"].casefold())

    def test_polite_long_definition_is_still_a_simple_question(self):
        result = route(
            "Could you please explain to me what a minim means in British note names?",
            LearnerContext(),
        )
        self.assertEqual(result["mode"], "direct")
        self.assertEqual(result["questions"], [])
        self.assertIn("half note", result["answer"].casefold())

    def test_chinese_learning_pack_is_not_classified_by_whitespace_count(self):
        context = LearnerContext(response_language="zh-Hant")
        result = route("請幫我分析這份樂譜並製作完整學習包。", context)
        self.assertNotEqual(result["mode"], "direct")
        self.assertLessEqual(len(result["questions"]), 5)

    def test_short_explicit_learning_pack_request_is_not_simple_definition(self):
        result = route("Create a Learning Pack about crotchets", LearnerContext())
        self.assertNotEqual(result["mode"], "direct")

    def test_minim_terminology_has_a_useful_public_definition(self):
        result = terminology("minim", LearnerContext())
        self.assertTrue(result.get("definition"), "Public foundational definitions cannot all be null")
        self.assertEqual(result["relation"], "exact")

    def test_unknown_term_is_not_invented_as_a_dispute(self):
        result = terminology("zqv-unattested-notation-system", LearnerContext())
        self.assertIn(result.get("state"), {"unsupported", "review_required"})
        self.assertNotEqual(result.get("relation"), "disputed")

    def test_integer_one_is_not_a_privacy_consent_boolean(self):
        with self.assertRaises((ValueError, TypeError)):
            LearnerContext(no_save=1)

    def test_integer_zero_is_not_a_text_only_boolean(self):
        with self.assertRaises((ValueError, TypeError)):
            LearnerContext(text_only=0)

    def test_every_v_i_is_not_automatically_a_cadence(self):
        answer = route("Is every V-I a cadence?", LearnerContext())["answer"].casefold()
        self.assertTrue(any(word in answer for word in ("phrase", "boundary", "formal", "closure")))
        self.assertTrue(any(word in answer for word in ("not", "no", "depends")))

    def test_movable_do_preserves_the_explicit_tonic(self):
        answer = route("In movable do, which note is do in G major?", LearnerContext())["answer"]
        self.assertIn("G", answer)
        self.assertTrue(any(word in answer.casefold() for word in ("tonic", "movable")))

    def test_octave_labels_require_the_software_convention(self):
        answer = route("Why does this app label middle C C3?", LearnerContext())["answer"].casefold()
        self.assertTrue(any(word in answer for word in ("convention", "software", "numbering")))
        self.assertIn("c4", answer)

    def test_jazz_does_not_inherit_an_absolute_classical_ban(self):
        answer = route("Are parallel fifths always forbidden in jazz?", LearnerContext())["answer"].casefold()
        self.assertTrue(any(word in answer for word in ("style", "context", "jazz")))
        self.assertTrue(any(word in answer for word in ("not", "no", "depends")))


class OwnerGeneralizationAcceptance(unittest.TestCase):
    def test_semiquaver_is_not_matched_as_quaver(self):
        result = route("What is a semiquaver?", LearnerContext())
        self.assertIn("sixteenth", result["answer"].casefold())

    def test_demisemiquaver_is_not_matched_as_eighth_note(self):
        result = route("What is a demisemiquaver?", LearnerContext())
        self.assertTrue(any(value in result["answer"].casefold() for value in ("32nd", "thirty-second")))

    def test_movable_do_generalizes_beyond_one_hardcoded_key(self):
        for tonic in ("D", "F", "A", "Bb"):
            with self.subTest(tonic=tonic):
                result = route(f"In movable do, which note is do in {tonic} major?", LearnerContext())
                self.assertIn(tonic, result["answer"])
                self.assertIn("tonic", result["answer"].casefold())

    def test_fixed_do_does_not_change_to_the_major_key_tonic(self):
        result = route("In fixed do, which note is do in G major?", LearnerContext())
        self.assertRegex(result["answer"], r"\bC\b")
        self.assertIn("fixed", result["answer"].casefold())

    def test_chinese_response_preference_applies_to_solfege_explanations(self):
        result = route("In movable do, which note is do in D major?", LearnerContext(response_language="zh-Hant"))
        self.assertRegex(result["answer"], "[\\u4e00-\\u9fff]")
        self.assertIn("D", result["answer"])

    def test_caplin_and_us_iac_are_not_same_resolver_context(self):
        caplin = terminology("IAC", LearnerContext(analysis_framework="Caplin"))
        american = terminology("IAC", LearnerContext(analysis_framework="US-tonal-harmony"))
        self.assertNotEqual((caplin.get("record_id"), caplin.get("selected_framework")),
                            (american.get("record_id"), american.get("selected_framework")))

    def test_both_profile_and_caller_dict_are_not_shared_mutable_state(self):
        original = {"note_names": "en-GB"}
        context = LearnerContext(terminology_preference=original)
        original["note_names"] = "en-US"
        self.assertEqual(context.terminology_preference["note_names"], "en-GB")
        with self.assertRaises((TypeError, AttributeError)):
            context.terminology_preference["note_names"] = "en-US"


if __name__ == "__main__":
    unittest.main()
