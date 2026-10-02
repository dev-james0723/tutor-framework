"""Incremental local Learning Pack production with truthful per-artifact status."""
from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path
from .models import LearningBrief, PackContent
from .render import payload_for, notes_html, notes_markdown, form_svg, document_html, esc, NAMES
from .export import ExportRuntime, print_pdf, annotate_score
from ..cache import BuildCache, atomic_json, content_hash, file_hash


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def validate_content(dossier: dict, brief: LearningBrief, content: PackContent,
                     allow_source_roots: tuple[Path, ...] = ()) -> tuple[dict[str, Path], str]:
    if not brief.confirmed or brief.source_hash != dossier['source_hash']:
        raise ValueError('learning brief is unconfirmed or belongs to a different source revision')
    primary = Path(dossier['source_path']).expanduser().resolve()
    roots = (primary.parent,) + tuple(Path(p).expanduser().resolve() for p in allow_source_roots)
    sources = {}
    primary_id = ''
    page_counts, line_counts = {}, {}
    for source in content.sources:
        path = Path(source.path).expanduser().resolve()
        if not _inside(path, roots):
            raise ValueError('content source is outside operator-authorized source roots')
        if not path.is_file() or file_hash(path) != source.content_hash:
            raise ValueError('source is missing or its content hash has changed: ' + source.source_id)
        sources[source.source_id] = path
        if path == primary and source.content_hash == dossier['source_hash']:
            primary_id = source.source_id
        if path.suffix.lower() == '.pdf':
            import pymupdf as fitz
            with fitz.open(path) as pdf:
                if pdf.needs_pass: raise ValueError('source PDF is encrypted')
                page_counts[source.source_id] = len(pdf)
        elif path.suffix.lower() in {'.md', '.txt'}:
            line_counts[source.source_id] = len(path.read_text(encoding='utf-8').splitlines())
    if not primary_id or file_hash(primary) != dossier['source_hash']:
        raise ValueError('primary source revision is not registered in the authored pack')
    units = {unit['unit_id'] for unit in dossier['units']}
    if {item.unit_id for item in content.coverage} != units:
        raise ValueError('coverage must account for every source unit exactly once')
    for block in (*content.blocks, *content.practice):
        for cite in block.citations:
            if cite.page and cite.page > page_counts.get(cite.source_id, 1):
                raise ValueError('citation points outside the source document')
            if cite.line_end and cite.line_end > line_counts.get(cite.source_id, 10**9):
                raise ValueError('citation line range is outside the source text')
    for passage in content.passages:
        if passage.page > page_counts.get(passage.source_id, 0):
            raise ValueError('passage has no corresponding source score page')
    for annotation in content.annotations:
        if annotation.page > page_counts.get(annotation.source_id, 0):
            raise ValueError('annotation is outside the source PDF')
    if set(content.visual_reviewed_pages) - set(range(1, dossier['page_count']+1)):
        raise ValueError('visual review references nonexistent source pages')
    return sources, primary_id


def _quiz(payload):
    lines=['# Practice and transfer', '', 'Answer policy: '+payload['answer_policy'], '']
    for index, item in enumerate(payload['practice'], 1):
        lines += [f"## {index}. {item['prompt']}", '', 'Passages: '+', '.join(item['passage_ids']), '']
        if item['transfer_from']:
            lines += ['Compare with: '+item['transfer_from'], '']
        if 'answer' in item:
            lines += ['**Answer:** '+item['answer'], '', '**Reasoning:** '+item['rationale'], '',
                      '**Evidence state:** '+item['answer_state'], '']
        else:
            lines += ['Make a claim and cite the visible/audible evidence. Request the worked explanation afterwards.', '']
    return '\n'.join(lines)


def _flashcards(payload):
    stream=io.StringIO(); writer=csv.writer(stream, delimiter='\t', lineterminator='\n')
    def safe(value):
        value=str(value).replace('\x00','')
        return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
    writer.writerow(['Prompt','Answer','Evidence state','Passage'])
    for item in payload['practice']:
        writer.writerow([safe(item['prompt']),safe(item.get('answer','Answer withheld until requested')),
                         item['answer_state'],', '.join(item['passage_ids'])])
    return stream.getvalue()


