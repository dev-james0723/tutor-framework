"""Executable musical answers, not merely successful routing or keyword matching."""
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from tutor_framework.domains.music.global_theory import LearnerContext


class MusicalOperationsAcceptance(unittest.TestCase):
    def setUp(self):
        try:
            self.evaluate = importlib.import_module('tutor_framework.domains.music.global_theory.operations').evaluate
        except ModuleNotFoundError:
            self.fail('The source-bound musical operations are not implemented')

    def run_op(self, operation, **parameters):
        return self.evaluate({'operation':operation, **parameters}, LearnerContext())

    def test_written_interval_number_quality_and_direction(self):
        cases=[('C4','E4','major',3,4),('C4','Eb4','minor',3,3),('C4','F#4','augmented',4,6),
               ('C4','Gb4','diminished',5,6),('C4','E5','major',10,16),('C5','G4','perfect',4,5),
               ('C#4','Db4','diminished',2,0),('B#3','C4','diminished',2,0)]
        for a,b,quality,number,semitones in cases:
            with self.subTest(first=a,second=b):
                result=self.run_op('interval',first=a,second=b)
                self.assertEqual(result['data']['quality'],quality)
                self.assertEqual(result['data']['number'],number)
                self.assertEqual(result['data']['semitones'],semitones)
                self.assertEqual(result['state'],'computed_from_explicit_input')
                self.assertTrue(result['claim_id'])
        self.assertEqual(self.run_op('interval',first='C5',second='G4')['data']['direction'],'descending')

    def test_unknown_octave_is_not_silently_assumed(self):
        for bad in ('C','H4','C+4','C4; echo hello'):
            with self.subTest(pitch=bad),self.assertRaises(ValueError):
                self.run_op('interval',first=bad,second='G4')

    def test_major_and_minor_scales_preserve_spelling(self):
        self.assertEqual(self.run_op('scale',tonic='F#4',mode='major')['data']['notes'],
                         ['F#4','G#4','A#4','B4','C#5','D#5','E#5','F#5'])
        self.assertEqual(self.run_op('scale',tonic='A3',mode='harmonic_minor')['data']['notes'],
                         ['A3','B3','C4','D4','E4','F4','G#4','A4'])
        descending=self.run_op('scale',tonic='A3',mode='melodic_minor',direction='descending')
        self.assertEqual(descending['data']['notes'],['A4','G4','F4','E4','D4','C4','B3','A3'])

    def test_chord_root_and_inversion_do_not_come_from_lowest_note_alone(self):
        result=self.run_op('chord',notes=['B3','D4','F4','G4'])
        self.assertEqual(result['data']['root'],'G')
        self.assertEqual(result['data']['quality'],'dominant_seventh')
        self.assertEqual(result['data']['inversion'],1)
        self.assertEqual(result['data']['figured_bass'],'6/5')
        result=self.run_op('chord',notes=['C4','Eb4','Gb4','Bb4'])
        self.assertEqual(result['data']['quality'],'half_diminished_seventh')

    def test_ambiguous_or_unsupported_pitch_set_does_not_get_fake_chord_name(self):
        result=self.run_op('chord',notes=['C4','D4','F#4'])
        self.assertEqual(result['state'],'review_required')
        self.assertIsNone(result['data']['quality'])

    def test_fixed_and_movable_do_and_minor_basis(self):
        fixed=self.run_op('solfege',notes=['G4','A4','B4'],system='fixed_do',seventh_syllable='si')
        self.assertEqual([n['syllable'] for n in fixed['data']['notes']],['sol','la','si'])
        movable=self.run_op('solfege',notes=['G4','A4','B4'],system='movable_do',tonic='G4',mode='major')
        self.assertEqual([n['syllable'] for n in movable['data']['notes']],['do','re','mi'])
        missing=self.run_op('solfege',notes=['A3','C4','E4'],system='movable_do',tonic='A3',mode='natural_minor')
        self.assertEqual(missing['state'],'review_required')
        la=self.run_op('solfege',notes=['A3','C4','E4'],system='movable_do',tonic='A3',mode='natural_minor',minor_basis='la')
        self.assertEqual([n['syllable'] for n in la['data']['notes']],['la','do','mi'])

    def test_compound_meter_and_irregular_grouping(self):
        result=self.run_op('meter',numerator=6,denominator=8)
        self.assertEqual(result['data']['beats'],2)
        self.assertEqual(result['data']['beat_durations_quarters'],['3/2','3/2'])
        self.assertEqual(self.run_op('meter',numerator=5,denominator=8)['state'],'review_required')
        result=self.run_op('meter',numerator=5,denominator=8,groups=[2,3])
        self.assertEqual(result['data']['beat_durations_quarters'],['1','3/2'])
        with self.assertRaises(ValueError):self.run_op('meter',numerator=5,denominator=8,groups=[3,3])

    def test_voice_leading_keeps_style_separate_from_the_pitch_fact(self):
        start={'bass':'C3','soprano':'G3'};end={'bass':'D3','soprano':'A3'}
        classical=self.run_op('voice_leading',before=start,after=end,style='common_practice')
        jazz=self.run_op('voice_leading',before=start,after=end,style='jazz')
        self.assertEqual(classical['data']['parallels'][0]['interval'],'perfect_fifth')
        self.assertEqual(classical['data']['parallels'][0]['judgment'],'avoid_in_this_exercise')
        self.assertEqual(jazz['data']['parallels'][0]['judgment'],'style_dependent_not_a_universal_error')
        self.assertFalse(jazz['data']['complete_counterpoint_assessment'])

    def test_no_nationality_or_unknown_tradition_inference(self):
        unsupported=self.run_op('raga',notes=['C4','D4','E4'])
        self.assertEqual(unsupported['state'],'unsupported')
        self.assertNotIn('Western',unsupported.get('inferred_tradition',''))

    def test_chinese_explanation_and_no_save_are_effective(self):
        context=LearnerContext(response_language='zh-Hant',no_save=True,text_only=True,
                               curriculum_context={'id':'AP-Music-Theory','version':'2025'},
                               terminology_preference={'note_names':'en-GB'})
        result=self.evaluate({'operation':'interval','first':'C4','second':'Eb4'},context)
        self.assertRegex(result['explanation'],'[\u4e00-\u9fff]')
        self.assertEqual(result['data']['quality'],'minor')
        self.assertFalse(result['persisted'])
        self.assertEqual(result['context']['curriculum_context']['id'],'AP-Music-Theory')
        self.assertEqual(result['context']['terminology_preference']['note_names'],'en-GB')

    def test_source_identity_attaches_to_each_computed_claim(self):
        result=self.run_op('interval',first='D4',second='A4',source_id='score-example:bar-2')
        self.assertEqual(result['source_id'],'score-example:bar-2')
        self.assertEqual(result['provenance_kind'],'analytical_interpretation')
        self.assertFalse(result['official_answer'])
        self.assertFalse(result['musically_verified_from_scan'])
        self.assertTrue(result['reference_sources'])

    def test_enharmonic_semitone_distance_does_not_prove_perfect_fifths(self):
        result=self.run_op('voice_leading',before={'low':'C4','high':'F##4'},after={'low':'D4','high':'G##4'},style='common_practice')
        self.assertEqual(result['data']['parallels'],[])

    def test_jazz_context_does_not_silently_apply_classical_descending_minor(self):
        context=LearnerContext(musical_tradition='jazz')
        result=self.evaluate({'operation':'scale','tonic':'A3','mode':'melodic_minor','direction':'descending'},context)
        self.assertEqual(result['state'],'review_required')
        self.assertIn('convention',result['data']['reason'])

    def test_lowered_unison_retains_diminished_not_augmented_spelling(self):
        self.assertEqual(self.run_op('interval',first='C#4',second='C4')['data']['quality'],'diminished')
        self.assertEqual(self.run_op('interval',first='D#4',second='Db4')['data']['quality'],'2-times-diminished')
        self.assertEqual(self.run_op('interval',first='C4',second='C#4')['data']['quality'],'augmented')

    def test_unknown_extra_parameters_fail_instead_of_ignored_assumptions(self):
        with self.assertRaises(ValueError):self.run_op('interval',first='C4',second='G4',assume_octave=True)
        with self.assertRaises(ValueError):self.run_op('meter',numerator=True,denominator=4)


if __name__=='__main__':unittest.main()
