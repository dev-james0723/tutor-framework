"""Atomic content-addressed local build artifacts with output verification."""
from __future__ import annotations
import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def file_hash(path: Path | str) -> str:
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def content_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:
            json.dump(value,out,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False);out.write('\n');out.flush();os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


@dataclass(frozen=True)
class BuildResult:
    key: str
    directory: Path
    reused: bool
    hashes: dict[str,str]


class BuildCache:
    def __init__(self,root: Path | str):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.events=[]

    def build(self,kind: str,params: dict,inputs: dict[str,Path],outputs: tuple[str,...],producer: Callable[[Path],None]) -> BuildResult:
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',kind):raise ValueError('invalid build stage')
        if not outputs or len(set(outputs))!=len(outputs):raise ValueError('unique expected outputs are required')
        for name in outputs:
            p=Path(name)
            if p.is_absolute() or '..' in p.parts or name=='receipt.json':raise ValueError('unsafe cache output path')
        input_hashes={name:file_hash(path) for name,path in inputs.items()}
        spec={'cache_schema':1,'stage':kind,'params':params,'inputs':input_hashes,'outputs':outputs}
        key=content_hash(spec);dest=self.root/key
        with (self.root/'.build.lock').open('a+') as lock:
            deadline=time.monotonic()+60
            while True:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>deadline:raise TimeoutError('another local build holds the cache lock')
                    time.sleep(.1)
            valid=False
            if dest.is_dir():
                try:
                    receipt=json.loads((dest/'receipt.json').read_text())
                    valid=receipt['key']==key and content_hash(receipt['spec'])==key and all(
                        (dest/n).is_file() and not (dest/n).is_symlink() and file_hash(dest/n)==receipt['hashes'][n] for n in outputs)
                except (OSError,ValueError,KeyError,TypeError):valid=False
            if valid:
                result=BuildResult(key,dest,True,receipt['hashes']);self.events.append({'stage':kind,'key':key,'reused':True});return result
            work=Path(tempfile.mkdtemp(prefix='.staging-',dir=self.root))
            try:
                producer(work)
                if {name:file_hash(path) for name,path in inputs.items()}!=input_hashes:
                    raise RuntimeError('source changed during build; discard result and rerun')
                for name in outputs:
                    p=work/name
                    if not p.is_file() or p.is_symlink() or work not in p.resolve().parents:
                        raise ValueError(f'producer did not create safe expected output {name}')
                hashes={n:file_hash(work/n) for n in outputs}
                atomic_json(work/'receipt.json',{'key':key,'spec':spec,'hashes':hashes})
                if dest.exists():
                    # These are only our disposable cache entries; preserve a
                    # compact corruption record, never delete user input assets.
                    atomic_json(self.root/(key+'.invalid.json'),{'key':key,'reason':'output/receipt validation failed'})
                    shutil.rmtree(dest)
                os.replace(work,dest)
                result=BuildResult(key,dest,False,hashes);self.events.append({'stage':kind,'key':key,'reused':False});return result
            finally:
                if work.exists():shutil.rmtree(work)