def _mindmap(payload):
    nodes=payload['form']; lines=['# '+payload['title'], '']
    body=['<header><div class="kicker">CAPLIN / CONCEPT MAP</div><h1>'+esc(payload['title'])+'</h1></header>',
          '<p>Expand a topic to inspect its source-grounded notes. No network connection is required.</p>']
    if nodes:
        body.append(form_svg(nodes))
        for node in nodes:
            lines += ['  '*({'movement':0,'section':1,'theme':2,'phrase':3,'idea':4}[node['level']])+'- '+node['label']]
    for section in NAMES:
        blocks=[b for b in payload['blocks'] if b['section']==section]
        if not blocks: continue
        lines += ['', '## '+NAMES[section][0]]
        body.append('<details class="details"><summary>'+esc(NAMES[section][0])+'</summary>')
        for block in blocks:
            lines += ['- '+block['title']]
            body.append('<h3>'+esc(block['title'])+'</h3><p>'+esc(block['body'])+'</p>')
        body.append('</details>')
    return '\n'.join(lines)+'\n', document_html(payload['title'],''.join(body))


def build_pack(dossier: dict, brief: LearningBrief, content: PackContent,
               output: Path | str, *, runtime: ExportRuntime | None = None,
               pdf: bool = True, allow_source_roots: tuple[Path, ...] = (), product_name: str = "CAPLIN") -> dict:
    sources, primary_id = validate_content(dossier, brief, content, allow_source_roots)
    payload = payload_for(brief, content)
    payload["product_name"] = product_name
    output = Path(output).expanduser().resolve()
    if output in sources.values() or any(output in p.parents for p in sources.values()):
        raise ValueError('output may not replace or contain an input source')
    materials=set(brief.materials)
    if pdf and materials & {'notes','cheat_sheet'} and runtime is None:
        raise ValueError('PDF requested but no trusted local PDF renderer is configured')
    artifact_names=[];pending={};states={}
    if 'notes' in materials:
        artifact_names += ['notes.md','notes.html']+(['notes.pdf'] if pdf else [])
    if 'annotated_score' in materials:
        if not dossier.get('score_pages'):
            pending['annotated_score']='No source score pages; do not invent notation for a text handout.'
        else: artifact_names.append('annotated-score.pdf')
    if 'quiz' in materials:
        if not payload['practice']:pending['quiz']='No source-grounded practice items were authored.'
        else:artifact_names.append('practice-quiz.md')
    if 'flashcards' in materials:
        if not payload['practice']:pending['flashcards']='No evidence-bearing flashcards were authored.'
        else:artifact_names.append('flashcards.tsv')
    for name,file in [('listening_guide','listening-guide.md'),('essay_outline','essay-outline.md')]:
        sections={'listening_guide'} if name=='listening_guide' else {'assignment_decoder','evidence','alternatives','takeaway'}
        if name in materials:
            if not any(b['section'] in sections for b in payload['blocks']):pending[name]='No visible content covers this selected material.'
            else:artifact_names.append(file)
    if 'cheat_sheet' in materials:
        if not any(b['section']=='takeaway' for b in payload['blocks']):
            pending['cheat_sheet']='Author a concise takeaway block before requesting a one-page sheet.'
        else: artifact_names += ['cheat-sheet.html','cheat-sheet.md']+(['cheat-sheet.pdf'] if pdf else [])
    if 'mindmap' in materials:artifact_names += ['mindmap.md','mindmap.html']
    video=payload.get('video_source_id')
    if 'video' in materials:
        artifact_names.append('video-request.json')
        if video:
            artifact_names.append('lesson.mp4')
            states['video']='reused_existing_video_not_regenerated_or_perceptually_approved'
        else:
            pending['video']='A new video renderer is not implemented by this pack exporter. Continue the existing whiteboard workflow under this confirmed brief.'
    expected=tuple(artifact_names+['learning-pack.json','qa.json'])
    engine_files={p.name:p for p in Path(__file__).parent.glob('*.py')}
    engine_files['print_pdf.cjs']=Path(__file__).with_name('print_pdf.cjs')
    inputs={**{'source-'+key:value for key,value in sources.items()},**engine_files}
    params={'pack_schema':1, 'brief':brief.to_dict(), 'visible_payload_hash':content_hash(payload),
            'source_content_hash':content_hash(content.to_dict()), 'dossier_hash':content_hash(dossier),
            'pdf':pdf, 'runtime':runtime.identity() if pdf and runtime else None}
    cache=BuildCache(output/'revisions')
    def produce(directory):
        details={}
        def write(name,value): (directory/name).write_text(value,encoding='utf-8')
        if 'notes.md' in artifact_names:
            write('notes.md',notes_markdown(payload));write('notes.html',notes_html(payload))
            if pdf:details['notes.pdf']=print_pdf(directory/'notes.html',directory/'notes.pdf',runtime)
        if 'annotated-score.pdf' in artifact_names:
            details['annotated-score.pdf']=annotate_score(payload,dossier['score_pages'],primary_id,directory/'annotated-score.pdf')
        if 'practice-quiz.md' in artifact_names:write('practice-quiz.md',_quiz(payload))
        if 'flashcards.tsv' in artifact_names:write('flashcards.tsv',_flashcards(payload))
        if 'listening-guide.md' in artifact_names:write('listening-guide.md',notes_markdown(payload,sections={'listening_guide'}))
        if 'essay-outline.md' in artifact_names:write('essay-outline.md',notes_markdown(payload,sections={'assignment_decoder','evidence','alternatives','takeaway'}))
        if 'cheat-sheet.html' in artifact_names:
            write('cheat-sheet.html',notes_html(payload,only_sections={'takeaway'},compact=True))
            write('cheat-sheet.md',notes_markdown(payload,sections={'takeaway'}))
            if pdf:
                details['cheat-sheet.pdf']=print_pdf(directory/'cheat-sheet.html',directory/'cheat-sheet.pdf',runtime)
                if details['cheat-sheet.pdf']['pages']!=1:
                    raise ValueError('one-page takeaway exceeded one page; shorten the content, not the typography')
        if 'mindmap.html' in artifact_names:
            markdown,html=_mindmap(payload);write('mindmap.md',markdown);write('mindmap.html',html)
        if 'video-request.json' in artifact_names:
            atomic_json(directory/'video-request.json',{'learning_brief':brief.to_dict(),
                        'state':states.get('video','pending_renderer'), 'source_id':video,
                        'rendered_new_video':False, 'reason':pending.get('video','Original registered video reused without changing its content.')})
        if 'lesson.mp4' in artifact_names:shutil.copyfile(sources[video],directory/'lesson.mp4')
        unresolved=[item.unit_id for item in content.coverage if item.unresolved]
        score_review=set(dossier.get('score_pages',[])).issubset(set(content.visual_reviewed_pages))
        qa={'artifact_integrity':'passed', 'coverage':'review_required' if unresolved else 'passed',
            'unresolved_units':unresolved, 'source_hashes':'passed',
            'answer_policy_enforcement':'passed', 'source_score_visual_review':'recorded_by_author' if score_review else 'review_required',
            'content_accuracy':'review_required', 'output_visual_review':'review_required',
            'video_generated':False, 'pending_materials':pending, 'exports':details,
            'note':'Successful export and author review metadata are not an independent musical or visual certification.'}
        atomic_json(directory/'qa.json',qa)
        hashes={name:file_hash(directory/name) for name in artifact_names}
        hashes['qa.json']=file_hash(directory/'qa.json')
        manifest={'schema_version':'1.0', 'learning_brief':brief.to_dict(), 'content':payload,
                  'artifact_hashes':hashes, 'pending_materials':pending, 'material_states':states,
                  'state':'built_with_pending_materials' if pending else 'built_for_review',
                  'video_generated':False, 'source_hashes':{key:file_hash(path) for key,path in sources.items()},
                  'raw_answers_embedded':brief.answers_visible, 'source_content_hash':params['source_content_hash']}
        atomic_json(directory/'learning-pack.json',manifest)
    result=cache.build('learning-pack',params,inputs,expected,produce)
    manifest=json.loads((result.directory/'learning-pack.json').read_text())
    pointer={'directory':str(result.directory),'revision':result.key,'reused':result.reused,
             'state':manifest['state'],'pending_materials':pending,'artifacts':list(manifest['artifact_hashes'])}
    atomic_json(output/'latest.json',pointer)
    return pointer


def verify_pack(directory: Path | str) -> dict:
    directory=Path(directory).resolve(); manifest=json.loads((directory/'learning-pack.json').read_text())
    failures=[]
    for name,digest in manifest['artifact_hashes'].items():
        path=(directory/name).resolve()
        if directory not in path.parents or not path.is_file() or file_hash(path)!=digest:
            failures.append(name)
    report={'artifact_integrity':'failed' if failures else 'passed','failed_artifacts':failures,
            'content_accuracy':'review_required','output_visual_review':'review_required',
            'video_generated':False,'pending_materials':manifest['pending_materials']}
    return report
