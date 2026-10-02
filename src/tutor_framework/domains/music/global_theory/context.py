"""Compose the learner's stated preferences without inferring identity from location."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from collections.abc import Mapping
import re


MODULES = (
    "foundations", "rhythm", "aural", "tonal_harmony_counterpoint",
    "form_caplin_alternatives", "jazz_pop_songwriting", "composition_performance",
    "exam", "terminology", "score_pdf_lecture_audio_evidence", "learning_pack",
    "source_qa",
)

MODULE_STATUS = {
    "foundations": "pilot_supported", "rhythm": "pilot_supported",
    "aural": "explicit_solfege_only_no_audio_dictation", "tonal_harmony_counterpoint": "bounded_chord_and_voice_motion_operations",
    "form_caplin_alternatives": "caplin_opt_in", "jazz_pop_songwriting": "review_required",
    "composition_performance": "original_open_response_practice_not_board_calibrated", "exam": "pilot_supported",
    "terminology": "pilot_supported", "score_pdf_lecture_audio_evidence": "explicit_musicxml_and_claim_conflicts_pdf_omr_review_required",
    "learning_pack": "existing_adapter", "source_qa": "pilot_supported",
}


@dataclass(frozen=True)
class LearnerContext:
    response_language: str = "en"
    terminology_preference: dict[str, str] = field(default_factory=dict)
    curriculum_context: dict[str, str] = field(default_factory=dict)
    target_level_or_competencies: tuple[str, ...] = ()
    musical_tradition: str = "unknown"
    analysis_framework: str = "unknown"
    notation_and_solfege_system: dict[str, str] = field(default_factory=dict)
    learning_goal: str = "unknown"
    desired_deliverables: tuple[str, ...] = ()
    no_save: bool = False
    text_only: bool = False

    def __post_init__(self):
        if self.response_language not in {"en", "zh-Hant", "bilingual"}:
            raise ValueError("unsupported response language")
        if type(self.no_save) is not bool or type(self.text_only) is not bool:
            raise ValueError("privacy preferences must be booleans")
        for name in ("terminology_preference", "curriculum_context", "notation_and_solfege_system"):
            value = getattr(self, name)
            if not isinstance(value, Mapping) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
                raise ValueError("context mappings require string keys and values")
            object.__setattr__(self, name, MappingProxyType(dict(value)))
        object.__setattr__(self, "desired_deliverables", tuple(self.desired_deliverables))
        object.__setattr__(self, "target_level_or_competencies", tuple(self.target_level_or_competencies))
        if any(not isinstance(x, str) for x in self.desired_deliverables):
            raise ValueError("invalid deliverable")


def route(question: str, context: LearnerContext) -> dict:
    if not question.strip():
        raise ValueError("question required")
    q = question.casefold()
    operation_request = _explicit_operation(question)
    if operation_request is not None:
        from .operations import evaluate
        result = evaluate(operation_request, context)
        answer = result['explanation']
        if result['operation'] == 'scale':
            answer += ' ' + ', '.join(result['data'].get('notes', []))
        return {'mode':'direct','answer':answer,'questions':[],'deliverables':['text'],
                'modules':['foundations'],'evidence_state':result['state'],'operation_result':result}
    substantial = any(x in q for x in (
        "analyze", "analyse", "learning pack", "study pack", "學習包", "分析", "樂譜", "mock exam",
        "whole paper", "pdf", "audio", "lecture", "handout", "assignment", "annotate",
        "mock", "試卷", "模擬卷", "真題", "全部", "教授", "雲端", "考試"))
    simple = not substantial and (len(question.split()) <= 24 or any(x in q for x in ("what is", "what does", "why does", "which note", "are parallel", "is every")))
    answer = foundational_answer(question, context)
    if answer is None:
        answer = "This topic requires source or specialist review; no unsupported musical conclusion is asserted." if simple else ""
    if simple:
        return {"mode": "direct", "answer": answer, "questions": [], "deliverables": ["text"],
                "modules": ["terminology" if any(x in q for x in ("crotchet", "cadence", "iac")) else "foundations"],
                "evidence_state": "bounded_explanation" if foundational_answer(question, context) else "review_required"}
    missing = []
    if context.learning_goal == "unknown":
        missing.append("What do you want to accomplish with this material?")
    if not context.target_level_or_competencies:
        missing.append("Which step is difficult, or what have you already tried?")
    if not (context.curriculum_context.get("id") or context.curriculum_context.get("name")):
        missing.append("Which course, exam version, or assigned framework applies?")
    if not context.desired_deliverables:
        missing.append("Which outputs do you want: notes, annotated score, practice, or another format?")
    if context.analysis_framework == "unknown" and any(x in q for x in ("form", "cadence", "harmony")):
        missing.append("Which analysis framework should govern the answer?")
    deliverables = list(context.desired_deliverables or ("notes",))
    if context.text_only:
        deliverables = [x for x in deliverables if x not in {"video", "audio", "annotated_score", "mindmap"}] or ["text"]
    return {"mode": "guided", "answer": answer, "questions": missing[:5],
            "deliverables": deliverables, "modules": ["learning_pack" if "pack" in q else "source_qa"],
            "evidence_state": "requires_material_review"}


NOTE_NAMES = (
    ("demisemiquaver", "thirty-second note", "三十二分音符", "1/32"),
    ("semiquaver", "sixteenth note", "十六分音符", "1/16"),
    ("quaver", "eighth note", "八分音符", "1/8"),
    ("crotchet", "quarter note", "四分音符", "1/4"),
    ("minim", "half note", "二分音符", "1/2"),
    ("semibreve", "whole note", "全音符", "1"),
    ("breve", "double whole note", "二全音符", "2"),
)


def foundational_answer(question: str, context: LearnerContext) -> str | None:
    """Bounded foundational rules, independent of benchmark IDs and national identity."""
    q = question.casefold().replace("–", "-").replace("—", "-")
    zh = context.response_language == "zh-Hant"
    for uk, us, chinese, ratio in NOTE_NAMES:
        if re.search(r"(?<![a-z])(?:" + re.escape(uk) + "|" + re.escape(us) + r")(?![a-z])", q) or chinese in q:
            en = f"A {uk} is a {us}, with {ratio} of a whole note's duration. The number of beats depends on the meter and beat unit."
            translated = f"{uk} 即 {us}／{chinese}，時值是全音符的 {ratio}。實際拍數取決於拍號與主要拍，不能只靠音符名稱判斷。"
            return translated if zh else en + (" " + translated if context.response_language == "bilingual" else "")
    system = " ".join(context.notation_and_solfege_system.values()).casefold().replace("_", " ")
    if "fixed do" in q or "fixed-do" in q or ("do" in q and "fixed" in system):
        return "固定唱名（fixed do）以 C 為 do，不會因調性改為 G；變音的唱法另依所用系統。" if zh else "In fixed do, C is do regardless of whether the key is G major or another key. Chromatic syllables depend on the fixed-do convention."
    if any(word in q for word in ("movable do", "moveable do", "movable-do", "首調")) or ("do" in q and "movable" in system):
        match = re.search(r"\b([a-g])([#b♯♭]?)\s+major\b", q)
        if match:
            tonic = match.group(1).upper() + match.group(2).replace("♯", "#").replace("♭", "b")
            return (f"首調唱名（movable do）以主音為 do；在 {tonic} 大調，主音 {tonic} 就是 do。"
                    if zh else f"In movable do, {tonic} is do because {tonic} is the tonic of {tonic} major.")
        return "首調唱名的大調以主音為 do；小調須先區分 do-based 與 la-based 系統。" if zh else "In movable do, do is the major-key tonic. For minor, distinguish do-based from la-based minor before assigning syllables."
    if "middle c" in q or "中央c" in q or "中央 c" in q:
        return "中央 C 的八度編號取決於軟件慣例；同一音高可能標為 C3 或 C4。科學音高記號通常用 C4，須核對軟件基準。" if zh else "Octave numbering varies by software convention: the same middle C may be labeled C3 or C4. Scientific pitch notation uses C4; check the software's reference pitch rather than assuming an octave error."
    if "v-i" in q and any(word in q for word in ("every", "always", "cadence", "終止")):
        return "不是每個 V–I 都是終止式；還須看樂句邊界、收束作用及所選分析框架。" if zh else "No. A V-I progression is not automatically a cadence: phrase boundary, closure, and the selected formal framework matter."
    if "parallel fifth" in q and any(word in q for word in ("jazz", "pop", "always")):
        return "平行五度不是所有風格都禁用；爵士、流行與古典聲部進行的任務不同，須依風格及聲部語境判斷。" if zh else "No. Parallel fifths are not always forbidden in jazz or popular music. Evaluate style, voicing and harmonic context rather than imposing a universal classical exercise rule."
    if "imperfect cadence" in q or re.search(r"\biac\b", q) or "不完全終止" in q:
        from .terminology import terminology
        resolved = terminology("IAC" if "iac" in q else "imperfect cadence", context)
        return resolved.get("definition") or "Specify UK exam terminology, US tonal harmony, or Caplin: those cadence definitions are not interchangeable."
    return None


def _explicit_operation(question):
    """Only explicit pitch/octave requests run automatically; no file or key guesses."""
    pitch_token = r"([A-G](?:#{1,2}|b{1,2})?[0-8])"
    match = re.fullmatch(r"\s*(?:What is|Identify|Name) (?:the )?interval (?:from )?" + pitch_token + r" (?:to|and) " + pitch_token + r"[?.!]?\s*", question)
    if match:
        return {'operation':'interval','first':match.group(1),'second':match.group(2)}
    match = re.fullmatch(r"\s*(?:Spell|Show|List)(?: the)? " + pitch_token + r" (major|natural minor|harmonic minor|melodic minor) scale[?.!]?\s*", question)
    if match:
        return {'operation':'scale','tonic':match.group(1),'mode':match.group(2).replace(' ','_')}
    return None
