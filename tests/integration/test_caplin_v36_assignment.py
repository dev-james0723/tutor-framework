"""TDD: independent annotation gates and isolated score/essay/self-proof PDFs."""
from __future__ import annotations
import tempfile
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path

from tutor_framework.domains.music.lesson.learning_pack.assignment_engine import (
    ScoreFact, ScoreMark, AnnotationProof, CadenceCheck, IntentionalError,
    PassageCorrespondence, SymbolicCadenceSnapshot, audit_assignment,
)
from tutor_framework.domains.music.lesson.learning_pack.assignment_pdf import render_assignment, _score_pdf


def fixture():
    marks=(
        ScoreMark("a1",1,"cadence","I:PAC",(0.12,0.16,0.35,0.13),5,8),
        ScoreMark("a2",1,"phrase","BI′",(0.10,0.42,0.35,0.12),9,10,depth=2),
    )
    proofs=(
        AnnotationProof("a1",5,8,"I:HC",(
            ScoreFact("harmony","root-position dominant close",5,8,"score:1/mm5-8"),
            ScoreFact("bass","V in bass at m.8",8,8,"score:1/mm8"),
            ScoreFact("melody","open melodic ending",8,8,"score:1/mm8"),
            ScoreFact("grouping","phrase ends at m.8",8,8,"score:1/mm8"),
        ),"Lesson 2, 04:10", "Dominant arrival without HC is an alternative",
        CadenceCheck("HC",8,True,True,False,None,True)),
        AnnotationProof("a2",9,10,"BI′",(
            ScoreFact("melody","recognizable BI with changed ending",9,10,"score:1/mm9-10"),
            ScoreFact("rhythm","opening rhythm retained",9,10,"score:1/mm9-10"),
        ),"Lesson 1, 03:00","Could function as a new idea"),
    )
    errors=(IntentionalError("a1","I:PAC","I:HC","Deliberate challenge: dominant is not authentic closure"),)
    return marks,proofs,errors


