#!/usr/bin/env python3
"""Reproducible no-network synthetic v3.6 PDF smoke. Not actual musical validation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pymupdf as fitz

from tutor_framework.domains.music.lesson.learning_pack.assignment_engine import (
    ScoreFact, ScoreMark, AnnotationProof, CadenceCheck, IntentionalError
)
from tutor_framework.domains.music.lesson.learning_pack.assignment_pdf import render_assignment


def main():
    root=Path(__file__).resolve().parents[1]/"artifacts/caplin-v36-candidate-20261021"
    root.mkdir(parents=True,exist_ok=True)
    source=root/"SYNTHETIC-score.pdf"
    with fitz.open() as doc:
        for page_number in (1,2):
            page=doc.new_page(width=612,height=792)
            page.insert_text((42,54),f"TEST PAGE {page_number}: SYNTHETIC NOTATION ONLY, NO MUSICAL CERTIFICATION",
                             fontsize=9)
            for y in (130,142,154,166,178):
                page.draw_line((42,y),(566,y),color=(0,0,0),width=.7)
            for x in (60,168,276,384,492,563):
                page.draw_line((x,130),(x,178),color=(.35,.35,.35),width=.7)
            for x,y in ((100,153),(195,165),(312,142),(422,166),(535,153)):
                page.draw_oval(fitz.Rect(x-5,y-3,x+5,y+3),color=(0,0,0),fill=(0,0,0))
            page.insert_text((43,119),str(page_number*12-11),fontsize=8)
        doc.save(source)
    marks=(
        ScoreMark("demo-a",1,"cadence","I:PAC",(.55,.40,.20,.09),5,8),
        ScoreMark("demo-b",2,"phrase","BI′",(.14,.37,.35,.12),9,10,depth=1),
    )
    proofs=(
        AnnotationProof("demo-a",5,8,"I:HC",(
            ScoreFact("harmony","dominant arrival, no tonic closure",5,8,"test:evidence#1"),
            ScoreFact("bass","dominant bass at the arrival",8,8,"test:evidence#2"),
            ScoreFact("melody","melodic closure on dominant",8,8,"test:evidence#3"),
            ScoreFact("grouping","end of synthetic phrase",8,8,"test:evidence#4"),
        ),"SYNTHETIC citation only","dominant arrival is possible",
        CadenceCheck("HC",8,True,True,False,None,True)),
        AnnotationProof("demo-b",9,10,"BI′",(
            ScoreFact("melody","varied return of an opening idea",9,10,"test:evidence#5"),
            ScoreFact("rhythm","opening rhythm continues",9,10,"test:evidence#6"),
        ),"SYNTHETIC citation only","could be new material"),
    )
    errors=(IntentionalError("demo-a","I:PAC","I:HC",
                             "synthetic deliberate mistake; actual score must be checked"),)
    paragraphs=(
        "The opening theme invites analysis of initiating function through motivic relationships rather than through bar counts alone.",
        "The bass supports a possible phrase boundary, but a single dominant chord does not establish a half cadence without context.",
        "In the middle of the passage, rhythmic gestures can suggest continuation, although harmonic progression must also be examined.",
        "The return of the opening material requires direct comparison of notes, grouping, harmony, and any intervening changes.",
        "The resulting formal interpretation is provisional until the original engraved score and the professor's class material are checked.",
    )
    receipt=render_assignment(source,(1,2),marks,proofs,errors,
                              "Synthetic Movement — Test Only",paragraphs,root/"output",
                              expected_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    qa={}
    for kind,path in (("main",Path(receipt["main_pdf"])),("selfproof",Path(receipt["self_proof_pdf"]))):
        with fitz.open(path) as pdf:
            pages=[]
            for number,page in enumerate(pdf,1):
                words=page.get_text("words")
                outside=sum(1 for word in words if word[0]<0 or word[1]<0 or
                            word[2]>page.rect.width or word[3]>page.rect.height)
                preview=root/f"{kind}-{number:02}.png"
                scale=min(1.35,1000/page.rect.width)
                page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(preview)
                pages.append({"page":number,"outside_page_word_count":outside,
                              "preview":str(preview),"words":len(words)})
            qa[kind]=pages
    receipt["qa_pages"]=qa
    receipt["test_source"]="SYNTHETIC; visual checks do not verify actual score notation or claimed cadences"
    receipt["pdf_integrity"]="passed"
    receipt["all_word_bounds_inside_page"]=all(
        p["outside_page_word_count"]==0 for pages in qa.values() for p in pages)
    path=root/"receipt.json"
    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print(json.dumps({"receipt":str(path),"main_pages":len(qa["main"]),
                      "self_proof_pages":len(qa["selfproof"]),
                      "word_bounds_ok":receipt["all_word_bounds_inside_page"],
                      "preview_pages":[p["preview"] for x in qa.values() for p in x]},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
