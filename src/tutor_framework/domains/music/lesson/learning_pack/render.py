"""Pure, deterministic presentation. Filter answers BEFORE constructing any artifact."""
from __future__ import annotations
import html
from .models import LearningBrief, PackContent, SECTIONS

NAMES = {
 'assignment_decoder':('Assignment decoder','功課解讀'), 'objectives':('Learning objectives','學習目標'),
 'passage_analysis':('Passage-by-passage analysis','逐段樂譜分析'), 'formal_map':('Formal hierarchy','曲式層次'),
 'listening_guide':('Purposeful listening','聆聽指引'), 'concepts':('Concept notes','核心概念'),
 'evidence':('Evidence ledger','論點與證據'), 'alternatives':('Alternative readings','其他合理讀法'),
 'course':('Course and theory connections','課堂與理論連結'), 'context':('History and music literature','歷史與音樂文獻'),
 'comparisons':('Controlled musical comparisons','對照音樂例子'), 'practice':('Practice and retrieval','練習與回想'),
 'transfer':('Transfer to different material','遷移練習'), 'takeaway':('Final takeaway','重點總結')}


def payload_for(brief: LearningBrief, content: PackContent) -> dict:
    if not brief.confirmed:
        raise ValueError('production requires confirmed learning intent')
    show = brief.answers_visible
    blocks = [block.to_dict() for block in content.blocks if show or not block.answer_bearing]
    visible = {block['block_id'] for block in blocks}
    practice = []
    for item in content.practice:
        entry = {'item_id':item.item_id, 'prompt':item.prompt, 'passage_ids':item.passage_ids,
                 'transfer_from':item.transfer_from, 'citations':[c.to_dict() for c in item.citations]}
        if show:
            entry.update(answer=item.answer, rationale=item.rationale, answer_state=item.answer_state)
        else:
            entry.update(answer_state='withheld_by_policy')
        practice.append(entry)
    # Do not embed hidden answers in data attributes, comments, sidecars or HTML source.
    nodes = [node.to_dict() for node in content.form if show or not node.answer_bearing]
    node_ids = {node['node_id'] for node in nodes}
    nodes = [node for node in nodes if not node['parent_id'] or node['parent_id'] in node_ids]
    coverage = [{'unit_id':item.unit_id, 'block_ids':[bid for bid in item.block_ids if bid in visible],
                 'state':'unresolved' if item.unresolved else 'covered' if set(item.block_ids)&visible else 'withheld_by_policy',
                 'reason':item.unresolved} for item in content.coverage]
    return {'title':content.title, 'brief':brief.to_dict(), 'blocks':blocks, 'practice':practice,
            'passages':[p.to_dict() for p in content.passages],
            'annotations':[a.to_dict() for a in content.annotations if show or not a.answer_bearing],
            'form':nodes, 'sources':[s.to_dict() for s in content.sources], 'coverage':coverage,
            'answer_policy':'visible_with_evidence_limits' if show else 'withheld_until_explicit_reveal',
            'video_source_id':content.video_source_id if show else ''}


def esc(value):
    return html.escape(str(value), quote=True)


def heading(section, language):
    names=NAMES[section]
    return names[0] if language=='en' else names[1] if language=='zh-Hant' else names[1]+' / '+names[0]


def citation_text(citation, sources):
    source=sources[citation['source_id']]
    location=citation['locator']
    if citation['page']: location+=' | PDF p. '+str(citation['page'])
    if citation['line_start']:location+=f" | lines {citation['line_start']}-{citation['line_end'] or citation['line_start']}"
    return source['title']+' — '+location


STYLE = '''
@page { size: A4; margin: 19mm 18mm 20mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "PingFang TC", "Noto Sans CJK TC", sans-serif; color:#203b3a; margin:0; font-size:10.5pt; line-height:1.55; background:#fff; }
main { max-width:920px; margin:auto; }
header { border-top:8px solid #25685e; padding-top:20px; margin-bottom:28px; }
.kicker { font-size:10pt; font-weight:700; letter-spacing:2px; color:#50726a; }
h1 { font-size:28pt; line-height:1.2; margin:12px 0; }
h2 { font-size:17pt; line-height:1.25; margin:28px 0 13px; border-bottom:1px solid #b8d1ca; padding-bottom:8px; break-after:avoid; }
h3 { font-size:12pt; line-height:1.4; margin:0 0 8px; break-after:avoid; }
p { margin:7px 0; orphans:3; widows:3; overflow-wrap:anywhere; }
.note { padding:13px 15px; margin:12px 0; background:#f4f8f5; border-left:3px solid #689c8d; break-inside:avoid; }
.meta,.citation { font-size:8.5pt; color:#526a66; }
.tag { font-size:8pt; border:1px solid #c6d8d2; border-radius:3px; padding:2px 6px; display:inline-block; margin:0 4px 6px 0; }
.notice { border:1px solid #c8d6d1; padding:12px 15px; background:#fff9eb; }
.answer { padding:10px 12px; border-left:3px solid #b47b47; }
.coverage { width:100%; border-collapse:collapse; font-size:8.5pt; }
th,td { padding:6px 8px; border-bottom:1px solid #dce7e2; text-align:left; vertical-align:top; }
.details { padding:10px 14px; margin:8px 0; border:1px solid #c6d8d2; }
a { color:#286f68; overflow-wrap:anywhere; }
svg { display:block; max-width:100%; height:auto; }
@media screen { body { background:#edf2ef; padding:30px; } main { background:white; padding:35px; border-radius:12px; } }
@media print { .screen-only { display:none; } a { text-decoration:none; } }
'''


