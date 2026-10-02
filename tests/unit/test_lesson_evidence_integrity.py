"""Regression tests against inherited false-positive QA and MIDI rejection."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tutor_framework.domains.music.lesson.adapters import midi_notes
from tutor_framework.domains.music.lesson.compiler import compile_existing
from tutor_framework.domains.music.lesson.pilot import audit
from tutor_framework.domains.music.lesson.verify_existing import verify
from tests.unit.test_lesson_media import midi_bytes


class EvidenceIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.out=self.root/'outputs';self.out.mkdir()
        self.manifest={'title':'Synthetic lesson','fps':24,'scenes':[], 'voice':{}}
        for name in ['lesson.mp4','annotated-score.pdf','lesson.srt','lesson.vtt']:
            (self.out/name).write_text('not actual media')
        for name in ['receipt.json','validation.json']:(self.out/name).write_text('{}')
        self.save()

    def save(self):
        (self.out/'lesson-manifest.json').write_text(json.dumps(self.manifest))

    def test_existing_files_alone_do_not_prove_decode_or_caption_structure(self):
        result=compile_existing(self.root,self.root/'audit.json')
        for name in ['decode','caption_structure','baseline_preserved']:
            self.assertNotEqual(result['qa']['checks'][name],'passed',name)

    def test_absent_transfer_and_context_are_not_present(self):
        result=audit(self.root)
        self.assertFalse(result['different_material_transfer'])
        self.assertFalse(result['context_card'])
        self.assertFalse(result['mochi'])
        self.assertFalse(result['english_captions'])

    def test_unrendered_transfer_metadata_is_not_an_actual_pilot_scene(self):
        self.manifest.update(transfer={'verified':True},context_card={'verified':True})
        self.save();result=audit(self.root)
        self.assertFalse(result['different_material_transfer']);self.assertFalse(result['context_card'])

    def test_legacy_claimed_passes_are_not_fresh_evidence(self):
        fake={'notation_review':{'a':'looks right'},'music':[{'notation_parse':'pass','peak':.1}],
              'speech':[{'caption_text_and_bounds':'pass','peak':.1}], 'visual_layout':{'scene_warnings':[]}}
        (self.out/'validation.json').write_text(json.dumps(fake))
        # Executable absence should be explicit; no external command is needed here.
        with patch('subprocess.run',side_effect=FileNotFoundError('ffmpeg absent')):
            result=verify(self.root)
        for name in ['decode','source_notation','protected_listening','loudness_and_clipping','notation_readability','layout_collisions']:
            self.assertNotEqual(result['checks'][name],'passed',name)

    def test_legal_zero_velocity_note_on_is_equivalent_to_note_off(self):
        original=midi_bytes();equivalent=original.replace(b'\x83\x60\x80\x3c\x00',b'\x83\x60\x90\x3c\x00')
        self.assertEqual(midi_notes(original),midi_notes(equivalent))


if __name__=='__main__':unittest.main()
