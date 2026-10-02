"""Versioned public crosswalk metadata with independently authored bounded guidance."""
from __future__ import annotations
import json
from importlib.resources import files

RELATIONS = frozenset({"exact", "context-dependent", "broader", "narrower", "overlapping", "not-equivalent", "disputed"})
FOUNDATIONS = {
    "T001": "A breve is a double whole note: twice the duration of a whole note.",
    "T002": "A semibreve is a whole note. Its beat count depends on the meter and beat unit.",
    "T003": "A minim is a half note: half a whole note's duration, not a universal number of beats.",
    "T004": "A crotchet is a quarter note: one quarter of a whole note's duration.",
    "T005": "A quaver is an eighth note: one eighth of a whole note's duration.",
    "T006": "A semiquaver is a sixteenth note: one sixteenth of a whole note's duration.",
    "T007": "A demisemiquaver is a thirty-second note: one thirty-second of a whole note's duration.",
    "T030": "Fixed do associates do with C rather than the tonic of every key. Chromatic syllables vary by teaching convention.",
    "T031": "Movable do gives the major-key tonic the syllable do. Do-based and la-based minor must be distinguished.",
}
CADENCES = {
    "T062": "In US tonal-harmony usage, IAC means imperfect authentic cadence, a V-I authentic close lacking one or more PAC conditions. Course conventions may admit cases that Caplin excludes; do not silently transfer those definitions.",
    "T063": "Caplin's IAC uses narrower formal and root-position conditions than a generic imperfect-authentic label. The preserved local protocol has a soprano-condition conflict; keep that record review_required and consult its permitted source rather than treating every non-PAC V-I as Caplin IAC.",
    "T064": "In UK exam terminology, imperfect cadence refers to a cadential ending on V, commonly called a half cadence in US usage. It is not equivalent to US imperfect authentic cadence (IAC), which closes on I.",
    "T065": "A half cadence closes a phrase or relevant formal unit on dominant harmony. Merely encountering V inside a phrase does not establish a cadence.",
}
CADENCES_ZH = {
    "T062": "US IAC 是 imperfect authentic cadence：屬於 V–I 的正格收束，但不完全符合 PAC 條件。課程可能接受 Caplin 不接受的情形，不能把兩套定義合併。",
    "T063": "Caplin 的 IAC 採較窄的形式功能與根位條件。保留版本的高音條件有衝突，須標為 review_required 並查閱獲准使用的原始依據；不可把所有非 PAC 的 V–I 都視為 Caplin IAC。",
    "T064": "UK imperfect cadence 指終止於 V 的收束，US 常稱 half cadence；它不等於終止於 I 的 US imperfect authentic cadence（IAC）。",
    "T065": "半終止指樂句或相關形式單位在屬和聲收束；樂句中途出現 V 並不足以證明半終止。",
}


def records() -> list[dict]:
    data = json.loads(files(__package__).joinpath("data/terminology.json").read_text(encoding="utf-8"))
    if len(data["records"]) != 100 or any(r["relation"] not in RELATIONS for r in data["records"]):
        raise ValueError("terminology registry is incomplete or invalid")
    return data["records"]


def terminology(term: str, context=None) -> dict:
    if not isinstance(term, str) or not term.strip():
        raise ValueError("term required")
    query = term.casefold().strip(); rows = records(); index = {r['record_id']: r for r in rows}
    candidates = [r for r in rows if query in r['original_term'].casefold()]
    framework = getattr(context, 'analysis_framework', 'unknown')
    preferences = getattr(context, 'terminology_preference', {})
    cadence_context = preferences.get('cadences', preferences.get('cadence', ''))
    cadence_query = query == 'iac' or 'imperfect cadence' in query or 'imperfect authentic' in query
    if cadence_query:
        candidates = [index[r] for r in ('T062','T063','T064')]
        selected = 'T063' if 'caplin' in framework.casefold() else 'T064' if ('uk' in cadence_context.casefold() or 'gb' in cadence_context.casefold() or query=='imperfect cadence') else 'T062'
        chosen = index[selected]
    elif candidates:
        chosen = min(candidates, key=lambda r: len(r['original_term']))
    else:
        return {'term':term,'relation':None,'state':'unsupported','candidates':[]}
    result = dict(chosen); record_id = result['record_id']
    definition = FOUNDATIONS.get(record_id) or CADENCES.get(record_id)
    if getattr(context, 'response_language', 'en') == 'zh-Hant' and record_id in CADENCES_ZH:
        definition = CADENCES_ZH[record_id]
    result.update({'definition':definition,
        'definition_origin':'independently_authored_guidance' if definition else 'withheld_pending_rights_review',
        'selected_framework':framework,'terminology_pack_revision':'2026-10-02.v1',
        'state':'review_required' if not definition or record_id=='T063' else 'bounded_definition',
        'candidates':[r['record_id'] for r in candidates],
        'ambiguity_warning': 'Cadence labels are framework-bound; no automatic equivalence.' if cadence_query else None})
    return result