def document_html(title, body, *, language='en'):
    return ('<!doctype html><html lang="'+('zh-Hant' if language!='en' else 'en')+'"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:">'
            '<title>'+esc(title)+'</title><style>'+STYLE+'</style></head><body><main>'+body+'</main></body></html>')


def form_svg(nodes):
    if not nodes: return ''
    levels={'movement':0,'section':1,'theme':2,'phrase':3,'idea':4}
    height=70*len(nodes)+20
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {height}" role="img" aria-label="Formal hierarchy">']
    for index,node in enumerate(nodes):
        x=20+levels[node['level']]*55; y=15+index*70
        parts.append(f'<rect x="{x}" y="{y}" width="{760-x}" height="54" rx="8" fill="#edf5f0" stroke="#8aafa1"/>')
        label=node['level'].upper()+' | '+node['label']
        parts.append(f'<text x="{x+14}" y="{y+23}" font-size="15" fill="#203b3a">{esc(label[:85])}</text>')
        parts.append(f'<text x="{x+14}" y="{y+43}" font-size="12" fill="#526a66">{esc(", ".join(node["passage_ids"]))}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def notes_html(payload, *, only_sections=None, compact=False):
    language=payload['brief']['language']; sources={s['source_id']:s for s in payload['sources']}
    blocks=payload['blocks']; selected=set(only_sections or SECTIONS)
    body=['<header><div class="kicker">'+esc(payload.get('product_name','CAPLIN'))+' / LEARNING PACK</div><h1>'+esc(payload['title'])+'</h1>',
          '<p class="meta">'+esc(payload['brief']['goal'])+' · '+esc(payload['brief']['help_mode'])+' · '+esc(payload['brief']['depth'])+'</p></header>']
    if payload['answer_policy'].startswith('withheld'):
        body.append('<div class="notice">Guided study: worked answers and analytical score labels are withheld. Ask to reveal them when you are ready.</div>')
    if payload['form'] and ('formal_map' in selected or only_sections is None):
        body.append('<h2>'+esc(heading('formal_map',language))+'</h2>'+form_svg(payload['form']))
    for section in SECTIONS:
        group=[block for block in blocks if block['section']==section]
        if section not in selected or not group:continue
        body.append('<h2>'+esc(heading(section,language))+'</h2>')
        for block in group:
            body.append('<article class="note"><h3>'+esc(block['title'])+'</h3><div><span class="tag">'+esc(block['claim_kind'])+'</span><span class="tag">'+esc(block['evidence_state'])+'</span></div>')
            if block['passage_ids']:body.append('<p class="meta">'+esc(' · '.join(block['passage_ids']))+'</p>')
            for paragraph in block['body'].split('\n\n'):
                body.append('<p>'+esc(paragraph).replace('\n','<br>')+'</p>')
            if block['listening_relevance']:
                body.append('<p><strong>Why this matters here:</strong> '+esc(block['listening_relevance'])+'</p>')
            for cite in block['citations']:body.append('<p class="citation">Source: '+esc(citation_text(cite,sources))+'</p>')
            body.append('</article>')
    if not compact and payload['practice'] and (only_sections is None or {'practice','transfer'} & selected):
        body.append('<h2>'+esc(heading('practice',language))+'</h2>')
        for index,item in enumerate(payload['practice'],1):
            body.append('<article class="note"><h3>'+str(index)+'. '+esc(item['prompt'])+'</h3>')
            if item['transfer_from']:body.append('<p class="meta">Transfer: '+esc(item['transfer_from'])+' → '+esc(', '.join(item['passage_ids']))+'</p>')
            if 'answer' in item:
                body.append('<div class="answer"><p>'+esc(item['answer'])+'</p><p>'+esc(item['rationale'])+'</p><p class="meta">'+esc(item['answer_state'])+'</p></div>')
            else:body.append('<p>Listen / inspect → make a claim → cite the evidence → request the explanation.</p>')
            body.append('</article>')
    if not compact and only_sections is None:
        body.append('<h2>Coverage and source register</h2><table class="coverage"><thead><tr><th>Source unit</th><th>Status</th><th>Notes</th></tr></thead><tbody>')
        for item in payload['coverage']:
            body.append('<tr><td>'+esc(item['unit_id'])+'</td><td>'+esc(item['state'])+'</td><td>'+esc(item['reason'] or ', '.join(item['block_ids']))+'</td></tr>')
        body.append('</tbody></table>')
        for source in payload['sources']:
            body.append('<p class="citation"><strong>'+esc(source['source_id'])+' · '+esc(source['title'])+'</strong><br>'+esc(source['rights'])+'<br>SHA-256 '+esc(source['content_hash'])+'</p>')
    return document_html(payload['title'],''.join(body),language=language)


def notes_markdown(payload, *, sections=None):
    sources={s['source_id']:s for s in payload['sources']}
    lines=['# '+payload['title'],'',f"Purpose: {payload['brief']['goal']} | Mode: {payload['brief']['help_mode']}",'',
           'Answer policy: '+payload['answer_policy'],'']
    selected=set(sections or SECTIONS)
    for section in SECTIONS:
        group=[b for b in payload['blocks'] if b['section']==section]
        if section not in selected or not group:continue
        lines+=['## '+heading(section,payload['brief']['language']),'']
        for block in group:
            lines+=['### '+block['title'],'',block['body'],'',
                    '**Evidence type:** '+block['claim_kind']+'; **state:** '+block['evidence_state'],
                    '**Passages:** '+(', '.join(block['passage_ids']) or 'concept-level'),'']
            if block['listening_relevance']:lines+=['Why this matters here: '+block['listening_relevance'],'']
            for cite in block['citations']:lines+=['Source: '+citation_text(cite,sources),'']
    return '\n'.join(lines)+'\n'
