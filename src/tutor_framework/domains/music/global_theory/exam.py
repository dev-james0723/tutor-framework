"""Rights-gated, revision-bound exam intake and answer-isolated tutoring.

Intake accepts original bytes and a caller-provided parser adapter. No text-only
fallback, network acquisition, or answer authority is inferred from parsing.
"""
from __future__ import annotations

import hashlib
import json
import re
import math
import copy
import os
from dataclasses import dataclass
from pathlib import Path
from .exam_storage import PrivateExamPersistence


LAYERS = frozenset({"source_question", "official_answer", "third_party_explanation",
                    "ai_derived_answer", "teacher_result", "learner_answer"})
FLAGS = ("source_found", "document_verified", "processing_authorized", "parsed",
         "answer_matched", "musically_verified", "reviewed_usable")


def _safe_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,100}", value):
        raise ValueError("unsafe identifier")
    return value


def _hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class PurposeGrant:
    grant_id: str
    resource_ids: tuple[str, ...]
    purpose: str
    tenant_id: str
    retain_original: bool
    external_processing: bool = False

    def __post_init__(self):
        _safe_id(self.grant_id); _safe_id(self.tenant_id)
        if type(self.retain_original) is not bool or type(self.external_processing) is not bool:
            raise ValueError("grant flags must be booleans")
        if self.purpose not in {"private_study", "internal_evaluation", "licensed_product"}:
            raise ValueError("purpose must be scoped")
        for resource_id in self.resource_ids:
            _safe_id(resource_id)


