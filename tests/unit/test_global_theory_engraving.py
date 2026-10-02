"""Real MusicXML engraving through the existing symbolic/MIDI contracts."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from tutor_framework.domains.music.global_theory.engraving import engrave_original_score


def original_musicxml():
    notes = ''.join(f'<note id="n{i}"><pitch><step>{step}</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>' for i, step in enumerate('CDEC', 1))
    return '<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Original</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><direction><sound tempo="120"/></direction>' + notes + '</measure></part></score-partwise>'


@unittest.skipUnless(importlib.util.find_spec('verovio') and (importlib.util.find_spec('fitz') or importlib.util.find_spec('pymupdf')), 'local Verovio/PyMuPDF runtime required')
class EngravingAcceptance(unittest.TestCase):
    def test_real_notation_and_midi_share_the_symbolic_event_stream(self):
        result = engrave_original_score(original_musicxml())
        self.assertEqual(result['symbolic_pitches'], [60, 62, 64, 60])
        self.assertEqual(result['midi_validation']['state'], 'passed')
        self.assertTrue(result['pdf_bytes'].startswith(b'%PDF-'))
        self.assertTrue(result['midi_bytes'].startswith(b'MThd'))
        self.assertIn('<svg', result['svg'])
        self.assertEqual(result['provider'], 'verovio-local')
        self.assertEqual(result['musical_expert_review'], 'review_required')

    def test_optional_persist_is_no_save_aware(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'original-score'
            with self.assertRaises(ValueError):
                engrave_original_score(original_musicxml(), destination=destination, no_save=True)
            self.assertFalse(destination.exists())
            result = engrave_original_score(original_musicxml(), destination=destination)
            self.assertTrue((destination / 'score.pdf').is_file())
            self.assertTrue((destination / 'score.musicxml').is_file())
            self.assertEqual(len(result['artifact_hashes']), 4)

    def test_external_entities_and_invalid_xml_never_reach_renderer(self):
        for invalid in ('<!DOCTYPE x [<!ENTITY xx SYSTEM "file:///private/data">]><x>&xx;</x>', '<broken>'):
            with self.subTest(xml=invalid):
                with self.assertRaises((ValueError, TypeError)):
                    engrave_original_score(invalid)

    def test_existing_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                engrave_original_score(original_musicxml(), destination=Path(tmp))


if __name__ == '__main__':
    unittest.main()
