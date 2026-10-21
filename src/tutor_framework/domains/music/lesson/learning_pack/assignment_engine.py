"""Caplin v3.6 candidate: source-anchored assignment evidence and independent structural checks.

This is NOT a score recognizer. A checked ledger establishes traceability and
internal consistency, not independent verification of the original notation.
"""
from __future__ import annotations
import math
import re
from dataclasses import dataclass
from typing import Sequence


def _span(first: int, last: int) -> None:
    if type(first) is not int or type(last) is not int or first < 1 or last < first:
        raise ValueError("measure span must be a valid positive inclusive range")


@dataclass(frozen=True)
class ScoreFact:
    aspect: str
    description: str
    start: int
    end: int
    score_locator: str

    def __post_init__(self):
        _span(self.start,self.end)
        if self.aspect not in {"melody","rhythm","bass","harmony","grouping","formal_context","texture"}:
            raise ValueError("unsupported musical evidence aspect")
        if not self.description.strip() or not self.score_locator.strip():
            raise ValueError("a fact requires a specific observation and score locator")


@dataclass(frozen=True)
class ScoreMark:
    annotation_id: str
    page: int
    kind: str
    label: str
    box: tuple[float,float,float,float]
    measure_start: int
    measure_end: int
    depth: int=0

    def __post_init__(self):
        _span(self.measure_start,self.measure_end)
        if not self.annotation_id or self.kind not in {"cadence","phrase","idea","section"}:
            raise ValueError("unknown annotation")
        if type(self.page) is not int or self.page<1 or self.depth<0 or self.depth>4:
            raise ValueError("invalid page or formal bracket depth")
        if len(self.box)!=4 or not all(type(x) in (int,float) and math.isfinite(x) for x in self.box):
            raise ValueError("invalid normalized rectangle")
        x,y,w,h=self.box
        if not (0<=x<1 and 0<=y<1 and 0<w<=1-x and 0<h<=1-y):
            raise ValueError("annotation must be inside the source page")
        if not self.label.strip() or "?" in self.label or re.search(r"\\b(?:m\\.|mm\\.)\\s*\\d+",self.label):
            raise ValueError("uncertain or numbered score labels are forbidden")
        if "varied" in self.label.casefold() or "B1" in self.label:
            raise ValueError("use BI′, never B1 or BI (varied)")
        if self.kind=="cadence" and not re.fullmatch(r"[A-Ga-gIViv]+:(?:HC|IAC|PAC)",self.label):
            raise ValueError("cadence must have clean key:HC/IAC/PAC notation")


@dataclass(frozen=True)
class CadenceCheck:
    kind: str
    arrival_measure: int
    progression: bool
    dominant_root: bool
    tonic_root: bool
    soprano_degree: int | None
    phrase_boundary: bool

    def __post_init__(self):
        if self.kind not in {"HC","IAC","PAC"} or self.arrival_measure<1:
            raise ValueError("unknown cadence")
        if self.soprano_degree not in (None,1,2,3,4,5,6,7):
            raise ValueError("invalid soprano arrival degree")


@dataclass(frozen=True)
class AnnotationProof:
    annotation_id: str
    measure_start: int
    measure_end: int
    correct_label: str
    facts: tuple[ScoreFact,...]
    course_locator: str
    alternative: str
    cadence: CadenceCheck | None=None

    def __post_init__(self):
        _span(self.measure_start,self.measure_end)
        if not self.annotation_id or not self.correct_label or not self.course_locator.strip():
            raise ValueError("annotation proof needs a course reference and label")
        if not isinstance(self.facts,tuple):
            raise ValueError("evidence facts must be immutable")


@dataclass(frozen=True)
class IntentionalError:
    annotation_id: str
    submitted_label: str
    correct_label: str
    explanation: str

    def __post_init__(self):
        if not all((self.annotation_id,self.submitted_label,self.correct_label,self.explanation)):
            raise ValueError("deliberate error must disclose the location and correction")
        if self.submitted_label==self.correct_label:
            raise ValueError("the alleged deliberate error is not an error")


