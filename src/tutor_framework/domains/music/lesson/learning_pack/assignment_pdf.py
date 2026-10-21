"""V3.6 candidate: faithful, margin-safe annotated score + essay and separate self-proof.

Nothing in this exporter parses real notes, approves a musical interpretation, or
overwrites a submitted source. Distinct return states intentionally remain pending
perceptual and visual review until an independent reviewer completes them.
"""
from __future__ import annotations
import hashlib
import html
import re
from pathlib import Path
from typing import Sequence

from .assignment_engine import (
    ScoreMark, AnnotationProof, IntentionalError, PassageCorrespondence, audit_assignment,
)

PAGE_CSS = """
* {font-family: serif; font-size:11pt; line-height:1.5; color:#202020;}
h1 {font-family:sans-serif; font-size:18pt; line-height:1.25;}
h2 {font-family:sans-serif; font-size:12pt; margin:0;}
b {font-weight:bold;}
"""
COLORS = {"cadence":(0.78,0.20,0.18), "phrase":(0.08,0.49,0.51),
          "idea":(0.08,0.49,0.51),"section":(0.20,0.37,0.73)}


def _new_text_page(doc):
    return doc.new_page(width=612,height=792)


def _text_pdf(title: str, sections: Sequence[str]):
    """Paginate whole paragraphs/records at 11pt without squeezing to fit."""
    import pymupdf as fitz
    document=fitz.open()
    page=_new_text_page(document)
    heading="<h1>"+html.escape(title)+"</h1>"
    spare,scale=page.insert_htmlbox(fitz.Rect(50,54,562,122),heading,css=PAGE_CSS,scale_low=1)
    if spare<0 or scale!=1:
        raise ValueError("PDF title cannot fit at intended font size")
    top=124
    for section in sections:
        text="<p>"+html.escape(section).replace("\n","<br>")+"</p>"
        inserted=False
        for _ in range(2):
            if top>=690:
                page=_new_text_page(document); top=64
            area=fitz.Rect(50,top,562,745)
            spare,scale=page.insert_htmlbox(area,text,css=PAGE_CSS,scale_low=1)
            if spare>=0 and scale==1:
                top=745-spare+15
                inserted=True
                break
            page=_new_text_page(document);top=64
        if not inserted:
            document.close()
            raise ValueError("An essay paragraph or proof record exceeds one readable PDF page")
    return document


