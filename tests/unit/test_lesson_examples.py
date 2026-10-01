import importlib
import unittest
from dataclasses import replace
from fractions import Fraction as F
from tutor_framework.domains.music.lesson.models import ExampleSpec,Passage,MeasureVisit
from tutor_framework.domains.music.lesson.symbolic import parse_score,traverse,Event
from tests.unit.test_lesson_symbolic import score,measure,note


class ExampleTests(unittest.TestCase):
    def setUp(self):
        try:self.l=importlib.import_module('tutor_framework.domains.music.lesson.examples')
        except ImportError:self.fail('Music Example Lab not implemented')

    def test_one_symbolic_revision_drives_parts(self):
        raw=score(measure('1',note(dur=12)),measure('1',note('E',dur=12)))
        p=Passage('p','e',(MeasureVisit('1',1),),('P1','P2'),'R=N')
        spec=ExampleSpec('melody','xml','p','90','melody',('P1',),'Hear the selected melodic line')
        xml,ledger=self.l.prepare_example(raw,spec,p)
        parsed=parse_score(xml)
        self.assertEqual(parsed.parts,('P1',));self.assertEqual(ledger['bpm'],'90')
        self.assertEqual(ledger['symbolic_revision'],parsed.revision)

    def test_controlled_rewrite_changes_only_declared_pitch(self):
        raw=score(measure('1',note(dur=12)))
        p=Passage('p','e',(MeasureVisit('1',1),),('P1',),'R=N')
        spec=ExampleSpec('b','xml','p','120','rewrite',(),'Compare last soprano degree',parent_id='a',changed_note_id='P1:1:n1',changed_midi=64)
        xml,ledger=self.l.prepare_example(raw,spec,p)
        self.assertEqual(parse_score(xml).events[0].midi,64)
        self.assertEqual(ledger['controlled_changes'][0]['field'],'midi')

    def test_unknown_controlled_note_is_not_silently_ignored(self):
        raw=score(measure('1',note(dur=12)));p=Passage('p','e',(MeasureVisit('1',1),),('P1',),'R=N')
        spec=ExampleSpec('b','xml','p','120','rewrite',(),'Compare',parent_id='a',changed_note_id='missing',changed_midi=64)
        with self.assertRaises(ValueError):self.l.prepare_example(raw,spec,p)

    def test_explicit_repeat_expansion_keeps_source_visit_mapping(self):
        raw=score(measure('1',note(dur=12)));p=Passage('p','e',(MeasureVisit('1',1),MeasureVisit('1',2)),('P1',),'R=N')
        spec=ExampleSpec('a','xml','p','120','identity',(),'Hear both written visits')
        xml,ledger=self.l.prepare_example(raw,spec,p)
        self.assertEqual(len(parse_score(xml).labels),2)
        self.assertEqual([x['source_occurrence'] for x in ledger['traversal']],[1,2])

    def test_fragment_transpose_and_expansion_are_labelled_derivatives(self):
        es=(Event('a','P1','1',1,'1','1',F(0),F(1),60),Event('b','P1','1',1,'1','1',F(1),F(1),62))
        frag=self.l.extract_motive(es,F(0),F(1));self.assertEqual(len(frag),1)
        moved=self.l.transpose_example(frag,7);self.assertEqual(moved[0].midi,67)
        extended=self.l.repeat_fragment(es,F(0),F(1),3)
        self.assertEqual(len(extended),3);self.assertEqual([x.onset for x in extended],[F(0),F(1),F(2)])
        self.assertEqual(len({x.event_id for x in extended}),3)

    def test_harmonic_reduction_requires_explicit_grid(self):
        es=(Event('a','P1','1',1,'1','1',F(0),F(2),60),Event('b','P1','1',1,'2','1',F(0),F(1),64))
        reduced=self.l.harmonic_reduction(es,(F(0),F(1),F(2)))
        self.assertEqual([x['pitches'] for x in reduced],[(60,64),(60,)])
        with self.assertRaises(ValueError):self.l.harmonic_reduction(es,())

    def test_comparison_catalog_has_real_notated_templates(self):
        catalog=self.l.teaching_catalog()
        self.assertTrue({'sentence','period','hybrid','cadence','non_cadence','fragmentation','tonal_return','thematic_return','expansion','extension'}<=set(catalog))
        for name,entry in catalog.items():
            self.assertGreater(len(parse_score(entry['musicxml']).events),0,name)
            self.assertIn('pedagogical',entry['status'])


if __name__=='__main__':unittest.main()
