"""Command-line entrypoint used by the existing installed Caplin skill."""
from __future__ import annotations
import argparse
import dataclasses
import importlib.util
import json
import sys
import typing
from pathlib import Path
from tutor_framework.protocol.models import ProtocolModel
from ..cache import atomic_json
from .models import LearningBrief, PackContent
from .document import scan_document, read_dossier
from .intake import questions, confirm_brief
from .export import ExportRuntime, render_review_pages
from .service import build_pack, verify_pack


def read_json(path):
    path=Path(path)
    if path.stat().st_size>8_000_000:
        raise ValueError('input JSON exceeds the supported size')
    return json.loads(path.read_text(encoding='utf-8'))


def model_schema(model):
    def schema(annotation):
        origin=typing.get_origin(annotation);args=typing.get_args(annotation)
        if origin in (tuple,list):
            return {'type':'array','items':schema(args[0]) if args else {}}
        if isinstance(annotation,type) and issubclass(annotation,ProtocolModel):
            return model_schema(annotation)
        return {'type':{str:'string',int:'integer',float:'number',bool:'boolean'}.get(annotation,'string')}
    fields=dataclasses.fields(model);hints=typing.get_type_hints(model)
    properties={field.name:schema(hints[field.name]) for field in fields}
    properties['schema_version']={'const':model.SCHEMA_VERSION}
    required=['schema_version']+[field.name for field in fields if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING]
    return {'type':'object','additionalProperties':False,'required':required,'properties':properties}


def parser():
    p=argparse.ArgumentParser(prog='caplin-learning-pack',description='Source-grounded notes and study materials. Ask learning intent before building.')
    commands=p.add_subparsers(dest='command',required=True)
    doctor=commands.add_parser('doctor');doctor.add_argument('--runtime')
    schema=commands.add_parser('schema');schema.add_argument('--output')
    intake=commands.add_parser('intake');intake.add_argument('source');intake.add_argument('--output',required=True)
    intake.add_argument('--score-pages',default='');intake.add_argument('--language',default='en',choices=['en','zh-Hant','bilingual']);intake.add_argument('--known')
    brief=commands.add_parser('brief');brief.add_argument('dossier');brief.add_argument('--answers',required=True);brief.add_argument('--output',required=True)
    build=commands.add_parser('build');build.add_argument('dossier');build.add_argument('--brief',required=True);build.add_argument('--content',required=True);build.add_argument('--output',required=True)
    build.add_argument('--runtime');build.add_argument('--no-pdf',action='store_true');build.add_argument('--allow-source-root',action='append',default=[])
    verify=commands.add_parser('verify');verify.add_argument('directory')
    preview=commands.add_parser('review-pages');preview.add_argument('pdf');preview.add_argument('--output',required=True)
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=='doctor':
            pdf=importlib.util.find_spec('pymupdf') is not None
            browser=None
            if args.runtime:browser=ExportRuntime.from_file(args.runtime).identity()
            result={'capabilities':['intake','learning_brief','notes','annotated_score','quiz','flashcards','listening_guide','essay_outline','cheat_sheet','mindmap'],
                    'pymupdf_available':pdf,'pdf_browser_configured':browser is not None,
                    'new_video_renderer':False,'video_workflow':'Existing whiteboard/Mochi workflow; selected existing video can be reused with provenance.',
                    'external_calls':False,'python':sys.version.split()[0]}
        elif args.command=='schema':
            result={'LearningBrief':model_schema(LearningBrief),'PackContent':model_schema(PackContent),
                    'note':'Structural schemas; runtime additionally validates provenance, source bounds, coverage and answer policy.'}
            if args.output:atomic_json(Path(args.output),result)
        elif args.command=='intake':
            pages=tuple(int(x.strip()) for x in args.score_pages.split(',') if x.strip())
            dossier=scan_document(args.source,args.output,score_pages=pages)
            intake=questions(dossier,read_json(args.known) if args.known else {},args.language)
            target=Path(dossier['dossier_path']).parent/'intake-questions.json';atomic_json(target,intake)
            result={'dossier':dossier['dossier_path'],'intake':intake,'questions_path':str(target)}
        elif args.command=='brief':
            dossier=read_dossier(args.dossier);brief=confirm_brief(dossier,read_json(args.answers))
            atomic_json(Path(args.output),brief.to_dict());result={'brief':str(Path(args.output).resolve()),'learning_brief':brief.to_dict()}
        elif args.command=='build':
            result=build_pack(read_dossier(args.dossier),LearningBrief.from_dict(read_json(args.brief)),
                              PackContent.from_dict(read_json(args.content)),args.output,
                              runtime=ExportRuntime.from_file(args.runtime) if args.runtime else None,
                              pdf=not args.no_pdf,allow_source_roots=tuple(Path(p) for p in args.allow_source_root))
        elif args.command=='verify':
            result=verify_pack(args.directory)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result['artifact_integrity']=='passed' else 2
        else:
            result={'review_images':render_review_pages(Path(args.pdf),Path(args.output))}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,TypeError,OSError,KeyError,RuntimeError) as error:
        print(json.dumps({'state':'blocked','error':str(error)},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
