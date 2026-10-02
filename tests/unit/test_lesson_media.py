import importlib
import struct
import tempfile
import unittest
from pathlib import Path


def midi_bytes():
    # C4 at 0, note off at quarter=1, tempo 120, 480 ticks/quarter.
    track=b'\x00\xff\x51\x03\x07\xa1\x20'+b'\x00\x90\x3c\x40'+b'\x83\x60\x80\x3c\x00'+b'\x00\xff\x2f\x00'
    return b'MThd'+struct.pack('>IHHH',6,0,1,480)+b'MTrk'+struct.pack('>I',len(track))+track


class MediaTests(unittest.TestCase):
    def setUp(self):
        try:self.a=importlib.import_module('tutor_framework.domains.music.lesson.adapters')
        except ImportError:self.fail('local media adapter not implemented')

    def test_midi_reader_measures_actual_note_on_and_off(self):
        notes=self.a.midi_notes(midi_bytes())
        self.assertEqual(len(notes),1);self.assertEqual(notes[0]['midi'],60)
        self.assertEqual(notes[0]['start'],0);self.assertEqual(notes[0]['duration'],.5)

    def test_malformed_midi_fails_closed(self):
        for bad in (b'not midi',midi_bytes()[:-5],midi_bytes().replace(b'\x83\x60\x80\x3c\x00',b'\x83\x60\x90\x3c\x40')):
            with self.assertRaises(ValueError):self.a.midi_notes(bad)

    def test_symbolic_midi_mismatch_is_failed_not_warning(self):
        notes=self.a.midi_notes(midi_bytes())
        expected=[{'midi':60,'onset':'0','duration':'1'}]
        self.assertEqual(self.a.compare_midi(expected,notes,'120')['state'],'passed')
        self.assertEqual(self.a.compare_midi([{'midi':62,'onset':'0','duration':'1'}],notes,'120')['state'],'failed')

    def test_symbolic_midi_latency_mismatch_fails(self):
        notes=self.a.midi_notes(midi_bytes());notes[0]['start']=.2
        self.assertEqual(self.a.compare_midi([{'midi':60,'onset':'0','duration':'1'}],notes,'120')['state'],'failed')

    def test_remote_provider_is_not_supported_by_local_adapter(self):
        with self.assertRaises(PermissionError):self.a.require_local_provider('remote-tts')
        self.a.require_local_provider('kokoro-local')

    def test_publication_inventory_cannot_omit_required_checks(self):
        try:q=importlib.import_module('tutor_framework.domains.music.lesson.mediaqa')
        except ImportError:self.fail('complete media QA inventory missing')
        report=q.release_decision({'decode':'passed'})
        self.assertFalse(report['verified_lesson']);self.assertIn('perceptual_listening',report['blocked_checks'])
        self.assertEqual(report['checks']['perceptual_listening'],'validation_unavailable')


if __name__=='__main__':unittest.main()
