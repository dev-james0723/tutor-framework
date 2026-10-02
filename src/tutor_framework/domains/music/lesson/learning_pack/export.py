"""Local PDF export and faithful source-page annotation, with no remote dependencies."""
from __future__ import annotations

import html
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from ..cache import file_hash


@dataclass(frozen=True)
class ExportRuntime:
    node: str
    playwright: str
    chromium: str

    @classmethod
    def from_file(cls, path):
        data=json.loads(Path(path).read_text())
        if set(data) - {'node','playwright','chromium'}:
            raise ValueError('unsupported runtime settings')
        return cls(**data)

    def identity(self):
        paths={'node':Path(self.node).expanduser().resolve(strict=True),
               'playwright':Path(self.playwright).expanduser().resolve(strict=True),
               'chromium':Path(self.chromium).expanduser().resolve(strict=True)}
        package=paths['playwright']/'package.json'
        if not package.is_file() or not paths['chromium'].is_file() or not paths['node'].is_file():
            raise ValueError('existing local PDF renderer runtime is incomplete')
        return {'node':file_hash(paths['node']), 'chromium':file_hash(paths['chromium']),
                'playwright':file_hash(package), 'runner':file_hash(Path(__file__).with_name('print_pdf.cjs'))}


def print_pdf(source: Path, destination: Path, runtime: ExportRuntime) -> dict:
    runtime.identity()
    result=subprocess.run([runtime.node,str(Path(__file__).with_name('print_pdf.cjs')),
                           str(source),str(destination),runtime.playwright,runtime.chromium],
                          capture_output=True,text=True,timeout=120)
    if result.returncode:
        raise RuntimeError('Local PDF export failed: '+result.stderr[-3000:])
    import pymupdf as fitz
    with fitz.open(destination) as document:
        if not len(document) or not any(page.get_text().strip() for page in document):
            raise ValueError('PDF export is empty or lacks readable text')
        return {'pages':len(document), 'text_characters':sum(len(p.get_text()) for p in document),
                'state':'rendered_not_visually_approved'}


def annotate_score(payload: dict, score_pages: list[int], primary_source_id: str, destination: Path) -> dict:
    """Keep original vector score pages intact; draw overlays and a separate margin legend."""
    import pymupdf as fitz
    sources={source['source_id']:source for source in payload['sources']}
    source=sources[primary_source_id]
    annotations=[a for a in payload['annotations'] if a['source_id']==primary_source_id]
    if not score_pages:
        raise ValueError('no inspected score pages were declared')
    result=fitz.open();counts=[]
    with fitz.open(source['path']) as original:
        for number in score_pages:
            if not 1<=number<=len(original):
                raise ValueError('score page outside original document')
            source_page=original[number-1];width=source_page.rect.width;height=source_page.rect.height
            if source_page.rotation:
                raise ValueError('rotated score page requires an explicit coordinate normalization before annotation')
            page=result.new_page(width=width+245,height=height)
            page.show_pdf_page(fitz.Rect(0,0,width,height),original,number-1)
            page.draw_line((width+8,22),(width+8,height-22),color=(.7,.79,.75),width=.8)
            header='<b>'+html.escape(payload.get('product_name','CAPLIN'))+f' / SCORE STUDY</b><br>Source PDF page {number}<br>'+html.escape(payload['answer_policy'])
            page.insert_htmlbox(fitz.Rect(width+20,22,width+230,95),header,
                                css='* {font-family:sans-serif;font-size:10pt;color:#2b5148;}')
            current=105
            items=sorted((a for a in annotations if a['page']==number),key=lambda a:a['box'][1])
            for index,annotation in enumerate(items,1):
                x,y,w,h=annotation['box'];rect=fitz.Rect(x*width,y*height,(x+w)*width,(y+h)*height)
                page.draw_rect(rect,color=(.19,.50,.42),width=1.1,overlay=True)
                page.insert_text((10,rect.y0+9),str(index),fontsize=8,color=(.19,.50,.42),overlay=True)
                page.draw_line((rect.x1,rect.y0),(width+14,rect.y0),color=(.5,.66,.58),width=.6,overlay=True)
                current=max(current,rect.y0)
                text='<b>'+str(index)+'. '+html.escape(annotation['label'])+'</b><br><span style="font-size:8pt">'+html.escape(annotation['passage_id'])+'<br>'+html.escape(annotation['evidence_state'])+'</span>'
                box=fitz.Rect(width+20,current,width+230,min(current+110,height-35))
                if box.height<65:
                    raise ValueError('too many annotations for a readable source-page legend; split the teaching passage')
                spare,scale=page.insert_htmlbox(box,text,
                    css='* {font-family:sans-serif;font-size:10pt;line-height:1.35;color:#24473e;}',scale_low=.8)
                if spare<0:
                    raise ValueError('score annotation label does not fit; shorten it or split the note')
                current+=max(80,box.height-spare+16)
            if not items:
                page.insert_htmlbox(fitz.Rect(width+20,120,width+230,240),
                    'Inspect the original score first.<br><br>Worked analytical labels are withheld in guided mode, or await source review.',
                    css='* {font-family:sans-serif;font-size:11pt;color:#39594e;}')
            counts.append({'source_page':number,'annotations':len(items),'source_geometry':'preserved_at_original_scale'})
    result.set_metadata({'title':payload['title']+' - annotated score','author':'Caplin Tutor',
                         'subject':'Source-faithful overlays; analytical interpretations retain evidence states'})
    result.save(destination,garbage=4,deflate=True);result.close()
    return {'pages':counts,'state':'rendered_not_visually_approved'}


def render_review_pages(pdf: Path, output: Path, *, max_width: int=1400) -> list[str]:
    import pymupdf as fitz
    output.mkdir(parents=True,exist_ok=True);images=[]
    with fitz.open(pdf) as document:
        for number,page in enumerate(document,1):
            scale=min(2,max_width/page.rect.width)
            destination=output/f'{pdf.stem}-{number:03d}.png'
            page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(destination)
            images.append(str(destination))
    return images
