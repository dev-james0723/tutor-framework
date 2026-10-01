import importlib
import unittest
from fractions import Fraction as F
from tutor_framework.domains.music.lesson.models import Passage, MeasureVisit


def note(step='C', dur=4, *, chord=False, voice='1', tie='', alter=0):
    ties = ''.join('<tie type="'+t+'"/>' for t in tie.split(',') if t)
    return f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step><alter>{alter}</alter><octave>4</octave></pitch><duration>{dur}</duration><voice>{voice}</voice>{ties}</note>'


def score(body, second=None):
    attrs='<attributes><divisions>4</divisions><time><beats>3</beats><beat-type>4</beat-type></time></attributes>'
    return '<score-partwise><part-list/><part id="P1">'+attrs+body+'</part>'+('' if second is None else '<part id="P2">'+attrs+second+'</part>')+'</score-partwise>'


def measure(label, body, implicit=True):
    attrs='<attributes><divisions>4</divisions><time><beats>3</beats><beat-type>4</beat-type></time></attributes>'
    return f'<measure number="{label}" implicit="{"yes" if implicit else "no"}">{attrs}{body}</measure>'


class SymbolicTests(unittest.TestCase):
    def setUp(self):
        try:self.s = importlib.import_module('tutor_framework.domains.music.lesson.symbolic')
        except ImportError:self.fail('reusable symbolic traversal not implemented')

    def route(self, x, labels, parts=('P1',), entry='complete_attack'):
        counts={}; visits=[]
        for label in labels:
            counts[label]=counts.get(label,0)+1; visits.append(MeasureVisit(label,counts[label]))
        return self.s.traverse(x, Passage('p','edition',tuple(visits),parts,'R=N',entry))

    def test_pickup_is_not_padded_to_full_bar(self):
        x=self.s.parse_score(score(measure('0',note(dur=3)+note('D',dur=1))+measure('1',note('E',dur=12))))
        events=self.route(x,['0','1'])
        self.assertEqual([e.onset for e in events],[F(0),F(3,4),F(1)])
        self.assertEqual(events[-1].duration,F(3))

    def test_chords_share_attack_and_backup_preserves_voice(self):
        x=self.s.parse_score(score(measure('1',note()+note('E',chord=True)+'<backup><duration>4</duration></backup>'+note('G',voice='2'))))
        events=self.route(x,['1'])
        self.assertEqual([e.onset for e in events],[F(0)]*3)
        self.assertEqual({e.voice for e in events},{'1','2'})

    def test_multiple_parts_are_not_concatenated(self):
        x=self.s.parse_score(score(measure('1',note()),measure('1',note('E'))))
        events=self.route(x,['1'],('P1','P2'))
        self.assertEqual(len(events),2);self.assertEqual(events[0].onset,events[1].onset)

    def test_explicit_repeats_preserve_printed_labels_and_visit_ids(self):
        x=self.s.parse_score(score(measure('24a',note())+measure('17',note('D'))+measure('24b',note('E'))))
        events=self.route(x,['17','24a','17','24b'])
        self.assertEqual([(e.measure,e.occurrence) for e in events],[('17',1),('24a',1),('17',2),('24b',1)])
        self.assertEqual(len({e.event_id for e in events}),4)

    def test_ties_merge_playback_but_keep_engraving_ids(self):
        x=self.s.parse_score(score(measure('1',note(tie='start'))+measure('2',note(tie='stop'))))
        events=self.route(x,['1','2']); attacks=self.s.playback_notes(events)
        self.assertEqual(len(attacks),1);self.assertEqual(attacks[0].duration,F(2));self.assertEqual(len(attacks[0].notation_ids),2)

    def test_tie_entry_without_attack_fails(self):
        x=self.s.parse_score(score(measure('2',note(tie='stop'))))
        with self.assertRaisesRegex(ValueError,'tie'):
            self.route(x,['2'])

    def test_explicit_tie_may_change_voice_when_endpoint_is_unique(self):
        x=self.s.parse_score(score(measure('1',note(tie='start',voice='3'))+measure('2',note(tie='stop',voice='2'))))
        attacks=self.s.playback_notes(self.route(x,['1','2']))
        self.assertEqual(len(attacks),1);self.assertEqual(attacks[0].duration,F(2))

    def test_ambiguous_cross_voice_tie_fails_closed(self):
        first=note(tie='start',voice='1')+'<backup><duration>4</duration></backup>'+note(tie='start',voice='2')
        x=self.s.parse_score(score(measure('1',first)+measure('2',note(tie='stop',voice='3'))))
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            self.route(x,['1','2'])

    def test_open_tie_exit_fails(self):
        x=self.s.parse_score(score(measure('1',note(tie='start'))))
        with self.assertRaisesRegex(ValueError,'tie'):
            self.route(x,['1'])

    def test_fractional_divisions_do_not_drift(self):
        body='<attributes><divisions>3</divisions><time><beats>1</beats><beat-type>4</beat-type></time></attributes>'+note(dur=1)+note('D',dur=1)+note('E',dur=1)
        x=self.s.parse_score('<score-partwise><part id="P1"><measure number="1">'+body+'</measure></part></score-partwise>')
        self.assertEqual([e.onset for e in self.route(x,['1'])],[F(0),F(1,3),F(2,3)])

    def test_instrument_transposition_changes_sounding_pitch(self):
        body='<attributes><transpose><diatonic>-1</diatonic><chromatic>-2</chromatic></transpose></attributes>'+note()
        x=self.s.parse_score(score(measure('1',body)))
        self.assertEqual(self.route(x,['1'])[0].midi,58)

    def test_unknown_measure_or_part_fails_closed(self):
        x=self.s.parse_score(score(measure('1',note())))
        for labels,parts in [(['2'],('P1',)),(['1'],('P3',))]:
            with self.assertRaises(ValueError):self.route(x,labels,parts)

    def test_duplicate_printed_measure_requires_disambiguation(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.s.parse_score(score(measure('1',note())+measure('1',note())))

    def test_negative_backup_rejected(self):
        with self.assertRaises(ValueError):self.s.parse_score(score(measure('1','<backup><duration>4</duration></backup>'+note())))

    def test_unsupported_grace_or_unpitched_not_silently_dropped(self):
        for body in ['<note><grace/><pitch><step>C</step><octave>4</octave></pitch></note>','<note><unpitched/><duration>4</duration></note>']:
            with self.assertRaises(ValueError):self.s.parse_score(score(measure('1',body)))

    def test_entities_and_oversized_xml_rejected(self):
        for payload in ['<!DOCTYPE x [<!ENTITY xx "value">]>'+score(measure('1',note())), 'x'*2_000_001]:
            with self.assertRaises(ValueError):self.s.parse_score(payload)

    def test_same_revision_hash_independent_of_formatting(self):
        a=score(measure('1',note()))
        self.assertEqual(self.s.parse_score(a).revision,self.s.parse_score(a.replace('><','>\n<')).revision)

    def test_select_parts_and_bass_reduction_retain_symbolic_origin(self):
        x=self.s.parse_score(score(measure('1',note()+note('E',chord=True)),measure('1',note('G'))))
        all_notes=self.route(x,['1'],('P1','P2'))
        chosen=self.s.transform(all_notes,kind='part',part_ids=('P1',))
        self.assertEqual(len(chosen),2)
        bass=self.s.transform(chosen,kind='lowest')
        self.assertEqual(len(bass),1);self.assertEqual(bass[0].midi,60)

    def test_controlled_comparison_rejects_unapproved_changes(self):
        a=self.route(self.s.parse_score(score(measure('1',note()))),['1'])
        b=self.route(self.s.parse_score(score(measure('1',note('E')))),['1'])
        changes=self.s.controlled_diff(a,b,allowed_fields=('midi',))
        self.assertEqual(len(changes),1)
        with self.assertRaises(ValueError):self.s.controlled_diff(a,b,allowed_fields=('duration',))


if __name__=='__main__':unittest.main()
