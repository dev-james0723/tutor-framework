"""TDD: professor-specific assertions require directly relevant, independently verifiable evidence."""
from __future__ import annotations
import importlib.util
import sqlite3
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "integrations/caplin-form-tutor-v36/scripts/learning_models.py"
spec = importlib.util.spec_from_file_location("caplin_v36_learning_models", SOURCE)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class ProfessorEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE claims(id INTEGER PRIMARY KEY, source_id TEXT, locator TEXT, text TEXT,
                authority TEXT, verification TEXT, stance TEXT);
          CREATE TABLE concepts(id INTEGER PRIMARY KEY, name TEXT);
          CREATE TABLE claim_concepts(claim_id INTEGER, concept_id INTEGER);
          CREATE TABLE professor_patterns(id INTEGER PRIMARY KEY, category TEXT UNIQUE,
                support_count INTEGER, wording TEXT);
          CREATE TABLE professor_pattern_evidence(pattern_id INTEGER, claim_id INTEGER,
                relation TEXT, PRIMARY KEY(pattern_id, claim_id));
        """)
        self.db.execute("INSERT INTO concepts VALUES(1,'cadence')")
        self.db.execute("INSERT INTO concepts VALUES(2,'sentence')")
        self.db.commit()

    def claim(self, ident, name, locator, text, category=None, status="verified",
              authority="instructor", stance="support"):
        self.db.execute("INSERT INTO claims VALUES (?,?,?,?,?,?,?)",
                        (ident,name,locator,text,authority,status,stance))
        if category is not None:
            self.db.execute("INSERT INTO claim_concepts VALUES (?,?)",(ident,category))
        self.db.commit()

    def test_unrelated_instructor_claims_never_substitute_for_target_concept(self):
        self.claim(1,"lecture-1","00:04","Sentence beginnings are unstable",2)
        self.claim(2,"lecture-2","00:12","Basic ideas can return",2)
        self.assertEqual(model.derive_professor_patterns(self.db,"cadence"),[])
        self.assertEqual(self.db.execute("SELECT count(*) FROM professor_patterns").fetchone()[0],0)

    def test_requires_two_independent_anchors_and_verified_status(self):
        self.claim(1,"lecture-1","00:04","Cadence needs a real closing progression",1)
        self.claim(2,"lecture-1","00:04","Cadence is contextual",1)
        self.assertEqual(model.derive_professor_patterns(self.db,"cadence"),[])
        self.claim(3,"lecture-2","00:15","Cadence can be deceptive",1,status="review_required")
        self.assertEqual(model.derive_professor_patterns(self.db,"cadence"),[])
        self.claim(4,"lecture-2","00:20","Cadence needs the bass as evidence",1)
        patterns=model.derive_professor_patterns(self.db,"cadence")
        self.assertEqual(len(patterns),1)
        self.assertEqual(patterns[0]["support_count"],2)
        e=model.professor_evidence(self.db,patterns[0]["id"])
        self.assertEqual(set(e["support_claim_ids"]),{1,4})

    def test_multiconcept_claims_are_not_lost_and_text_match_is_exact(self):
        self.claim(1,"lecture-a","00:10","Avoid treating a single chord as proof",1)
        self.claim(2,"lecture-b","00:19","Confirm melodic closure with harmonic function",1)
        self.db.executemany("INSERT INTO claim_concepts VALUES(?,2)",[(1,),(2,)])
        self.db.commit()
        patterns=model.derive_professor_patterns(self.db,"cadence")
        self.assertEqual(patterns[0]["support_count"],2)
        self.claim(3,"lecture-c","00:22","Cadence is contextual",None)
        self.assertEqual(model.derive_professor_patterns(self.db,"cadence")[0]["support_count"],3)

    def test_counterexamples_are_concept_scoped_and_stale_links_are_removed(self):
        self.claim(1,"one","t1","Cadence is syntactic",1)
        self.claim(2,"two","t2","Cadence needs context",1)
        self.claim(3,"three","t3","A cadence can fail",1,stance="counterexample")
        self.claim(4,"four","t4","Sentence repeats idea",2,stance="counterexample")
        pattern=model.derive_professor_patterns(self.db,"cadence")[0]
        self.assertEqual(model.professor_evidence(self.db,pattern["id"])["counterexample_claim_ids"],[3])
        self.db.execute("UPDATE claims SET verification='review_required' WHERE id=2")
        self.db.commit()
        self.assertEqual(model.derive_professor_patterns(self.db,"cadence"),[])
        self.assertEqual(self.db.execute("SELECT count(*) FROM professor_patterns").fetchone()[0],0)


if __name__=="__main__":
    unittest.main()
