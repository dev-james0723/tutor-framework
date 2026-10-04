"""Thin adapter to deterministic authority. No network or private exam store."""
import base64
import binascii
import io
import re
import stat
import zipfile
import zlib
from importlib.resources import files
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from defusedxml.ElementTree import fromstring as safe_xml
from tutor_framework.domains.music.global_theory.context import LearnerContext
from tutor_framework.domains.music.global_theory.operations import evaluate
from tutor_framework.domains.music.global_theory.score_workflow import analyze_score, compare_curricula, reconcile_claims
from tutor_framework.domains.music.global_theory.mini_exam import build_mini_exam, solve_item
from tutor_framework.domains.music.global_theory.open_practice import build_open_practice, assess_open_response
from .schemas import TheoryContext

MAX_SCORE_BYTES = 2_000_000
OPEN_TOPICS = {"composition", "voice_leading", "form_comparison"}
SAFE_SVG_TAGS = {"svg","g","path","defs","symbol","use","text","tspan","rect","line","polyline","circle","ellipse","polygon","title","desc","style"}

def learner_context(values):
    return LearnerContext(**TheoryContext.model_validate(values).model_dump())

def operation(name, request):
    if "operation" in request.inputs:
        raise ValueError("Operation is determined by the typed endpoint")
    return evaluate({"operation":name.replace("-","_"), **request.inputs}, learner_context(request.context))

def decode_score(filename, data):
    extension = PurePosixPath(filename).suffix.lower()
    if extension not in {".xml", ".musicxml", ".mxl"}:
        raise ValueError("Upload MusicXML or MXL; PDF and image recognition are unavailable")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Invalid score encoding") from error
    if not raw or len(raw) > MAX_SCORE_BYTES:
        raise ValueError("Score must be nonempty and at most 2 MB")
    if extension != ".mxl":
        return raw
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 64 or sum(e.file_size for e in entries) > MAX_SCORE_BYTES:
                raise ValueError("MXL archive exceeds processing limit")
            names = set()
            for entry in entries:
                if entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise ValueError("Unsupported MXL compression method")
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError("Unsafe MXL archive path")
                if entry.filename in names or entry.flag_bits & 1 or entry.file_size > max(1,entry.compress_size)*100:
                    raise ValueError("Unsafe MXL duplicate, encryption, or expansion ratio")
                names.add(entry.filename)
            container = safe_xml(archive.read("META-INF/container.xml"), forbid_dtd=True)
            roots = [node for node in container.iter() if node.tag.rsplit("}",1)[-1] == "rootfile"]
            if len(roots) != 1:
                raise ValueError("MXL needs one unambiguous score root")
            name = roots[0].get("full-path", "")
            if name not in names or PurePosixPath(name).suffix.lower() not in {".xml", ".musicxml"}:
                raise ValueError("MXL root is missing or unsupported")
            return archive.read(name)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, NotImplementedError, RuntimeError, zlib.error) as error:
        raise ValueError("Invalid MXL container") from error

def sanitize_svg(svg):
    root = safe_xml(svg, forbid_dtd=True)
    for parent in root.iter():
        for child in list(parent):
            if child.tag.rsplit("}",1)[-1] not in SAFE_SVG_TAGS:
                parent.remove(child)
        for name,value in list(parent.attrib.items()):
            local = name.rsplit("}",1)[-1].lower()
            if local.startswith("on") or (local in {"href", "src"} and not value.startswith("#")) or re.search(r"url\(\s*[^#]",value,re.I):
                del parent.attrib[name]
        if parent.tag.rsplit("}",1)[-1] == "style" and re.search(r"@import|url\(\s*[^#]",parent.text or "",re.I):
            parent.text = ""
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    return ET.tostring(root, encoding="unicode")

