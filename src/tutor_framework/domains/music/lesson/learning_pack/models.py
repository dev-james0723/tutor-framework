"""Typed learning intent and source-grounded content, shared by every output.

The host tutor reasons about inspected sources. These models never call an LLM,
recognize notation, grant consent, or turn an analytical opinion into a fact.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from tutor_framework.protocol.models import ProtocolModel
from ..models import safe_id, sha256, text

GOALS = {'assignment', 'understand', 'exam', 'discussion', 'notes'}
MATERIALS = {'notes', 'annotated_score', 'listening_guide', 'quiz', 'flashcards',
             'essay_outline', 'cheat_sheet', 'mindmap', 'video'}
SECTIONS = ('assignment_decoder', 'objectives', 'passage_analysis', 'formal_map',
            'listening_guide', 'concepts', 'evidence', 'alternatives', 'course',
            'context', 'comparisons', 'practice', 'transfer', 'takeaway')
CLAIM_KINDS = {'source_observation', 'historical_fact', 'primary_source_statement',
               'scholar_interpretation', 'course_interpretation', 'caplin_theory',
               'tutor_judgment', 'pedagogical_example', 'study_instruction'}
EVIDENCE_STATES = {'verified', 'review_required', 'candidate', 'contradicted', 'validation_unavailable'}


def bounded(value: str, name: str, limit: int = 20000, *, empty: bool = False) -> None:
    if not empty:
        text(value, name)
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError(f'{name} must be bounded plain text')


def unique(values, field):
    result = {getattr(value, field): value for value in values}
    if len(result) != len(values):
        raise ValueError(f'duplicate {field}')
    return result


@dataclass
class LearningBrief(ProtocolModel):
    source_hash: str
    goal: str
    materials: tuple[str, ...]
    help_mode: str = 'guided'
    depth: str = 'standard'
    language: str = 'en'
    prior_knowledge: str = ''
    deadline: str = ''
    confirmed: bool = False
    no_video: bool = False

    def __post_init__(self):
        super().__post_init__()
        sha256(self.source_hash)
        if self.goal not in GOALS:
            raise ValueError('unknown learning purpose')
        if not self.materials or set(self.materials) - MATERIALS or len(set(self.materials)) != len(self.materials):
            raise ValueError('select distinct supported materials')
        if self.help_mode not in {'guided', 'coached', 'worked', 'review'}:
            raise ValueError('unknown answer-reveal policy')
        if self.depth not in {'brief', 'standard', 'deep'}:
            raise ValueError('unknown depth')
        if self.language not in {'en', 'zh-Hant', 'bilingual'}:
            raise ValueError('unsupported notes language')
        bounded(self.prior_knowledge, 'prior knowledge', 2000, empty=True)
        bounded(self.deadline, 'deadline', 200, empty=True)
        if type(self.confirmed) is not bool or type(self.no_video) is not bool:
            raise ValueError('confirmation/no-video must be explicit booleans')
        if self.no_video and 'video' in self.materials:
            raise ValueError('no-video overrides a video selection')

    @property
    def answers_visible(self):
        return self.help_mode in {'worked', 'review'}


@dataclass
class PackSource(ProtocolModel):
    source_id: str
    path: str
    content_hash: str
    title: str
    rights: str
    kind: str = 'document'
    private: bool = True

    def __post_init__(self):
        super().__post_init__()
        safe_id(self.source_id); sha256(self.content_hash)
        bounded(self.path, 'source path', 4096); bounded(self.title, 'source title', 300)
        bounded(self.rights, 'source rights/use basis', 2000)
        if self.kind not in {'document', 'score', 'symbolic', 'audio', 'video', 'image'}:
            raise ValueError('unknown source kind')
        if type(self.private) is not bool:
            raise ValueError('explicit source privacy required')


@dataclass
class Citation(ProtocolModel):
    source_id: str
    locator: str
    page: int = 0
    line_start: int = 0
    line_end: int = 0

    def __post_init__(self):
        super().__post_init__(); safe_id(self.source_id); bounded(self.locator, 'source locator', 1000)
        for value in (self.page, self.line_start, self.line_end):
            if type(value) is not int or value < 0:
                raise ValueError('source page and line references must be nonnegative integers')
        if self.line_end and self.line_end < self.line_start:
            raise ValueError('source line range reversed')


@dataclass
class PackPassage(ProtocolModel):
    passage_id: str
    source_id: str
    edition: str
    measures: str
    page: int
    occurrence: str = '1'
    traversal: tuple[str, ...] = ()
    evidence_state: str = 'review_required'

    def __post_init__(self):
        super().__post_init__(); safe_id(self.passage_id); safe_id(self.source_id)
        bounded(self.edition, 'edition', 300); bounded(self.measures, 'measure scope', 300)
        bounded(self.occurrence, 'repeat occurrence', 100)
        if type(self.page) is not int or self.page < 1:
            raise ValueError('passage PDF page is required')
        if self.evidence_state not in EVIDENCE_STATES:
            raise ValueError('unknown passage evidence state')
        for label in self.traversal:
            bounded(label, 'explicit printed measure traversal', 100)


@dataclass
class NoteBlock(ProtocolModel):
    block_id: str
    section: str
    title: str
    body: str
    passage_ids: tuple[str, ...] = ()
    citations: tuple[Citation, ...] = ()
    claim_kind: str = 'tutor_judgment'
    evidence_state: str = 'review_required'
    answer_bearing: bool = True
    listening_relevance: str = ''

    def __post_init__(self):
        super().__post_init__(); safe_id(self.block_id)
        bounded(self.title, 'block title', 300); bounded(self.body, 'notes content')
        if self.section not in SECTIONS or self.claim_kind not in CLAIM_KINDS or self.evidence_state not in EVIDENCE_STATES:
            raise ValueError('unknown notes section, claim type or evidence state')
        if type(self.answer_bearing) is not bool:
            raise ValueError('answer disclosure must be explicit')
        if self.claim_kind != 'study_instruction' and not self.citations:
            raise ValueError('factual and analytical notes require source-level provenance')
        if self.section == 'context':
            bounded(self.listening_relevance, 'current-passage relevance', 3000)
        if self.evidence_state == 'verified' and self.claim_kind == 'tutor_judgment':
            raise ValueError('a tutor analytical judgment must remain an interpretation, not verified fact')


@dataclass
class CoverageItem(ProtocolModel):
    unit_id: str
    block_ids: tuple[str, ...]
    unresolved: str = ''

    def __post_init__(self):
        super().__post_init__(); safe_id(self.unit_id)
        if not self.block_ids and not self.unresolved.strip():
            raise ValueError('every source unit needs content coverage or an explicit unresolved reason')
        bounded(self.unresolved, 'coverage limitation', 3000, empty=True)


@dataclass
class PracticeItem(ProtocolModel):
    item_id: str
    prompt: str
    answer: str
    rationale: str
    passage_ids: tuple[str, ...]
    citations: tuple[Citation, ...]
    transfer_from: str = ''
    answer_state: str = 'review_required'

    def __post_init__(self):
        super().__post_init__(); safe_id(self.item_id)
        bounded(self.prompt, 'practice prompt', 3000)
        bounded(self.answer, 'practice answer', 5000, empty=True)
        bounded(self.rationale, 'practice rationale', 5000, empty=True)
        if self.answer_state not in EVIDENCE_STATES:
            raise ValueError('unknown answer evidence state')
        if self.answer and not self.citations:
            raise ValueError('practice answers require evidence')


@dataclass
class ScoreAnnotation(ProtocolModel):
    annotation_id: str
    passage_id: str
    source_id: str
    page: int
    box: tuple[float, float, float, float]
    label: str
    answer_bearing: bool = True
    evidence_state: str = 'review_required'

    def __post_init__(self):
        super().__post_init__()
        for value in (self.annotation_id, self.passage_id, self.source_id): safe_id(value)
        bounded(self.label, 'score annotation', 600)
        if type(self.page) is not int or self.page < 1 or len(self.box) != 4:
            raise ValueError('invalid annotation page or box')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in self.box):
            raise ValueError('invalid annotation coordinate')
        x, y, width, height = self.box
        if not (0 <= x < 1 and 0 <= y < 1 and 0 < width <= 1-x and 0 < height <= 1-y):
            raise ValueError('annotation box must remain inside the original source page')
        if type(self.answer_bearing) is not bool or self.evidence_state not in EVIDENCE_STATES:
            raise ValueError('invalid annotation disclosure/evidence state')


@dataclass
class FormNode(ProtocolModel):
    node_id: str
    label: str
    level: str
    passage_ids: tuple[str, ...]
    parent_id: str = ''
    answer_bearing: bool = True

    def __post_init__(self):
        super().__post_init__(); safe_id(self.node_id); bounded(self.label, 'form label', 300)
        if self.level not in {'movement', 'section', 'theme', 'phrase', 'idea'}:
            raise ValueError('formal levels must remain distinct')
        if type(self.answer_bearing) is not bool:
            raise ValueError('invalid form disclosure state')


@dataclass
class PackContent(ProtocolModel):
    title: str
    sources: tuple[PackSource, ...]
    passages: tuple[PackPassage, ...]
    blocks: tuple[NoteBlock, ...]
    coverage: tuple[CoverageItem, ...]
    practice: tuple[PracticeItem, ...] = ()
    annotations: tuple[ScoreAnnotation, ...] = ()
    form: tuple[FormNode, ...] = ()
    video_source_id: str = ''
    visual_reviewed_pages: tuple[int, ...] = ()
    review_notes: str = ''

    def __post_init__(self):
        super().__post_init__(); bounded(self.title, 'learning pack title', 300)
        sources=unique(self.sources, 'source_id'); passages=unique(self.passages, 'passage_id')
        blocks=unique(self.blocks, 'block_id'); unique(self.coverage, 'unit_id')
        unique(self.practice, 'item_id'); unique(self.annotations, 'annotation_id'); form=unique(self.form, 'node_id')
        if not sources or not blocks:
            raise ValueError('a Learning Pack needs real registered sources and authored content')
        for passage in self.passages:
            if passage.source_id not in sources: raise ValueError('unknown passage source')
        for block in self.blocks:
            if set(block.passage_ids)-passages.keys(): raise ValueError('unknown block passage')
        for item in (*self.blocks, *self.practice):
            if set(item.passage_ids)-passages.keys(): raise ValueError('unknown practice passage')
            for citation in item.citations:
                if citation.source_id not in sources: raise ValueError('unknown claim source')
        for coverage in self.coverage:
            if set(coverage.block_ids)-blocks.keys(): raise ValueError('unknown coverage block')
        for item in self.practice:
            if item.transfer_from and (item.transfer_from not in passages or not item.passage_ids
                                      or item.transfer_from in item.passage_ids):
                raise ValueError('transfer needs a different registered passage')
            if item.transfer_from and item.answer_state == 'verified' and any(passages[p].evidence_state != 'verified' for p in item.passage_ids):
                raise ValueError('an unverified transfer passage cannot supply a verified answer')
        for annotation in self.annotations:
            if annotation.passage_id not in passages or annotation.source_id not in sources:
                raise ValueError('unknown annotation passage/source')
            if annotation.source_id != passages[annotation.passage_id].source_id:
                raise ValueError('annotation and passage editions disagree')
        levels={'movement':0, 'section':1, 'theme':2, 'phrase':3, 'idea':4}
        for node in self.form:
            if set(node.passage_ids)-passages.keys(): raise ValueError('unknown form passage')
            if node.parent_id:
                if node.parent_id not in form or levels[form[node.parent_id].level] >= levels[node.level]:
                    raise ValueError('cyclic, inverted or unknown formal hierarchy')
        if self.video_source_id and (self.video_source_id not in sources or sources[self.video_source_id].kind != 'video'):
            raise ValueError('video must reference an actual registered video source')
        if any(type(p) is not int or p < 1 for p in self.visual_reviewed_pages):
            raise ValueError('invalid visually reviewed source-page list')
        if self.visual_reviewed_pages and not self.review_notes.strip():
            raise ValueError('visual review needs concrete observation notes')
