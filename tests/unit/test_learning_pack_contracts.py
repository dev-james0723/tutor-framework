"""Learning intent, provenance and answer-reveal contracts, independent of media tools."""
import importlib
import json
import unittest
from dataclasses import replace

H='a'*64
DOSSIER={'source_hash':H,'source_path':'/private/assignment.pdf','page_count':2,
         'pages':[{'page':1},{'page':2}], 'units':[{'unit_id':'p1-u1','page':1,'text':'Compare phrase functions.'}],
         'score_pages':[2], 'title':'Assignment'}


class LearningPackContracts(unittest.TestCase):
    def setUp(self):
        try:
            self.m=importlib.import_module('tutor_framework.domains.music.lesson.learning_pack.models')
            self.i=importlib.import_module('tutor_framework.domains.music.lesson.learning_pack.intake')
            self.r=importlib.import_module('tutor_framework.domains.music.lesson.learning_pack.render')
        except ImportError:self.fail('Learning Pack contracts/intake/render not implemented')

    def brief(self,**changes):
        args={'confirmed':True,'goal':'understand','materials':['notes','annotated_score','quiz'],
              'help_mode':'guided','depth':'standard','language':'en','source_hash':H}
        args.update(changes)
        return self.i.confirm_brief(DOSSIER,args)

    def content(self):
        m=self.m
        src=m.PackSource('assignment','/private/assignment.pdf',H,'User assignment','private study only')
        cite=m.Citation('assignment','Question 1 and score page 2',page=2)
        block=m.NoteBlock('claim','passage_analysis','A worked claim','SECRET ANSWER',('p1',),(cite,),'tutor_judgment','review_required',True)
        concept=m.NoteBlock('concept','concepts','Method','Compare evidence before naming the form.',(),(cite,),'caplin_theory','review_required',False)
        passage=m.PackPassage('p1','assignment','edition-a','1-4',2,'1',('1','2','3','4'))
        cover=m.CoverageItem('p1-u1',('claim','concept'))
        question=m.PracticeItem('q1','What supports the boundary?','SECRET ANSWER','Use the evidence.',('p1',),(cite,))
        return m.PackContent('Example',(src,),(passage,),(block,concept),(cover,),(question,))

    def test_intake_is_three_to_five_questions_and_does_not_confirm(self):
        result=self.i.questions(DOSSIER,{},'en')
        self.assertTrue(3<=len(result['questions'])<=5)
        self.assertEqual(result['state'],'awaiting_user')
        self.assertNotIn('confirmed',result)

    def test_already_known_answers_are_not_asked_again(self):
        result=self.i.questions(DOSSIER,{'goal':'exam','materials':['notes'],'help_mode':'guided'},'en')
        keys={x['key'] for x in result['questions']}
        self.assertFalse({'goal','materials','help_mode'} & keys)

    def test_cantonese_questions(self):
        result=self.i.questions(DOSSIER,{},'zh-Hant')
        self.assertIn('今次',result['questions'][0]['question'])

    def test_explicit_no_video_wins_over_recommendations(self):
        brief=self.brief(use_recommendations=True,no_video=True,materials=['notes','video'])
        self.assertNotIn('video',brief.materials)

    def test_recommendations_require_an_explicit_acceptance(self):
        with self.assertRaises(ValueError):self.i.confirm_brief(DOSSIER,{'use_recommendations':True})

    def test_no_score_handout_does_not_invent_annotation_requirement(self):
        plain={**DOSSIER,'score_pages':[]}
        result=self.i.questions(plain,{},'en')
        self.assertNotIn('annotated_score',result['recommended_materials'])

    def test_empty_or_unknown_materials_rejected(self):
        for value in [[],['unrestricted_shell']]:
            with self.assertRaises(ValueError):self.brief(materials=value)

    def test_unknown_goal_rejected(self):
        with self.assertRaises(ValueError):self.brief(goal='publish_private_sources')

    def test_unconfirmed_or_stale_brief_rejected(self):
        with self.assertRaises(ValueError):self.brief(confirmed=False)
        with self.assertRaises(ValueError):self.brief(source_hash='b'*64)

    def test_brief_roundtrip_and_unknown_field_rejection(self):
        brief=self.brief();self.assertEqual(self.m.LearningBrief.from_dict(brief.to_dict()).to_dict(),brief.to_dict())
        payload=brief.to_dict();payload['remote_api_approved']=True
        with self.assertRaises(ValueError):self.m.LearningBrief.from_dict(payload)

    def test_guided_pack_cannot_leak_answer_in_any_render_payload(self):
        payload=self.r.payload_for(self.brief(),self.content())
        self.assertNotIn('SECRET ANSWER',json.dumps(payload))
        self.assertIn('Compare evidence',json.dumps(payload))
        self.assertEqual(payload['practice'][0]['answer_state'],'withheld_by_policy')

    def test_worked_pack_includes_answer_and_explains_provenance(self):
        payload=self.r.payload_for(self.brief(help_mode='worked'),self.content())
        self.assertIn('SECRET ANSWER',json.dumps(payload))
        self.assertIn('tutor_judgment',json.dumps(payload))
        self.assertIn('review_required',json.dumps(payload))

    def test_annotations_default_to_answer_bearing(self):
        ann=self.m.ScoreAnnotation('a','p1','assignment',2,(.1,.2,.6,.1),'SECRET ANSWER')
        content=replace(self.content(),annotations=(ann,))
        self.assertNotIn('SECRET ANSWER',json.dumps(self.r.payload_for(self.brief(),content)))

    def test_annotation_outside_page_rejected(self):
        for box in [(0,0,2,.1),(-1,0,.2,.2),(0,0,0,.2),(float('nan'),0,.2,.2)]:
            with self.assertRaises((ValueError,TypeError)):self.m.ScoreAnnotation('a','p1','assignment',2,box,'label')

    def test_historical_claim_needs_citation_and_listening_relevance(self):
        with self.assertRaises(ValueError):self.m.NoteBlock('h','context','History','Historical claim',(),(),'historical_fact')
        with self.assertRaises(ValueError):self.m.NoteBlock('h','context','History','Historical claim',(),(self.m.Citation('s','section'),),'historical_fact')

    def test_unknown_claim_source_or_passage_is_rejected(self):
        content=self.content();bad=replace(content.blocks[0],passage_ids=('missing',))
        with self.assertRaises(ValueError):replace(content,blocks=(bad,))

    def test_unverified_transfer_answer_is_not_promoted(self):
        content=self.content();q=replace(content.practice[0],transfer_from='p-other',answer_state='review_required')
        with self.assertRaises(ValueError):replace(content,practice=(q,))

    def test_coverage_requires_explicit_unresolved_reason(self):
        with self.assertRaises(ValueError):self.m.CoverageItem('p1-u1',())
        self.m.CoverageItem('p1-u1',(),unresolved='Source score needs review')

    def test_form_hierarchy_is_not_flattened(self):
        content=self.content();node=self.m.FormNode('theme','Theme','theme',('p1',))
        child=self.m.FormNode('phrase','Phrase','phrase',('p1',),'theme')
        content=replace(content,form=(node,child))
        payload=self.r.payload_for(self.brief(help_mode='worked'),content)
        self.assertEqual(payload['form'][1]['parent_id'],'theme')

    def test_cyclic_or_unknown_form_parents_rejected(self):
        node=self.m.FormNode('theme','Theme','theme',('p1',),'theme')
        with self.assertRaises(ValueError):replace(self.content(),form=(node,))

    def test_injection_is_inert_content_not_a_command(self):
        block=replace(self.content().blocks[1],body='<script>fetch("https://evil.invalid")</script>')
        content=replace(self.content(),blocks=(self.content().blocks[0],block))
        html=self.r.notes_html(self.r.payload_for(self.brief(),content))
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)


if __name__=='__main__':unittest.main()