class ExamStore:
    def __init__(self, catalogue: dict[str, dict], *, tenant_id: str, no_save: bool = False,
                 storage_root: Path | None = None):
        self.tenant_id = _safe_id(tenant_id)
        if type(no_save) is not bool:
            raise ValueError("no-save must be a boolean")
        self.no_save = no_save
        if no_save and storage_root is not None:
            raise ValueError("no-save forbids storage root")
        self.storage_root = Path(storage_root).resolve() if storage_root else None
        self.catalogue = copy.deepcopy(catalogue)
        self._papers: dict[str, dict] = {}
        self._layers: dict[str, dict[str, list[dict]]] = {}
        self._sessions: dict[str, dict] = {}
        self._persistence = PrivateExamPersistence(self.storage_root, self.tenant_id) if self.storage_root else None
        self._refresh()

    def _refresh(self):
        if self._persistence:
            self._papers, self._layers, self._sessions = self._persistence.load()

    def _persist(self):
        if self._persistence:
            self._persistence.save(self._papers, self._layers, self._sessions)

    def ingest(self, resource_id: str, original_bytes: bytes, grant: PurposeGrant | None,
               mineru_adapter=None) -> dict:
        self._refresh()
        _safe_id(resource_id)
        resource = self.catalogue.get(resource_id)
        if not resource or resource.get("resource_id") != resource_id:
            raise ValueError("resource identity is not in catalogue")
        for field in ("board", "year", "paper", "language", "syllabus_id"):
            _safe_id(str(resource.get(field, "")))
        if type(resource.get("grade")) is not int or resource["grade"] not in range(1, 9):
            raise ValueError("invalid grade identity")
        if grant is None or grant.tenant_id != self.tenant_id or resource_id not in grant.resource_ids:
            raise ValueError("processing grant does not cover resource and tenant")
        fixture = resource.get("synthetic") is True or resource.get("rights") == "test-only"
        if not fixture and not getattr(mineru_adapter, "verified_mineru_adapter", False):
            raise ValueError("real resources require the existing MinerU integration")
        if getattr(mineru_adapter, "resource_id", resource_id) != resource_id:
            raise ValueError("parser resource identity differs from catalogue")
        if getattr(mineru_adapter, "requires_external_processing", False) and (not grant.external_processing or self.no_save):
            raise ValueError("external processing requires a scoped grant and cannot satisfy no-save")
        if not isinstance(original_bytes, bytes) or not original_bytes.startswith(b"%PDF-"):
            raise ValueError("original PDF bytes required")
        digest = _hash(original_bytes)
        if resource.get("sha256") != digest:
            raise ValueError("original bytes checksum mismatch")
        if not resource.get("rights") or not resource.get("syllabus_id"):
            raise ValueError("resource rights and syllabus identity required")
        if mineru_adapter is None:
            raise RuntimeError("validation_unavailable: no verified MinerU adapter supplied")
        parsed = mineru_adapter(original_bytes)
        if not isinstance(parsed, dict) or not parsed.get("page_map") or not parsed.get("questions"):
            raise ValueError("parser returned no structured page/question tree")
        page_map = parsed["page_map"]
        indices = [p.get("pdf_page_index") for p in page_map]
        if indices != list(range(len(indices))):
            raise ValueError("page map must preserve PDF indices")
        paper_id = ":".join(str(resource[k]) for k in ("board", "grade", "year", "paper", "language", "syllabus_id"))
        revision_id = _hash((paper_id+":"+digest).encode())[:20]
        paper_revision_id = f"{paper_id}:{revision_id}"
        if paper_revision_id in self._papers:
            return copy.deepcopy(self._papers[paper_revision_id])
        numbers = [q.get("original_number") for q in parsed["questions"]]
        if len(set(numbers)) != len(numbers) or any(not isinstance(n, str) or not n for n in numbers):
            raise ValueError("duplicate or missing question number")
        parents = {q["original_number"]: q.get("parent_number") for q in parsed["questions"]}
        for number in numbers:
            seen = set(); cursor = number
            while cursor is not None:
                if cursor in seen or cursor not in parents:
                    raise ValueError("cyclic or orphan question hierarchy")
                seen.add(cursor); cursor = parents[cursor]
        questions = []
        for raw in parsed["questions"]:
            parent = raw.get("parent_number")
            if parent is not None and (parent not in numbers or parent == raw["original_number"]):
                raise ValueError("orphan question hierarchy")
            if not raw.get("stem") or not raw.get("pages") or not raw.get("regions"):
                raise ValueError("question stem, page and regions are required")
            if raw.get("response_type") in {"single_select", "multiple_select"} and len(raw.get("options", [])) < 2:
                raise ValueError("missing choices")
            if any(not (option.get("label") or option.get("id")) or not (option.get("text") or option.get("image_region_id"))
                   for option in raw.get("options", [])):
                raise ValueError("incomplete option")
            if (raw.get("marks") is None or type(raw["marks"]) not in (int, float)
                    or not math.isfinite(raw["marks"]) or raw["marks"] <= 0):
                raise ValueError("missing question marks")
            if any(page not in indices for page in raw["pages"]):
                raise ValueError("question page outside document")
            for region in raw["regions"]:
                bbox = region.get("bbox")
                if region.get("page") not in indices or not isinstance(bbox, list) or len(bbox) != 4 or not all(type(x) in (int, float) and math.isfinite(x) for x in bbox) or not (0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1):
                    raise ValueError("invalid normalized coordinates")
            number = raw["original_number"]
            question_id = f"{paper_revision_id}:q:{number}"
            questions.append({"question_id": question_id, "paper_revision_id": paper_revision_id,
                              "parent_id": f"{paper_revision_id}:q:{parent}" if parent else None,
                              "original_number": number, "grade": resource["grade"],
                              "syllabus_id": resource["syllabus_id"], "year": resource["year"],
                              "paper": resource["paper"], "language": resource["language"],
                              "stem": raw["stem"], "instructions": raw.get("instructions", ""), "pages": copy.deepcopy(raw["pages"]),
                              "regions": [copy.deepcopy({k: r[k] for k in ("page", "bbox", "kind", "region_id", "sha256", "image_path", "source_coordinates") if k in r}) for r in raw["regions"]],
                              "options": [{"label": o.get("label") or o.get("id"), "text": o.get("text", ""), "image_region_id": o.get("image_region_id")}
                                          for o in raw.get("options", [])],
                              "marks": raw["marks"], "response_type": raw.get("response_type", "written"),
                              "concept_ids": raw.get("concept_ids", []),
                              "parser_status": "candidate", "review_status": "review_required",
                              "uncertainties": ["Musical notation and answer have not been independently verified."]})
        paper = {"paper_revision_id": paper_revision_id, "paper_id": paper_id,
                 "resource_id": resource_id, "identity": {k: resource[k] for k in ("board", "grade", "year", "paper", "language", "syllabus_id")},
                 "sha256": digest, "rights": resource["rights"], "grant_id": grant.grant_id,
                 "source_url": resource.get("source_url"),
                 "page_map": page_map, "questions": questions,
                 "flags": dict(zip(FLAGS, (True, resource.get("document_verified") is True, True, True, False, False, False))),
                 "parser_status": "structured_candidate_not_musically_verified"}
        self._papers[paper_revision_id] = copy.deepcopy(paper)
        for question in questions:
            self._layers.setdefault(question["question_id"], {})["source_question"] = [{"kind":"source_question", "question_id":question["question_id"], "source_id":resource_id, "content":copy.deepcopy(question)}]
        if self.storage_root and grant.retain_original:
            target = self.storage_root / self.tenant_id / paper_revision_id.replace(":", "_")
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(target.parent, 0o700)
            target.mkdir(parents=False, exist_ok=False, mode=0o700)
            with os.fdopen(os.open(target / "original.pdf", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as file:
                file.write(original_bytes)
            (target / "manifest.json").write_text(json.dumps(paper, ensure_ascii=False), encoding="utf-8")
        self._persist()
        return copy.deepcopy(paper)

    def retrieve(self, *, grade=None, syllabus_id=None, year=None, paper=None,
                 number=None, partial_stem=None, concept=None, image_hash=None) -> list[dict]:
        self._refresh()
        matches = []
        for record in self._papers.values():
            for q in record["questions"]:
                checks = ((grade, q["grade"]), (syllabus_id, q["syllabus_id"]),
                          (year, q["year"]), (paper, q["paper"]), (number, q["original_number"]))
                if any(wanted is not None and wanted != actual for wanted, actual in checks):
                    continue
                if partial_stem and partial_stem.casefold() not in q["stem"].casefold():
                    continue
                if concept and concept not in q["concept_ids"]:
                    continue
                if image_hash and image_hash not in [r.get("sha256") for r in q["regions"]]:
                    continue
                matches.append(self._public_question(q))
        return matches

    @staticmethod
    def _public_question(q: dict) -> dict:
        # Explicit allowlist; parser metadata and any answer-bearing nested keys stay server-side.
        result = {k: q[k] for k in ("question_id", "paper_revision_id", "original_number",
                                  "grade", "syllabus_id", "year", "paper", "language", "stem",
                                  "pages", "marks", "response_type")}
        result["options"] = [{"label": option["label"], "text": option.get("text", "")}
                             for option in q["options"]]
        result["regions"] = [{"page": r["page"], "bbox": r["bbox"]} for r in q["regions"]]
        result["instructions"] = q.get("instructions", "")
        result["parent_id"] = q.get("parent_id")
        return copy.deepcopy(result)

    def _question(self, question_id: str) -> dict:
        for paper in self._papers.values():
            for question in paper["questions"]:
                if question["question_id"] == question_id:
                    return question
        raise ValueError("exact question revision not found")

    def add_layer(self, question_id: str, kind: str, content: str, *, source_id: str,
                  source_paper_revision_id: str | None = None) -> dict:
        self._refresh()
        question = self._question(question_id)
        if source_paper_revision_id is not None and source_paper_revision_id != question["paper_revision_id"]:
            raise ValueError("answer provenance points to a different paper revision")
        if kind not in LAYERS or kind in {"source_question", "official_answer"}:
            raise ValueError("invalid answer layer")
        if not content or not source_id:
            raise ValueError("content and origin required")
        layer = {"kind": kind, "content": content, "source_id": source_id,
                 "question_id": question_id, "source_paper_revision_id": source_paper_revision_id}
        self._layers.setdefault(question_id, {}).setdefault(kind, []).append(layer)
        self._persist()
        return copy.deepcopy(layer)

    def match_official_answer(self, question_id: str, *, answer_resource_id: str,
                              answer_bytes: bytes, grant: PurposeGrant,
                              answer_number: str, answer_text: str,
                              source_locator: dict | None = None, reviewer_id: str | None = None) -> dict:
        self._refresh()
        question = self._question(question_id)
        paper = self._papers[question['paper_revision_id']]
        source = self.catalogue.get(answer_resource_id)
        if not source or source.get('resource_id') != answer_resource_id:
            raise ValueError('answer resource identity not in catalogue')
        if source.get('authority') != 'official' or source.get('resource_type') not in {'official_answer', 'official_answer_key', 'official_sample_answers'}:
            raise ValueError('third-party, question or inferred sources cannot become official answers')
        if grant.tenant_id != self.tenant_id or answer_resource_id not in grant.resource_ids:
            raise ValueError('answer grant does not match tenant and resource')
        if source.get('answer_for') != paper['resource_id']:
            raise ValueError('answer publication not paired to this question paper')
        for field in ('board', 'grade', 'year', 'paper', 'language', 'syllabus_id'):
            if source.get(field) != paper['identity'][field]:
                raise ValueError('answer publication set/version does not match paper')
        if not source.get('rights') or source.get('document_verified') is not True:
            raise ValueError('answer document identity and rights require verification')
        if not isinstance(answer_bytes, bytes) or not answer_bytes.startswith(b'%PDF-') or _hash(answer_bytes) != source.get('sha256') or _hash(answer_bytes) == paper['sha256']:
            raise ValueError('answer bytes missing, changed or identical to question paper')
        if answer_number != question['original_number'] or not isinstance(answer_text, str) or not answer_text.strip():
            raise ValueError('answer hierarchy does not match exact question')
        if not reviewer_id or not source_locator:
            raise ValueError('verified answer source region and reviewer required')
        _safe_id(reviewer_id)
        page_number, bbox = source_locator.get('page'), source_locator.get('bbox')
        if type(page_number) is not int or not isinstance(bbox, list) or len(bbox) != 4 or not all(type(x) in (int, float) and math.isfinite(x) for x in bbox) or not (0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1):
            raise ValueError('invalid source answer coordinates')
        try:
            import fitz
        except ImportError as error:
            raise RuntimeError('local answer-source verification requires PyMuPDF') from error
        with fitz.open(stream=answer_bytes, filetype='pdf') as document:
            if document.needs_pass or page_number not in range(document.page_count):
                raise ValueError('answer page inaccessible or missing')
            page = document[page_number]
            rectangle = fitz.Rect(bbox[0]*page.rect.width, bbox[1]*page.rect.height,
                                  bbox[2]*page.rect.width, bbox[3]*page.rect.height)
            text = page.get_text('text', clip=rectangle)
        normalize = lambda value: ' '.join(value.split()).casefold()
        expected = normalize(answer_text)
        pattern = re.compile(r'^\s*' + re.escape(answer_number) + r'[.)\s:]+(.+?)\s*$', re.MULTILINE)
        extracted = [normalize(match.group(1)) for match in pattern.finditer(text)]
        if expected not in extracted:
            raise ValueError('answer text is not verified in the numbered source region; notation-only answers require expert review')
        layer = {'kind':'official_answer', 'content':answer_text.strip(), 'source_id':answer_resource_id,
                 'question_id':question_id, 'source_paper_revision_id':question['paper_revision_id'],
                 'answer_sha256':_hash(answer_bytes), 'source_text_verified':True,
                 'source_locator':copy.deepcopy(source_locator), 'reviewer_id':reviewer_id,
                 'review_status':'source_text_verified_not_musically_verified',
                 'source_is_synthetic':source.get('synthetic') is True}
        self._layers.setdefault(question_id, {}).setdefault('official_answer', []).append(layer)
        paper['flags']['answer_matched'] = True
        self._persist()
        return copy.deepcopy(layer)

    def tutor(self, question_id: str, mode: str, *, confirmed_question_id: str | None = None,
              attempt: str | None = None, session_id: str | None = None, hint_level: int = 1) -> dict:
        self._refresh()
        question = self._question(question_id)
        revision = question['paper_revision_id']
        if mode not in {'hint', 'worked', 'check', 'targeted_practice', 'exam_simulation'}:
            raise ValueError('unknown tutoring mode')
        active = [s for s in self._sessions.values() if s.get('kind') != 'practice' and s['paper_revision_id'] == revision and not s['closed']]
        if active and mode != 'exam_simulation':
            raise ValueError('active exam withholds answers across the entire paper')
        if mode in {'worked', 'check'} and confirmed_question_id != question_id:
            raise ValueError('confirm exact paper and question revision')
        visible = self._public_question(question)
        if mode == 'hint':
            if type(hint_level) is not int or hint_level not in (1, 2, 3):
                raise ValueError('hint level must be 1, 2 or 3')
            text = question['stem'].casefold()
            if any(w in text for w in ('note name', 'uk name', 'eighth note', 'duration', 'rest')):
                hints = ('Separate note-value terminology from the number of beats.', 'Compare the written values using one common duration unit; do not infer the answer from word length.', 'Eliminate choices with a different duration. Keep UK and US note-name conventions distinct.')
            elif any(w in text for w in ('interval', 'scale degree')):
                hints = ('Locate both written pitches and the clef.', 'Count letter names inclusively for the interval number; inspect accidentals separately.', 'Use the question’s key and requested convention. Distinguish interval number from quality.')
            else:
                hints = ('Identify the requested concept and its source region.', 'Read the clef, key, time signature and instructions before applying a rule.', 'Check each option against the stated evidence; uncertain notation still needs review.')
            return {'mode':mode, 'question':visible, 'hint':hints[hint_level-1], 'hint_level':hint_level, 'answer_visible':False}
        if mode == 'exam_simulation':
            if not session_id:
                raise ValueError('exam session id required')
            _safe_id(session_id)
            if active and session_id not in self._sessions:
                raise ValueError('another session already holds this paper')
            state = self._sessions.setdefault(session_id, {'kind':'exam', 'paper_revision_id':revision, 'question_id':question_id, 'closed':False, 'attempts':[]})
            if state['paper_revision_id'] != revision or state['closed']:
                raise ValueError('exam session is closed or bound to another paper')
            if attempt is not None:
                if not isinstance(attempt, str) or len(attempt) > 10000:
                    raise ValueError('bounded learner answer required')
                state['attempts'].append({'question_id':question_id, 'answer':attempt})
                self._layers.setdefault(question_id, {}).setdefault('learner_answer', []).append({'kind':'learner_answer','question_id':question_id,'source_id':session_id,'content':attempt})
            self._persist()
            return {'mode':mode, 'question':visible, 'answer_visible':False, 'state':'open', 'session_id':session_id,
                    'paper_questions':[self._public_question(q) for q in self._papers[revision]['questions']]}
        if mode == 'targeted_practice':
            from .mini_exam import build_mini_exam
            seed = int(_hash(question_id.encode())[:8], 16)
            bundle = build_mini_exam(grade=question['grade'], syllabus_id=question['syllabus_id'], seed=seed, source_questions=(question['stem'],))
            if 'student_paper' not in bundle:
                return {'mode':mode, 'state':'review_required','reason':bundle.get('reason'), 'answer_visible':False}
            practice_id = 'practice-' + _hash(question_id.encode())[:16]
            self._sessions[practice_id] = {'kind':'practice','paper_revision_id':revision,'question_id':question_id,'closed':False,'bundle':bundle}
            self._persist()
            return {'mode':mode,'state':'original_practice','practice_id':practice_id,'student_paper':bundle['student_paper'],'answer_visible':False}
        layers = self._layers.get(question_id, {})
        available = layers.get('official_answer') or layers.get('teacher_result') or layers.get('ai_derived_answer')
        answer = available[-1] if available else None
        feedback = None
        if mode == 'check':
            if not isinstance(attempt, str) or len(attempt) > 10000:
                raise ValueError('bounded learner attempt required')
            self._layers.setdefault(question_id, {}).setdefault('learner_answer', []).append({'kind':'learner_answer','question_id':question_id,'source_id':'learner:'+self.tenant_id,'content':attempt})
            if not answer:
                feedback = 'Assessment is unavailable: no verified or derived answer is linked to this exact question. Your answer has not been marked wrong.'
            elif question['response_type'] not in {'single_select', 'single_select_candidate'}:
                feedback = 'An open response requires a question-specific rubric and reviewer; a model answer is not the only acceptable wording.'
            else:
                normalize = lambda value: ' '.join(value.split()).casefold()
                choices = {normalize(o['label']):normalize(o.get('text','')) for o in question['options']}
                learner = choices.get(normalize(attempt), normalize(attempt))
                reference = choices.get(normalize(answer['content']), normalize(answer['content']))
                feedback = ('Your response matches the available answer; source and musical review still apply.' if learner == reference else 'Your response differs from the available answer. Recheck the source notation and convention; this is practice feedback only.')
            self._persist()
        result = {'mode':mode, 'question':visible, 'answer':answer['content'] if answer else None,
                  'answer_origin':answer['kind'] if answer else 'unavailable',
                  'answer_provenance':copy.deepcopy(answer) if answer else None,
                  'state':'review_required' if not answer else 'provisional_not_musically_verified',
                  'practice_feedback_only':mode=='check', 'feedback':feedback,
                  'exam_convention':{'board':self._papers[revision]['identity']['board'],'syllabus_id':question['syllabus_id']},
                  'evidence_flags':copy.deepcopy(self._papers[revision]['flags'])}
        if mode=='check':
            result.update({'learner_answer':attempt,'learner_answer_origin':'learner_answer'})
        if mode=='worked':
            result['worked_solution'] = 'Use the exact source question and its numbered answer linkage. The available answer is ' + (str(answer['content']) if answer else 'not available') + '. Do not infer unread pitches or rhythms; analytical and exam conventions remain separate.'
        return result

    def finish_exam(self, session_id: str, *, exit_confirmed: bool = False) -> dict:
        self._refresh()
        state = self._sessions.get(session_id)
        if not state or state.get('kind')=='practice' or type(exit_confirmed) is not bool or not exit_confirmed:
            raise ValueError('explicit exam exit required')
        state['closed'] = True
        self._persist()
        qid = state['question_id']
        result = self.tutor(qid, 'worked', confirmed_question_id=qid)
        result['submitted_attempts'] = copy.deepcopy(state['attempts'])
        result['official_prediction'] = False
        return result

    def finish_practice(self, practice_id: str, *, completed: bool = False) -> dict:
        self._refresh()
        state = self._sessions.get(practice_id)
        if type(completed) is not bool or not completed or not state or state.get('kind')!='practice':
            raise ValueError('explicit practice completion required')
        if any(s.get("kind") != "practice" and s["paper_revision_id"] == state["paper_revision_id"] and not s["closed"] for s in self._sessions.values()):
            raise ValueError("practice answers cannot bypass an active paper exam")
        state['closed'] = True
        self._persist()
        return copy.deepcopy(state['bundle'])
