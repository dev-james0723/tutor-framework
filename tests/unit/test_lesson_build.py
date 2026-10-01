import importlib
import json
import tempfile
import unittest
from pathlib import Path
from fractions import Fraction as F


class BuildTests(unittest.TestCase):
    def setUp(self):
        try:
            self.c=importlib.import_module('tutor_framework.domains.music.lesson.cache')
            self.t=importlib.import_module('tutor_framework.domains.music.lesson.timeline')
        except ImportError:self.fail('content-addressed cache and sample clock not implemented')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_cache_reuses_only_hash_verified_outputs(self):
        calls=[]; cache=self.c.BuildCache(self.root/'cache')
        def build(d):calls.append(1);(d/'asset.txt').write_text('ok')
        a=cache.build('test',{'revision':1},{},('asset.txt',),build)
        b=cache.build('test',{'revision':1},{},('asset.txt',),build)
        self.assertFalse(a.reused);self.assertTrue(b.reused);self.assertEqual(len(calls),1)
        (b.directory/'asset.txt').write_text('corrupt')
        c=cache.build('test',{'revision':1},{},('asset.txt',),build)
        self.assertFalse(c.reused);self.assertEqual(len(calls),2)

    def test_changed_source_and_config_invalidate(self):
        source=self.root/'source';source.write_text('one');cache=self.c.BuildCache(self.root/'cache')
        def build(d):(d/'out').write_text(source.read_text())
        a=cache.build('music',{'tempo':120},{'score':source},('out',),build)
        source.write_text('two');b=cache.build('music',{'tempo':120},{'score':source},('out',),build)
        c=cache.build('music',{'tempo':60},{'score':source},('out',),build)
        self.assertEqual(len({a.key,b.key,c.key}),3)

    def test_speech_change_does_not_invalidate_music(self):
        c=self.c.BuildCache(self.root/'cache')
        def build(d):(d/'out').write_text('ok')
        m=c.build('music',{'score':'rev'}, {},('out',),build)
        c.build('speech',{'text':'old'}, {},('out',),build)
        c.build('speech',{'text':'new'}, {},('out',),build)
        self.assertEqual(m.key,c.build('music',{'score':'rev'}, {},('out',),build).key)
        self.assertTrue(c.build('music',{'score':'rev'}, {},('out',),build).reused)

    def test_failed_producer_cannot_write_success_receipt(self):
        c=self.c.BuildCache(self.root/'cache')
        def fail(d):(d/'partial').write_text('partial');raise RuntimeError('failed')
        with self.assertRaises(RuntimeError):c.build('bad',{}, {},('out',),fail)
        self.assertFalse(list((self.root/'cache').glob('*/receipt.json')))

    def test_missing_producer_output_fails(self):
        with self.assertRaises(ValueError):self.c.BuildCache(self.root/'cache').build('bad',{}, {},('out',),lambda d:None)

    def test_cache_cannot_escape_root(self):
        c=self.c.BuildCache(self.root/'cache')
        for name in ('../outside','/tmp/absolute','a/../../outside'):
            with self.assertRaises(ValueError):c.build('bad',{}, {},(name,),lambda d:None)

    def test_corrupt_receipt_is_not_cache_hit(self):
        c=self.c.BuildCache(self.root/'cache')
        def build(d):(d/'out').write_text('ok')
        a=c.build('test',{}, {},('out',),build);(a.directory/'receipt.json').write_text('{broken')
        self.assertFalse(c.build('test',{}, {},('out',),build).reused)

    def test_integer_sample_frame_clock(self):
        clock=self.t.Clock()
        self.assertEqual(clock.samples_per_frame,2000)
        self.assertEqual(clock.seconds_to_samples(F(1,3)),16000)
        self.assertEqual(clock.frame_ceil(2001),4000)
        self.assertEqual(clock.frames(4000),2)
        with self.assertRaises(ValueError):clock.frames(2001)

    def test_clock_rejects_unrepresentable_frame_rate(self):
        with self.assertRaises(ValueError):self.t.Clock(sample_rate=44100,fps=24)

    def test_sequence_uses_final_asset_lengths(self):
        clips=[self.t.Clip('voice','speech',48001,'Words.'),self.t.Clip('music','music',96000,'Listen to the bass.')]
        s=self.t.sequence('scene',clips)
        self.assertEqual(s.clips[0].start,12000)
        self.assertEqual(s.clips[0].end-s.clips[0].start,48001)
        self.assertEqual(s.clips[1].end-s.clips[1].start,96000)
        self.assertEqual(s.duration%2000,0)
        self.assertEqual(s.captions[0]['text'],'Words.')
        self.assertLessEqual(s.captions[0]['end'],s.clips[1].start)

    def test_protected_listening_rejects_any_speech_or_transition(self):
        music=self.t.PlacedClip('m','music',1000,5000,'purpose')
        for role in ('speech','transition'):
            with self.assertRaises(ValueError):self.t.validate_windows([music,self.t.PlacedClip('x',role,4999,6000,'')])
        self.t.validate_windows([music,self.t.PlacedClip('x','speech',5000,6000,'')])

    def test_music_needs_listening_purpose(self):
        with self.assertRaises(ValueError):self.t.Clip('m','music',1000,'')

    def test_caption_format_and_no_fake_word_alignment(self):
        cues=[{'start':12000,'end':60000,'text':'Listen first.'}]
        srt=self.t.captions_srt(cues)
        self.assertIn('00:00:00,250 --> 00:00:01,250',srt)
        self.assertEqual(srt.count('-->'),1)
        self.assertTrue(self.t.captions_vtt(cues).startswith('WEBVTT\n\n'))

    def test_questions_require_sufficient_wait_before_reveal(self):
        with self.assertRaises(ValueError):self.t.validate_reveal(48000,96000,minimum_seconds=6)
        self.t.validate_reveal(48000,336000,minimum_seconds=6)


if __name__=='__main__':unittest.main()
