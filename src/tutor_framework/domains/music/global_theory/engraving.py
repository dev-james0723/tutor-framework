"""Local original-score engraving reusing symbolic and MIDI verification contracts."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from tutor_framework.domains.music.lesson.symbolic import parse_score
from tutor_framework.domains.music.lesson.adapters import require_local_provider, midi_notes, compare_midi


def _portable_svg(svg: str) -> str:
    """Expand internal glyph references for PDF renderers lacking nested SVG support."""
    import copy
    import xml.etree.ElementTree as ET
    namespace = '{http://www.w3.org/2000/svg}'
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    root = ET.fromstring(svg)
    definitions = {node.get('id'): node for node in root.iter() if node.get('id')}
    for parent in list(root.iter()):
        for index, child in enumerate(list(parent)):
            if child.tag == namespace + 'use':
                href = child.get('{http://www.w3.org/1999/xlink}href', child.get('href', ''))
                if not href.startswith('#') or href[1:] not in definitions:
                    raise ValueError('engraving has an unresolved glyph reference')
                replacement = ET.Element(namespace + 'g')
                if child.get('transform'):
                    replacement.set('transform', child.get('transform'))
                replacement.append(copy.deepcopy(definitions[href[1:]]))
                parent.remove(child); parent.insert(index, replacement)
    for child in root:
        if child.tag == namespace + 'svg':
            bounds = [float(value) for value in child.attrib.pop('viewBox').split()]
            width = float(root.get('width').removesuffix('px'))
            height = float(root.get('height').removesuffix('px'))
            child.tag = namespace + 'g'
            child.set('transform', f'scale({width/bounds[2]},{height/bounds[3]}) translate({-bounds[0]},{-bounds[1]})')
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] in {'path','ellipse','polygon','polyline','rect'}:
            node.set('stroke', 'black')
    return ET.tostring(root, encoding='unicode')


def engrave_original_score(musicxml: str, *, destination: Path | None = None,
                           title: str = "Original music-reading exercise",
                           no_save: bool = False) -> dict:
    """Render an original symbolic exercise without network or automatic persistence.

    Rendered notation and MIDI must agree with the framework's independently parsed
    event stream. This establishes consistency, not pedagogical expert approval.
    """
    if type(no_save) is not bool or (no_save and destination is not None):
        raise ValueError("no-save forbids an engraving destination")
    if not isinstance(musicxml, str) or len(musicxml.encode()) > 1_000_000:
        raise ValueError("bounded MusicXML text required")
    if any(marker in musicxml.casefold() for marker in ("<!doctype", "<!entity", "<image", "<link")):
        raise ValueError("external entities and resources are not allowed in original notation")
    if destination is not None:
        destination = Path(destination).expanduser().resolve()
        if destination.exists():
            raise ValueError("refusing to overwrite an existing score destination")
    try:
        score = parse_score(musicxml)
    except Exception as error:
        raise ValueError("original MusicXML failed symbolic validation") from error
    require_local_provider("verovio-local")
    try:
        import verovio
        import fitz
    except ImportError as error:
        raise RuntimeError("Local engraving requires the optional Verovio and PyMuPDF dependencies") from error
    toolkit = verovio.toolkit()
    toolkit.setOptions({"pageWidth": 1800, "pageHeight": 900, "scale": 60,
                        "adjustPageHeight": True, "breaks": "none", "header": "none", "footer": "none"})
    if not toolkit.loadData(musicxml) or toolkit.getPageCount() != 1:
        raise ValueError("original mini-score must produce exactly one engravable page")
    svg = _portable_svg(toolkit.renderToSVG(1))
    midi = base64.b64decode(toolkit.renderToMIDI(), validate=True)
    expected = [{"midi": event.midi, "onset": str(event.onset)} for event in score.events]
    validation = compare_midi(expected, midi_notes(midi), "120")
    if validation["state"] != "passed":
        raise ValueError("engraved MIDI disagrees with the independently parsed symbolic notes")
    with fitz.open(stream=svg.encode("utf-8"), filetype="svg") as vector:
        if len(vector[0].get_drawings()) < len(score.events) * 2:
            raise ValueError("engraving lost its visible staff or note glyphs")
        vector_pdf = vector.convert_to_pdf()
    with fitz.open(stream=vector_pdf, filetype="pdf") as source:
        with fitz.open() as document:
            page = document.new_page(width=612, height=792)
            page.insert_text((48, 54), title[:90], fontsize=16)
            page.insert_text((48, 77), "System-created original notation | Treble clef | 4/4 | Local symbolic verification", fontsize=8.5)
            page.show_pdf_page(fitz.Rect(48, 118, 564, 340), source, 0)
            page.insert_text((48, 385), "Read the pitches and trace the return to the tonic. Check the separate worked solution.", fontsize=9)
            page.insert_text((48, 408), "This is an original learning example, not an official examination paper.", fontsize=8.5)
            document.set_metadata({"title": title, "author": "Global Music Theory Super Skill"})
            pdf_bytes = document.tobytes(garbage=4, deflate=True)
    result = {"provider": "verovio-local", "provider_version": toolkit.getVersion(),
              "symbolic_pitches": [event.midi for event in score.events],
              "midi_validation": validation, "musical_expert_review": "review_required",
              "svg": svg, "pdf_bytes": pdf_bytes, "midi_bytes": midi,
              "score_region": [48 / 612, 118 / 792, 516 / 612, 222 / 792],
              "external_calls": False, "persisted": False}
    if destination is not None:
        destination.mkdir(parents=True, exist_ok=False)
        files = {"score.musicxml": musicxml.encode(), "score.svg": svg.encode(),
                 "score.pdf": pdf_bytes, "score.mid": midi}
        for name, data in files.items():
            (destination / name).write_bytes(data)
        result["artifact_hashes"] = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        result["directory"] = str(destination)
        result["persisted"] = True
    return result
