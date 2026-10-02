"""Original acceptance assertions against the visually checked primary outline."""
import unittest

from tutor_framework.domains.music.global_theory.syllabus import syllabus_for


class VerifiedSyllabusAcceptance(unittest.TestCase):
    def test_grade_one_exact_scope_not_other_system_grade_equivalence(self):
        pack = syllabus_for("abrsm-theory-from-2020", 1)
        self.assertEqual(pack["major_keys"], ["C", "G", "D", "F"])
        self.assertEqual(pack["minor_keys"], [])
        self.assertEqual(pack["interval_scope"], "number_above_tonic")
        self.assertEqual(pack["grade_equivalences"], [])
        self.assertIn("Grade 1", pack["source_locator"])
        self.assertEqual(pack["source_verification"], "primary_outline_visually_checked")

    def test_grade_two_does_not_leak_melodic_minor_or_interval_quality(self):
        pack = syllabus_for("abrsm-theory-from-2020", 2)
        self.assertEqual(set(pack["minor_keys"]), {"A", "E", "D"})
        self.assertEqual(pack["minor_forms"], ["harmonic"])
        self.assertEqual(pack["interval_scope"], "number_above_tonic")
        self.assertNotIn("compound_meter", pack["generator_competencies"])

    def test_grade_three_inherits_foundations_and_adds_compound_meter(self):
        pack = syllabus_for("abrsm-theory-from-2020", 3)
        self.assertIn("compound_meter", pack["generator_competencies"])
        self.assertIn("duration_ratio", pack["generator_competencies"])
        self.assertEqual(pack["max_key_accidentals"], 4)
        self.assertEqual(set(pack["minor_forms"]), {"harmonic", "melodic"})
        self.assertNotIn("triad_inversion", pack["generator_competencies"])

    def test_grade_five_inversions_do_not_change_cadence_framework(self):
        pack = syllabus_for("abrsm-theory-from-2020", 5)
        self.assertIn("triad_inversion", pack["generator_competencies"])
        self.assertEqual(pack["inversion_labels"], {"root": "a", "first": "b", "second": "c"})
        self.assertEqual(pack["cadence_convention"], "ABRSM_UK_not_US_IAC")

    def test_unknown_version_and_advanced_grades_fail_closed(self):
        self.assertEqual(syllabus_for("abrsm-2099", 1)["state"], "review_required")
        for grade in (6, 7, 8):
            self.assertEqual(syllabus_for("abrsm-theory-from-2020", grade)["state"], "review_required")

    def test_one_data_authority_drives_all_five_grade_boundaries(self):
        import json
        from importlib.resources import files
        data = json.loads(files("tutor_framework.domains.music.global_theory").joinpath("data/abrsm_from_2020.json").read_text())
        for row in data["packs"]:
            runtime = syllabus_for("abrsm-theory-from-2020", row["grade"])
            for field in ("major_keys", "minor_keys", "minor_forms", "interval_scope", "generator_competencies"):
                self.assertEqual(runtime[field], row[field], f"Grade {row['grade']} {field} differs from versioned source data")

    def test_snapshots_are_not_mutable_global_authority(self):
        first = syllabus_for("abrsm-theory-from-2020", 1)
        first["major_keys"].append("B")
        self.assertNotIn("B", syllabus_for("abrsm-theory-from-2020", 1)["major_keys"])


if __name__ == "__main__":
    unittest.main()
