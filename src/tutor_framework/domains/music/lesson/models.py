"""Typed lesson contracts extending the framework's shared protocol.

No model performs I/O or authorizes a provider call merely by being loaded.
Reviews carry exact content bindings; numeric confidence is never proof.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from fractions import Fraction

from tutor_framework.protocol.models import ProtocolModel, EvidenceRef


class CheckState(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    UNAVAILABLE = "validation_unavailable"
    NOT_APPLICABLE = "not_applicable"


class EvidenceState(str, Enum):
    VERIFIED = "verified"
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    CONTRADICTED = "contradicted"
    UNAVAILABLE = "validation_unavailable"


class ClaimKind(str, Enum):
    HISTORICAL_FACT = "historical_fact"
    PRIMARY_STATEMENT = "primary_source_statement"
    SCHOLAR_INTERPRETATION = "scholar_interpretation"
    COURSE_INTERPRETATION = "instructor_course_interpretation"
    CAPLIN_THEORY = "caplin_theory"
    TUTOR_JUDGMENT = "tutor_analytical_judgment"


def text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")


def sha256(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("a lowercase SHA-256 content hash is required")


def positive_int(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer, not a boolean")


def rational(value: str, name: str, *, positive: bool = False) -> Fraction:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError(f"{name} must be a bounded rational string")
    try:
        number = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"invalid rational {name}") from exc
    if number < 0 or (positive and number == 0):
        raise ValueError(f"{name} is outside the permitted range")
    return number


@dataclass
class ReviewRecord(ProtocolModel):
    check_id: str
    state: CheckState
    input_hashes: dict[str, str]
    method: str
    reviewer: str
    details: str
    SCHEMA_VERSION = "2.0"

    def __post_init__(self) -> None:
        super().__post_init__()
        text(self.check_id, "check_id")
        if not isinstance(self.state, CheckState):
            raise ValueError("review state must be a CheckState")
        if not isinstance(self.input_hashes, dict):
            raise ValueError("input_hashes must be an object")
        for key, digest in self.input_hashes.items():
            text(key, "input name"); sha256(digest)
        if self.state == CheckState.PASSED:
            if not self.input_hashes:
                raise ValueError("passed reviews require exact input bindings")
            for name in ("method", "reviewer", "details"):
                text(getattr(self, name), name)


@dataclass
class MeasureVisit(ProtocolModel):
    label: str
    occurrence: int
    start_beat: str = "1"
    end_beat: str | None = None
    SCHEMA_VERSION = "2.0"

    def __post_init__(self) -> None:
        super().__post_init__()
        text(self.label, "printed measure label")
        positive_int(self.occurrence, "repeat occurrence")
        start = rational(self.start_beat, "start beat", positive=True)
        if self.end_beat is not None and rational(self.end_beat, "end beat", positive=True) <= start:
            raise ValueError("end beat must follow start beat")


@dataclass
class Passage(ProtocolModel):
    passage_id: str
    edition_id: str
    visits: tuple[MeasureVisit, ...]
    part_ids: tuple[str, ...]
    real_measure_mapping: str
    entry_policy: str = "complete_attack"
    evidence_state: EvidenceState = EvidenceState.REVIEW_REQUIRED
    SCHEMA_VERSION = "2.0"

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in ("passage_id", "edition_id", "real_measure_mapping"):
            text(getattr(self, name), name)
        if not self.visits or not all(isinstance(v, MeasureVisit) for v in self.visits):
            raise ValueError("a passage requires explicit typed measure visits")
        keys = [(v.label, v.occurrence) for v in self.visits]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate measure occurrence")
        if not self.part_ids or len(set(self.part_ids)) != len(self.part_ids):
            raise ValueError("distinct participating parts are required")
        for part in self.part_ids:
            text(part, "part id")
        if self.entry_policy not in {"complete_attack", "preroll", "reviewed_sustain"}:
            raise ValueError("unknown tied-entry policy")
        if not isinstance(self.evidence_state, EvidenceState):
            raise ValueError("invalid evidence state")


@dataclass
class ContextCard(ProtocolModel):
    card_id: str
    passage_id: str
    kind: ClaimKind
    statement: str
    listening_relevance: str
    evidence: tuple[EvidenceRef, ...]
    state: EvidenceState = EvidenceState.REVIEW_REQUIRED
    SCHEMA_VERSION = "2.0"

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in ("card_id", "passage_id", "statement", "listening_relevance"):
            text(getattr(self, name), name)
        if not isinstance(self.kind, ClaimKind) or not isinstance(self.state, EvidenceState):
            raise ValueError("context kind and state must be explicit")
        if not self.evidence or not all(isinstance(e, EvidenceRef) for e in self.evidence):
            raise ValueError("context needs source-level evidence")
        for evidence in self.evidence:
            if not evidence.anchors:
                raise ValueError("context requires source locators, not a bibliography alone")
            sha256(evidence.content_hash)


@dataclass
class RightsRecord(ProtocolModel):
    composition: str
    edition: str
    recording: str
    local_use_basis: str
    SCHEMA_VERSION = "2.0"

    def __post_init__(self) -> None:
        super().__post_init__()
        allowed = {"public_domain", "licensed", "original", "user_provided", "unknown", "not_applicable"}
        if any(getattr(self, n) not in allowed for n in ("composition", "edition", "recording")):
            raise ValueError("rights for composition, edition and recording must remain distinct")
        text(self.local_use_basis, "scope/rights evidence")


@dataclass
class ProductionGrant(ProtocolModel):
    approval_id: str
    provider: str
    asset_hashes: tuple[str, ...]
    private_transfer: bool
    max_usd: float
    expires_at: str
    SCHEMA_VERSION = "2.0"

    def __post_init__(self) -> None:
        super().__post_init__()
        text(self.approval_id, "approval id"); text(self.provider, "provider")
        for digest in self.asset_hashes:
            sha256(digest)
        if len(set(self.asset_hashes)) != len(self.asset_hashes):
            raise ValueError("duplicate approved asset")
        if type(self.private_transfer) is not bool:
            raise ValueError("private transfer must be explicit")
        if isinstance(self.max_usd, bool) or not isinstance(self.max_usd, (int, float)) or not math.isfinite(self.max_usd) or self.max_usd < 0:
            raise ValueError("invalid approved cost")
        expires = datetime.fromisoformat(self.expires_at)
        if expires.tzinfo is None:
            raise ValueError("grant expiry requires a timezone")


def safe_id(value: str) -> None:
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}',value) or value in {'.','..'}:
        raise ValueError('invalid stable identifier')


@dataclass
class SourceAsset(ProtocolModel):
    asset_id: str
    path: str
    content_hash: str
    kind: str
    origin: str
    rights: RightsRecord
    evidence_state: EvidenceState = EvidenceState.REVIEW_REQUIRED
    private: bool = True
    derived_from: tuple[str,...] = ()
    provenance: tuple[EvidenceRef,...] = ()
    SCHEMA_VERSION = '2.0'

    def __post_init__(self):
        super().__post_init__();safe_id(self.asset_id);text(self.path,'source path');sha256(self.content_hash);text(self.origin,'source origin')
        if self.kind not in {'score','symbolic','image','narration','music','performance','document'}:raise ValueError('unknown source kind')
        if not isinstance(self.evidence_state,EvidenceState) or not isinstance(self.rights,RightsRecord):raise ValueError('invalid source evidence/rights')
        if type(self.private) is not bool:raise ValueError('privacy must be explicit')


@dataclass
class ExampleSpec(ProtocolModel):
    example_id: str
    symbolic_source_id: str
    passage_id: str
    bpm: str
    transformation: str
    part_ids: tuple[str,...]
    purpose: str
    parent_id: str = ''
    changed_note_id: str = ''
    changed_midi: int | None = None
    SCHEMA_VERSION = '2.0'

    def __post_init__(self):
        super().__post_init__()
        for n in ('example_id','symbolic_source_id','passage_id'):safe_id(getattr(self,n))
        bpm=rational(self.bpm,'quarter-note tempo',positive=True)
        if not 20<=bpm<=300:raise ValueError('tempo outside bounded teaching range')
        if self.transformation not in {'identity','part','melody','bass','lowest','highest','rewrite'}:raise ValueError('unknown example transformation')
        text(self.purpose,'example learning purpose')
        if self.transformation in {'part','melody','bass','lowest','highest'} and not self.part_ids:raise ValueError('focused listening needs explicitly chosen score parts')
        if self.transformation=='rewrite':
            text(self.parent_id,'rewrite parent');text(self.changed_note_id,'controlled changed note')
            if type(self.changed_midi) is not int or not 0<=self.changed_midi<=127:raise ValueError('invalid controlled replacement pitch')
        elif self.changed_note_id or self.changed_midi is not None:raise ValueError('pitch edit requires explicit rewrite provenance')


@dataclass
class BeatSpec(ProtocolModel):
    kind: str
    text: str = ''
    example_id: str = ''
    pause_seconds: str = '0'
    narration_asset: str = ''
    narration_text_hash: str = ''
    reveals: tuple[str,...] = ()
    SCHEMA_VERSION = '2.0'

    def __post_init__(self):
        super().__post_init__()
        if self.kind not in {'speech','music','pause'}:raise ValueError('unsupported lesson beat')
        pause=rational(self.pause_seconds,'pause duration')
        if pause>60:raise ValueError('pause exceeds bounded teaching window')
        if self.kind in {'speech','music'}:text(self.text,'narration or listening purpose')
        if self.kind=='music' and not self.example_id:raise ValueError('music needs a symbolic example')
        if self.kind!='music' and self.example_id:raise ValueError('speech and music cannot share one beat')
        if self.kind=='pause' and pause<=0:raise ValueError('pause must be positive')
        if self.kind!='pause' and pause!=0:raise ValueError('pause must have its own beat')
        if self.narration_asset:
            if self.kind!='speech':raise ValueError('narration asset on non-speech beat')
            sha256(self.narration_text_hash)
        if self.kind=='speech' and len(self.text)>120:raise ValueError('split dense narration into phrase-sized final audio cues')


@dataclass
class Annotation(ProtocolModel):
    label: str
    image_index: int
    x: float
    y: float
    width: float
    height: float
    at_beat: int = 0
    SCHEMA_VERSION = '2.0'

    def __post_init__(self):
        super().__post_init__();text(self.label,'annotation label')
        if type(self.image_index) is not int or self.image_index<0 or type(self.at_beat) is not int or self.at_beat<0:raise ValueError('invalid annotation index')
        for n in ('x','y','width','height'):
            v=getattr(self,n)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('invalid annotation geometry')
        if not 0<=self.x<1 or not 0<=self.y<1 or not 0<self.width<=1-self.x or not 0<self.height<=1-self.y:raise ValueError('annotation outside source image')


@dataclass
class VisualSpec(ProtocolModel):
    kind: str
    source_ids: tuple[str,...]
    items: tuple[str,...]
    annotations: tuple[Annotation,...] = ()
    mochi: str = 'none'
    SCHEMA_VERSION = '2.0'

    def __post_init__(self):
        super().__post_init__()
        if self.kind not in {'text','score','engraving','form_map','tonal_route','harmonic_strip','motivic_genealogy','voice_leading','context','comparison'}:raise ValueError('unknown reusable visual component')
        if self.mochi not in {'none','point','listen','think','wave'}:raise ValueError('unknown canonical Mochi pose')
        if len(self.source_ids)>2:raise ValueError('at most two readable score images per scene')
        for a in self.annotations:
            if a.image_index>=len(self.source_ids):raise ValueError('annotation source image missing')


@dataclass
class SceneSpec(ProtocolModel):
    scene_id: str
    title: str
    stage: str
    passage_id: str
    beats: tuple[BeatSpec,...]
    visual: VisualSpec
    question_id: str = ''
    answers_question_id: str = ''
    transfer_from_passage_id: str = ''
    context_id: str = ''
    SCHEMA_VERSION = '2.0'

    def __post_init__(self):
        super().__post_init__();safe_id(self.scene_id);text(self.title,'scene title')
        if self.stage not in {'orient','listen','predict','notice','reason','compare','return','transfer','consolidate','full_listening','context'}:raise ValueError('unknown teaching stage')
        if not self.beats or not all(isinstance(b,BeatSpec) for b in self.beats):raise ValueError('scene requires typed beats')
        if not isinstance(self.visual,VisualSpec):raise ValueError('scene requires a typed visual')
        if self.question_id and self.answers_question_id:raise ValueError('question and analytical reveal must be separate scenes')
        if any(a.at_beat>=len(self.beats) for a in self.visual.annotations):raise ValueError('annotation reveal beat missing')


@dataclass
class LessonManifest(ProtocolModel):
    lesson_id: str
    title: str
    objectives: tuple[str,...]
    sources: tuple[SourceAsset,...]
    passages: tuple[Passage,...]
    examples: tuple[ExampleSpec,...]
    scenes: tuple[SceneSpec,...]
    contexts: tuple[ContextCard,...] = ()
    reviews: tuple[ReviewRecord,...] = ()
    finale_source_id: str = ''
    local_preview_only: bool = True
    sample_rate: int = 48000
    fps: int = 24
    SCHEMA_VERSION = '2.0'

    def __post_init__(self):
        super().__post_init__();safe_id(self.lesson_id);text(self.title,'lesson title')
        if not self.objectives or not self.scenes:raise ValueError('a lesson requires objectives and scenes')
        for objective in self.objectives:text(objective,'learning objective')
        if self.sample_rate!=48000 or self.fps!=24:raise ValueError('this compiler contract uses 48 kHz and 24 fps')
        if type(self.local_preview_only) is not bool:raise ValueError('release scope must be explicit')
        def index(values,key):
            result={getattr(v,key):v for v in values}
            if len(result)!=len(values):raise ValueError('duplicate lesson identifier')
            return result
        sources=index(self.sources,'asset_id');passages=index(self.passages,'passage_id');examples=index(self.examples,'example_id');index(self.scenes,'scene_id');contexts=index(self.contexts,'card_id');index(self.reviews,'check_id')
        for source in self.sources:
            if set(source.derived_from)-sources.keys():raise ValueError('unknown source provenance parent')
        for ex in self.examples:
            if ex.symbolic_source_id not in sources or sources[ex.symbolic_source_id].kind!='symbolic':raise ValueError('example needs a registered symbolic source')
            if ex.passage_id not in passages:raise ValueError('example passage missing')
            if ex.parent_id and ex.parent_id not in examples:raise ValueError('rewrite parent missing')
        for ex in self.examples:
            visited=set();current=ex
            while current.parent_id:
                if current.example_id in visited:raise ValueError('cyclic example derivation')
                visited.add(current.example_id);current=examples[current.parent_id]
        for context in self.contexts:
            if context.passage_id not in passages:raise ValueError('Context Card passage missing')
        questions=set()
        for scene in self.scenes:
            if scene.passage_id not in passages:raise ValueError('scene passage missing')
            if set(scene.visual.source_ids)-sources.keys():raise ValueError('scene source image missing')
            for beat in scene.beats:
                if beat.example_id and beat.example_id not in examples:raise ValueError('music example missing')
                if beat.narration_asset and (beat.narration_asset not in sources or sources[beat.narration_asset].kind!='narration'):raise ValueError('narration source missing')
            if scene.context_id and scene.context_id not in contexts:raise ValueError('Context Card missing')
            if scene.stage=='transfer' and (not scene.transfer_from_passage_id or scene.transfer_from_passage_id not in passages or scene.transfer_from_passage_id==scene.passage_id):raise ValueError('transfer must use different registered material')
            if scene.question_id:
                if scene.question_id in questions:raise ValueError('duplicate question ID')
                questions.add(scene.question_id)
            if scene.answers_question_id and scene.answers_question_id not in questions:raise ValueError('answer precedes question')
        if self.finale_source_id and (self.finale_source_id not in sources or sources[self.finale_source_id].kind!='performance'):raise ValueError('finale needs a registered complete-performance source')
