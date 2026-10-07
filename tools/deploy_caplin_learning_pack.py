#!/usr/bin/env python3
"""Deploy a narrow overlay into an EXISTING Caplin skill, with backup and rollback.

Private knowledge files are neither copied into the repository nor replaced.
This tool does not install dependencies, push code, or enable external services.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

VERSION = '3.4.0'
GATE = ('> Learning Pack selection gate: run this video workflow only when the confirmed '
        'LearningBrief includes video. It does not override guided answer policy. '
        'The Learning Pack audit/export entrypoint is not a new video renderer.\n\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data); file.flush(); os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def patch_skill(text, section, repository):
    if not re.search(r'^name:\s*caplin-form-tutor\s*$', text, re.M):
        raise ValueError('target is not the existing caplin-form-tutor skill')
    match = re.search(r'version:\s*"([0-9.]+)"', text)
    if not match or match.group(1) not in {'3.3.0', VERSION}:
        raise ValueError('unexpected installed version; reconcile it before updating')
    text = text[:match.start(1)] + VERSION + text[match.end(1):]
    begin = next((text.find(marker) for marker in ('## Learning Pack and goal setup', '## Final teaching-video step') if marker in text), -1)
    end = text.find('## Learn mode', begin)
    if begin < 0 or end < 0:
        raise ValueError('existing learning/video routing markers are missing; no blind rewrite')
    text = text[:begin] + section.replace('{{REPOSITORY}}', str(repository)).rstrip() + '\n\n' + text[end:]
    old = 'Finish score updates, essays, tests, assignments, and uploaded handouts with Mochi\'s narrated, captioned whiteboard lesson, whole-score context, verified playback, original musical examples, and a full-performance finale when studying a piece.'
    new = 'Create goal-driven Learning Packs from assignments and handouts: ask learning intent, then generate source-cited notes, faithful score annotations and selected study aids, with Mochi whiteboard video only when requested.'
    return text.replace(old, new)


def deploy_installation(repository, skill_root, python, export_runtime, backup_root, *, dry_run=False):
    repository=Path(repository).expanduser().resolve(strict=True)
    skill_root=Path(skill_root).expanduser().resolve()
    python=Path(python).expanduser().resolve(strict=True)
    export_runtime=Path(export_runtime).expanduser().resolve(strict=True) if export_runtime else None
    backup_root=Path(backup_root).expanduser().resolve()
    if not (skill_root/'SKILL.md').is_file():
        raise ValueError('an existing Caplin skill is required; do not create a second skill')
    if not (repository/'src/tutor_framework/domains/music/lesson/learning_pack/__main__.py').is_file():
        raise ValueError('authoritative Learning Pack code is missing')
    bundle=repository/'integrations/caplin-learning-pack'
    if not bundle.is_dir(): raise ValueError('reviewed integration bundle is missing')
    if skill_root in backup_root.parents or backup_root == skill_root:
        raise ValueError('backups must be outside the live skill directory')
    if export_runtime:
        config=json.loads(export_runtime.read_text())
        if set(config) != {'node','playwright','chromium'}:
            raise ValueError('unexpected PDF runtime configuration')
        for value in config.values():
            if not Path(value).expanduser().exists(): raise ValueError('PDF runtime path is missing')
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=repository,capture_output=True,text=True,check=True).stdout.strip()
    changes={}
    for folder in ('scripts','references','tests'):
        source=bundle/folder
        if not source.exists(): continue
        for file in source.rglob('*'):
            if file.is_file() and not file.is_symlink() and '__pycache__' not in file.parts:
                relative=file.relative_to(bundle)
                if file.suffix not in {'.py','.md','.json','.txt'}:
                    raise ValueError('unexpected executable/binary in skill integration bundle')
                changes[str(relative)]=file.read_bytes()
    current=(skill_root/'SKILL.md').read_text()
    changes['SKILL.md']=patch_skill(current,(bundle/'skill-section.md').read_text(),repository).encode()
    workflow=skill_root/'references/teaching-video-workflow.md'
    if not workflow.is_file(): raise ValueError('existing video workflow reference is missing')
    workflow_text=workflow.read_text()
    if 'Learning Pack selection gate:' not in workflow_text:
        workflow_text=GATE+workflow_text
    changes['references/teaching-video-workflow.md']=workflow_text.encode()
    # Update version assertions without dropping their behavioral tests.
    for filename in ('test_audio_score_listener_contract.py','test_video_compiler_contract.py'):
        path=skill_root/'tests'/filename
        if path.is_file():
            text=path.read_text().replace('version: "3.3.0"','version: "3.4.0"').replace('version_is_3_3','version_is_3_4')
            changes['tests/'+filename]=text.encode()
    config={'repository':str(repository),'python':str(python),'export_runtime':str(export_runtime) if export_runtime else None,'release_commit':commit}
    changes['learning-pack-runtime.json']=(json.dumps(config,indent=2)+'\n').encode()
    before={name:digest((skill_root/name).read_bytes()) if (skill_root/name).is_file() else None for name in changes}
    if dry_run:
        return {'state':'dry_run','version':VERSION,'files':sorted(changes),'release_commit':commit}
    backup=backup_root/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    backup.mkdir(parents=True,exist_ok=False)
    entries={}
    for name,data in changes.items():
        target=skill_root/name
        if target.exists() and (target.is_symlink() or not target.is_file()):
            raise ValueError('refusing to replace a symlink or non-file in the skill')
        if target.is_file(): atomic_write(backup/'files'/name,target.read_bytes())
        entries[name]={'before':before[name],'after':digest(data),'existed':before[name] is not None}
    receipt={'skill_root':str(skill_root),'repository':str(repository),'release_commit':commit,'version':VERSION,'files':entries,'state':'prepared'}
    atomic_write(backup/'receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
    written=[]
    try:
        for name,data in changes.items():
            target=skill_root/name
            now=digest(target.read_bytes()) if target.is_file() else None
            if now!=before[name]: raise RuntimeError('skill changed concurrently: '+name)
            atomic_write(target,data);written.append(name)
        mismatch=[name for name,data in changes.items() if digest((skill_root/name).read_bytes())!=digest(data)]
        if mismatch: raise RuntimeError('deployment verification failed: '+', '.join(mismatch))
    except Exception:
        for name in reversed(written):
            target=skill_root/name
            if before[name] is None: target.unlink()
            else: atomic_write(target,(backup/'files'/name).read_bytes())
        raise
    receipt['state']='deployed';atomic_write(backup/'receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
    return {'state':'deployed','version':VERSION,'release_commit':commit,'backup':str(backup),
            'files':sorted(changes),'verification':{'mismatched':mismatch,'checked_files':len(changes)}}


def rollback_installation(backup):
    backup=Path(backup).resolve(strict=True);receipt=json.loads((backup/'receipt.json').read_text())
    skill=Path(receipt['skill_root']).resolve()
    for name,info in receipt['files'].items():
        path=(skill/name).resolve()
        if skill not in path.parents: raise ValueError('unsafe rollback path')
        if not path.is_file() or digest(path.read_bytes())!=info['after']:
            raise ValueError('live file changed since deployment; do not overwrite it in rollback')
    for name,info in receipt['files'].items():
        target=skill/name
        if info['existed']:
            original=(backup/'files'/name).read_bytes()
            if digest(original)!=info['before']: raise ValueError('backup content hash mismatch')
            atomic_write(target,original)
        else: target.unlink()
    receipt['state']='rolled_back';atomic_write(backup/'receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
    return {'state':'rolled_back'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--skill-root',type=Path,required=True)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--export-runtime',type=Path)
    parser.add_argument('--backup-root',type=Path,required=True)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    result=deploy_installation(args.repo,args.skill_root,args.python,args.export_runtime,args.backup_root,dry_run=args.dry_run)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