def score(request):
    raw = decode_score(request.filename, request.data_base64)
    # Preflight before the original byte-screening parser. Defusedxml recognizes
    # encodings, so UTF-16 DTDs/entities cannot bypass this service boundary.
    # Only the engine's supported metadata-only declaration may be removed;
    # internal subsets and every other DTD remain forbidden. Nothing is fetched.
    normalized = re.sub(rb'<!DOCTYPE\s+score-partwise\s+PUBLIC\s+"[^"<>\[\]]*"\s+"[^"<>\[\]]*"\s*>',b'',raw)
    root = safe_xml(normalized, forbid_dtd=True)
    try:
        result = analyze_score(raw, source_id=request.source_id, context=learner_context(request.context))
    except ZeroDivisionError as error:
        raise ValueError("Invalid score timing fraction") from error
    if result.get("event_count",0) > 2000:
        raise ValueError("This score exceeds the 2000-event MVP processing limit")
    notes = [node for node in root.iter() if node.tag.rsplit("}",1)[-1] == "note"]
    for note,event in zip(notes,result["events"],strict=True):
        note.set("id",event["event_id"])
    import verovio
    verovio.enableLog(verovio.LOG_OFF)
    toolkit = verovio.toolkit()
    toolkit.setResourcePath(str(files('verovio') / 'data'))
    toolkit.setOptions({"pageWidth":1600,"pageHeight":2000,"scale":40,"svgViewBox":True,"breaks":"auto"})
    if not toolkit.loadData(ET.tostring(root,encoding="unicode")):
        raise ValueError("The verified renderer cannot engrave this score")
    pages = toolkit.getPageCount()
    if not 1 <= pages <= 20:
        raise ValueError("Rendered score exceeds the MVP page limit")
    result["svg_pages"] = [sanitize_svg(toolkit.renderToSVG(n)) for n in range(1,pages+1)]
    result["render_version"] = toolkit.getVersion()
    return result

def _bundle(request):
    if request.topic in OPEN_TOPICS:
        return build_open_practice(topic=request.topic, seed=request.seed)
    if request.topic != "fundamentals":
        return {"state":"unsupported","reason":"No verified original template for this topic"}
    return build_mini_exam(grade=request.grade, syllabus_id="abrsm-theory-from-2020", seed=request.seed)

def generate(request):
    bundle = _bundle(request)
    if "student_paper" not in bundle:
        return bundle
    student = bundle["student_paper"]
    opened = request.topic in OPEN_TOPICS
    item = student if opened else student["questions"][request.item_index]
    # Positive allowlist: future teacher fields cannot accidentally travel to the browser.
    fields = {"question_id","concept_id","passage_id","claim_id","competency","prompt","given","options","musicxml","response_type","origin","topic","instructions"}
    return {"state":"original_practice_available", "item":{k:v for k,v in item.items() if k in fields},
            "rubric_version":student["version"],"disclaimer":student["disclaimer"],"open_response":opened,
            "grade_equivalences":[],"full_exam_blueprint_verified":False}

def check(request):
    if request.action == "hint" and request.mode == "check":
        raise PermissionError("Check mode withholds hints until an answer is submitted")
    bundle = _bundle(request)
    if "student_paper" not in bundle:
        return bundle
    if request.topic in OPEN_TOPICS:
        if request.action == "hint":
            return {"state":"hint_available", "hint":bundle["worked_solutions"]["steps"][0],"answer_exposed":False}
        assessment = assess_open_response(bundle,request.response)
        return {**assessment,"result_state":assessment["state"],"rubric_version":bundle["student_paper"]["version"],
                "answer_exposed":False,"official_score":False}
    item = bundle["student_paper"]["questions"][request.item_index]
    solution = bundle["worked_solutions"]["solutions"][request.item_index]["worked_solution"]
    if request.action == "hint":
        return {"state":"hint_available","hint":solution.split(" For these givens,")[0],"answer_exposed":False}
    if not isinstance(request.response,str) or not request.response.strip():
        raise ValueError("Submit an answer before feedback")
    expected = solve_item(item)
    option = next(o["id"] for o in item["options"] if o["text"] == expected)
    return {"state":"original_practice_feedback", "result_state":"correct" if request.response == option else "incorrect",
            "question_id":item["question_id"],"concept_id":item["concept_id"],"rubric_version":bundle["student_paper"]["version"],
            "answer_text":expected,"worked_solution":solution,"answer_exposed":True,"official_score":False}
