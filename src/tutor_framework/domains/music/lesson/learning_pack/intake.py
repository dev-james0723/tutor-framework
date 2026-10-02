"""Ask only unresolved learning-intent questions; PDF text is never consent."""
from __future__ import annotations
from .models import LearningBrief, GOALS, MATERIALS


def recommendations(dossier: dict, goal: str = 'understand') -> list[str]:
    selected = ['notes']
    if dossier.get('score_pages'):
        selected.append('annotated_score')
    if goal in {'understand', 'discussion'}:
        selected += ['listening_guide', 'quiz']
    elif goal == 'exam':
        selected += ['quiz', 'flashcards', 'cheat_sheet']
    elif goal == 'assignment':
        selected += ['essay_outline']
    else:
        selected += ['mindmap']
    return selected


def questions(dossier: dict, known: dict | None = None, locale: str = 'en') -> dict:
    known = known or {}
    chinese = locale in {'zh-Hant', 'bilingual'}
    choices = [
        ('goal', '今次最想達到咩目的？' if chinese else 'What do you want to achieve with this material?',
         ['assignment', 'understand', 'exam', 'discussion', 'notes']),
        ('help_mode', '想點樣幫你？先引導你諗，定睇完整分析？' if chinese else 'Should I guide your reasoning, work question-by-question, show a worked analysis, or review your answers?',
         ['guided', 'coached', 'worked', 'review']),
        ('materials', '想攞邊啲教材？亦可以直接用建議組合。' if chinese else 'Which materials should I produce? You can accept the recommended set.',
         sorted(MATERIALS)),
        ('preferences', '深度、筆記語言、已識嘅內容或者期限，有冇要調整？' if chinese else 'Any preferences for depth, notes language, prior knowledge, or deadline?',
         ['defaults', 'custom']),
    ]
    pending = [{'key': key, 'question': prompt, 'options': options} for key, prompt, options in choices
               if key not in known and not (key == 'preferences' and all(k in known for k in ('depth', 'language', 'prior_knowledge', 'deadline')))]
    rec = recommendations(dossier, known.get('goal', 'understand'))
    if known.get('no_video'):
        rec = [item for item in rec if item != 'video']
    return {'state': 'awaiting_user', 'source_hash': dossier['source_hash'],
            'document_summary': {'pages': dossier['page_count'], 'units': len(dossier.get('units', [])),
                                 'score_pages': dossier.get('score_pages', []), 'title': dossier.get('title', '')},
            'questions': pending, 'recommended_materials': rec,
            'recommendation_reason': 'Start with source-grounded notes; add only aids that serve the selected purpose.',
            'skip_rule': 'Do not repeat answers already supplied. Explicit no-video/text-only overrides previous defaults.',
            'no_generation_started': True}


def confirm_brief(dossier: dict, answers: dict) -> LearningBrief:
    allowed = {'confirmed', 'goal', 'materials', 'help_mode', 'depth', 'language', 'prior_knowledge',
               'deadline', 'no_video', 'source_hash', 'use_recommendations', 'preferences'}
    if set(answers) - allowed:
        raise ValueError('unknown learning-intent fields: ' + ', '.join(sorted(set(answers)-allowed)))
    if answers.get('confirmed') is not True:
        raise ValueError('wait for the user to confirm intent or explicitly accept recommendations')
    if answers.get('source_hash', dossier['source_hash']) != dossier['source_hash']:
        raise ValueError('the source changed after intake; confirm the revised material')
    goal = answers.get('goal', 'understand')
    if goal not in GOALS:
        raise ValueError('unknown learning goal')
    accepted = answers.get('use_recommendations', False)
    if type(accepted) is not bool:
        raise ValueError('recommendation acceptance must be a boolean')
    materials = recommendations(dossier, goal) if accepted else answers.get('materials')
    if materials is None:
        raise ValueError('choose outputs or explicitly accept recommendations')
    if not isinstance(materials, (list, tuple)) or any(not isinstance(item, str) for item in materials):
        raise ValueError('materials must be an explicit list')
    if answers.get('no_video'):
        materials = [item for item in materials if item != 'video']
    return LearningBrief(source_hash=dossier['source_hash'], goal=goal, materials=tuple(materials),
                         help_mode=answers.get('help_mode', 'guided'), depth=answers.get('depth', 'standard'),
                         language=answers.get('language', 'en'), prior_knowledge=answers.get('prior_knowledge', ''),
                         deadline=answers.get('deadline', ''), confirmed=True, no_video=answers.get('no_video', False))
