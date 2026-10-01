import importlib
import unittest
from tutor_framework.domains.music.lesson.models import Passage,MeasureVisit,RightsRecord
H='a'*64


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.m=importlib.import_module('tutor_framework.domains.music.lesson.models')
        self.assertTrue(hasattr(self.m,'LessonManifest'),'full typed lesson manifest not implemented')

    def make(self):
        m=self.m
        source=m.SourceAsset('score','source.musicxml',H,'symbolic','user supplied',RightsRecord('public_domain','user_provided','not_applicable','private local study'))
        passage=Passage('p','ed',(MeasureVisit('1',1),),('P1',),'R=N')
        example=m.ExampleSpec('ex','score','p','120','identity',(), 'Original source demonstration')
        scene=m.SceneSpec('orient','Where are we?','orient','p',(m.BeatSpec('speech','Listen to the ending.'),),m.VisualSpec('text',(),('A short learning objective',)))
        return m.LessonManifest('lesson','Lesson',('Compare cadential evidence',),(source,),(passage,),(example,),(scene,))

    def test_roundtrip_and_single_manifest(self):
        x=self.make();self.assertEqual(self.m.LessonManifest.from_dict(x.to_dict()).to_dict(),x.to_dict())

    def test_missing_reference_rejected(self):
        x=self.make().to_dict();x['examples'][0]['passage_id']='missing'
        with self.assertRaises(ValueError):self.m.LessonManifest.from_dict(x)

    def test_duplicate_ids_rejected(self):
        x=self.make().to_dict();x['sources']*=2
        with self.assertRaises(ValueError):self.m.LessonManifest.from_dict(x)

    def test_remote_grants_cannot_be_embedded_in_lesson(self):
        x=self.make().to_dict();x['production_grants']=[{'approved':True}]
        with self.assertRaises(ValueError):self.m.LessonManifest.from_dict(x)

    def test_missing_music_purpose_rejected(self):
        with self.assertRaises(ValueError):self.m.BeatSpec('music','',example_id='ex')

    def test_music_cannot_also_contain_speech(self):
        with self.assertRaises(ValueError):self.m.BeatSpec('speech','Words',example_id='ex')

    def test_narration_asset_must_match_text_hash(self):
        with self.assertRaises(ValueError):self.m.BeatSpec('speech','Words',narration_asset='voice')

    def test_visual_unknown_component_rejected(self):
        with self.assertRaises(ValueError):self.m.VisualSpec('eval-javascript',(),())

    def test_transfer_requires_different_passage(self):
        x=self.make().to_dict();x['scenes'][0]['stage']='transfer';x['scenes'][0]['transfer_from_passage_id']='p'
        with self.assertRaises(ValueError):self.m.LessonManifest.from_dict(x)

    def test_reveal_before_question_rejected(self):
        x=self.make().to_dict();x['scenes'][0]['answers_question_id']='q'
        with self.assertRaises(ValueError):self.m.LessonManifest.from_dict(x)

    def test_render_paths_cannot_escape_build_root(self):
        with self.assertRaises(ValueError):self.m.SceneSpec('../out','Title','orient','p',(self.m.BeatSpec('speech','Text'),),self.m.VisualSpec('text',(),()))

    def test_public_source_is_not_implicitly_verified(self):
        source=self.make().sources[0]
        self.assertEqual(source.evidence_state.value,'review_required')


if __name__=='__main__':unittest.main()