@dataclass(frozen=True)
class PassageCorrespondence:
    exposition: tuple[int,int]
    recapitulation: tuple[int,int]
    exposition_notes: str
    recapitulation_notes: str
    rhythm_comparison: str
    bass_comparison: str
    harmony_comparison: str
    function_comparison: str
    changes: str
    exposition_locator: str
    recapitulation_locator: str

    def __post_init__(self):
        _span(*self.exposition);_span(*self.recapitulation)
        fields=(self.exposition_notes,self.recapitulation_notes,self.rhythm_comparison,
                self.bass_comparison,self.harmony_comparison,self.function_comparison,
                self.changes,self.exposition_locator,self.recapitulation_locator)
        if not all(value.strip() for value in fields):
            raise ValueError("Crux correspondence needs actual notes and all musical comparisons")


@dataclass(frozen=True)
class SymbolicCadenceSnapshot:
    """Independent score-symbol candidate, not proof of correct OMR transcription."""
    annotation_id: str
    arrival_measure: int
    tonic_pc: int
    mode: str
    prior_dominant_root_pc: int
    arrival_root_pc: int
    arrival_bass_pc: int
    arrival_soprano_pc: int
    score_locator: str
    transcription_state: str

    def __post_init__(self):
        if not self.annotation_id or self.arrival_measure<1 or not self.score_locator.strip():
            raise ValueError("symbolic cadence requires exact independent score location")
        if self.mode not in {"major","minor"} or self.transcription_state not in {"verified","review_required"}:
            raise ValueError("invalid tonic mode or source verification state")
        for pitch_class in (self.tonic_pc,self.prior_dominant_root_pc,
                            self.arrival_root_pc,self.arrival_bass_pc,self.arrival_soprano_pc):
            if type(pitch_class) is not int or not 0<=pitch_class<=11:
                raise ValueError("symbolic pitch classes must be integers 0–11")


def _check_symbolic_snapshot(snap: SymbolicCadenceSnapshot, proof: AnnotationProof) -> list[str]:
    """Contrast independently sourced pitch classes against the author's cadence."""
    reasons=[]
    cadence=proof.cadence
    if cadence is None:
        return ["symbolic cadence snapshot supplied for non-cadence proof"]
    if snap.transcription_state!="verified":
        reasons.append("symbolic notes have not been verified against the actual score")
    if snap.arrival_measure!=cadence.arrival_measure:
        reasons.append("symbolic arrival measure disagrees with cadence annotation")
    if snap.prior_dominant_root_pc!=(snap.tonic_pc+7)%12:
        reasons.append("prior dominant root is not the expected pitch class")
    arrival_root=(snap.tonic_pc+7)%12 if cadence.kind=="HC" else snap.tonic_pc
    if snap.arrival_root_pc!=arrival_root:
        reasons.append("symbolic arrival chord does not match cadence function")
    if snap.arrival_bass_pc!=arrival_root:
        reasons.append("symbolic bass contradicts required root-position cadence arrival")
    if cadence.kind=="PAC" and snap.arrival_soprano_pc!=snap.tonic_pc:
        reasons.append("symbolic soprano does not reach tonic in PAC")
    if cadence.kind=="IAC" and snap.arrival_soprano_pc!=(
            snap.tonic_pc+(4 if snap.mode=="major" else 3))%12:
        reasons.append("symbolic soprano does not reach third in IAC")
    return reasons


def _check_cadence(cadence: CadenceCheck | None, correct_label: str, final: int) -> list[str]:
    if not re.fullmatch(r"[A-Ga-gIViv]+:(?:HC|IAC|PAC)",correct_label):
        return ["correct cadence reading must be a clean key-prefixed label"]
    expected=correct_label.rsplit(":",1)[-1]
    if cadence is None:
        return ["no independent cadence structure supplied"]
    issues=[]
    if cadence.kind!=expected or cadence.arrival_measure!=final:
        issues.append("cadence kind or arrival measure disagrees with proof")
    if not all((cadence.progression,cadence.dominant_root,cadence.phrase_boundary)):
        issues.append("cadential progression/root-position dominant/formal boundary not all supported")
    if expected=="HC" and cadence.tonic_root:
        issues.append("HC cannot claim tonic as its final chord")
    if expected in {"PAC","IAC"}:
        if not cadence.tonic_root or cadence.soprano_degree!=(1 if expected=="PAC" else 3):
            issues.append("authentic-cadence tonic root or soprano arrival is unsupported")
    return issues