class EvidenceDrivenAssignmentTests(unittest.TestCase):
    def test_verified_ledger_structure_and_deliberate_error_register(self):
        marks,proofs,errors=fixture()
        report=audit_assignment(marks,proofs,{"Crux":False,"Essay":True},
                   {"Essay":True},errors=errors)
        self.assertEqual(report["structural_gate"],"passed",report["issues"])
        self.assertEqual(report["content_accuracy"],"review_required")
        self.assertEqual(report["intentional_error_count"],1)

    def test_unregistered_error_and_weak_cadence_block(self):
        marks,proofs,errors=fixture()
        self.assertEqual(audit_assignment(marks,proofs,{}, {},errors=())["structural_gate"],"failed")
        weak=replace(proofs[0],cadence=replace(proofs[0].cadence,dominant_root=False))
        self.assertEqual(audit_assignment(marks,(weak,proofs[1]),{}, {},errors=errors)["structural_gate"],"failed")

    def test_every_annotation_requires_independent_aspects_and_precise_locator(self):
        marks,proofs,errors=fixture()
        weak=replace(proofs[1],facts=(proofs[1].facts[0],))
        report=audit_assignment(marks,(proofs[0],weak),{}, {},errors=errors)
        self.assertIn("a2",str(report["issues"]))
        orphan=audit_assignment(marks,proofs[:1],{}, {},errors=errors)
        self.assertEqual(orphan["structural_gate"],"failed")

    def test_crux_requirement_needs_direct_score_correspondence(self):
        marks,proofs,errors=fixture()
        report=audit_assignment(marks,proofs,{"Crux":True},{"Crux":True},errors=errors)
        self.assertEqual(report["structural_gate"],"failed")
        crux=PassageCorrespondence((42,44),(262,264),"E4 G4 A4","D4 F4 G4",
              "same dotted rhythm","same scale-degree bass pattern","tonicized context compared",
              "recap return of closing idea","transposed and extended by one bar",
              "score:exposition mm42-44","score:recap mm262-264")
        report=audit_assignment(marks,proofs,{"Crux":True},{"Crux":True},
                                correspondences=(crux,),errors=errors)
        self.assertEqual(report["structural_gate"],"passed",report["issues"])

    def test_independent_symbolic_cadence_sanity_checks_bass_and_arrival(self):
        marks,proofs,errors=fixture()
        wrong=SymbolicCadenceSnapshot("a1",8,0,"major",7,7,0,2,
                                      "verified score event at mm. 7–8","verified")
        report=audit_assignment(marks,proofs,{}, {},errors=errors,
                                symbolic_snapshots=(wrong,))
        self.assertEqual(report["structural_gate"],"failed")
        self.assertIn("bass",str(report["issues"]))
        fixed=replace(wrong,arrival_bass_pc=7)
        report=audit_assignment(marks,proofs,{}, {},errors=errors,
                                symbolic_snapshots=(fixed,))
        self.assertEqual(report["structural_gate"],"passed",report["issues"])
        self.assertEqual(report["musical_source_verification"],"symbolic_consistency_only")

    def test_renderer_fails_closed_if_source_revision_changed(self):
        import pymupdf as fitz
        marks,proofs,errors=fixture()
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"original.pdf"
            with fitz.open() as pdf:
                pdf.new_page().insert_text((60,80),"score fixture")
                pdf.save(source)
            with self.assertRaises(ValueError):
                render_assignment(source,(1,),marks,proofs,errors,"Piece",
                    tuple("A complete analytical paragraph about form and evidence." for _ in range(5)),
                    Path(td)/"out",expected_source_sha256="a"*64)

    def test_overlapping_formal_brackets_route_to_safe_margin(self):
        import pymupdf as fitz
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"score.pdf"
            with fitz.open() as pdf:
                page=pdf.new_page(width=612,height=792)
                for y in (120,132,144,156,168):
                    page.draw_line((45,y),(560,y),color=(0,0,0))
                pdf.save(source)
            first=ScoreMark("p1",1,"phrase","Presentation",(.12,.42,.3,.1),9,10,depth=1)
            second=ScoreMark("p2",1,"phrase","Continuation",(.12,.42,.3,.1),11,12,depth=1)
            output,placed=_score_pdf(source,(1,),(first,second))
            output.close()
            self.assertEqual([p["route"] for p in placed],
                             ["clear-source-bracket","gutter"])

    def test_required_crux_is_reconciled_in_standalone_selfproof(self):
        import pymupdf as fitz
        marks,proofs,errors=fixture()
        crux=PassageCorrespondence((42,44),(262,264),"E4 G4 A4","D4 F4 G4",
              "same dotted rhythm","same bass degrees","key context compared",
              "return of closing idea","transposition plus insertions",
              "source p1 mm42-44","source p5 mm262-264")
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"score.pdf"
            with fitz.open() as pdf:
                pdf.new_page(width=612,height=792).insert_text((50,80),"synthetic source")
                pdf.save(source)
            options={"expected_source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                     "requirements":{"Crux":True},"completed":{"Crux":True}}
            paragraphs=tuple("An analytical paragraph grounded in verified musical sources."
                            for _ in range(5))
            with self.assertRaises(ValueError):
                render_assignment(source,(1,),marks,proofs,errors,"Piece",paragraphs,
                                  Path(td)/"blocked",**options)
            receipt=render_assignment(source,(1,),marks,proofs,errors,"Piece",paragraphs,
                  Path(td)/"allowed",correspondences=(crux,),**options)
            with fitz.open(receipt["self_proof_pdf"]) as proof:
                text=" ".join(p.get_text() for p in proof)
                self.assertIn("Crux",text)
                self.assertIn("262",text)
                self.assertIn("dotted rhythm",text)

    def test_renderer_keeps_original_score_and_separates_proof(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF media runtime required")
        marks,proofs,errors=fixture()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"score.pdf"
            with fitz.open() as score:
                page=score.new_page(width=612,height=792)
                for y in (120,132,144,156,168):
                    page.draw_line((45,y),(560,y),color=(0,0,0))
                page.insert_text((49,92),"Synthetic score fixture — NOT verified notation")
                page.insert_text((50,110),"1")
                score.save(source)
            receipt=render_assignment(source, (1,), marks, proofs, errors,
                "Synthetic movement", (
                    "The opening idea establishes a clear point of departure with repeated motivic material.",
                    "The second phrase changes the harmonic direction while preserving the opening rhythm.",
                    "The bass provides a more reliable guide than a rest or a sudden change in texture.",
                    "The comparison of the earlier material with its return must be made from the notes.",
                    "The final cadence must be evaluated as a progression rather than an isolated chord.",
                ),root/"out",expected_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
            main=Path(receipt["main_pdf"]);proof=Path(receipt["self_proof_pdf"])
            self.assertTrue(main.is_file() and proof.is_file())
            with fitz.open(source) as base, fitz.open(main) as combined, fitz.open(proof) as selfproof:
                self.assertGreaterEqual(len(combined),2)
                self.assertIn("Synthetic movement",combined[-1].get_text())
                self.assertNotIn("Deliberate challenge", " ".join(page.get_text() for page in combined))
                self.assertIn("Deliberate challenge"," ".join(page.get_text() for page in selfproof))
                # Copy-based PDF source must survive unchanged on a region untouched by the overlays.
                crop=fitz.Rect(40,540,560,700)  # an area not targeted by a fixture annotation
                self.assertEqual(base[0].get_pixmap(clip=crop).samples,
                                 combined[0].get_pixmap(clip=crop).samples)
            self.assertEqual(receipt["musical_review"],"review_required")
            self.assertEqual(receipt["visual_review"],"review_required")


if __name__=="__main__":
    unittest.main()
