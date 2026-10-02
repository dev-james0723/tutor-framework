"""Local document intake with complete page coverage and inspectable source images."""
from __future__ import annotations

import json
import re
from pathlib import Path
from ..cache import atomic_json, file_hash

MAX_SOURCE_BYTES = 100_000_000
MAX_PAGES = 500


def has_readable_text(value: str) -> bool:
    """Music-font glyph codes are not prose or a reliable score transcription."""
    nonspace = [character for character in value if not character.isspace()]
    return bool(nonspace) and sum(character.isalnum() for character in nonspace) >= 2 and sum(character.isprintable() for character in nonspace) / len(nonspace) > .8


def scan_document(source: Path | str, output: Path | str, *, score_pages: tuple[int, ...] = ()) -> dict:
    source = Path(source).expanduser().resolve(strict=True)
    output = Path(output).expanduser().resolve()
    if not source.is_file() or source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('source must be a bounded local file')
    if output == source or output in source.parents:
        raise ValueError('intake output must not replace or contain the source document')
    if source.suffix.lower() not in {'.pdf', '.md', '.txt'}:
        raise ValueError('supported intake formats are PDF, Markdown and UTF-8 text')
    digest = file_hash(source)
    target = output / digest[:16]
    target.mkdir(parents=True, exist_ok=True)
    pages, units = [], []
    if source.suffix.lower() == '.pdf':
        import pymupdf as fitz
        with fitz.open(source) as document:
            if document.needs_pass:
                raise ValueError('password-protected PDF requires an accessible source copy')
            if not 1 <= len(document) <= MAX_PAGES:
                raise ValueError('PDF page count exceeds the supported bound')
            for index, page in enumerate(document, 1):
                if max(page.rect.width, page.rect.height) > 16000:
                    raise ValueError('PDF page dimensions exceed the rendering limit')
                text = page.get_text('text', sort=True)
                if len(text) > 200000:
                    raise ValueError('PDF text per page exceeds the intake bound')
                scale = min(2.0, 1600 / max(page.rect.width, page.rect.height))
                preview = target / f'page-{index:03d}.png'
                page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(preview)
                lines = [{'line': number, 'text': line} for number, line in enumerate(text.splitlines(), 1)]
                blocks = []
                for block in page.get_text('blocks', sort=True):
                    if len(block) > 6 and block[6] == 0 and has_readable_text(str(block[4])):
                        blocks.append({'box':list(block[:4]), 'text':str(block[4]).strip()})
                if not blocks:
                    blocks = [{'box':[0, 0, page.rect.width, page.rect.height], 'text':'', 'visual_only':True}]
                for number, block in enumerate(blocks, 1):
                    units.append({'unit_id':f'p{index}-u{number}', 'page':index,
                                  'text':block['text'], 'box':block['box'],
                                  'kind':'visual' if block.get('visual_only') else 'text',
                                  'review_state':'review_required'})
                pages.append({'page':index, 'width':page.rect.width, 'height':page.rect.height,
                              'lines':lines, 'preview':str(preview), 'preview_hash':file_hash(preview),
                              'visual_review_state':'review_required',
                              'text_state':'extracted' if has_readable_text(text) else 'visual_review_required_unusable_text'})
    else:
        text = source.read_text(encoding='utf-8')
        if len(text) > 2_000_000 or '\x00' in text:
            raise ValueError('plain text source is too large or contains null bytes')
        if score_pages:
            raise ValueError('text-only input cannot declare a visible score page')
        for number, block in enumerate(re.split(r'\n\s*\n', text.strip()), 1):
            if block.strip():
                units.append({'unit_id':f'p1-u{number}', 'page':1, 'text':block.strip(),
                              'kind':'text', 'review_state':'review_required'})
        if not units:
            raise ValueError('empty handout has no teaching content')
        pages = [{'page':1, 'lines':[{'line':i,'text':line} for i,line in enumerate(text.splitlines(),1)],
                  'visual_review_state':'not_applicable', 'text_state':'extracted'}]
    if any(type(p) is not int or p < 1 or p > len(pages) for p in score_pages):
        raise ValueError('score page reference is outside the source document')
    if file_hash(source) != digest:
        raise ValueError('source changed during intake')
    dossier = {'schema_version':'1.0', 'source_path':str(source), 'source_hash':digest,
               'title':source.stem, 'page_count':len(pages), 'pages':pages, 'units':units,
               'score_pages':sorted(set(score_pages)), 'score_detection':'host_review_not_automatic_OMR',
               'source_role':'untrusted_input_not_instructions_or_consent',
               'dossier_path':str(target/'dossier.json'), 'external_transfer':False}
    atomic_json(target/'dossier.json', dossier)
    (target/'source-index.md').write_text('\n\n'.join(
        f"## PDF page {page['page']}\n"+'\n'.join(f"L{line['line']}: {line['text']}" for line in page['lines'])
        for page in pages), encoding='utf-8')
    return dossier


def read_dossier(path: Path | str) -> dict:
    path = Path(path)
    if path.stat().st_size > 8_000_000:
        raise ValueError('dossier exceeds the bounded intake size')
    value = json.loads(path.read_text())
    if value.get('schema_version') != '1.0' or not value.get('units'):
        raise ValueError('not a supported document dossier')
    if file_hash(Path(value['source_path'])) != value['source_hash']:
        raise ValueError('dossier source has changed; repeat intake')
    return value