def _score_pdf(source: Path, pages: Sequence[int], marks: Sequence[ScoreMark]):
    import pymupdf as fitz
    result=fitz.open();placements=[]
    with fitz.open(source) as original:
        if original.needs_pass:
            raise ValueError("encrypted scores require source access")
        for number in pages:
            if type(number) is not int or not 1<=number<=len(original):
                raise ValueError("requested score page is absent")
            source_page=original[number-1]
            if source_page.rotation:
                raise ValueError("rotated score requires normalized coordinates")
            width,height=source_page.rect.width,source_page.rect.height
            # Preserve original notation pixel-for-pixel; additional area is a margin.
            output=result.new_page(width=width+240,height=height)
            output.show_pdf_page(fitz.Rect(0,0,width,height),original,number-1)
            output.draw_line((width+8,12),(width+8,height-12),color=(0.72,0.72,0.72),width=.5)
            entries=[m for m in marks if m.page==number]
            obstacles=[fitz.Rect(b[:4]) for b in source_page.get_text("blocks") if len(b)>=4]
            obstacles.extend(fitz.Rect(d["rect"]) for d in source_page.get_drawings())
            lane_y=26
            placed_overlays=[]
            for mark in sorted(entries,key=lambda m:(m.box[1],m.depth,m.annotation_id)):
                x,y,w,h=mark.box
                rect=fitz.Rect(x*width,y*height,(x+w)*width,(y+h)*height)
                color=COLORS[mark.kind]
                if lane_y+62>height-18:
                    result.close()
                    raise ValueError("margin overflow: divide dense score or enlarge the page")
                # Use clean labels, printed measures from the proof, no invented counters.
                label=html.escape(mark.label)
                meta=html.escape(f"mm. {mark.measure_start}–{mark.measure_end}")
                item=f'<b>{label}</b><br><span style="font-size:8pt">{meta}</span>'
                spare,scale=output.insert_htmlbox(
                    fitz.Rect(width+19,lane_y,width+224,lane_y+53),item,
                    css="* {font-family:sans-serif;font-size:10pt;line-height:1.2;}",
                    scale_low=1)
                if spare<0 or scale!=1:
                    result.close()
                    raise ValueError("margin annotation cannot fit at readable size")
                output.draw_line((width+17,lane_y),(width+17,lane_y+49),color=color,width=2)
                route="gutter"
                # A formal bracket enters the source only if the original engraved
                # score and text leave a certified empty corridor above the target.
                if mark.kind in {"phrase","idea","section"}:
                    y_line=rect.y0-14-12*mark.depth
                    corridor=fitz.Rect(rect.x0-2,y_line-4,rect.x1+2,y_line+8)
                    clear=(corridor.y0>=12 and corridor.x0>=8 and
                           corridor.x1<=width-8 and not any(
                                corridor.intersects(obstacle) for obstacle in obstacles+placed_overlays))
                    if clear:
                        output.draw_polyline([(rect.x0,y_line+6),(rect.x0,y_line),
                                              (rect.x1,y_line),(rect.x1,y_line+6)],
                                             color=color,width=1.2)
                        placed_overlays.append(corridor)
                        route="clear-source-bracket"
                elif mark.kind=="cadence":
                    # Never put a cadence box over notes. A safe empty corridor
                    # may surround the box; otherwise the red margin card is the mark.
                    proposal=fitz.Rect(rect.x0,rect.y0-25,rect.x0+83,rect.y0-6)
                    clear=(proposal.y0>=12 and proposal.x1<=width-8 and
                           not any(proposal.intersects(o) for o in obstacles+placed_overlays))
                    if clear:
                        output.draw_rect(proposal,color=color,width=1.2)
                        output.insert_text((proposal.x0+3,proposal.y1-5),
                                           mark.label,fontsize=9,color=color)
                        placed_overlays.append(proposal)
                        route="clear-source-cadence-box"
                placements.append({"id":mark.annotation_id,"page":number,"route":route,
                                   "margin_y":lane_y,"source_box":tuple(rect)})
                lane_y+=65
    result.set_metadata({"title":"Evidence-driven score annotation",
                         "subject":"Original score preserved; margin markers and cautious clear-space overlays"})
    return result,placements