def audit_assignment(
    marks: Sequence[ScoreMark],
    proofs: Sequence[AnnotationProof],
    requirements: dict[str,bool],
    completed: dict[str,bool],
    *,
    correspondences: Sequence[PassageCorrespondence]=(),
    errors: Sequence[IntentionalError]=(),
    symbolic_snapshots: Sequence[SymbolicCadenceSnapshot]=(),
) -> dict:
    """Independently check the authored ledger; NOT a claim of perceptual musical review."""
    problems=[]
    ids=[m.annotation_id for m in marks]
    proof_ids=[p.annotation_id for p in proofs]
    error_ids=[e.annotation_id for e in errors]
    if len(set(ids))!=len(ids): problems.append("duplicate visible annotation identifiers")
    if len(set(proof_ids))!=len(proof_ids): problems.append("duplicate proof identifiers")
    if len(set(error_ids))!=len(error_ids): problems.append("duplicate error-register identifiers")
    if set(ids)!=set(proof_ids):
        problems.append("score markings and self-proof identifiers disagree")
    if not 1<=len(errors)<=3:
        problems.append("standing rule requires 1–3 disclosed intentional errors for this assignment package")
    if set(error_ids)-set(ids):
        problems.append("intentional error register references no visible annotation")
    for name,required in requirements.items():
        if required and not completed.get(name,False):
            problems.append("missing required assignment component: "+name)
    if requirements.get("Crux",False) and not correspondences:
        problems.append("probable Crux has no direct exposition/recapitulation musical comparison")
    by_proof={p.annotation_id:p for p in proofs}
    by_error={e.annotation_id:e for e in errors}
    for mark in marks:
        proof=by_proof.get(mark.annotation_id)
        if proof is None: continue
        loc=mark.annotation_id
        if (mark.measure_start,mark.measure_end)!=(proof.measure_start,proof.measure_end):
            problems.append(loc+": measure boundaries differ from evidence")
        aspects={f.aspect for f in proof.facts}
        if len(aspects)<2:
            problems.append(loc+": fewer than two independent musical evidence aspects")
        for fact in proof.facts:
            if fact.start<proof.measure_start or fact.end>proof.measure_end:
                problems.append(loc+": evidence locator extends beyond proposed passage")
        err=by_error.get(loc)
        if err is None and mark.label!=proof.correct_label:
            problems.append(loc+": marked label differs from verified master without registered error")
        if err is not None and (mark.label!=err.submitted_label or
                                proof.correct_label!=err.correct_label):
            problems.append(loc+": intentional error register does not match the master reading")
        if mark.kind=="cadence" or proof.cadence is not None:
            if not {"bass","harmony","melody","grouping"}.issubset(aspects):
                problems.append(loc+": cadence missing bass/harmony/melody/grouping evidence")
            problems.extend(loc+": "+reason for reason in
                            _check_cadence(proof.cadence,proof.correct_label,mark.measure_end))
    snapshots={s.annotation_id:s for s in symbolic_snapshots}
    if len(snapshots)!=len(symbolic_snapshots):
        problems.append("duplicate independent symbolic snapshot identifiers")
    if set(snapshots)-set(ids):
        problems.append("symbolic snapshots refer to nonexistent annotations")
    for proof in proofs:
        snap=snapshots.get(proof.annotation_id)
        if snap is not None:
            problems.extend(proof.annotation_id+": "+reason for reason in
                            _check_symbolic_snapshot(snap,proof))
    cadence_ids={p.annotation_id for p in proofs if p.cadence is not None}
    symbolic_state=("symbolic_consistency_only"
                    if cadence_ids and cadence_ids.issubset(snapshots) and
                    all(s.transcription_state=="verified" for s in symbolic_snapshots) and
                    not problems else "validation_unavailable")
    return {
        "structural_gate":"failed" if problems else "passed",
        "issues":problems,
        "annotations":len(marks),
        "proof_records":len(proofs),
        "intentional_error_count":len(errors),
        "correspondences_recorded":len(correspondences),
        "content_accuracy":"review_required",
        "musical_source_verification":symbolic_state,
        "note":"A matching evidence ledger is not proof that the score actually contains the claimed notes.",
    }