def render_assignment(
    source_pdf: str | Path, score_pages: Sequence[int], marks: Sequence[ScoreMark],
    proofs: Sequence[AnnotationProof], errors: Sequence[IntentionalError],
    essay_title: str, essay_paragraphs: Sequence[str], output: str | Path,
    *, expected_source_sha256: str,
    requirements: dict[str,bool] | None=None,
    completed: dict[str,bool] | None=None,
    correspondences: Sequence[PassageCorrespondence]=(),
) -> dict:
    """Build two independent PDFs only after structural gates pass."""
    import pymupdf as fitz
    source=Path(source_pdf).resolve(strict=True)
    if source.suffix.lower()!=".pdf":
        raise ValueError("source score must be an existing PDF")
    if not re.fullmatch("[0-9a-fA-F]{64}",expected_source_sha256):
        raise ValueError("source revision SHA-256 is required")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected_source_sha256.lower():
        raise ValueError("source score has changed since evidence was collected")
    if len(essay_paragraphs) not in (5,6) or not all(p.strip() for p in essay_paragraphs):
        raise ValueError("default assignment essay needs five or six substantive paragraphs")
    if not essay_title.strip():
        raise ValueError("the essay needs a piece-name title")
    if set(m.page for m in marks)-set(score_pages):
        raise ValueError("a mark references a non-exported score page")
    checklist={"Essay":True} if requirements is None else dict(requirements)
    checklist["Essay"]=True
    completed_steps={"Essay":True} if completed is None else dict(completed)
    completed_steps["Essay"]=True
    report=audit_assignment(marks,proofs,checklist,completed_steps,
                            correspondences=correspondences,errors=errors)
    if report["structural_gate"]!="passed":
        raise ValueError("assignment evidence gate failed: "+"; ".join(report["issues"]))
    target=Path(output).expanduser().resolve()
    if target==source.parent or source in target.parents or target==source:
        raise ValueError("never write exports on top of or inside the source path")
    target.mkdir(parents=True,exist_ok=True)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    score,placements=_score_pdf(source,score_pages,marks)
    essay=None;selfproof=None
    try:
        essay=_text_pdf(essay_title,essay_paragraphs)
        corrections={error.annotation_id:error for error in errors}
        proof_sections=[
            "Independent proof ledger — this audit describes recorded evidence; "
            "actual musical review of the engraved score remains required."
        ]
        for proof in proofs:
            mark=next(m for m in marks if m.annotation_id==proof.annotation_id)
            lines=[
                f"{proof.annotation_id} — mm. {proof.measure_start}–{proof.measure_end}: {mark.label}",
                "Master reading: "+proof.correct_label,
                "Professor course source: "+proof.course_locator,
                *("Evidence / "+f.aspect+": "+f.description+" ("+f.score_locator+")" for f in proof.facts),
                "Alternative: "+(proof.alternative or "none asserted"),
            ]
            if proof.cadence is not None:
                lines.append(f"Cadence check: {proof.cadence.kind} at m. {proof.cadence.arrival_measure}; "
                             f"progression={proof.cadence.progression}, dominant-root={proof.cadence.dominant_root}, "
                             f"tonic-root={proof.cadence.tonic_root}, soprano={proof.cadence.soprano_degree}, "
                             f"formal-boundary={proof.cadence.phrase_boundary}")
            if proof.annotation_id in corrections:
                error=corrections[proof.annotation_id]
                lines.append("INTENTIONAL ERROR — "+error.explanation)
                lines.append("Corrected label: "+error.correct_label)
            proof_sections.append("\n".join(lines))
        if requirements is not None:
            proof_sections.append("Assignment checklist (caller-provided, not independently "
                                  "parsed from the original assignment sheet): "
                                  +"; ".join(name+": "+(
                                      "recorded complete" if completed_steps.get(name,False)
                                      else "not complete") for name,needed in checklist.items() if needed))
        for index,match in enumerate(correspondences,1):
            proof_sections.append(
                f"Probable Crux correspondence {index}: "
                f"exposition mm. {match.exposition[0]}–{match.exposition[1]} "
                f"↔ recapitulation mm. {match.recapitulation[0]}–{match.recapitulation[1]}\n"
                f"Exposition notes: {match.exposition_notes}; "
                f"recapitulation notes: {match.recapitulation_notes}\n"
                f"Rhythm: {match.rhythm_comparison}; bass: {match.bass_comparison}; "
                f"harmony: {match.harmony_comparison}; formal function: {match.function_comparison}\n"
                f"Alterations/insertions: {match.changes}\n"
                f"Original score locators: {match.exposition_locator}; {match.recapitulation_locator}\n"
                "Musical correspondence remains subject to independent source-score inspection.")
        selfproof=_text_pdf(essay_title+" — Independent Self-proof",proof_sections)
        main=fitz.open();main.insert_pdf(score);main.insert_pdf(essay)
        main_path=target/"annotated-score-and-essay.pdf"
        proof_path=target/"self-proof.pdf"
        main.save(main_path,garbage=4,deflate=True)
        selfproof.save(proof_path,garbage=4,deflate=True)
        main.close()
    finally:
        score.close()
        if essay is not None: essay.close()
        if selfproof is not None: selfproof.close()
    if hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash:
        raise RuntimeError("source file was changed during export")
    with fitz.open(main_path) as main,fitz.open(proof_path) as proof:
        if len(main)<=len(score_pages) or not len(proof):
            raise RuntimeError("main essay or separate proof pages missing")
        proof_text=" ".join(page.get_text() for page in proof)
        if any(e.explanation not in proof_text for e in errors):
            raise RuntimeError("intentional error explanation missing from standalone proof")
    return {
        "main_pdf":str(main_path),"self_proof_pdf":str(proof_path),
        "score_pages":len(score_pages),"annotations":len(marks),
        "intentional_error_count":len(errors),"source_sha256":source_hash,
        "structural_gate":"passed","musical_review":"review_required",
        "visual_review":"review_required","listening":"not_performed",
        "annotation_placements":placements,
        "requirement_coverage":"caller_checklist_only" if requirements is not None else "not_checked_against_source",
        "correspondences_recorded":len(correspondences),
        "note":"Export integrity is not score correctness or visual approval.",
    }
